"""Orchestration for Live Markets — maps Twelve Data's raw response shapes
onto our own schemas. No Attention Score, no anomaly detection: this is a
plain live-quote lookup, separate from Detective Mode's analysis engine."""
from __future__ import annotations

import math

from app.services.twelve_data_client import MarketDataUnavailable, TwelveDataClient


def _to_float(v) -> float | None:
    if v in (None, "", "null"):
        return None
    try:
        value = float(v)
        return value if math.isfinite(value) else None
    except (TypeError, ValueError):
        return None


def _to_int(v) -> int | None:
    f = _to_float(v)
    return int(f) if f is not None else None


class LiveMarketService:
    def __init__(self) -> None:
        self.client = TwelveDataClient()

    async def search(self, query: str) -> list[dict]:
        matches = await self.client.search_symbol(query)
        return [
            {
                "symbol": m.get("symbol", ""),
                "name": m.get("instrument_name", m.get("symbol", "")),
                "exchange": m.get("exchange", ""),
                "mic_code": m.get("mic_code"),
                "country": m.get("country"),
                "currency": m.get("currency"),
                "instrument_type": m.get("instrument_type"),
            }
            for m in matches
        ]

    async def quote(self, symbol: str, exchange: str | None = None) -> dict:
        q = await self.client.get_quote(symbol, exchange)
        price = _to_float(q.get("close"))
        if price is None:
            raise MarketDataUnavailable("Live market data provider returned an invalid price.")
        prev_close = _to_float(q.get("previous_close"))
        change = _to_float(q.get("change"))
        change_pct = _to_float(q.get("percent_change"))
        return {
            "symbol": q.get("symbol", symbol.upper()),
            "name": q.get("name", symbol.upper()),
            "exchange": q.get("exchange", exchange or ""),
            "currency": q.get("currency"),
            "price": price,
            "previous_close": prev_close,
            "change": change,
            "change_pct": change_pct,
            "day_high": _to_float(q.get("high")),
            "day_low": _to_float(q.get("low")),
            "volume": _to_int(q.get("volume")),
            "is_market_open": q.get("is_market_open"),
            "as_of": q.get("datetime"),
        }

    async def history(self, symbol: str, exchange: str | None = None, outputsize: int = 180) -> dict:
        series = await self.client.get_daily_series(symbol, exchange, outputsize)
        meta = series.get("meta", {})
        values = series.get("values", []) or []
        candles = [
            {
                "date": v.get("datetime", ""),
                "open": _to_float(v.get("open")),
                "high": _to_float(v.get("high")),
                "low": _to_float(v.get("low")),
                "close": _to_float(v.get("close")),
                "volume": _to_int(v.get("volume")),
            }
            for v in values
        ]
        candles.sort(key=lambda c: c["date"])  # oldest-first for charting
        return {
            "symbol": meta.get("symbol", symbol.upper()),
            "exchange": meta.get("exchange", exchange),
            "interval": meta.get("interval", "1day"),
            "candles": candles,
        }
