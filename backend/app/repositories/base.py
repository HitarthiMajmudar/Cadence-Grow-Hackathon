"""Base repository — thin async wrapper over a Mongo-compatible collection."""
from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from app.db import client as db_client


def new_id() -> str:
    return uuid.uuid4().hex


def utcnow() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


class BaseRepository:
    collection_name: str = ""

    def __init__(self, db: Any | None = None) -> None:
        self._db = db

    @property
    def collection(self):
        db = self._db or db_client.get_db()
        return db[self.collection_name]

    async def insert(self, doc: dict) -> dict:
        doc.setdefault("_id", new_id())
        await self.collection.insert_one(doc)
        return doc

    async def insert_many(self, docs: list[dict]) -> int:
        if not docs:
            return 0
        for d in docs:
            d.setdefault("_id", new_id())
        res = await self.collection.insert_many(docs)
        return len(getattr(res, "inserted_ids", docs))

    async def get(self, _id: str) -> dict | None:
        return await self.collection.find_one({"_id": _id})

    async def find_one(self, query: dict, sort=None) -> dict | None:
        return await self.collection.find_one(query, sort=sort)

    async def find(self, query: dict, *, sort=None, skip: int = 0, limit: int = 0) -> list[dict]:
        cur = self.collection.find(query)
        if sort:
            cur = cur.sort(sort)
        if skip:
            cur = cur.skip(skip)
        if limit:
            cur = cur.limit(limit)
        return await cur.to_list(length=limit or None)

    async def count(self, query: dict | None = None) -> int:
        return await self.collection.count_documents(query or {})

    async def update(self, query: dict, changes: dict, *, upsert: bool = False) -> None:
        await self.collection.update_one(query, {"$set": changes}, upsert=upsert)

    async def upsert(self, query: dict, on_insert: dict, changes: dict) -> None:
        await self.collection.update_one(
            query, {"$set": changes, "$setOnInsert": on_insert}, upsert=True
        )

    async def delete(self, query: dict) -> int:
        res = await self.collection.delete_many(query)
        return getattr(res, "deleted_count", 0)
