"""Shared enums and base models."""
from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, ConfigDict


class ApiModel(BaseModel):
    model_config = ConfigDict(populate_by_name=True, use_enum_values=True)


class Freshness(StrEnum):
    FRESH = "fresh"
    DELAYED = "delayed"
    STALE = "stale"
    MISSING = "missing"
    CONFLICTING = "conflicting"


class Severity(StrEnum):
    CRITICAL = "critical"
    HIGH = "high"
    MODERATE = "moderate"
    LOW = "low"
    MINIMAL = "minimal"


class Verdict(StrEnum):
    UNUSUAL_PRICE_VOLUME = "Unusual price and volume activity"
    SECTOR_DRIVEN = "Sector-driven movement"
    MARKET_WIDE = "Market-wide movement"
    NEWS_SUPPORTED = "News-supported movement"
    PRE_NEWS = "Price activity before recorded news"
    HEADLINE_NOISE = "Headline noise"
    VOLATILITY_REGIME = "Volatility-regime change"
    POSSIBLE_BREAKOUT = "Possible breakout"
    POSSIBLE_BREAKDOWN = "Possible breakdown"
    CONFLICTING = "Conflicting evidence"
    INSUFFICIENT_DATA = "Insufficient data"
    NORMAL = "Normal movement"


class CaseStatus(StrEnum):
    NEW = "new"
    VIEWED = "viewed"
    SAVED = "saved"
    DISMISSED = "dismissed"


class ChangeClass(StrEnum):
    IMPORTANT = "important"
    INVESTIGATING = "investigating"
    EXPLAINED = "explained"
    NORMAL = "normal"
    INSUFFICIENT_DATA = "insufficient_data"


class DetectiveStatus(StrEnum):
    SUPPORTS = "supports"
    OPPOSES = "opposes"
    INCONCLUSIVE = "inconclusive"


class EventType(StrEnum):
    EARNINGS = "earnings"
    ACQUISITION = "acquisition"
    REGULATION = "regulation"
    LEADERSHIP = "leadership"
    PRODUCT_LAUNCH = "product_launch"
    LEGAL_ISSUE = "legal_issue"
    ANALYST_ACTION = "analyst_action"
    FINANCING = "financing"
    OPERATIONAL = "operational"
    MARKET = "market"
    SECTOR = "sector"
    OTHER = "other"


class ErrorResponse(ApiModel):
    detail: str
    code: str = "error"
