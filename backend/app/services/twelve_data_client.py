"""Thin async client for the Twelve Data REST API — the sole source of real,
live market prices in this app (Detective Mode never calls this; see
app/services/live_market_service.py for the feature this powers).

Twelve Data quirk: many error conditions (bad key, unsupported plan, unknown
symbol) come back as HTTP 200 with `{"status": "error", "code": ..., "message":
...}` rather than a matching HTTP status, so every response body is inspected
regardless of the transport status code.
"""
from __future__ import annotations

import logging
import time
from typing import Any

import httpx

from app.core.config import get_settings
from app.core.errors import AppError, NotFoundError

logger = logging.getLogger("market_detective.live")

_QUOTE_TTL_SECONDS = 30
_HISTORY_TTL_SECONDS = 6 * 60 * 60
_SEARCH_TTL_SECONDS = 60 * 60

_cache: dict[tuple, tuple[float, Any]] = {}


def _cache_get(key: tuple) -> Any | None:
    hit = _cache.get(key)
    if not hit:
        return None
    expires_at, value = hit
    if time.monotonic() >= expires_at:
        _cache.pop(key, None)
        return None
    return value


def _cache_set(key: tuple, value: Any, ttl_seconds: float) -> None:
    _cache[key] = (time.monotonic() + ttl_seconds, value)


class MarketDataNotConfigured(AppError):
    def __init__(self) -> None:
        super().__init__(
            "Live market data isn't configured on this server yet. "
            "Set TWELVE_DATA_API_KEY to enable Live Markets.",
            code="market_data_not_configured",
            status_code=503,
        )


class MarketDataUnavailable(AppError):
    def __init__(self, detail: str = "Live market data is temporarily unavailable.") -> None:
        super().__init__(detail, code="market_data_unavailable", status_code=502)


class MarketDataRateLimited(AppError):
    def __init__(self) -> None:
        super().__init__(
            "Live market data provider rate limit reached. Try again shortly.",
            code="rate_limited",
            status_code=429,
        )


class TwelveDataClient:
    def __init__(self) -> None:
        self.settings = get_settings()

    def _require_key(self) -> str:
        if not self.settings.twelve_data_api_key:
            raise MarketDataNotConfigured()
        return self.settings.twelve_data_api_key

    async def _get(self, path: str, params: dict[str, Any]) -> dict:
        params = {**params, "apikey": self._require_key()}
        url = f"{self.settings.twelve_data_base_url}{path}"
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(url, params=params)
        except httpx.TimeoutException as exc:
            raise MarketDataUnavailable("Live market data provider timed out.") from exc
        except httpx.HTTPError as exc:
            raise MarketDataUnavailable() from exc

        if resp.status_code == 429:
            raise MarketDataRateLimited()

        try:
            data = resp.json()
        except ValueError as exc:
            raise MarketDataUnavailable("Live market data provider returned a bad response.") from exc

        if not isinstance(data, dict):
            raise MarketDataUnavailable("Live market data provider returned a bad response.")

        if data.get("status") == "error":
            code = data.get("code")
            message = data.get("message", "Unknown provider error.")
            if code == 429:
                raise MarketDataRateLimited()
            if code in (401, 403):
                logger.warning("Twelve Data auth/plan error: %s", message)
                raise MarketDataUnavailable("Live market data provider rejected the request.")
            if code == 404:
                raise NotFoundError(f"No live data found for that symbol. ({message})")
            raise MarketDataUnavailable(message)

        if not resp.is_success:
            raise MarketDataUnavailable(f"Live market data provider error ({resp.status_code}).")

        return data

    async def search_symbol(self, query: str) -> list[dict]:
        key = ("search", query.strip().lower())
        cached = _cache_get(key)
        if cached is not None:
            return cached
        data = await self._get("/symbol_search", {"symbol": query, "outputsize": 15})
        matches = data.get("data", []) or []
        _cache_set(key, matches, _SEARCH_TTL_SECONDS)
        return matches

    async def get_quote(self, symbol: str, exchange: str | None = None) -> dict:
        key = ("quote", symbol.upper(), exchange)
        cached = _cache_get(key)
        if cached is not None:
            return cached
        params: dict[str, Any] = {"symbol": symbol}
        if exchange:
            params["exchange"] = exchange
        data = await self._get("/quote", params)
        if not data or "close" not in data:
            raise NotFoundError(f"Unknown symbol '{symbol}'.")
        _cache_set(key, data, _QUOTE_TTL_SECONDS)
        return data

    async def get_daily_series(
        self, symbol: str, exchange: str | None = None, outputsize: int = 180,
    ) -> dict:
        key = ("history", symbol.upper(), exchange, outputsize)
        cached = _cache_get(key)
        if cached is not None:
            return cached
        params: dict[str, Any] = {
            "symbol": symbol,
            "interval": "1day",
            "outputsize": outputsize,
        }
        if exchange:
            params["exchange"] = exchange
        data = await self._get("/time_series", params)
        if not data.get("values"):
            raise NotFoundError(f"No historical data for '{symbol}'.")
        _cache_set(key, data, _HISTORY_TTL_SECONDS)
        return data
