from __future__ import annotations

from datetime import datetime

from pydantic import Field

from app.schemas.common import ApiModel


class DemoClockOut(ApiModel):
    user_id: str
    current_dataset_timestamp: datetime
    dataset_first_timestamp: datetime
    dataset_last_timestamp: datetime
    default_present_timestamp: datetime
    bars_from_present: int
    bars_to_end: int
    is_at_end: bool
    updated_at: datetime
    dataset_label: str = "Offline Research Dataset"
    demo_mode: bool = True


class AdvanceClockRequest(ApiModel):
    bars: int | None = Field(default=None, ge=1, le=210)


class ClockAdvanceResult(ApiModel):
    clock: DemoClockOut
    advanced_bars: int
    market_hours_advanced: float
    from_timestamp: datetime
    to_timestamp: datetime
    new_case_ids: list[str] = Field(default_factory=list)
