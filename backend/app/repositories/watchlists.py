from __future__ import annotations

from app.repositories.base import BaseRepository, new_id, utcnow


class WatchlistRepository(BaseRepository):
    collection_name = "watchlists"

    async def create(self, user_id: str, name: str, symbols: list[str],
                     attention_threshold: int = 55,
                     daily_attention_budget: str = "top_3") -> dict:
        doc = {
            "_id": new_id(),
            "user_id": user_id,
            "name": name.strip(),
            "symbols": _dedupe_upper(symbols),
            "attention_threshold": int(attention_threshold),
            "daily_attention_budget": daily_attention_budget,
            "created_at": utcnow(),
            "updated_at": utcnow(),
        }
        await self.insert(doc)
        return doc

    async def list_for_user(self, user_id: str) -> list[dict]:
        return await self.find({"user_id": user_id}, sort=[("created_at", 1)])

    async def get_for_user(self, user_id: str, watchlist_id: str) -> dict | None:
        return await self.find_one({"_id": watchlist_id, "user_id": user_id})

    async def rename(self, user_id: str, watchlist_id: str, name: str) -> dict | None:
        wl = await self.get_for_user(user_id, watchlist_id)
        if not wl:
            return None
        await self.update({"_id": watchlist_id}, {"name": name.strip(), "updated_at": utcnow()})
        wl["name"] = name.strip()
        return wl

    async def delete_for_user(self, user_id: str, watchlist_id: str) -> bool:
        removed = await self.delete({"_id": watchlist_id, "user_id": user_id})
        return removed > 0

    async def set_symbols(self, watchlist_id: str, symbols: list[str]) -> None:
        await self.update({"_id": watchlist_id},
                          {"symbols": _dedupe_upper(symbols), "updated_at": utcnow()})

    async def add_symbol(self, user_id: str, watchlist_id: str, symbol: str) -> dict | None:
        wl = await self.get_for_user(user_id, watchlist_id)
        if not wl:
            return None
        symbols = _dedupe_upper([*wl.get("symbols", []), symbol])
        await self.set_symbols(watchlist_id, symbols)
        wl["symbols"] = symbols
        return wl

    async def remove_symbol(self, user_id: str, watchlist_id: str, symbol: str) -> dict | None:
        wl = await self.get_for_user(user_id, watchlist_id)
        if not wl:
            return None
        symbols = [s for s in wl.get("symbols", []) if s.upper() != symbol.upper()]
        await self.set_symbols(watchlist_id, symbols)
        wl["symbols"] = symbols
        return wl

    async def update_settings(self, user_id: str, watchlist_id: str, *,
                              attention_threshold: int | None = None,
                              daily_attention_budget: str | None = None) -> dict | None:
        wl = await self.get_for_user(user_id, watchlist_id)
        if not wl:
            return None
        changes: dict = {"updated_at": utcnow()}
        if attention_threshold is not None:
            changes["attention_threshold"] = int(attention_threshold)
        if daily_attention_budget is not None:
            changes["daily_attention_budget"] = daily_attention_budget
        await self.update({"_id": watchlist_id}, changes)
        wl.update(changes)
        return wl

    async def count_for_user(self, user_id: str) -> int:
        return await self.count({"user_id": user_id})


def _dedupe_upper(symbols: list[str]) -> list[str]:
    seen: list[str] = []
    for s in symbols:
        u = s.strip().upper()
        if u and u not in seen:
            seen.append(u)
    return seen
