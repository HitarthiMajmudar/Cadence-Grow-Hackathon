"""
Anomaly detection.

Two layers, deliberately kept separate:

1. Transparent statistical scoring (z-scores, ratios, regime comparison) — the
   primary, fully explainable signal.
2. Isolation Forest over a handful of standardised features — a SUPPORTING
   signal only. If there is not enough data to train it, it is skipped and a
   small confidence penalty is recorded; it never becomes the sole basis for a
   verdict.
"""
from __future__ import annotations

import logging

import numpy as np
import pandas as pd

from app.ml.scoring_config import isolation_forest_config, signal_thresholds

logger = logging.getLogger("market_detective.ml")

ISO_FEATURES = [
    "return_zscore",
    "volume_zscore",
    "volatility_ratio",
    "sector_adjusted_return",
    "market_adjusted_return",
    "dist_from_ma",
]


def add_isolation_forest(features: pd.DataFrame) -> pd.DataFrame:
    """Attach ``iso_forest_score`` (0..1, higher = more anomalous) + ``iso_trained``."""
    cfg = isolation_forest_config()
    out = features.copy()
    out["iso_forest_score"] = 0.0
    out["iso_trained"] = False

    if not cfg.get("enabled", True):
        return out

    mat = out[ISO_FEATURES].replace([np.inf, -np.inf], np.nan)
    mask = mat.notna().all(axis=1)
    usable = mat[mask]

    if len(usable) < cfg["min_training_rows"]:
        logger.info("Isolation Forest skipped: only %d usable rows", len(usable))
        return out

    try:
        from sklearn.ensemble import IsolationForest
        from sklearn.preprocessing import RobustScaler

        scaler = RobustScaler()
        X = scaler.fit_transform(usable.values)
        model = IsolationForest(
            n_estimators=cfg["n_estimators"],
            contamination=cfg["contamination"],
            random_state=cfg["random_state"],
            n_jobs=1,
        )
        model.fit(X)
        raw = -model.score_samples(X)  # higher = more anomalous
        lo, hi = np.percentile(raw, 5), np.percentile(raw, 99)
        norm = np.clip((raw - lo) / (hi - lo + 1e-9), 0.0, 1.0)
        out.loc[mask, "iso_forest_score"] = norm
        out.loc[mask, "iso_trained"] = True
        logger.info("Isolation Forest trained on %d rows", len(usable))
    except Exception as exc:  # noqa: BLE001
        logger.warning("Isolation Forest failed (%s) — continuing without it", exc)

    return out


def count_agreeing_signals(row: pd.Series | dict) -> tuple[int, list[str]]:
    """How many independent signals fire for this bar (used by signal_agreement)."""
    th = signal_thresholds()
    fired: list[str] = []

    def val(k: str, default: float = 0.0) -> float:
        v = row[k] if k in row else default
        try:
            v = float(v)
        except (TypeError, ValueError):
            return default
        return default if np.isnan(v) else v

    if (abs(val("return_zscore")) >= th["return_z_threshold"]
            or abs(val("ret_cum_zscore")) >= th["return_cum_z_threshold"]):
        fired.append("price")
    if val("volume_ratio", 1.0) >= th["volume_ratio_threshold"]:
        fired.append("volume")
    if abs(val("sector_adj_cum")) >= th["sector_divergence_pct"]:
        fired.append("sector")
    if abs(val("market_adj_cum")) >= th["market_divergence_pct"]:
        fired.append("market")
    if val("volatility_ratio", 1.0) >= th["volatility_ratio_threshold"]:
        fired.append("volatility")
    if abs(val("news_sentiment_shift")) >= th["news_shift_threshold"] or val("news_count_change") >= 1:
        fired.append("news")
    if val("iso_forest_score") >= 0.7:
        fired.append("iso_forest")

    # de-duplicate to at most one point per conceptual axis
    axes = set(fired)
    return len(axes), sorted(axes)


def statistical_flags(row: pd.Series | dict) -> dict:
    """Boolean context flags used by the verdict tree + detectives."""
    th = signal_thresholds()

    def val(k, d=0.0):
        try:
            v = float(row[k])
            return d if np.isnan(v) else v
        except (KeyError, TypeError, ValueError):
            return d

    ret_z = val("return_zscore")
    ret_cum_z = val("ret_cum_zscore")
    ret_cum = val("ret_cum_short")
    sector_adj_cum = val("sector_adj_cum")
    market_adj_cum = val("market_adj_cum")
    cz = th["return_cum_z_threshold"]
    price_dir = 1 if ret_cum > 0 else (-1 if ret_cum < 0 else (1 if ret_z > 0 else -1))
    return {
        "price_unusual": abs(ret_z) >= th["return_z_threshold"] or abs(ret_cum_z) >= cz,
        "price_extreme": abs(ret_z) >= th["return_z_threshold"] + 1.5 or abs(ret_cum_z) >= cz + 1.5,
        "price_direction": price_dir,
        "volume_unusual": val("volume_ratio", 1.0) >= th["volume_ratio_threshold"],
        "sector_divergent": abs(sector_adj_cum) >= th["sector_divergence_pct"],
        "market_divergent": abs(market_adj_cum) >= th["market_divergence_pct"],
        "moved_with_sector": abs(sector_adj_cum) < th["sector_divergence_pct"]
        and abs(val("sector_ret_cum_short")) >= 0.02,
        "moved_with_market": abs(market_adj_cum) < th["market_divergence_pct"]
        and abs(val("market_ret_cum_short")) >= 0.02,
        "volatility_regime": val("volatility_ratio", 1.0) >= th["volatility_ratio_threshold"],
        "breakout": val("breakout_strength") >= 0.6,
        "breakdown": val("breakdown_strength") >= 0.6,
        "has_recent_news": val("news_count") >= 1,
        "news_sentiment": val("news_sentiment"),
        "news_shift": val("news_sentiment_shift"),
        "iso_flag": val("iso_forest_score") >= 0.7,
    }
