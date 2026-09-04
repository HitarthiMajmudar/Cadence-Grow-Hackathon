"""Loads the Offline Research Dataset from data/generated/ into memory."""
from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

import pandas as pd

from app.core.config import DATASET_DIR


class DatasetMissingError(RuntimeError):
    pass


def _require(path: Path) -> Path:
    if not path.exists():
        raise DatasetMissingError(
            f"{path.name} not found in data/generated/. "
            f"Run:  python -m app.data.generator"
        )
    return path


@lru_cache
def load_meta() -> dict:
    return json.loads(_require(DATASET_DIR / "dataset_meta.json").read_text())


@lru_cache
def load_stocks() -> list[dict]:
    return json.loads(_require(DATASET_DIR / "stocks.json").read_text())


@lru_cache
def load_sectors() -> dict:
    return json.loads(_require(DATASET_DIR / "sectors.json").read_text())


@lru_cache
def load_news() -> list[dict]:
    return json.loads(_require(DATASET_DIR / "news_headlines.json").read_text())


@lru_cache
def load_quality_events() -> list[dict]:
    path = DATASET_DIR / "data_quality_events.json"
    return json.loads(path.read_text()) if path.exists() else []


@lru_cache
def load_scenario_manifest() -> list[dict]:
    """PRIVATE — tests only. The inference engine must never call this."""
    path = DATASET_DIR / "scenario_manifest.json"
    return json.loads(path.read_text()) if path.exists() else []


def load_observations() -> pd.DataFrame:
    df = pd.read_csv(_require(DATASET_DIR / "market_observations.csv"))
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    return df


def market_symbol() -> str:
    return load_meta()["market_index"]


def stock_symbols() -> list[str]:
    return [s["symbol"] for s in load_stocks()]


def sector_members() -> dict[str, list[str]]:
    return {s["id"]: s["symbols"] for s in load_sectors()["sectors"]}


def dataset_present_timestamp() -> pd.Timestamp:
    return pd.to_datetime(load_meta()["demo_present_timestamp"])


def dataset_bounds() -> tuple[pd.Timestamp, pd.Timestamp]:
    m = load_meta()
    return pd.to_datetime(m["first_timestamp"]), pd.to_datetime(m["last_timestamp"])


def all_bar_timestamps() -> list[pd.Timestamp]:
    obs = load_observations()
    return sorted(obs["timestamp"].unique().tolist())  # type: ignore[return-value]


def clear_cache() -> None:
    for fn in (load_meta, load_stocks, load_sectors, load_news,
               load_quality_events, load_scenario_manifest):
        fn.cache_clear()
