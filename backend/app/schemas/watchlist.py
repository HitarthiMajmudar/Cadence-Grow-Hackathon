from __future__ import annotations

from datetime import datetime

from pydantic import Field

from app.schemas.common import ApiModel, Freshness

ATTENTION_BUDGETS = {
    "top_3": "Show only the top 3 cases",
    "top_5": "Show only the top 5 cases",
    "score_gt_70": "Show cases scoring above 70",
    "score_gt_55": "Show cases scoring above 55",
    "unexplained_only": "Show only unexplained anomalies",
    "hide_sector_driven": "Hide normal sector-driven movements",
    "all": "Show every case",
}


class WatchlistCreate(ApiModel):
    name: str = Field(min_length=1, max_length=80)
    symbols: list[str] = Field(default_factory=list)
    attention_threshold: int = Field(default=55, ge=0, le=100)
    daily_attention_budget: str = "top_3"


class WatchlistRename(ApiModel):
    name: str = Field(min_length=1, max_length=80)


class WatchlistSettings(ApiModel):
    attention_threshold: int | None = Field(default=None, ge=0, le=100)
    daily_attention_budget: str | None = None


class SymbolRequest(ApiModel):
    symbol: str = Field(min_length=1, max_length=20)


class WatchlistItem(ApiModel):
    symbol: str
    name: str
    sector: str
    sector_name: str
    latest_price: float | None
    previous_close: float | None
    change_pct: float | None
    change_abs: float | None
    attention_score: float
    severity: str
    freshness: Freshness
    verdict: str | None = None
    spark: list[float] = Field(default_factory=list)
    open_case_id: str | None = None


class WatchlistOut(ApiModel):
    id: str = Field(alias="_id")
    user_id: str
    name: str
    symbols: list[str]
    attention_threshold: int
    daily_attention_budget: str
    created_at: datetime
    updated_at: datetime


class WatchlistDetail(WatchlistOut):
    items: list[WatchlistItem] = Field(default_factory=list)
    dataset_timestamp: datetime | None = None
