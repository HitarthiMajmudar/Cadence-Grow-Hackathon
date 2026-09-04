# Scenario Manifest

The dataset generator deliberately injects 16 situations and records, in
`data/generated/scenario_manifest.json`, the verdict each one *should* receive.

> **The inference engine never reads this file.** Only the test suite loads it
> (`tests/test_scenarios.py`), and `tests/test_dataset_and_quality.py::
> test_manifest_not_referenced_by_engine_module` asserts the engine's source
> contains no reference to it. This document is a human-readable copy for
> reviewers.

## Why inject scenarios?

Real "ground truth" for market anomalies doesn't exist. By constructing the
situations we can (a) tune the engine against known-correct answers and (b) prove
in CI that it still reaches them. Each entry carries a `reason` explaining what
the scenario is meant to exercise.

## The 16 scenarios

| Scenario | Kind | Target | Injected at | Expected verdict | Case? |
| --- | --- | --- | --- | --- | --- |
| `past_market_crash` | market crash | whole market | 2025-02-28 09:15 | **Market-wide movement** | yes |
| `past_stock_spike_tcs` | stock price+volume spike | TCS | 2025-03-26 09:15 | **Unusual price and volume activity** | yes |
| `past_sector_decline_banking` | sector decline | BANKING | 2025-05-07 09:15 | **Sector-driven movement** | yes |
| `past_conflicting_tatamotors` | positive news, negative price | TATAMOTORS | 2025-05-23 09:15 | **Conflicting evidence** | yes |
| `past_pre_news_icicibank` | activity before the headline | ICICIBANK | 2025-06-10 09:15 | **Price activity before recorded news** | yes |
| `future_stock_spike_tatamotors` | stock price+volume spike | TATAMOTORS | 2025-07-08 09:15 | **Unusual price and volume activity** | yes |
| `future_sector_decline_it` | sector decline | IT | 2025-07-11 09:15 | **Sector-driven movement** | yes |
| `future_pre_news_reliance` | activity before the headline | RELIANCE | 2025-07-15 09:15 | **Price activity before recorded news** | yes |
| `future_market_crash` | market crash | whole market | 2025-07-18 09:15 | **Market-wide movement** | yes |
| `future_conflicting_infy` | positive news, negative price | INFY | 2025-07-23 09:15 | **Conflicting evidence** | yes |
| `future_volume_no_price_itc` | volume spike, flat price | ITC | 2025-07-25 09:15 | **Headline noise** | yes |
| `future_volatility_regime_hdfcbank` | volatility-regime change | HDFCBANK | 2025-07-29 09:15 | **Volatility-regime change** | yes |
| `future_missing_data_sbin` | missing data | SBIN | 2025-08-01 09:15 | Insufficient data | **no** |
| `future_stale_data_ongc` | stale feed | ONGC | 2025-08-05 09:15 | Insufficient data | **no** |
| `future_conflicting_source_maruti` | two sources disagree | MARUTI | 2025-08-07 09:15 | Normal movement | **no** |
| `future_normal_nestle_like` | ordinary drift (negative control) | HINDUNILVR | 2025-08-11 09:15 | Normal movement | **no** |

The "past" scenarios are visible the moment the demo opens; the "future" ones are
revealed by **Advance Market Time** / **Replay What I Missed**.

## What each kind exercises

| Kind | The distinction the engine must make |
| --- | --- |
| stock price+volume spike | stock-specific vs. sector/market — `sector_adj_cum` large, `moved_with_*` false |
| sector decline | the whole sector moved together — `sector_adj_cum` ≈ 0, sector moved more than the market |
| market crash | everything moved — `market_adj_cum` ≈ 0, index moved a lot |
| positive news / negative price | news sentiment and price direction **disagree** ⇒ *Conflicting evidence*, not *Unusual activity* |
| activity before the headline | a real move with **no material news before it**, and the first material related headline arriving 1–2 sessions **later** |
| volume spike, flat price | abnormal turnover **without** a price response ⇒ *Headline noise*, low attention |
| volatility-regime change | many big bars, ~zero net move at 7- and 20-bar horizons |
| missing / stale data | reduce **confidence**, don't fabricate, don't spawn a spurious case (incl. the "catch-up" bar when the feed resumes) |
| two sources disagree | keep the conflict, pick the higher-priority value, reduce confidence, **don't** flag a case |
| ordinary drift | a **negative control** — attention must stay below threshold and no case is created |

## Current status

`python -m scripts.diagnose` and `pytest tests/test_scenarios.py`:
**12 / 12 injected verdicts match · 4 / 4 negative controls produce no case.**

The `expected_min_attention` / `expected_max_attention` bounds in the manifest are
loose sanity checks (verified with a ±6 margin); the **verdict match** is the
hard assertion.
