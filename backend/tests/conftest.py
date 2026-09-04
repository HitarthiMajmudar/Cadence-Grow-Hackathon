"""
Shared pytest fixtures.

Unit + service tests run against the file-backed local store (fast, no external
services). If MONGODB_TEST_URI is set, `mongo_db` becomes available for optional
integration tests — and it is guarded so it can never touch the production DB.
"""
from __future__ import annotations

import os
import uuid
from pathlib import Path

import pytest
import pytest_asyncio

os.environ.setdefault("DB_BACKEND", "memory")
os.environ.setdefault("APP_ENV", "test")

from app.core.config import Settings, assert_test_database, get_settings  # noqa: E402
from app.db.client import Database  # noqa: E402


@pytest.fixture(scope="session")
def anyio_backend() -> str:
    return "asyncio"


@pytest.fixture()
def tmp_settings(tmp_path: Path) -> Settings:
    get_settings.cache_clear()
    store = tmp_path / "store"
    store.mkdir()
    s = Settings(
        db_backend="memory",
        local_store_dir=str(store),
        mongodb_db_name="market_detective",
        mongodb_test_db_name="market_detective_test",
        app_env="test",
    )
    return s


@pytest_asyncio.fixture()
async def db(tmp_settings: Settings):
    """A fresh, isolated file-backed database per test."""
    database = Database()
    await database.connect(tmp_settings, db_name="market_detective_test")
    database.set_autoflush(False)  # keep bulk inserts fast during tests
    try:
        yield database
    finally:
        await database.disconnect()


@pytest_asyncio.fixture()
async def repos(db, monkeypatch):
    """Point the repository layer's default handle at the per-test database."""
    import app.db.client as client_mod

    monkeypatch.setattr(client_mod, "get_db", lambda: db.db)
    monkeypatch.setattr(client_mod.database, "_db", db.db, raising=False)
    monkeypatch.setattr(client_mod.database, "_backend", db.backend, raising=False)
    yield db


@pytest.fixture(scope="session")
def engine():
    from app.services.analysis_engine import get_engine

    return get_engine()


@pytest.fixture(scope="session")
def scenario_manifest():
    from app.data.loader import load_scenario_manifest

    return load_scenario_manifest()


@pytest.fixture()
def unique_email() -> str:
    return f"test-{uuid.uuid4().hex[:10]}@example.com"


# --- optional MongoDB integration -------------------------------------------- #

@pytest_asyncio.fixture()
async def mongo_db():
    uri = os.environ.get("MONGODB_TEST_URI")
    if not uri:
        pytest.skip("MONGODB_TEST_URI not set — skipping MongoDB integration test")
    s = get_settings()
    assert_test_database(s.mongodb_test_db_name, s)
    database = Database()
    await database.connect(
        Settings(db_backend="mongo", mongodb_uri=uri,
                 mongodb_db_name=s.mongodb_test_db_name),
        db_name=s.mongodb_test_db_name,
    )
    yield database
    # clean only collections this suite creates
    for name in ("users", "watchlists", "visit_snapshots", "user_case_states",
                 "case_feedback", "demo_clock"):
        await database.db[name].delete_many({})
    await database.disconnect()
