"""Users, watchlists, snapshots, demo clock — repository behaviour + persistence."""
from __future__ import annotations

import pytest

from app.repositories.snapshots import DemoClockRepository, VisitSnapshotRepository
from app.repositories.users import UserRepository, normalize_email
from app.repositories.watchlists import WatchlistRepository

pytestmark = pytest.mark.asyncio


async def test_demo_user_create_and_retrieve(repos, unique_email):
    users = UserRepository()
    u1, created1 = await users.get_or_create("Ada", unique_email)
    assert created1 is True
    u2, created2 = await users.get_or_create("Ada Lovelace", unique_email.upper())
    assert created2 is False
    assert u1["_id"] == u2["_id"]  # case-insensitive email match
    assert u2["name"] == "Ada Lovelace"


async def test_unique_email_index_enforced(repos, unique_email):
    coll = repos.db["users"]
    await coll.insert_one({"email_normalized": normalize_email(unique_email), "name": "A"})
    from app.db.memory import DuplicateKeyError

    with pytest.raises(DuplicateKeyError):
        await coll.insert_one({"email_normalized": normalize_email(unique_email), "name": "B"})


async def test_watchlist_crud(repos, unique_email):
    users = UserRepository()
    u, _ = await users.get_or_create("Sam", unique_email)
    wr = WatchlistRepository()

    wl = await wr.create(u["_id"], "Core", ["RELIANCE", "reliance", "TCS"])
    assert wl["symbols"] == ["RELIANCE", "TCS"]  # deduped + uppercased

    renamed = await wr.rename(u["_id"], wl["_id"], "Core Holdings")
    assert renamed["name"] == "Core Holdings"

    await wr.add_symbol(u["_id"], wl["_id"], "infy")
    got = await wr.get_for_user(u["_id"], wl["_id"])
    assert "INFY" in got["symbols"]

    await wr.remove_symbol(u["_id"], wl["_id"], "TCS")
    got = await wr.get_for_user(u["_id"], wl["_id"])
    assert "TCS" not in got["symbols"]

    assert await wr.delete_for_user(u["_id"], wl["_id"]) is True
    assert await wr.get_for_user(u["_id"], wl["_id"]) is None


async def test_watchlist_isolation_between_users(repos):
    users = UserRepository()
    a, _ = await users.get_or_create("A", "a@x.com")
    b, _ = await users.get_or_create("B", "b@x.com")
    wr = WatchlistRepository()
    wl = await wr.create(a["_id"], "A list", ["TCS"])
    assert await wr.get_for_user(b["_id"], wl["_id"]) is None


async def test_snapshot_persists_and_is_latest(repos):
    users = UserRepository()
    u, _ = await users.get_or_create("Snap", "snap@x.com")
    wr = WatchlistRepository()
    wl = await wr.create(u["_id"], "L", ["TCS"])
    snaps = VisitSnapshotRepository()

    await snaps.acknowledge(
        user_id=u["_id"], watchlist_id=wl["_id"], dataset_timestamp="2025-07-01T09:15:00",
        stock_states=[{"symbol": "TCS", "price": 100, "attention_score": 10}],
        seen_case_ids=["CASE-A"], attention_threshold=55, daily_attention_budget="top_3",
    )
    await snaps.acknowledge(
        user_id=u["_id"], watchlist_id=wl["_id"], dataset_timestamp="2025-07-04T15:15:00",
        stock_states=[{"symbol": "TCS", "price": 110, "attention_score": 40}],
        seen_case_ids=["CASE-A", "CASE-B"], attention_threshold=55, daily_attention_budget="top_3",
    )
    latest = await snaps.latest(u["_id"], wl["_id"])
    assert latest["stock_states"][0]["price"] == 110
    assert set(latest["seen_case_ids"]) == {"CASE-A", "CASE-B"}


async def test_demo_clock_unique_per_user(repos):
    clock = DemoClockRepository()
    d1 = await clock.set("user-1", "2025-07-04T15:15:00")
    d2 = await clock.set("user-1", "2025-07-08T09:15:00")
    assert d1["_id"] == d2["_id"]
    rows = await repos.db["demo_clock"].find({"user_id": "user-1"}).to_list(None)
    assert len(rows) == 1
