# Model Card — CADENCE Detective Mode analysis engine

## Overview

Detective Mode's "engine" is a pipeline of **small, local, deterministic**
models that turn a price/volume/news dataset into ranked, explained Investigation
Cases. There is **no LLM** and **no external service** anywhere in this pipeline.
(CADENCE's separate Live Markets feature does call an external API — Twelve
Data — for real quotes, but it never touches this engine: no Attention Score,
no anomaly detection, no verdict is computed for live-searched symbols.)

| Stage | Method | Role |
| --- | --- | --- |
| Feature engineering | trailing rolling statistics (robust) | inputs to everything downstream |
| Statistical anomaly | z-scores, ratios, regime comparison | **primary** anomaly signal |
| Multivariate anomaly | Isolation Forest (scikit-learn) | **supporting** signal only |
| News sentiment | TF-IDF + Logistic Regression | classify headline tone |
| News event type | keyword rules | tag headlines |
| Attention Score | additive weighted components | rank + surface cases |
| Verdict | deterministic decision tree | one label per case |
| Explanation | string templates | plain-language write-up |

## 1. Feature engineering (`app/ml/features.py`)

For every `(symbol, hourly bar)`, using **only data at or before that bar**:

| Feature | Definition |
| --- | --- |
| `return_pct`, `return_zscore` | 1-bar return; robust z = `(r − median₂₀) / (1.4826·MAD₂₀)` on the **trailing** window (`.shift(1)`), clipped to ±10 |
| `ret_cum_short`, `ret_cum_zscore` | 7-bar cumulative return; z = `cum / (robustσ · √7)` |
| `ret_cum_20` | 20-bar cumulative return |
| `volume_ratio`, `volume_zscore` | volume ÷ trailing median; robust z |
| `volatility_fast/slow`, `volatility_ratio` | rolling std of returns (10 / 40 bars); `fast/slow` |
| `vol_regime_strength` | count of trailing-10 bars with `|z| > 1.5` |
| `dist_from_ma` | close ÷ 20-bar MA − 1 |
| `drawdown` | close ÷ trailing-20 max − 1 |
| `breakout_strength`, `breakdown_strength` | `(close − priorHigh) / ATR`, `(priorLow − close) / ATR` |
| `market_return`, `market_adjusted_return`, `market_adj_cum` | vs NIFTYMD; **rolling beta** over 60 bars (shifted) |
| `sector_return`, `sector_adjusted_return`, `sector_adj_cum` | vs a **leave-one-out** mean of the sector's other members |
| `news_count`, `news_count_change`, `news_sentiment`, `news_sentiment_shift` | trailing-window local-news activity + tone |
| `history_bars`, `is_missing`, `freshness_status` | data-quality context |

**Why robust (median/MAD) z-scores?** A single very large move inflates a
mean/std baseline and makes itself — and the bars around it — look *less*
unusual. Median/MAD is insensitive to those outliers, so a real spike keeps a
large z-score across the whole episode.

**No future leakage.** All `.rolling()` calls are trailing; baselines use
`.shift(1)` so the current bar is not in its own reference window. Verified by
`tests/test_scoring_and_anomaly.py::test_no_future_data_leak_in_features`, which
recomputes features on a truncated copy of the series and asserts they match.

## 2. Statistical anomaly detection

The **primary** signal. Component sub-scores (below) are transparent functions of
the features above. If this and the Isolation Forest disagree, the statistical
layer wins and the disagreement is recorded as lower signal agreement.

## 3. Isolation Forest (`app/ml/anomaly.py`)

- **Features (6, RobustScaler-standardised):** `return_zscore`, `volume_zscore`,
  `volatility_ratio`, `sector_adjusted_return`, `market_adjusted_return`,
  `dist_from_ma`.
- **Params:** `n_estimators=200`, `contamination=0.03`, `random_state=42`.
- **Training data:** all ~15 000 `(symbol, bar)` rows of the synthetic history
  at once. This is *not* how you would train in production (you'd use a rolling
  window and never see the future) — acceptable for a prototype that only needs a
  corroborating signal.
- **Output:** `iso_forest_score ∈ [0, 1]` (percentile-normalised). It contributes
  **only** to *signal agreement* (fires at ≥ 0.7). If fewer than
  `min_training_rows` (400) usable rows exist, it is skipped and confidence is
  reduced by 8.

## 4. News sentiment (`app/ml/sentiment.py`)

- **Pipeline:** `TfidfVectorizer(ngram_range=(1,2), min_df=2, max_features=5000)`
  → `LogisticRegression(C=4, class_weight="balanced", random_state=42)`.
- **Training data:** the bundled `data/generated/news_training.csv` (~600 rows) —
  the generated headlines plus balanced templated examples, each labelled
  positive / neutral / negative by the template that produced it.
- **At runtime:** `predict_proba` → `score = P(pos) − P(neg)`, blended 75/25 with
  a keyword-rule score so obvious words are never mis-labelled; `|score| < 0.12`
  ⇒ neutral. Trains once at process start (< 1 s). Falls back to pure rules if
  the CSV is missing.
