"""Attention Score bounds, feature integrity, no future-data leakage."""
from __future__ import annotations

import numpy as np
import pandas as pd

from app.data import loader
from app.ml.features import FeatureEngine
from app.ml.scoring import score_row


def test_attention_score_always_in_range(engine):
    scores = engine.features["attention_score"]
    assert scores.min() >= 0.0
    assert scores.max() <= 100.0
    conf = engine.features["confidence"]
    assert conf.min() >= 20.0 and conf.max() <= 100.0


def test_score_row_on_extreme_inputs():
    row = {
        "return_zscore": 99, "ret_cum_zscore": 99, "ret_cum_short": 5,
        "volume_ratio": 50, "sector_adj_cum": 2, "market_adj_cum": 2,
        "volatility_ratio": 9, "vol_regime_strength": 10,
        "news_sentiment_shift": 5, "news_count_change": 9, "news_relevance": 1,
        "history_bars": 500, "freshness_status": "fresh",
    }
    r = score_row(row)
    assert r.score == 100.0
    assert r.severity == "critical"

    calm = {k: 0 for k in row}
    calm["volume_ratio"] = 1.0
    calm["history_bars"] = 500
    calm["freshness_status"] = "fresh"
    r2 = score_row(calm)
    assert r2.score < 10
    assert r2.severity == "minimal"


def test_data_quality_reduces_confidence_not_score():
    base = {
        "return_zscore": 3.5, "ret_cum_zscore": 4.0, "ret_cum_short": 0.06,
        "volume_ratio": 2.5, "sector_adj_cum": 0.04, "market_adj_cum": 0.03,
        "volatility_ratio": 1.2, "vol_regime_strength": 2,
        "news_sentiment_shift": 0.0, "news_count_change": 0, "news_relevance": 0,
        "history_bars": 500, "freshness_status": "fresh", "is_missing": False,
    }
    fresh = score_row(base)
    stale = score_row({**base, "freshness_status": "stale"})
    missing = score_row({**base, "freshness_status": "missing", "is_missing": True})

    assert stale.score == fresh.score          # score unchanged
    assert stale.confidence < fresh.confidence  # confidence reduced
    assert missing.confidence < stale.confidence
    assert missing.data_quality_warnings


def test_short_history_reduces_confidence():
    row = {
        "return_zscore": 2.0, "ret_cum_zscore": 2.0, "ret_cum_short": 0.02,
        "volume_ratio": 1.5, "sector_adj_cum": 0.01, "market_adj_cum": 0.01,
        "volatility_ratio": 1.1, "vol_regime_strength": 1, "news_sentiment_shift": 0,
        "news_count_change": 0, "news_relevance": 0, "freshness_status": "fresh",
    }
    long_hist = score_row({**row, "history_bars": 500})
    short_hist = score_row({**row, "history_bars": 10})
    assert short_hist.confidence < long_hist.confidence


def test_no_future_data_leak_in_features():
    """Recomputing features on a truncated series must match the full run up to
    the truncation point — proves rolling features are trailing-only."""
    obs = loader.load_observations()
    stocks = loader.load_stocks()
    sectors = loader.load_sectors()
    news = loader.load_news()
    mkt = loader.market_symbol()

    full = FeatureEngine(obs, stocks, sectors, news, mkt).compute_for_symbol("TCS")
    cut_ts = full["timestamp"].iloc[len(full) // 2 + 30]

    truncated_obs = obs[obs["timestamp"] <= cut_ts]
    truncated_news = [n for n in news if pd.Timestamp(n["timestamp"]) <= cut_ts]
    partial = FeatureEngine(truncated_obs, stocks, sectors, truncated_news, mkt).compute_for_symbol("TCS")

    check_cols = ["return_zscore", "volume_ratio", "sector_adj_cum",
                  "market_adj_cum", "volatility_ratio", "ret_cum_zscore"]
    merged = full.merge(partial, on="timestamp", suffixes=("_full", "_part"))
    # ignore the last few bars where the trailing window itself is shorter in the
    # truncated run only because there is no *earlier* data — that's not a leak
    merged = merged[merged["timestamp"] < cut_ts].tail(120)
    for col in check_cols:
        a = merged[f"{col}_full"].to_numpy()
        b = merged[f"{col}_part"].to_numpy()
        mask = ~(np.isnan(a) | np.isnan(b))
        assert np.allclose(a[mask], b[mask], atol=1e-6), f"future leak detected in {col}"


def test_scores_deterministic(engine):
    from app.services.analysis_engine import AnalysisEngine

    e2 = AnalysisEngine()
    pd.testing.assert_series_equal(
        engine.features["attention_score"].reset_index(drop=True),
        e2.features["attention_score"].reset_index(drop=True),
    )
