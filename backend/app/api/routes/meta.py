from __future__ import annotations

from fastapi import APIRouter

from app.db.client import database
from app.ml.scoring_config import load_config
from app.ml.sentiment import model_is_trained
from app.services.analysis_engine import get_engine

router = APIRouter(tags=["meta"])


@router.get("/health")
async def health() -> dict:
    engine = get_engine()
    return {
        "status": "ok",
        "db_backend": database.backend,
        "db_connected": await database.ping(),
        "dataset_label": engine.meta.get("label"),
        "dataset_first_timestamp": engine.meta.get("first_timestamp"),
        "dataset_last_timestamp": engine.meta.get("last_timestamp"),
        "dataset_present_timestamp": engine.meta.get("demo_present_timestamp"),
        "sentiment_model": "tfidf_logreg" if model_is_trained() else "rules",
        "scored_bars": len(engine.features),
        "cases": len(engine.generate_cases()),
    }


@router.get("/meta/dataset")
async def dataset_meta() -> dict:
    engine = get_engine()
    return {
        **engine.meta,
        "sectors": engine.sectors,
        "stocks": engine.stocks,
    }


@router.get("/meta/scoring-config")
async def scoring_config() -> dict:
    """The single Attention-Score configuration file, exposed read-only."""
    return load_config()
