"""Dataset-health and per-symbol data-quality reporting."""
from __future__ import annotations

import pandas as pd

from app.repositories.market import DataQualityEventRepository
from app.services.analysis_engine import get_engine
from app.services.demo_clock import DemoClockService

STATUS_TEXT = {
    "fresh": "All tracked symbols are reporting on schedule.",
    "delayed": "One or more feeds are running behind the simulated clock.",
    "stale": "One or more feeds are repeating their last good value.",
    "missing": "One or more symbols have gaps in the recent window.",
    "conflicting": "Stored sources disagree for one or more symbols; the higher-priority source is in use.",
}


class DataQualityService:
    def __init__(self) -> None:
        self.events = DataQualityEventRepository()
        self.engine = get_engine()
        self.clock = DemoClockService()

    async def dataset_health(self, user_id: str) -> dict:
        current_ts = await self.clock.current_timestamp(user_id)
        health = self.engine.dataset_health(current_ts)
        events = await self.events.all_events()
        visible = [
            {**e, "id": e.get("_id", ""), "timestamp": pd.Timestamp(e["timestamp"]).to_pydatetime()}
            for e in events if pd.Timestamp(e["timestamp"]) <= current_ts
        ]
        per_symbol = []
        for sym in self.engine.name_of:
            q = await self.symbol_quality(sym, current_ts)
            if q["events"] or q["freshness"] != "fresh":
                per_symbol.append(q)

        meta = self.engine.meta
        return {
            "dataset_label": meta.get("label", "Offline Research Dataset"),
            "dataset_first_timestamp": pd.Timestamp(meta["first_timestamp"]).to_pydatetime(),
            "dataset_last_timestamp": pd.Timestamp(meta["last_timestamp"]).to_pydatetime(),
            "current_dataset_timestamp": current_ts.to_pydatetime(),
            "freshness_overall": health["freshness_overall"],
            "freshness_status_text": STATUS_TEXT.get(health["freshness_overall"], ""),
            "total_observations": health["total_observations"],
            "symbols_tracked": health["symbols_tracked"],
            "symbols_with_issues": health["symbols_with_issues"],
            "missing_bars": health["missing_bars"],
            "stale_bars": health["stale_bars"],
            "conflicting_bars": health["conflicting_bars"],
            "events": visible,
            "per_symbol": per_symbol,
        }

    async def symbol_quality(self, symbol: str, current_ts: pd.Timestamp | None = None) -> dict:
        symbol = symbol.upper()
        if current_ts is None:
            current_ts = self.engine.timeline()[-1]
        g = self.engine.symbol_frame(symbol)
        sub = g[g["timestamp"] <= current_ts] if g is not None and not g.empty else g
        last_obs = pd.Timestamp(sub["timestamp"].iloc[-1]).to_pydatetime() if sub is not None and len(sub) else None
        recent = sub.tail(14) if sub is not None else None
        freshness = "fresh"
        missing_recent = 0
        if recent is not None and len(recent):
            missing_recent = int((recent["freshness_status"] == "missing").sum())
            for state in ("missing", "stale", "conflicting", "delayed"):
                if (recent["freshness_status"] == state).any():
                    freshness = state
                    break

        rows = await self.events.for_symbol(symbol)
        events = [
            {**e, "id": e.get("_id", ""), "timestamp": pd.Timestamp(e["timestamp"]).to_pydatetime()}
            for e in rows if pd.Timestamp(e["timestamp"]) <= current_ts
        ]
        penalty = max((float(e.get("confidence_penalty", 0)) for e in events), default=0.0)
        return {
            "symbol": symbol,
            "freshness": freshness,
            "last_observation": last_obs,
            "bars_missing_recent": missing_recent,
            "events": events,
            "confidence_penalty": penalty,
        }
