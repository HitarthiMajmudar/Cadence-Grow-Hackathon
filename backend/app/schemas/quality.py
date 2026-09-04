from __future__ import annotations

from datetime import datetime

from pydantic import Field

from app.schemas.common import ApiModel, Freshness


class DataQualityEventOut(ApiModel):
    id: str = Field(alias="_id")
    symbol: str
    timestamp: datetime
    status: Freshness
    sources: list
    details: str
    confidence_penalty: float


class SymbolQuality(ApiModel):
    symbol: str
    freshness: Freshness
    last_observation: datetime | None
    bars_missing_recent: int
    events: list[DataQualityEventOut]
    confidence_penalty: float


class DatasetHealth(ApiModel):
    dataset_label: str
    dataset_first_timestamp: datetime
    dataset_last_timestamp: datetime
    current_dataset_timestamp: datetime
    freshness_overall: Freshness
    freshness_status_text: str
    total_observations: int
    symbols_tracked: int
    symbols_with_issues: list[str]
    missing_bars: int
    stale_bars: int
    conflicting_bars: int
    events: list[DataQualityEventOut]
    per_symbol: list[SymbolQuality]
