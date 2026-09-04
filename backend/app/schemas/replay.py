from __future__ import annotations

from datetime import datetime

from pydantic import Field

from app.schemas.common import ApiModel, Freshness


class ReplayFrame(ApiModel):
    index: int
    timestamp: datetime
    close: float | None
    volume: int
    stock_indexed: float
    sector_indexed: float
    market_indexed: float
    attention_score: float
    confidence: float
    verdict: str
    severity: str
    freshness: Freshness
    return_zscore: float
    volume_ratio: float
    is_anomaly: bool
    anomaly_level: str  # none | moderate | serious
    case_id: str | None = None
    news_ids: list[str] = Field(default_factory=list)


class ReplayNewsMarker(ApiModel):
    id: str
    timestamp: datetime
    frame_index: int
    headline: str
    event_type: str
    sentiment_label: str
    sentiment_score: float


class ReplayAnomalyMarker(ApiModel):
    frame_index: int
    timestamp: datetime
    level: str
    attention_score: float
    verdict: str
    case_id: str | None
    label: str


class ReplayResponse(ApiModel):
    symbol: str
    company_name: str
    sector: str
    market_index: str
    start: datetime
    end: datetime
    frame_count: int
    bars_per_day: int
    frames: list[ReplayFrame]
    news_markers: list[ReplayNewsMarker]
    anomaly_markers: list[ReplayAnomalyMarker]
    score_evolution: list[dict]
    who_moved_first: str | None
    first_mover_detail: str
    dataset_label: str


class ReplayScoreEvolution(ApiModel):
    symbol: str
    points: list[dict]
