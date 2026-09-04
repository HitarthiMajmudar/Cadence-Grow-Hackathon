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
from app.repositories.snapshots import DemoClockRepository, VisitSnapshotRepository
from app.repositories.users import UserRepository
from app.repositories.watchlists import WatchlistRepository
from app.services.analysis_engine import AnalysisEngine

logger = logging.getLogger("market_detective.seed")

SEEDED_ACCOUNTS = [
    ("Demo Detective", "detective@marketdetective.app",
     ["RELIANCE", "TCS", "HDFCBANK", "TATAMOTORS", "INFY", "ITC", "ICICIBANK", "SBIN"]),
    ("Ridhi (Swing Trader)", "ridhi@marketdetective.app",
     ["TATAMOTORS", "MARUTI", "M&M", "RELIANCE", "SBIN"]),
    ("Arjun (Long-term)", "arjun@marketdetective.app",
     ["HDFCBANK", "ICICIBANK", "TCS", "INFY", "HINDUNILVR", "NESTLEIND"]),
]

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


async def seed_demo_accounts(engine: AnalysisEngine) -> int:
    """Idempotently create the seeded demo users, their watchlists, a baseline
    snapshot and their demo clock."""
    users = UserRepository()
    watchlists = WatchlistRepository()
    clock = DemoClockRepository()
    snapshots = VisitSnapshotRepository()
    cases_repo = CaseRepository()
    present = pd.Timestamp(engine.meta["demo_present_timestamp"])
    present_dt = present.to_pydatetime()

    created = 0
    for name, email, symbols in SEEDED_ACCOUNTS:
        user, _ = await users.get_or_create(name, email, is_seeded=True)
        if await watchlists.list_for_user(user["_id"]):
            await clock.ensure(user["_id"], present_dt)
            continue
        wl = await watchlists.create(user["_id"], "My Watchlist", symbols,
                                     attention_threshold=55, daily_attention_budget="top_3")
        await users.update_preferences(user["_id"], {"default_watchlist_id": wl["_id"]})
        states = []
        for sym in symbols:
            s = engine.state_at(sym, present)
            states.append({"symbol": sym, "price": s["price"],
                           "attention_score": s["attention_score"], "severity": s["severity"],
                           "freshness": s["freshness"], "verdict": s["verdict"]})
        base_cases = await cases_repo.list_up_to(present_dt, symbols=symbols)
        await snapshots.acknowledge(
            user_id=user["_id"], watchlist_id=wl["_id"], dataset_timestamp=present_dt,
            stock_states=states, seen_case_ids=[c["case_id"] for c in base_cases],
            attention_threshold=55, daily_attention_budget="top_3",
        )
        await clock.ensure(user["_id"], present_dt)
        created += 1
    logger.info("seeded %d new demo accounts", created)
    return created


async def auto_seed_if_empty(engine: AnalysisEngine) -> bool:
    """Called from the app lifespan. Seeds only if the cases collection is empty."""
    if await CaseRepository().count() > 0:
        return False
    logger.info("cases collection empty — auto-seeding …")
    await seed_market_data(engine)
    await seed_demo_accounts(engine)
    return True
