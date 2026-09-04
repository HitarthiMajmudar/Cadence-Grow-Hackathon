"""Per-user simulated market clock over the offline dataset."""
from __future__ import annotations

import pandas as pd

from app.core.config import get_settings
from app.repositories.snapshots import DemoClockRepository
from app.services.analysis_engine import get_engine


class DemoClockService:
    def __init__(self, repo: DemoClockRepository | None = None) -> None:
        self.repo = repo or DemoClockRepository()
        self.engine = get_engine()
        self.settings = get_settings()

    def _bounds(self) -> tuple[pd.Timestamp, pd.Timestamp, pd.Timestamp]:
        first, last = self.engine.timeline()[0], self.engine.timeline()[-1]
        present = pd.Timestamp(self.engine.meta["demo_present_timestamp"])
        return pd.Timestamp(first), pd.Timestamp(last), present

    async def get(self, user_id: str) -> dict:
        _first, _last, present = self._bounds()
        doc = await self.repo.ensure(user_id, present.to_pydatetime())
        return self._shape(user_id, doc)

    async def advance(self, user_id: str, bars: int | None = None) -> dict:
        bars = bars or self.settings.demo_clock_advance_bars
        doc = await self.repo.ensure(user_id, self._bounds()[2].to_pydatetime())
        current = pd.Timestamp(doc["current_dataset_timestamp"])
        new_ts = self.engine.advance_timestamp(current, bars)
        updated = await self.repo.set(user_id, new_ts.to_pydatetime())
        result = self._shape(user_id, updated)
        actual = self.engine.bars_between(current, new_ts)
        result["_advanced_from"] = current
        result["_advanced_bars"] = actual
        return result

    async def reset(self, user_id: str) -> dict:
        present = self._bounds()[2]
        updated = await self.repo.set(user_id, present.to_pydatetime())
        return self._shape(user_id, updated)

    async def current_timestamp(self, user_id: str) -> pd.Timestamp:
        doc = await self.repo.ensure(user_id, self._bounds()[2].to_pydatetime())
        return pd.Timestamp(doc["current_dataset_timestamp"])

    def _shape(self, user_id: str, doc: dict) -> dict:
        first, last, present = self._bounds()
        current = pd.Timestamp(doc["current_dataset_timestamp"])
        return {
            "user_id": user_id,
            "current_dataset_timestamp": current.to_pydatetime(),
            "dataset_first_timestamp": first.to_pydatetime(),
            "dataset_last_timestamp": last.to_pydatetime(),
            "default_present_timestamp": present.to_pydatetime(),
            "bars_from_present": self.engine.bars_between(present, current),
            "bars_to_end": self.engine.bars_between(current, last),
            "is_at_end": current >= last,
            "updated_at": doc.get("updated_at"),
            "dataset_label": self.engine.meta.get("label", "Offline Research Dataset"),
            "demo_mode": True,
        }
