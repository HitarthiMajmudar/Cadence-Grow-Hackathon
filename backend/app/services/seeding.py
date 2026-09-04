"""
Reusable seeding routines shared by scripts/seed.py and the app's optional
auto-seed on startup (so `uvicorn app.main:app` just works).
"""
from __future__ import annotations

import logging

import pandas as pd

from app.data import loader
from app.repositories.cases import CaseRepository
from app.repositories.market import (
    DataQualityEventRepository,
    MarketObservationRepository,
    NewsRepository,
    StockFeatureRepository,
)
from app.services.analysis_engine import AnalysisEngine

logger = logging.getLogger("market_detective.seed")

FEATURE_STORE_COLUMNS = [
    "symbol", "timestamp", "company_name", "sector", "close", "volume",
    "return_pct", "return_zscore", "ret_cum_zscore", "ret_cum_short",
    "volume_ratio", "volume_zscore", "volatility_ratio", "vol_regime_strength",
    "dist_from_ma", "drawdown", "breakout_strength", "breakdown_strength",
    "sector_adjusted_return", "sector_adj_cum", "market_adjusted_return", "market_adj_cum",
    "sector_ret_cum_short", "market_ret_cum_short",
    "news_count", "news_sentiment", "news_sentiment_shift",
    "attention_score", "confidence", "severity", "signal_agreement",
    "freshness_status", "history_bars",
]


def _clean(v):
    if isinstance(v, float) and pd.isna(v):
        return None
    if hasattr(v, "item"):
        return v.item()
    return v


async def seed_market_data(engine: AnalysisEngine) -> dict:
    """Persist observations, features, news, quality events and cases."""
    obs = loader.load_observations()
    obs_rows = []
    for r in obs.to_dict("records"):
        r = dict(r)
        r["symbol"] = str(r["symbol"])
        r["timestamp"] = pd.Timestamp(r["timestamp"]).to_pydatetime()
        for k in ("open", "high", "low", "close"):
            r[k] = None if pd.isna(r[k]) else float(r[k])
        r["volume"] = int(r["volume"]) if not pd.isna(r["volume"]) else 0
        obs_rows.append(r)
    n_obs = await MarketObservationRepository().bulk_replace(obs_rows)

    feats = engine.features.copy()
    feats = feats[[c for c in FEATURE_STORE_COLUMNS if c in feats.columns]].copy()
    feats["timestamp"] = feats["timestamp"].apply(lambda t: pd.Timestamp(t).to_pydatetime())
    feat_rows = [{k: _clean(v) for k, v in r.items()} for r in feats.to_dict("records")]
    n_feat = await StockFeatureRepository().bulk_replace(feat_rows)

    news_rows = [
        {**n, "symbols": [s.upper() for s in n.get("symbols", [])],
         "timestamp": pd.Timestamp(n["timestamp"]).to_pydatetime()}
        for n in engine.news
    ]
    n_news = await NewsRepository().bulk_replace(news_rows)

    dq_rows = [
        {**e, "timestamp": pd.Timestamp(e["timestamp"]).to_pydatetime()}
        for e in loader.load_quality_events()
    ]
    n_dq = await DataQualityEventRepository().bulk_replace(dq_rows)

    cases = engine.generate_cases(force=True)
    n_cases = await CaseRepository().replace_all([dict(c) for c in cases])

    logger.info("seeded market data: %d obs, %d features, %d news, %d dq, %d cases",
                n_obs, n_feat, n_news, n_dq, n_cases)
    return {"observations": n_obs, "features": n_feat, "news": n_news,
            "quality_events": n_dq, "cases": n_cases}


async def auto_seed_if_empty(engine: AnalysisEngine) -> bool:
    """Called from the app lifespan. Seeds only the shared market dataset (no
    accounts — those are created by real signup) if the cases collection is
    empty."""
    if await CaseRepository().count() > 0:
        return False
    logger.info("cases collection empty — auto-seeding …")
    await seed_market_data(engine)
    return True
