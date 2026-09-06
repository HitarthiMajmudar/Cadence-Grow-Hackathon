from unittest.mock import AsyncMock

import httpx
import pytest

from app.services.live_market_service import LiveMarketService, _to_float, _to_int
from app.services.twelve_data_client import MarketDataUnavailable, TwelveDataClient


@pytest.mark.parametrize("value", ["NaN", "Infinity", "-Infinity", None, "bad"])
def test_invalid_numeric_values_are_missing(value):
    assert _to_float(value) is None
    assert _to_int(value) is None


@pytest.mark.asyncio
async def test_missing_price_does_not_become_zero(monkeypatch):
    service = LiveMarketService()
    monkeypatch.setattr(service.client, "get_quote", AsyncMock(return_value={"close": "null"}))
    with pytest.raises(MarketDataUnavailable):
        await service.quote("AAPL")


@pytest.mark.asyncio
@pytest.mark.parametrize("payload", [None, [], "unexpected"])
async def test_non_object_provider_response_is_502(monkeypatch, payload):
    client = TwelveDataClient()
    monkeypatch.setattr(client, "_require_key", lambda: "test-key")
    monkeypatch.setattr(httpx.AsyncClient, "get", AsyncMock(return_value=httpx.Response(200, json=payload)))
    with pytest.raises(MarketDataUnavailable) as caught:
        await client._get("/quote", {"symbol": "AAPL"})
    assert caught.value.status_code == 502
