"""Live Markets — real quotes for any symbol via Twelve Data.

Kept entirely separate from app/schemas/market.py: these shapes describe real,
externally-sourced data with no Attention Score, no verdict, no Evidence
Court — Detective Mode's ML pipeline never touches this data.
"""
from __future__ import annotations

from app.schemas.common import ApiModel


class LiveSymbolMatch(ApiModel):
    symbol: str
    name: str
    exchange: str
    mic_code: str | None = None
    country: str | None = None
    currency: str | None = None
    instrument_type: str | None = None


class LiveQuote(ApiModel):
    symbol: str
    name: str
    exchange: str
    currency: str | None = None
    price: float
    previous_close: float | None = None
    change: float | None = None
    change_pct: float | None = None
    day_high: float | None = None
    day_low: float | None = None
    volume: int | None = None
    is_market_open: bool | None = None
    as_of: str | None = None


class LiveCandle(ApiModel):
    date: str
    open: float | None
    high: float | None
    low: float | None
    close: float | None
    volume: int | None = None


class LiveHistoryResponse(ApiModel):
    symbol: str
    exchange: str | None = None
    interval: str = "1day"
    candles: list[LiveCandle]
