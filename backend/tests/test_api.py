"""End-to-end API tests through the ASGI app (in-process, no network)."""
from __future__ import annotations

import httpx
import pytest
from asgi_lifespan import LifespanManager

pytestmark = pytest.mark.asyncio

PASSWORD = "Password123!"


@pytest.fixture()
async def client(tmp_path, monkeypatch):
    store = tmp_path / "api-store"
    store.mkdir()
    monkeypatch.setenv("DB_BACKEND", "memory")
    monkeypatch.setenv("LOCAL_STORE_DIR", str(store))
    monkeypatch.setenv("MONGODB_URI", "")
    monkeypatch.setenv("JWT_SECRET_KEY", "test-secret-key-not-for-prod")

    from app.core.config import get_settings
    from app.db.client import database  # the shared singleton main.py also uses

    get_settings.cache_clear()
    await database.disconnect()  # reset before the lifespan reconnects to tmp store

    from app.main import create_app

    app = create_app()
    async with LifespanManager(app):
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
            yield c
    await database.disconnect()
    get_settings.cache_clear()


async def _signup(client: httpx.AsyncClient, email="judge@example.com", password=PASSWORD) -> dict:
    r = await client.post(
        "/api/auth/signup", json={"name": "Judge", "email": email, "password": password})
    assert r.status_code == 201, r.text
    return r.json()


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


async def test_health(client):
    r = await client.get("/api/health")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ok"
    assert body["cases"] > 0


async def test_signup_creates_user_and_watchlist(client):
    body = await _signup(client)
    assert body["user"]["email"] == "judge@example.com"
    h = _auth(body["access_token"])
    r = await client.get("/api/watchlists", headers=h)
    assert r.status_code == 200
    assert len(r.json()) == 1
    assert r.json()[0]["symbols"]


async def test_duplicate_signup_conflicts_but_login_succeeds(client):
    first = await _signup(client, "same@example.com")
    dup = await client.post(
        "/api/auth/signup",
        json={"name": "Judge", "email": "same@example.com", "password": PASSWORD})
    assert dup.status_code == 409

    login = await client.post(
        "/api/auth/login", json={"email": "same@example.com", "password": PASSWORD})
    assert login.status_code == 200
    assert login.json()["user"]["id"] == first["user"]["id"]

    bad = await client.post(
        "/api/auth/login", json={"email": "same@example.com", "password": "wrong-password"})
    assert bad.status_code == 401


async def test_requires_auth_header(client):
    r = await client.get("/api/watchlists")
    assert r.status_code == 401

    r = await client.get("/api/watchlists", headers={"Authorization": "Bearer garbage-token"})
    assert r.status_code == 401


async def test_full_demo_journey(client):
    body = await _signup(client)
    h = _auth(body["access_token"])

    wl = (await client.get("/api/watchlists", headers=h)).json()[0]
    wid = wl["id"]

    clock0 = (await client.get("/api/demo-clock", headers=h)).json()
    assert clock0["bars_from_present"] == 0

    # advance twice
    for _ in range(2):
        r = await client.post("/api/demo-clock/advance", headers=h)
        assert r.status_code == 200
    clock1 = (await client.get("/api/demo-clock", headers=h)).json()
    assert clock1["bars_from_present"] > 0
    assert clock1["current_dataset_timestamp"] > clock0["current_dataset_timestamp"]

    # briefing after the jump
    br = (await client.get(f"/api/briefings?watchlist_id={wid}", headers=h)).json()
    assert "simulated market hours" in br["summary_line"]
    assert len(br["changes"]) == len(wl["symbols"])

    # ranked cases
    cases = (await client.get(f"/api/cases?watchlist_id={wid}&budget=all", headers=h)).json()
    assert cases["total"] >= 1
    pool = cases["needs_attention"] + cases["still_investigating"] + cases["explained"]
    assert pool, "expected at least one case for the demo watchlist"
    case_id = pool[0]["case_id"]

    detail = (await client.get(f"/api/cases/{case_id}", headers=h)).json()
    assert 0 <= detail["attention_score"] <= 100
    assert len(detail["detectives"]) == 4
    assert "components" in detail["breakdown"]

    # story card
    card = (await client.get(f"/api/cases/{case_id}/story-card", headers=h)).json()
    assert card["verdict"] == detail["verdict"]
    assert card["disclaimer"] == "Educational market analysis. Not investment advice."

    # replay
    sym = detail["symbol"]
    replay = (await client.get(f"/api/replay/{sym}?lookback_bars=80", headers=h)).json()
    assert replay["frame_count"] > 10
    assert all(0 <= f["attention_score"] <= 100 for f in replay["frames"])

    # mark seen -> snapshot persists
    r = await client.post("/api/briefings/mark-seen", headers=h, json={"watchlist_id": wid})
    assert r.status_code == 200
    br2 = (await client.get(f"/api/briefings?watchlist_id={wid}", headers=h)).json()
    assert br2["has_previous_snapshot"] is True

    # reset clock
    r = await client.post("/api/demo-clock/reset", headers=h)
    assert r.json()["bars_from_present"] == 0


async def test_case_status_is_user_specific(client):
    a = await _signup(client, "a2@example.com")
    b = await _signup(client, "b2@example.com")
    ha, hb = _auth(a["access_token"]), _auth(b["access_token"])
    cases = (await client.get("/api/cases?scope=all&budget=all", headers=ha)).json()
    pool = cases["needs_attention"] + cases["still_investigating"] + cases["explained"]
    cid = pool[0]["case_id"]

    await client.patch(f"/api/cases/{cid}/status", headers=ha, json={"status": "dismissed"})
    da = (await client.get(f"/api/cases/{cid}", headers=ha)).json()
    db_ = (await client.get(f"/api/cases/{cid}", headers=hb)).json()
    assert da["status"] == "dismissed"
    assert db_["status"] in ("new", "viewed")  # unaffected for user B


async def test_watchlist_delete_guard(client):
    body = await _signup(client, "guard@example.com")
    h = _auth(body["access_token"])
    wl = (await client.get("/api/watchlists", headers=h)).json()[0]
    r = await client.delete(f"/api/watchlists/{wl['id']}", headers=h)
    assert r.status_code == 409  # cannot delete the last watchlist


async def test_stock_endpoints(client):
    body = await _signup(client, "stocks@example.com")
    h = _auth(body["access_token"])
    stocks = (await client.get("/api/stocks")).json()
    assert len(stocks) >= 8
    sym = stocks[0]["symbol"]
    state = (await client.get(f"/api/stocks/{sym}/state", headers=h)).json()
    assert state["symbol"] == sym
    comp = (await client.get(f"/api/stocks/{sym}/comparison", headers=h)).json()
    assert len(comp["points"]) > 5
