from __future__ import annotations

from app.repositories.base import BaseRepository, new_id


class MarketObservationRepository(BaseRepository):
    collection_name = "market_observations"

    async def bulk_replace(self, rows: list[dict]) -> int:
        await self.collection.delete_many({})
        # insert in chunks to keep memory / payloads reasonable
        total = 0
        chunk = 2000
        for i in range(0, len(rows), chunk):
            await self.collection.insert_many(rows[i:i + chunk])
            total += len(rows[i:i + chunk])
        return total

    async def history(self, symbol: str, *, start=None, end=None,
                      skip: int = 0, limit: int = 0) -> list[dict]:
        query: dict = {"symbol": symbol.upper()}
        ts: dict = {}
        if start is not None:
            ts["$gte"] = start
        if end is not None:
            ts["$lte"] = end
        if ts:
            query["timestamp"] = ts
        return await self.find(query, sort=[("timestamp", 1)], skip=skip, limit=limit)

    async def latest(self, symbol: str, as_of=None) -> dict | None:
        query: dict = {"symbol": symbol.upper()}
        if as_of is not None:
            query["timestamp"] = {"$lte": as_of}
        return await self.find_one(query, sort=[("timestamp", -1)])

    async def count_for(self, symbol: str) -> int:
        return await self.count({"symbol": symbol.upper()})


class StockFeatureRepository(BaseRepository):
    collection_name = "stock_features"

    async def bulk_replace(self, rows: list[dict]) -> int:
        await self.collection.delete_many({})
        total = 0
        chunk = 2000
        for i in range(0, len(rows), chunk):
            await self.collection.insert_many(rows[i:i + chunk])
            total += len(rows[i:i + chunk])
        return total

    async def at(self, symbol: str, timestamp) -> dict | None:
        return await self.find_one({"symbol": symbol.upper(), "timestamp": {"$lte": timestamp}},
                                   sort=[("timestamp", -1)])

    async def series(self, symbol: str, start, end) -> list[dict]:
        return await self.find(
            {"symbol": symbol.upper(), "timestamp": {"$gte": start, "$lte": end}},
            sort=[("timestamp", 1)],
        )


class NewsRepository(BaseRepository):
    collection_name = "news_events"

    async def bulk_replace(self, rows: list[dict]) -> int:
        await self.collection.delete_many({})
        if rows:
            await self.collection.insert_many(rows)
        return len(rows)

    async def for_symbol(self, symbol: str, *, start=None, end=None) -> list[dict]:
        rows = await self.find({"symbols": symbol.upper()}, sort=[("timestamp", 1)])
        if start is not None:
            rows = [r for r in rows if r["timestamp"] >= start]
        if end is not None:
            rows = [r for r in rows if r["timestamp"] <= end]
        return rows

    async def between(self, start, end) -> list[dict]:
        return await self.find({"timestamp": {"$gte": start, "$lte": end}}, sort=[("timestamp", 1)])


class DataQualityEventRepository(BaseRepository):
    collection_name = "data_quality_events"

    async def bulk_replace(self, rows: list[dict]) -> int:
        await self.collection.delete_many({})
        for r in rows:
            r.setdefault("_id", new_id())
        if rows:
            await self.collection.insert_many(rows)
        return len(rows)

    async def for_symbol(self, symbol: str) -> list[dict]:
        return await self.find({"symbol": symbol.upper()}, sort=[("timestamp", 1)])

    async def all_events(self) -> list[dict]:
        return await self.find({}, sort=[("timestamp", 1)])
