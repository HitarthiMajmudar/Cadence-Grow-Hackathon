from __future__ import annotations

from app.repositories.base import BaseRepository, new_id, utcnow

VALID_STATUSES = {"new", "viewed", "saved", "dismissed"}


class CaseRepository(BaseRepository):
    collection_name = "investigation_cases"

    async def upsert_case(self, case: dict) -> None:
        case = dict(case)
        case.setdefault("created_at", utcnow())
        await self.collection.update_one(
            {"case_id": case["case_id"]},
            {"$set": case, "$setOnInsert": {"_id": new_id()}},
            upsert=True,
        )

    async def get_by_case_id(self, case_id: str) -> dict | None:
        return await self.find_one({"case_id": case_id})

    async def list_all(self, *, skip: int = 0, limit: int = 0) -> list[dict]:
        return await self.find({}, sort=[("detection_timestamp", 1)], skip=skip, limit=limit)

    async def list_up_to(self, dataset_ts, *, symbols: list[str] | None = None,
                         skip: int = 0, limit: int = 0) -> list[dict]:
        query: dict = {"detection_timestamp": {"$lte": dataset_ts}}
        if symbols is not None:
            query["symbol"] = {"$in": [s.upper() for s in symbols]}
        return await self.find(query, sort=[("attention_score", -1)], skip=skip, limit=limit)

    async def list_between(self, start, end, symbols: list[str] | None = None) -> list[dict]:
        query: dict = {"detection_timestamp": {"$gt": start, "$lte": end}}
        if symbols is not None:
            query["symbol"] = {"$in": [s.upper() for s in symbols]}
        return await self.find(query, sort=[("detection_timestamp", 1)])

    async def replace_all(self, cases: list[dict]) -> int:
        await self.collection.delete_many({})
        for c in cases:
            c.setdefault("_id", new_id())
            c.setdefault("created_at", utcnow())
        if cases:
            await self.collection.insert_many(cases)
        return len(cases)


class UserCaseStateRepository(BaseRepository):
    collection_name = "user_case_states"

    async def get(self, user_id: str, case_id: str) -> dict | None:
        return await self.find_one({"user_id": user_id, "case_id": case_id})

    async def set_status(self, user_id: str, case_id: str, status: str) -> dict:
        now = utcnow()
        changes = {"status": status, "updated_at": now}
        if status == "viewed":
            changes["viewed_at"] = now
        await self.collection.update_one(
            {"user_id": user_id, "case_id": case_id},
            {"$set": changes,
             "$setOnInsert": {"_id": new_id(), "user_id": user_id,
                              "case_id": case_id, "created_at": now}},
            upsert=True,
        )
        return await self.get(user_id, case_id)  # type: ignore[return-value]

    async def mark_viewed_if_new(self, user_id: str, case_id: str) -> None:
        state = await self.get(user_id, case_id)
        if state is None or state.get("status") == "new":
            await self.set_status(user_id, case_id, "viewed")

    async def states_for_user(self, user_id: str, case_ids: list[str] | None = None) -> dict[str, dict]:
        query: dict = {"user_id": user_id}
        if case_ids is not None:
            query["case_id"] = {"$in": case_ids}
        rows = await self.find(query)
        return {r["case_id"]: r for r in rows}

    async def recently_viewed(self, user_id: str, limit: int = 8) -> list[dict]:
        rows = await self.find({"user_id": user_id, "status": {"$in": ["viewed", "saved"]}})
        rows = [r for r in rows if r.get("viewed_at")]
        rows.sort(key=lambda r: r["viewed_at"], reverse=True)
        return rows[:limit]


class CaseFeedbackRepository(BaseRepository):
    collection_name = "case_feedback"

    async def add(self, user_id: str, case_id: str, feedback: str, note: str | None) -> dict:
        doc = {
            "_id": new_id(),
            "user_id": user_id,
            "case_id": case_id,
            "feedback": feedback,
            "note": note,
            "created_at": utcnow(),
        }
        await self.insert(doc)
        return doc

    async def for_case(self, case_id: str) -> list[dict]:
        return await self.find({"case_id": case_id}, sort=[("created_at", -1)])

    async def summary(self, case_id: str) -> dict:
        rows = await self.for_case(case_id)
        out: dict[str, int] = {}
        for r in rows:
            out[r["feedback"]] = out.get(r["feedback"], 0) + 1
        return out
