from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import Field

from app.schemas.common import ApiModel, CaseStatus, DetectiveStatus, Freshness


class ScoreComponent(ApiModel):
    key: str
    label: str
    points: float
    max_points: float
    detail: str


class Evidence(ApiModel):
    kind: Literal["supporting", "counter", "quality"]
    label: str
    detail: str
    metric: str | None = None
    value: float | None = None


class DetectiveFinding(ApiModel):
    detective: str
    key: Literal["stock", "volume", "sector", "news"]
    finding: str
    evidence: list[str]
    confidence: float
    status: DetectiveStatus


class DataQuality(ApiModel):
    freshness: Freshness
    confidence_penalty: float
    warnings: list[str] = Field(default_factory=list)
    sources_considered: list[str] = Field(default_factory=list)
    resolved_source: str | None = None
    conflict_detail: str | None = None


class RelatedNews(ApiModel):
    id: str
    timestamp: datetime
    headline: str
    source: str
    event_type: str
    sentiment_label: str
    sentiment_score: float
    minutes_from_detection: float
    relevance: float


class AttentionBreakdown(ApiModel):
    score: float
    confidence: float
    severity: str
    components: list[ScoreComponent]
    top_reasons: list[str]
    supporting_evidence: list[Evidence]
    counter_evidence: list[Evidence]
    data_quality_warnings: list[str]
    signal_agreement: int


class CaseOut(ApiModel):
    id: str = Field(alias="_id")
    case_id: str
    symbol: str
    company_name: str
    sector: str
    sector_name: str
    detection_timestamp: datetime
    comparison_start: datetime
    comparison_end: datetime
    attention_score: float
    confidence: float
    severity: str
    verdict: str
    headline_explanation: str
    explanation: str
    created_at: datetime

    # user-specific (merged in at read time)
    status: CaseStatus = CaseStatus.NEW
    viewed_at: datetime | None = None
    is_seen: bool = False


class CaseDetail(CaseOut):
    breakdown: AttentionBreakdown
    detectives: list[DetectiveFinding]
    score_components: list[ScoreComponent]
    supporting_evidence: list[Evidence]
    counter_evidence: list[Evidence]
    related_news: list[RelatedNews]
    data_quality: DataQuality
    metrics: dict[str, float]
    spark: list[float] = Field(default_factory=list)
    price_series: list[dict] = Field(default_factory=list)


class CaseListResponse(ApiModel):
    needs_attention: list[CaseOut]
    still_investigating: list[CaseOut]
    explained: list[CaseOut]
    total: int
    threshold: int
    budget: str
    budget_label: str
    page: int
    page_size: int


class CaseStatusUpdate(ApiModel):
    status: CaseStatus


class CaseFeedbackRequest(ApiModel):
    feedback: Literal["agree", "disagree", "not_useful", "useful"]
    note: str | None = Field(default=None, max_length=500)


class StoryCardData(ApiModel):
    case_id: str
    symbol: str
    company_name: str
    event_date: datetime
    attention_score: float
    confidence: float
    severity: str
    verdict: str
    one_line: str
    main_evidence: list[str]
    sparkline: list[float]
    dataset_label: str
    generated_at: datetime
    disclaimer: str = "Educational market analysis. Not investment advice."
