"""Since-You-Left comparisons + idempotent seeding."""
from __future__ import annotations

import pandas as pd
import pytest

from app.repositories.cases import CaseRepository
from app.repositories.users import UserRepository
from app.repositories.watchlists import WatchlistRepository
from app.services.briefing import BriefingService
from app.services.demo_clock import DemoClockService
from app.services.seeding import seed_market_data
from app.services.watchlist_service import WatchlistService

pytestmark = pytest.mark.asyncio


async def test_seed_market_data_is_idempotent(repos, engine):
    await seed_market_data(engine)
    obs1 = await repos.db["market_observations"].count_documents({})
    cases1 = await CaseRepository().count()

    await seed_market_data(engine)
    assert await repos.db["market_observations"].count_documents({}) == obs1
    assert await CaseRepository().count() == cases1


async def test_since_you_left_detects_advance(repos, engine):
    await seed_market_data(engine)
    users = UserRepository()
    u = await users.create("Journey", "journey@x.com", "hashed-pw")
    wl = await WatchlistService().ensure_default(u["_id"])

    clock = DemoClockService()
    briefing = BriefingService()

    b0 = await briefing.generate(u["_id"], wl["_id"])
    assert b0["has_previous_snapshot"] is True  # baseline snapshot created
    assert b0["market_hours_away"] == 0

    await clock.advance(u["_id"], 18)
    await clock.advance(u["_id"], 18)
    b1 = await briefing.generate(u["_id"], wl["_id"])

    assert b1["market_hours_away"] == 36
    assert "36 simulated market hours" in b1["summary_line"]
    assert len(b1["changes"]) == len(wl["symbols"])
    classes = {c["classification"] for c in b1["changes"]}
    assert classes & {"important", "investigating", "explained"}


async def test_mark_seen_persists_snapshot(repos, engine):
    await seed_market_data(engine)
    users = UserRepository()
    u = await users.create("Seen", "seen@x.com", "hashed-pw")
    wl = await WatchlistService().ensure_default(u["_id"])
    clock = DemoClockService()
    briefing = BriefingService()

    await clock.advance(u["_id"], 24)
    snap = await briefing.mark_seen(u["_id"], wl["_id"], [])
    assert snap is not None
    ts = pd.Timestamp(snap["dataset_timestamp"])

    # a fresh briefing now compares against this new snapshot
    b = await briefing.generate(u["_id"], wl["_id"])
    assert pd.Timestamp(b["snapshot_dataset_timestamp"]) == ts
    assert b["market_hours_away"] == 0


async def test_classification_covers_all_states(repos, engine):
    """Advancing far enough should surface Important + Explained + Investigating."""
    await seed_market_data(engine)
    users = UserRepository()
    u = await users.create("Wide", "wide@x.com", "hashed-pw")
    # a watchlist that hits several scenarios
    wr = WatchlistRepository()
    wl = await wr.create(u["_id"], "Wide", ["TATAMOTORS", "TCS", "INFY", "RELIANCE", "HDFCBANK", "SBIN"])
    await WatchlistService()._baseline_snapshot(u["_id"], wl)

    clock = DemoClockService()
    for _ in range(4):
        await clock.advance(u["_id"], 18)
    b = await BriefingService().generate(u["_id"], wl["_id"])
    classes = [c["classification"] for c in b["changes"]]
    assert "important" in classes
    assert b["changes_worth_attention"] >= 1
