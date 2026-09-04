from __future__ import annotations

from datetime import datetime

from pydantic import Field

from app.schemas.common import ApiModel, ChangeClass, Freshness


class StockChange(ApiModel):
    symbol: str
    name: str
    sector: str
    classification: ChangeClass
    price_then: float | None
    price_now: float | None
    price_change_pct: float | None
    attention_then: float
    attention_now: float
    attention_delta: float
    freshness: Freshness
    verdict: str | None
    headline: str
    new_case_id: str | None = None
    new_case_score: float | None = None


class BriefingResponse(ApiModel):
    watchlist_id: str
    watchlist_name: str
    has_previous_snapshot: bool
    snapshot_acknowledged_at: datetime | None
    snapshot_dataset_timestamp: datetime | None
    current_dataset_timestamp: datetime
    hours_away: float
    market_hours_away: float
    total_changes: int
    changes_worth_attention: int
    summary_line: str
    threshold: int
    budget: str
    changes: list[StockChange]
    new_case_ids: list[str] = Field(default_factory=list)
    counts: dict[str, int] = Field(default_factory=dict)


class MarkSeenRequest(ApiModel):
    watchlist_id: str
    seen_case_ids: list[str] = Field(default_factory=list)


class SnapshotOut(ApiModel):
    id: str = Field(alias="_id")
    user_id: str
    watchlist_id: str
    acknowledged_at: datetime
    dataset_timestamp: datetime
    stock_states: list[dict]
    seen_case_ids: list[str]
    attention_threshold: int
    daily_attention_budget: str