- **Limitation:** because training labels are template-derived, the classifier
  mostly learns the templates. This is fine for the prototype; a real deployment
  would need human-labelled financial headlines.

## 5. Event-type classification

Ordered keyword rules → one of: `earnings, acquisition, regulation, leadership,
product_launch, legal_issue, analyst_action, financing, operational, market,
other`. Fully inspectable in `EVENT_RULES`.

## 6. Attention Score (`app/ml/scoring.py`, `scoring_weights.json`)

Additive. Each component uses a **convex saturating ramp**
`max_points · ((x − onset)/(saturation − onset))^exponent` (exponent ≈ 1.1, so
small exceedances stay cheap and only genuine extremes approach the cap).

| Component | Max | Input |
| --- | --- | --- |
| Price surprise | 20 | `max(f(|return_zscore|), f(|ret_cum_zscore|))` |
| Volume anomaly | 15 | `volume_ratio` |
| Sector divergence | 15 | `|sector_adj_cum|` |
| Market divergence | 10 | `|market_adj_cum|` |
| Volatility-regime | 15 | `max(f(volatility_ratio), f(vol_regime_strength))` |
| News relevance & sentiment shift | 15 | `0.6·|shift| + 0.3·min(1, |Δcount|/2) + 0.3·relevance` |
| Signal agreement | 10 | `(n_axes − 1) · per_signal` |

`score = clip(Σ, 0, 100)`. **Confidence** starts at 100 and is *reduced* by data
problems (stale −25, missing −40, conflicting −15, delayed −10, short history
−20, thin news −5, iso-forest untrained −8), clamped to `[20, 100]`. **Data
quality never changes the score.**

Severity bands (config): critical ≥ 78, high ≥ 60, moderate ≥ 44, low ≥ 28,
else minimal.

## 7. Verdict decision tree (`app/ml/verdict.py`)

Deterministic; the order of checks **is** the priority:

1. **Insufficient data** — missing / short history / stale-and-quiet.
2. **Conflicting evidence** — significant move + related news whose sentiment
   *opposes* the price direction.
3. **Market-wide movement** — `|Δindex| ≥ 2.8 %`, `|market-adjusted| ≤ 2.2 %`,
   same direction.
4. **Sector-driven movement** — `|Δsector| ≥ 2.2 %`, `|sector-adjusted| ≤ 2.2 %`,
   sector moved more than the market.
5. **News-supported movement** — significant move + prior material news, matching
   direction.
6. **Price activity before recorded news** — significant move, *no* material news
   before, first **material** related headline within 2 sessions afterwards.
7. **Volatility-regime change** — sustained choppiness, ~zero net move at 7- and
   20-bar horizons.
8. **Unusual price and volume activity** — strong move + abnormal volume + sector
   divergence, not a market/sector move.
9. **Possible breakout / breakdown** — range break in ATR units, same direction.
10. **Headline noise** — related news but only a muted price response.
11. **Conflicting evidence** — the Evidence Court is split with no majority.
12. **Unusual price activity** — a strong lone move.
13. **Normal movement** — nothing crossed a threshold.

### "Material" news

Only the curated `research_primary` feed counts as *material* for checks 5/6.
The synthetic `local_wire` feed is treated as unverified background chatter, so
ordinary noise cannot mask (or fake) a price-before-news sequence. This is a
**modelling choice** for the prototype; a real system would weight source
credibility rather than treat it as binary.

### Responsible wording

The pre-news verdict is always phrased as *"unexplained activity occurred before
the first related headline **in this dataset** — a sequence worth investigating,
not proof of anything."* The engine never asserts insider trading or misconduct.

## 8. Evidence Court (`app/ml/detectives.py`)

Four detectives, each returning `{finding, evidence[], confidence, status}` where
status ∈ `supports / opposes ("explains it") / inconclusive` **relative to the
hypothesis "this is a noteworthy, stock-specific event worth attention"**:

- **Stock Detective** — is the move unusual for *this* stock? (z-scores, MA
  distance, drawdown, breakout).
- **Volume Detective** — is participation abnormal? (volume ratio / z).
- **Sector Detective** — did the whole sector move? ("opposes" if yes — that
  *explains it away*).
- **News Detective** — can recorded local news explain it? ("opposes" if timely
  matching news; "supports" if the move preceded the news or none exists).

## 9. Determinism & reproducibility

Fixed seeds throughout (`42`). `tests/test_scoring_and_anomaly.py::
test_scores_deterministic` builds the engine twice and asserts identical scores.
`tests/test_dataset_and_quality.py::test_generator_is_deterministic` asserts the
dataset is byte-identical across runs.

## 10. Known limitations (summary)

- Synthetic data; the classifier learns templates; Isolation Forest sees the
  whole history; no holiday calendar; source-credibility is binary; the verdict
  thresholds were hand-tuned against the scenario manifest and would need
  re-tuning on real data.
