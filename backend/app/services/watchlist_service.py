"""Enriches watchlists with live per-symbol state at the user's demo-clock time."""
from __future__ import annotations

import pandas as pd

from app.repositories.cases import CaseRepository
from app.repositories.snapshots import VisitSnapshotRepository
from app.repositories.watchlists import WatchlistRepository
from app.services.analysis_engine import get_engine
from app.services.demo_clock import DemoClockService


class WatchlistService:
    def __init__(self) -> None:
        self.repo = WatchlistRepository()
        self.cases = CaseRepository()
        self.snapshots = VisitSnapshotRepository()
        self.engine = get_engine()
        self.clock = DemoClockService()

    async def ensure_default(self, user_id: str, symbols: list[str] | None = None) -> dict:
        existing = await self.repo.list_for_user(user_id)
        if existing:
            return existing[0]
        default_symbols = symbols or ["RELIANCE", "TCS", "HDFCBANK", "TATAMOTORS", "INFY", "ITC"]
        wl = await self.repo.create(user_id, "My Watchlist", default_symbols)
        await self._baseline_snapshot(user_id, wl)
        return wl

    async def _baseline_snapshot(self, user_id: str, wl: dict) -> None:
        """A snapshot at the current demo time so the first 'Advance Market Time'
        immediately produces a real 'Since You Left' comparison."""
        if await self.snapshots.latest(user_id, wl["_id"]):
            return
        ts = await self.clock.current_timestamp(user_id)
        states = []
        for sym in wl.get("symbols", []):
            s = self.engine.state_at(sym, ts)
            states.append({
                "symbol": sym, "price": s["price"], "attention_score": s["attention_score"],
                "severity": s["severity"], "freshness": s["freshness"], "verdict": s["verdict"],
            })
        cases = await self.cases.list_up_to(ts.to_pydatetime(), symbols=wl.get("symbols", []))
        await self.snapshots.acknowledge(
            user_id=user_id, watchlist_id=wl["_id"], dataset_timestamp=ts.to_pydatetime(),
            stock_states=states, seen_case_ids=[c["case_id"] for c in cases],
            attention_threshold=wl.get("attention_threshold", 55),
            daily_attention_budget=wl.get("daily_attention_budget", "top_3"),
        )

    async def detail(self, user_id: str, watchlist_id: str) -> dict | None:
        wl = await self.repo.get_for_user(user_id, watchlist_id)
        if not wl:
            return None
        ts = await self.clock.current_timestamp(user_id)
        items = [self._item(sym, ts) for sym in wl.get("symbols", [])]
        # attach the top open case per symbol
        open_cases = await self.cases.list_up_to(
            ts.to_pydatetime(), symbols=wl.get("symbols", []))
        by_symbol: dict[str, dict] = {}
        for c in sorted(open_cases, key=lambda c: c["attention_score"], reverse=True):
            by_symbol.setdefault(c["symbol"], c)
        for it in items:
            c = by_symbol.get(it["symbol"])
            if c:
                it["open_case_id"] = c["case_id"]
                it["verdict"] = c["verdict"]
        return {
            **wl,
            "id": wl["_id"],
            "items": items,
            "dataset_timestamp": ts.to_pydatetime(),
        }

    def _item(self, symbol: str, ts: pd.Timestamp) -> dict:
        s = self.engine.state_at(symbol, ts)
        return {
            "symbol": symbol,
            "name": s["name"],
            "sector": s["sector"],
            "sector_name": s["sector_name"],
            "latest_price": s["price"],
            "previous_close": s["previous_close"],
            "change_pct": s["change_pct"],
            "change_abs": s["change_abs"],
            "attention_score": s["attention_score"],
            "severity": s["severity"],
            "freshness": s["freshness"],
            "verdict": s["verdict"],
            "spark": s["spark"],
            "open_case_id": None,
        }

    async def summary_list(self, user_id: str) -> list[dict]:
        return await self.repo.list_for_user(user_id)
