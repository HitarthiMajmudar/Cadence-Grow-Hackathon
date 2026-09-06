"""
Database client factory.

Chooses between MongoDB Atlas (Motor) and the file-backed local store based on
configuration, exposes a single ``get_database()`` dependency, and creates all
indexes idempotently.
"""
from __future__ import annotations

import logging
from typing import Any

from app.core.config import Settings, get_settings
from app.db.memory import MemoryClient, MemoryDatabase

logger = logging.getLogger("market_detective.db")

# collection name -> list of index specs; each spec is (keys, options)
INDEX_SPECS: dict[str, list[tuple[Any, dict]]] = {
    "users": [
        ([("email_normalized", 1)], {"unique": True, "name": "uniq_email_normalized"}),
    ],
    "watchlists": [
        ([("user_id", 1), ("name", 1)], {"name": "user_name"}),
        ([("user_id", 1), ("updated_at", -1)], {"name": "user_updated"}),
    ],
    "market_observations": [
        ([("symbol", 1), ("timestamp", 1)], {"name": "symbol_ts"}),
        ([("timestamp", 1)], {"name": "ts"}),
    ],
    "stock_features": [
        ([("symbol", 1), ("timestamp", 1)], {"unique": True, "name": "uniq_symbol_ts"}),
    ],
    "news_events": [
        ([("timestamp", 1)], {"name": "ts"}),
        ([("symbols", 1), ("timestamp", 1)], {"name": "symbols_ts"}),
    ],
    "visit_snapshots": [
        ([("user_id", 1), ("watchlist_id", 1), ("dataset_timestamp", -1)],
         {"name": "user_watchlist_ts"}),
        ([("user_id", 1), ("watchlist_id", 1), ("acknowledged_at", -1)],
         {"name": "user_watchlist_ack"}),
    ],
    "investigation_cases": [
        ([("symbol", 1), ("detection_timestamp", 1)], {"name": "symbol_detect"}),
        ([("attention_score", -1)], {"name": "attention_score"}),
        ([("case_id", 1)], {"unique": True, "name": "uniq_case_id"}),
        ([("detection_timestamp", 1)], {"name": "detect_ts"}),
    ],
    "user_case_states": [
        ([("user_id", 1), ("case_id", 1)], {"unique": True, "name": "uniq_user_case"}),
    ],
    "case_feedback": [
        ([("user_id", 1), ("case_id", 1)], {"name": "user_case"}),
    ],
    "data_quality_events": [
        ([("symbol", 1), ("timestamp", 1)], {"name": "symbol_ts"}),
    ],
    "demo_clock": [
        ([("user_id", 1)], {"unique": True, "name": "uniq_user_id"}),
    ],
}


class Database:
    """Thin wrapper holding the active client + database handle."""

    def __init__(self) -> None:
        self._client: Any = None
        self._db: Any = None
        self._backend: str = "memory"
        self._settings: Settings | None = None

    @property
    def backend(self) -> str:
        return self._backend

    @property
    def db(self) -> Any:
        if self._db is None:
            raise RuntimeError("Database not connected. Call connect() first.")
        return self._db

    async def connect(self, settings: Settings | None = None, *, db_name: str | None = None) -> None:
        settings = settings or get_settings()
        self._settings = settings
        backend = settings.effective_backend
        name = db_name or settings.mongodb_db_name

        if backend == "mongo":
            try:
                from motor.motor_asyncio import AsyncIOMotorClient

                self._client = AsyncIOMotorClient(
                    settings.mongodb_uri,
                    serverSelectionTimeoutMS=5000,
                    uuidRepresentation="standard",
                )
                await self._client.admin.command("ping")
                self._db = self._client[name]
                self._backend = "mongo"
                logger.info("Connected to MongoDB: %s / %s", settings.safe_uri_display(), name)
            except Exception as exc:  # noqa: BLE001
                if settings.db_backend == "mongo":
                    raise
                logger.warning(
                    "MongoDB unavailable (%s). Falling back to the file-backed local store.",
                    exc.__class__.__name__,
                )
                backend = "memory"

        if self._db is None:
            client = MemoryClient(settings.local_store_path)
            self._client = client
            self._db = client.get_database(name)
            self._backend = "memory"
            logger.info("Using file-backed local store at %s", settings.local_store_path)

        await self.ensure_indexes()

    async def ensure_indexes(self) -> None:
        for collection, specs in INDEX_SPECS.items():
            coll = self._db[collection]
            for keys, options in specs:
                try:
                    await coll.create_index(keys, **options)
                except Exception as exc:  # noqa: BLE001
                    if options.get("unique"):
                        raise RuntimeError(
                            f"Required unique index {options.get('name')} on {collection} failed"
                        ) from exc
                    logger.warning("index %s on %s skipped: %s", options.get("name"), collection, exc)

    async def ping(self) -> bool:
        try:
            if self._backend == "mongo":
                await self._client.admin.command("ping")
            return True
        except Exception:  # noqa: BLE001
            return False

    def set_autoflush(self, enabled: bool) -> None:
        if isinstance(self._db, MemoryDatabase):
            self._db.set_autoflush(enabled)

    def flush(self) -> None:
        if isinstance(self._db, MemoryDatabase):
            self._db.flush()

    async def disconnect(self) -> None:
        if self._client is not None:
            self.flush()
            close = getattr(self._client, "close", None)
            if close:
                close()
        self._client = None
        self._db = None


database = Database()


def get_db() -> Any:
    return database.db
