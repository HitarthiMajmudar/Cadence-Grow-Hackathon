"""Users, watchlists, snapshots, demo clock — repository behaviour + persistence."""
from __future__ import annotations

import pytest

from app.core.errors import ConflictError
from app.repositories.snapshots import DemoClockRepository, VisitSnapshotRepository
from app.repositories.users import UserRepository, normalize_email
from app.repositories.watchlists import WatchlistRepository

pytestmark = pytest.mark.asyncio


async def test_user_create_and_retrieve(repos, unique_email):
    users = UserRepository()
    u1 = await users.create("Ada", unique_email, "hashed-pw")
    assert u1["email_normalized"] == normalize_email(unique_email)
    fetched = await users.by_email(unique_email)
    assert fetched["_id"] == u1["_id"]


async def test_duplicate_email_rejected_case_insensitively(repos, unique_email):
    users = UserRepository()
    await users.create("Ada", unique_email, "hashed-pw")
    with pytest.raises(ConflictError):
        await users.create("Ada Lovelace", unique_email.upper(), "hashed-pw")


async def test_unique_email_index_enforced(repos, unique_email):
    coll = repos.db["users"]
    await coll.insert_one({"email_normalized": normalize_email(unique_email), "name": "A"})
    from app.db.memory import DuplicateKeyError

    with pytest.raises(DuplicateKeyError):
        await coll.insert_one({"email_normalized": normalize_email(unique_email), "name": "B"})


async def test_watchlist_crud(repos, unique_email):
    users = UserRepository()
    u = await users.create("Sam", unique_email, "hashed-pw")
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
    a = await users.create("A", "a@x.com", "hashed-pw")
    b = await users.create("B", "b@x.com", "hashed-pw")
    wr = WatchlistRepository()
    wl = await wr.create(a["_id"], "A list", ["TCS"])
    assert await wr.get_for_user(b["_id"], wl["_id"]) is None


async def test_snapshot_persists_and_is_latest(repos):
    users = UserRepository()
    u = await users.create("Snap", "snap@x.com", "hashed-pw")
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
