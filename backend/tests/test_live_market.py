"""Live Markets — auth gating and graceful behaviour with no API key configured.

A real Twelve Data key is required for full coverage of search/quote/history
parsing; that's exercised manually (see docs), not in CI.
"""
from __future__ import annotations

import httpx
import pytest
from asgi_lifespan import LifespanManager

pytestmark = pytest.mark.asyncio


@pytest.fixture()
async def client(tmp_path, monkeypatch):
    store = tmp_path / "live-store"
    store.mkdir()
    monkeypatch.setenv("DB_BACKEND", "memory")
    monkeypatch.setenv("LOCAL_STORE_DIR", str(store))
    monkeypatch.setenv("MONGODB_URI", "")
    monkeypatch.setenv("JWT_SECRET_KEY", "test-secret-key-not-for-prod")
    # Force-clear rather than delenv: pydantic-settings also reads backend/.env,
    # so a real local TWELVE_DATA_API_KEY there would otherwise leak into this test.
    monkeypatch.setenv("TWELVE_DATA_API_KEY", "")

    from app.core.config import get_settings
    from app.db.client import database

    get_settings.cache_clear()
    await database.disconnect()

    from app.main import create_app

    app = create_app()
    async with LifespanManager(app):
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
            yield c
    await database.disconnect()
    get_settings.cache_clear()


async def _auth_header(client: httpx.AsyncClient) -> dict:
    r = await client.post(
        "/api/auth/signup",
        json={"name": "Live", "email": "live@example.com", "password": "Password123!"})
    assert r.status_code == 201
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


async def test_live_search_requires_auth(client):
    r = await client.get("/api/live/search", params={"q": "AAPL"})
    assert r.status_code == 401


async def test_live_endpoints_503_without_api_key(client):
    h = await _auth_header(client)
    r = await client.get("/api/live/search", params={"q": "AAPL"}, headers=h)
    assert r.status_code == 503
    assert r.json()["code"] == "market_data_not_configured"

    r = await client.get("/api/live/AAPL/quote", headers=h)
    assert r.status_code == 503

    r = await client.get("/api/live/AAPL/history", headers=h)
    assert r.status_code == 503
