"""Loader + typed accessors for scoring_weights.json (the single scoring config)."""
from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

CONFIG_PATH = Path(__file__).with_name("scoring_weights.json")


@lru_cache
def load_config() -> dict[str, Any]:
    return json.loads(CONFIG_PATH.read_text())


def component_max_points() -> dict[str, float]:
    cfg = load_config()
    return {k: float(v["max_points"]) for k, v in cfg["components"].items()}


def component_label(key: str) -> str:
    return load_config()["components"][key]["label"]


def severity_for(score: float) -> str:
    bands = load_config()["severity_bands"]
    for name in ("critical", "high", "moderate", "low"):
        if score >= bands[name]:
            return name
    return "minimal"


def case_rules() -> dict[str, Any]:
    return load_config()["case_generation"]


def signal_thresholds() -> dict[str, float]:
    return load_config()["signals"]


def feature_params() -> dict[str, int]:
    return load_config()["features"]


def confidence_config() -> dict[str, Any]:
    return load_config()["confidence"]


def isolation_forest_config() -> dict[str, Any]:
    return load_config()["isolation_forest"]


def source_priority() -> dict[str, int]:
    return load_config()["source_priority"]
