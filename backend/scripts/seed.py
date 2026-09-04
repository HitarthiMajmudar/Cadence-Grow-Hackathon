"""
Idempotent database seed.

    python -m scripts.seed            # seed the configured database
    python -m scripts.seed --fresh    # regenerate the dataset first
    python -m scripts.seed --test     # seed the TEST database

Running it repeatedly does not duplicate users, watchlists, observations or cases.
"""
from __future__ import annotations

import argparse
import asyncio
import logging

from app.core.config import assert_test_database, get_settings
from app.core.logging import configure_logging
from app.data import loader
from app.db.client import database
from app.services.analysis_engine import get_engine, reset_engine
from app.services.seeding import seed_market_data

logger = logging.getLogger("market_detective.seed")


async def seed(*, fresh: bool, use_test_db: bool) -> None:
    settings = get_settings()
    db_name = settings.mongodb_test_db_name if use_test_db else settings.mongodb_db_name
    if use_test_db:
        assert_test_database(db_name, settings)

    if fresh:
        from app.data.generator import generate
        from app.ml.sentiment import _pipeline

        logger.info("regenerating offline dataset ...")
        generate(force=True)
        loader.clear_cache()
        _pipeline.cache_clear()
        reset_engine()

    await database.connect(settings, db_name=db_name)
    logger.info("seeding database '%s' (backend=%s)", db_name, database.backend)
    database.set_autoflush(False)

    engine = get_engine()
    await seed_market_data(engine)

    database.set_autoflush(True)
    database.flush()
    await database.disconnect()
    logger.info("seed complete.")


def main() -> None:
    configure_logging()
    ap = argparse.ArgumentParser(description="Seed the CADENCE database")
    ap.add_argument("--fresh", action="store_true", help="regenerate the offline dataset first")
    ap.add_argument("--test", action="store_true", help="seed the TEST database")
    args = ap.parse_args()
    asyncio.run(seed(fresh=args.fresh, use_test_db=args.test))


if __name__ == "__main__":
    main()
