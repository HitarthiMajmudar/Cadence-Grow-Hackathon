"""Failure paths must preserve authentication and persistence guarantees."""
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.core.config import Settings, validate_startup
from app.db.client import Database


@pytest.mark.parametrize("secret", [None, "", "   "])
@pytest.mark.parametrize("environment", ["dev", "test", "prod"])
def test_startup_requires_jwt_secret(secret, environment):
    settings = Settings(_env_file=None, db_backend="memory", app_env=environment,
                        jwt_secret_key=secret)
    with pytest.raises(RuntimeError, match="JWT_SECRET_KEY"):
        validate_startup(settings)


@pytest.mark.asyncio
async def test_required_unique_index_failure_is_fatal():
    database = Database()
    collection = MagicMock()
    collection.create_index = AsyncMock(side_effect=RuntimeError("duplicate data"))
    database._db = {"users": collection}
    with pytest.raises(RuntimeError, match="Required unique index uniq_email_normalized"):
        await database.ensure_indexes()


@pytest.mark.asyncio
async def test_optional_index_failure_is_best_effort(monkeypatch):
    import app.db.client as module

    monkeypatch.setattr(module, "INDEX_SPECS", {"optional": [([("x", 1)], {"name": "x"})]})
    database = Database()
    collection = MagicMock()
    collection.create_index = AsyncMock(side_effect=RuntimeError("unavailable"))
    database._db = {"optional": collection}
    await database.ensure_indexes()


@pytest.mark.asyncio
async def test_seed_failure_restores_autoflush_and_disconnects(monkeypatch):
    import app.main as module
    import app.services.analysis_engine as analysis
    import app.services.seeding as seeding

    database = MagicMock()
    database.connect = AsyncMock()
    database.disconnect = AsyncMock()
    monkeypatch.setattr(module, "database", database)
    monkeypatch.setattr(module, "validate_startup", lambda _: [])
    monkeypatch.setattr(analysis, "get_engine", MagicMock(return_value=MagicMock()))
    monkeypatch.setattr(seeding, "auto_seed_if_empty", AsyncMock(side_effect=RuntimeError("seed failed")))
    async with module.lifespan(module.create_app()):
        assert [call.args for call in database.set_autoflush.call_args_list] == [(False,), (True,)]
        database.flush.assert_called_once()
    database.disconnect.assert_awaited_once()
