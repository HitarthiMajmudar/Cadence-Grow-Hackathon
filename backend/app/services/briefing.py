"""'Since You Left' briefing — compares the current dataset state with the
user's last acknowledged snapshot for a watchlist."""
from __future__ import annotations

import pandas as pd

from app.ml.explain import classification_headline
from app.repositories.cases import CaseRepository, UserCaseStateRepository
from app.repositories.snapshots import VisitSnapshotRepository
from app.repositories.watchlists import WatchlistRepository
from app.schemas.common import ChangeClass
from app.services.analysis_engine import get_engine
from app.services.demo_clock import DemoClockService

EXPLAINED = {"Market-wide movement", "Sector-driven movement", "News-supported movement"}
INVESTIGATING = {"Conflicting evidence", "Volatility-regime change", "Insufficient data"}


class BriefingService:
    def __init__(self) -> None:
        self.snapshots = VisitSnapshotRepository()
        self.watchlists = WatchlistRepository()
        self.cases = CaseRepository()
        self.case_states = UserCaseStateRepository()
        self.engine = get_engine()
        self.clock = DemoClockService()

    async def generate(self, user_id: str, watchlist_id: str) -> dict | None:
        wl = await self.watchlists.get_for_user(user_id, watchlist_id)
        if not wl:
            return None
        current_ts = await self.clock.current_timestamp(user_id)
        snapshot = await self.snapshots.latest(user_id, watchlist_id)
        threshold = wl.get("attention_threshold", 55)
        budget = wl.get("daily_attention_budget", "top_3")

        prev_ts = pd.Timestamp(snapshot["dataset_timestamp"]) if snapshot else None
        prev_states = {s["symbol"]: s for s in snapshot["stock_states"]} if snapshot else {}
        seen_case_ids = set(snapshot["seen_case_ids"]) if snapshot else set()

        changes: list[dict] = []
        new_case_ids: list[str] = []
        worth_attention = 0

        # new cases since the snapshot. On a genuine first visit there is no
        # comparison point yet, so nothing counts as "new" — the user is asked to
        # acknowledge the briefing to start tracking.
        window_start = prev_ts if prev_ts is not None else current_ts
        fresh_cases = await self.cases.list_between(
            window_start.to_pydatetime(), current_ts.to_pydatetime(), symbols=wl["symbols"])
        cases_by_symbol: dict[str, list[dict]] = {}
        for c in fresh_cases:
            cases_by_symbol.setdefault(c["symbol"], []).append(c)
            if c["case_id"] not in seen_case_ids:
                new_case_ids.append(c["case_id"])

        first_visit = snapshot is None
        for symbol in wl.get("symbols", []):
            now = self.engine.state_at(symbol, current_ts)
            prev = prev_states.get(symbol)
            price_now = now["price"]
            attention_now = now["attention_score"]

            if first_visit:
                # nothing to compare against yet
                price_then = price_now
                attention_then = attention_now
            else:
                price_then = prev.get("price") if prev else self._price_at(symbol, prev_ts)
                attention_then = float(prev.get("attention_score", 0.0)) if prev else 0.0

            price_change_pct = None
            if price_then and price_now and not first_visit:
                price_change_pct = round((price_now / price_then - 1) * 100, 2)

            sym_cases = sorted(cases_by_symbol.get(symbol, []),
                               key=lambda c: c["attention_score"], reverse=True)
            top_case = sym_cases[0] if sym_cases else None
            verdict = top_case["verdict"] if top_case else now["verdict"]

            classification = self._classify(
                now, attention_then, attention_now, price_change_pct,
                top_case, threshold)
            is_new_case = bool(top_case and top_case["case_id"] in new_case_ids)
            big_move = price_change_pct is not None and abs(price_change_pct) >= 4.0
            if classification == ChangeClass.IMPORTANT.value:
                worth_attention += 1
            elif is_new_case and (top_case["attention_score"] >= threshold - 10 or big_move):
                # a fresh case on a real move is worth a look even if it's "explained"
                worth_attention += 1

            changes.append({
                "symbol": symbol,
                "name": now["name"],
                "sector": now["sector"],
                "classification": classification,
                "price_then": price_then,
                "price_now": price_now,
                "price_change_pct": price_change_pct,
                "attention_then": round(attention_then, 1),
                "attention_now": round(attention_now, 1),
                "attention_delta": round(attention_now - attention_then, 1),
                "freshness": now["freshness"],
                "verdict": verdict,
                "headline": classification_headline(classification, symbol, verdict),
                "new_case_id": top_case["case_id"] if (top_case and top_case["case_id"] in new_case_ids) else None,
                "new_case_score": top_case["attention_score"] if top_case else None,
            })

        counts: dict[str, int] = {}
        for c in changes:
            counts[c["classification"]] = counts.get(c["classification"], 0) + 1

        total_changes = sum(
            1 for c in changes
            if (c["price_change_pct"] is not None and abs(c["price_change_pct"]) >= 0.75)
            or abs(c["attention_delta"]) >= 8
            or c["new_case_id"]
        )
        market_hours = float(self.engine.bars_between(prev_ts, current_ts)) if prev_ts is not None else 0.0

        summary = self._summary_line(
            has_prev=snapshot is not None, market_hours=market_hours,
            total_changes=total_changes, worth=worth_attention)

        return {
            "watchlist_id": watchlist_id,
            "watchlist_name": wl["name"],
            "has_previous_snapshot": snapshot is not None,
            "snapshot_acknowledged_at": snapshot["acknowledged_at"] if snapshot else None,
            "snapshot_dataset_timestamp": prev_ts.to_pydatetime() if prev_ts is not None else None,
            "current_dataset_timestamp": current_ts.to_pydatetime(),
            "hours_away": round(market_hours, 1),
            "market_hours_away": round(market_hours, 1),
            "total_changes": total_changes,
            "changes_worth_attention": worth_attention,
            "summary_line": summary,
            "threshold": threshold,
            "budget": budget,
            "changes": sorted(changes, key=lambda c: _class_rank(c["classification"])),
            "new_case_ids": new_case_ids,
            "counts": counts,
        }

    def _price_at(self, symbol: str, ts: pd.Timestamp | None) -> float | None:
        if ts is None:
            return None
        row = self.engine.row_at(symbol, ts)
        if row is None:
            return None
        val = row.get("close")
        try:
            return round(float(val), 2)
        except (TypeError, ValueError):
            return None

    def _classify(self, now: dict, attn_then: float, attn_now: float,
                  price_change_pct: float | None, top_case: dict | None,
                  threshold: int) -> str:
        if now["freshness"] in ("missing",) or now["price"] is None:
            return ChangeClass.INSUFFICIENT_DATA.value
        verdict = top_case["verdict"] if top_case else now["verdict"]
        score = top_case["attention_score"] if top_case else attn_now

        if verdict == "Insufficient data":
            return ChangeClass.INSUFFICIENT_DATA.value
        if score >= threshold and (verdict not in EXPLAINED):
            return ChangeClass.IMPORTANT.value
        if verdict in INVESTIGATING or (threshold - 15 <= score < threshold):
            return ChangeClass.INVESTIGATING.value
        if verdict in EXPLAINED or (price_change_pct is not None and abs(price_change_pct) >= 2.0):
            return ChangeClass.EXPLAINED.value
        return ChangeClass.NORMAL.value

    def _summary_line(self, *, has_prev: bool, market_hours: float,
                      total_changes: int, worth: int) -> str:
        if not has_prev:
            return ("First visit to this watchlist — acknowledge the briefing to start "
                    "tracking what changes between now and your next visit.")
        hrs = int(round(market_hours))
        if total_changes == 0:
            return f"You were away for {hrs} simulated market hours. Nothing on this watchlist moved meaningfully."
        return (f"You were away for {hrs} simulated market hours. We found {total_changes} "
                f"change{'s' if total_changes != 1 else ''}, but only {worth} "
                f"deserve{'s' if worth == 1 else ''} your attention.")

    async def mark_seen(self, user_id: str, watchlist_id: str, seen_case_ids: list[str]) -> dict | None:
        wl = await self.watchlists.get_for_user(user_id, watchlist_id)
        if not wl:
            return None
        current_ts = await self.clock.current_timestamp(user_id)
        stock_states = []
        for symbol in wl.get("symbols", []):
            s = self.engine.state_at(symbol, current_ts)
            stock_states.append({
                "symbol": symbol,
                "price": s["price"],
                "attention_score": s["attention_score"],
                "severity": s["severity"],
                "freshness": s["freshness"],
                "verdict": s["verdict"],
            })
        # every case for these symbols up to now is now "seen"
        cases = await self.cases.list_up_to(current_ts.to_pydatetime(), symbols=wl["symbols"])
        seen = sorted({*seen_case_ids, *[c["case_id"] for c in cases]})
        for cid in seen:
            await self.case_states.mark_viewed_if_new(user_id, cid)

        return await self.snapshots.acknowledge(
            user_id=user_id, watchlist_id=watchlist_id,
            dataset_timestamp=current_ts.to_pydatetime(),
            stock_states=stock_states, seen_case_ids=seen,
            attention_threshold=wl.get("attention_threshold", 55),
            daily_attention_budget=wl.get("daily_attention_budget", "top_3"),
        )


def _class_rank(c: str) -> int:
    return {"important": 0, "investigating": 1, "explained": 2,
            "insufficient_data": 3, "normal": 4}.get(c, 5)
