from __future__ import annotations

from datetime import datetime

from pydantic import Field

from app.schemas.common import ApiModel, Freshness


class StockMeta(ApiModel):
    symbol: str
    name: str
    sector: str
    sector_name: str
    index: str
    weight: float
    currency: str
    summary: str


class Candle(ApiModel):
    timestamp: datetime
    open: float | None
    high: float | None
    low: float | None
    close: float | None
    volume: int
    freshness: Freshness = Freshness.FRESH
    source: str = "research_primary"


class StockState(ApiModel):
    symbol: str
    name: str
    sector: str
    sector_name: str
    as_of: datetime
    price: float | None
    previous_close: float | None
    change_pct: float | None
    change_abs: float | None
    day_volume: int
    attention_score: float
    confidence: float
    severity: str
    verdict: str | None
    freshness: Freshness
    spark: list[float] = Field(default_factory=list)
    open_case_id: str | None = None


class ComparisonPoint(ApiModel):
    timestamp: datetime
    stock_indexed: float
    sector_indexed: float
    market_indexed: float


class ComparisonSeries(ApiModel):
    symbol: str
    sector: str
    market_index: str
    start: datetime
    end: datetime
    points: list[ComparisonPoint]
    stock_return_pct: float
    sector_return_pct: float
    market_return_pct: float
    who_moved_first: str | None = None


class HistoryResponse(ApiModel):
    symbol: str
    interval: str
    candles: list[Candle]
    total: int
    page: int
    page_size: int
