"""CADENCE — FastAPI application entry point."""
from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.router import api_router
from app.core.config import get_settings, validate_startup
from app.core.errors import register_error_handlers
from app.core.logging import configure_logging
from app.db.client import database

logger = logging.getLogger("market_detective")

DESCRIPTION = """
**CADENCE** — *"cause every market move has a rhythm."*

An educational market-analysis prototype. **Detective Mode** compares what you
last saw with the latest state of an **Offline Research Dataset**, turns
meaningful changes into evidence-backed **Investigation Cases**, and replays
them in the **Market Time Machine** — all of it computed locally, with no
external market, news or LLM APIs. A separate **Live Markets** feature calls
the Twelve Data API for real quotes on any symbol you search; it has no
Attention Score and is not part of Detective Mode's analysis engine.

This tool does **not** give buy / sell / hold advice.
"""


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    configure_logging()
    for warning in validate_startup(settings):
        logger.warning(warning)

    await database.connect(settings)
    logger.info("persistence backend: %s", database.backend)

    # warm the analysis engine so the first request is fast
    from app.services.analysis_engine import get_engine
    engine = get_engine()
    engine.generate_cases()
    logger.info("analysis engine warm (%d scored bars)", len(engine.features))

    # convenience: seed automatically the first time so `uvicorn app.main:app`
    # works with no separate step. `python -m scripts.seed` stays the explicit path.
    try:
        from app.services.seeding import auto_seed_if_empty

        database.set_autoflush(False)
        if await auto_seed_if_empty(engine):
            logger.info("auto-seed complete")
        database.set_autoflush(True)
        database.flush()
    except Exception as exc:  # noqa: BLE001
        logger.warning("auto-seed skipped: %s", exc)

    yield

    await database.disconnect()


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title="CADENCE API",
        description=DESCRIPTION,
        version="1.0.0",
        lifespan=lifespan,
        docs_url="/docs",
        redoc_url="/redoc",
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    register_error_handlers(app)
    app.include_router(api_router)

    @app.get("/", include_in_schema=False)
    async def root() -> dict:
        return {"name": "CADENCE API", "docs": "/docs", "health": "/api/health"}

    return app


app = create_app()
