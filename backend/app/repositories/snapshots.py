from __future__ import annotations

from app.repositories.base import BaseRepository, new_id, utcnow


class VisitSnapshotRepository(BaseRepository):
    collection_name = "visit_snapshots"

    async def latest(self, user_id: str, watchlist_id: str) -> dict | None:
        rows = await self.find(
            {"user_id": user_id, "watchlist_id": watchlist_id},
            sort=[("acknowledged_at", -1)],
            limit=1,
        )
        return rows[0] if rows else None

    async def acknowledge(self, *, user_id: str, watchlist_id: str, dataset_timestamp,
                          stock_states: list[dict], seen_case_ids: list[str],
                          attention_threshold: int, daily_attention_budget: str) -> dict:
        doc = {
            "_id": new_id(),
            "user_id": user_id,
            "watchlist_id": watchlist_id,
            "acknowledged_at": utcnow(),
            "dataset_timestamp": dataset_timestamp,
            "stock_states": stock_states,
            "seen_case_ids": sorted(set(seen_case_ids)),
            "attention_threshold": int(attention_threshold),
            "daily_attention_budget": daily_attention_budget,
        }
        await self.insert(doc)
        return doc

    async def history(self, user_id: str, watchlist_id: str, limit: int = 10) -> list[dict]:
        return await self.find(
            {"user_id": user_id, "watchlist_id": watchlist_id},
            sort=[("acknowledged_at", -1)],
            limit=limit,
        )


class DemoClockRepository(BaseRepository):
    collection_name = "demo_clock"

    async def get(self, user_id: str) -> dict | None:
        return await self.find_one({"user_id": user_id})

    async def set(self, user_id: str, dataset_timestamp) -> dict:
        now = utcnow()
        await self.collection.update_one(
            {"user_id": user_id},
            {"$set": {"current_dataset_timestamp": dataset_timestamp, "updated_at": now},
             "$setOnInsert": {"_id": new_id(), "user_id": user_id}},
            upsert=True,
        )
        return await self.get(user_id)  # type: ignore[return-value]

    async def ensure(self, user_id: str, default_timestamp) -> dict:
        existing = await self.get(user_id)
        if existing:
            return existing
        return await self.set(user_id, default_timestamp)
