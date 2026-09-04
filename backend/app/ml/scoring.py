"""
The Attention Score (0-100).

Additive, fully explainable components (weights live in scoring_weights.json).
Data-quality problems reduce *confidence* only — they never raise the score.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field

import numpy as np
import pandas as pd

from app.ml.anomaly import count_agreeing_signals
from app.ml.scoring_config import (
    confidence_config,
    load_config,
    severity_for,
)


def _num(row, key, default=0.0):
    try:
        v = float(row[key])
        return default if (v is None or math.isnan(v)) else v
    except (KeyError, TypeError, ValueError):
        return default


def _saturating(x: float, onset: float, saturation: float, max_points: float,
                exponent: float | None = None) -> float:
    """0 below onset, convex ramp to max_points at saturation.

    A convex curve (exponent > 1) keeps small exceedances cheap so ordinary
    noise scores near zero and only genuine extremes approach the cap.
    """
    if exponent is None:
        exponent = load_config().get("curve_exponent", 1.3)
    x = abs(x)
    if x <= onset:
        return 0.0
    if x >= saturation:
        return max_points
    frac = (x - onset) / (saturation - onset)
    return max_points * (frac ** exponent)


@dataclass
class ComponentScore:
    key: str
    label: str
    points: float
    max_points: float
    detail: str


@dataclass
class AttentionResult:
    score: float
    confidence: float
    severity: str
    components: list[ComponentScore]
    top_reasons: list[str]
    supporting_evidence: list[dict]
    counter_evidence: list[dict]
    data_quality_warnings: list[str]
    signal_agreement: int
    agreeing_axes: list[str] = field(default_factory=list)

    def as_dict(self) -> dict:
        return {
            "score": round(self.score, 1),
            "confidence": round(self.confidence, 1),
            "severity": self.severity,
            "components": [c.__dict__ for c in self.components],
            "top_reasons": self.top_reasons,
            "supporting_evidence": self.supporting_evidence,
            "counter_evidence": self.counter_evidence,
            "data_quality_warnings": self.data_quality_warnings,
            "signal_agreement": self.signal_agreement,
            "agreeing_axes": self.agreeing_axes,
        }


def score_row(row: pd.Series | dict) -> AttentionResult:
    cfg = load_config()
    comps_cfg = cfg["components"]

    ret_z = _num(row, "return_zscore")
    ret_cum_z = _num(row, "ret_cum_zscore")
    ret_cum = _num(row, "ret_cum_short")
    vol_ratio = _num(row, "volume_ratio", 1.0)
    sector_adj_cum = _num(row, "sector_adj_cum")
    market_adj_cum = _num(row, "market_adj_cum")
    vol_regime = _num(row, "volatility_ratio", 1.0)
    news_shift = abs(_num(row, "news_sentiment_shift"))
    news_count_change = _num(row, "news_count_change")
    news_relevance = _num(row, "news_relevance")

    components: list[ComponentScore] = []

    # -- price surprise (stronger of the single-bar and episode z) ----- #
    c = comps_cfg["price_surprise"]
    p_bar = _saturating(ret_z, c["onset_z"], c["saturation_z"], c["max_points"])
    p_cum = _saturating(ret_cum_z, c["onset_z"] + 0.6, c["saturation_z"] + 1.5, c["max_points"])
    p = max(p_bar, p_cum)
    components.append(ComponentScore(
        "price_surprise", c["label"], p, c["max_points"],
        f"Single-bar return z {ret_z:+.2f}; {ret_cum * 100:+.1f}% cumulative move "
        f"over the window (episode z {ret_cum_z:+.2f}).",
    ))

    # -- volume anomaly ---------------------------------------------- #
    c = comps_cfg["volume_anomaly"]
    p = _saturating(vol_ratio, c["onset_ratio"], c["saturation_ratio"], c["max_points"])
    components.append(ComponentScore(
        "volume_anomaly", c["label"], p, c["max_points"],
        f"Volume {vol_ratio:.2f}x its 20-bar rolling average.",
    ))

    # -- sector divergence (cumulative, stock-specific component) ------- #
    c = comps_cfg["sector_divergence"]
    p = _saturating(sector_adj_cum, c["onset_pct"], c["saturation_pct"], c["max_points"])
    components.append(ComponentScore(
        "sector_divergence", c["label"], p, c["max_points"],
        f"Over the window the stock moved {sector_adj_cum * 100:+.2f}% more than the "
        f"rest of its sector.",
    ))

    # -- market divergence ------------------------------------------- #
    c = comps_cfg["market_divergence"]
    p = _saturating(market_adj_cum, c["onset_pct"], c["saturation_pct"], c["max_points"])
    components.append(ComponentScore(
        "market_divergence", c["label"], p, c["max_points"],
        f"Over the window the stock moved {market_adj_cum * 100:+.2f}% more than the "
        f"market index (beta-adjusted).",
    ))

    # -- volatility regime (ratio OR sustained choppiness) ------------ #
    c = comps_cfg["volatility_regime"]
    strength = _num(row, "vol_regime_strength")
    p_ratio = _saturating(vol_regime, c["onset_ratio"], c["saturation_ratio"], c["max_points"])
    p_strength = _saturating(strength, 4.0, 9.0, c["max_points"] * 0.8)
    p = max(p_ratio, p_strength)
    components.append(ComponentScore(
        "volatility_regime", c["label"], p, c["max_points"],
        f"Fast/slow volatility ratio {vol_regime:.2f}; {int(strength)} of the last "
        f"10 bars moved >1.5 sigma (range expansion).",
    ))

    # -- news relevance & sentiment shift ---------------------------- #
    c = comps_cfg["news_relevance_sentiment"]
    news_signal = min(
        1.0,
        0.60 * news_shift
        + 0.30 * min(1.0, abs(news_count_change) / 2.0)
        + 0.30 * news_relevance,
    )
    p = 0.0 if news_signal <= c["onset"] else c["max_points"] * news_signal
    components.append(ComponentScore(
        "news_relevance_sentiment", c["label"], p, c["max_points"],
        f"Local-news activity change {news_count_change:+.0f} with sentiment shift {_num(row, 'news_sentiment_shift'):+.2f}.",
    ))

    # -- signal agreement ------------------------------------------- #
    c = comps_cfg["signal_agreement"]
    n_signals, axes = count_agreeing_signals(row)
    p = min(c["max_points"], max(0, n_signals - 1) * c["per_signal"])
    components.append(ComponentScore(
        "signal_agreement", c["label"], p, c["max_points"],
        f"{n_signals} independent signals agree: {', '.join(axes) if axes else 'none'}.",
    ))

    raw = sum(cc.points for cc in components)
    score = float(np.clip(raw, 0.0, 100.0))

    # -- confidence (data quality reduces this, not the score) ------- #
    conf_cfg = confidence_config()
    pen = conf_cfg["penalties"]
    confidence = float(conf_cfg["base"])
    warnings: list[str] = []

    freshness = str(row.get("freshness_status", "fresh")) if hasattr(row, "get") else "fresh"
    if freshness == "missing" or bool(row.get("is_missing", False) if hasattr(row, "get") else False):
        confidence -= pen["missing"]
        warnings.append("Latest bar is missing from the primary feed.")
    elif freshness == "stale":
        confidence -= pen["stale"]
        warnings.append("Feed is delayed; recent prints repeat the last good value.")
    elif freshness == "delayed":
        confidence -= pen["delayed"]
        warnings.append("Data source is running behind real time.")
    elif freshness == "conflicting":
        confidence -= pen["conflicting"]
        warnings.append("Stored sources disagree on this bar; the higher-priority source was used.")

    hist = _num(row, "history_bars", 999)
    if hist < conf_cfg["short_history_bars"]:
        confidence -= pen["short_history"]
        warnings.append(f"Only {int(hist)} bars of history for a reliable baseline.")

    if _num(row, "news_count", 0) == 0 and score >= 45:
        confidence -= pen["thin_news_window"]

    if not bool(row.get("iso_trained", True) if hasattr(row, "get") else True):
        confidence -= pen["isolation_forest_untrained"]

    confidence = float(np.clip(confidence, conf_cfg["floor"], conf_cfg["ceiling"]))

    severity = severity_for(score)

    # -- reasons / evidence --------------------------------------- #
    ranked = sorted(components, key=lambda x: x.points, reverse=True)
    top_reasons = [f"{c.label}: {c.detail}" for c in ranked if c.points > 0][:3]
    if not top_reasons:
        top_reasons = ["No component crossed its onset threshold — movement looks ordinary."]

    supporting, counter = _evidence(row)

    return AttentionResult(
        score=score, confidence=confidence, severity=severity,
        components=components, top_reasons=top_reasons,
        supporting_evidence=supporting, counter_evidence=counter,
        data_quality_warnings=warnings, signal_agreement=n_signals, agreeing_axes=axes,
    )


def _evidence(row) -> tuple[list[dict], list[dict]]:
    supporting: list[dict] = []
    counter: list[dict] = []

    ret_z = _num(row, "return_zscore")
    ret_cum_z = _num(row, "ret_cum_zscore")
    vol_ratio = _num(row, "volume_ratio", 1.0)
    sector_adj_cum = _num(row, "sector_adj_cum")
    market_adj_cum = _num(row, "market_adj_cum")
    vol_regime = _num(row, "volatility_ratio", 1.0)
    sec_cum = _num(row, "sector_ret_cum_short")
    mkt_cum = _num(row, "market_ret_cum_short")

    if abs(ret_z) >= 2 or abs(ret_cum_z) >= 3:
        supporting.append({"kind": "supporting", "label": "Move is statistically large",
                           "detail": f"Single-bar z {ret_z:+.2f}, episode z {ret_cum_z:+.2f} — "
                                     f"well outside this stock's normal range.",
                           "metric": "return_zscore", "value": round(ret_z, 2)})
    elif abs(ret_z) < 1 and abs(ret_cum_z) < 1.5:
        counter.append({"kind": "counter", "label": "Move is within normal range",
                        "detail": f"Return z-score is only {ret_z:+.2f} (episode z {ret_cum_z:+.2f}).",
                        "metric": "return_zscore", "value": round(ret_z, 2)})

    if vol_ratio >= 1.8:
        supporting.append({"kind": "supporting", "label": "Participation is elevated",
                           "detail": f"Volume ran at {vol_ratio:.2f}x its rolling average.",
                           "metric": "volume_ratio", "value": round(vol_ratio, 2)})
    elif vol_ratio < 1.1:
        counter.append({"kind": "counter", "label": "Volume is unremarkable",
                        "detail": f"Volume was {vol_ratio:.2f}x average — no unusual participation.",
                        "metric": "volume_ratio", "value": round(vol_ratio, 2)})

    if abs(sector_adj_cum) >= 0.015:
        supporting.append({"kind": "supporting", "label": "Diverged from its sector",
                           "detail": f"Stock-specific component is {sector_adj_cum * 100:+.2f}% vs sector peers.",
                           "metric": "sector_adj_cum", "value": round(sector_adj_cum, 4)})
    elif abs(sec_cum) >= 0.02 and abs(sector_adj_cum) < 0.012:
        counter.append({"kind": "counter", "label": "Sector moved together",
                        "detail": f"The rest of the sector moved {sec_cum * 100:+.2f}% over the same window.",
                        "metric": "sector_ret_cum_short", "value": round(sec_cum, 4)})

    if abs(mkt_cum) >= 0.02 and abs(market_adj_cum) < 0.012:
        counter.append({"kind": "counter", "label": "Market moved too",
                        "detail": f"The index moved {mkt_cum * 100:+.2f}% over the same window.",
                        "metric": "market_ret_cum_short", "value": round(mkt_cum, 4)})

    if vol_regime >= 1.4:
        supporting.append({"kind": "supporting", "label": "Volatility regime shifted",
                           "detail": f"Short-horizon volatility is {vol_regime:.2f}x the longer-horizon level.",
                           "metric": "volatility_ratio", "value": round(vol_regime, 2)})

    if _num(row, "news_count") == 0 and abs(ret_z) >= 2:
        counter.append({"kind": "counter", "label": "No local news in the window",
                        "detail": "The move is not explained by any recorded local headline yet.",
                        "metric": "news_count", "value": 0.0})
    elif _num(row, "news_count") >= 1:
        supporting.append({"kind": "supporting", "label": "Local news present",
                           "detail": f"{int(_num(row, 'news_count'))} related headline(s) in the trailing window.",
                           "metric": "news_count", "value": round(_num(row, "news_count"), 0)})

    return supporting[:5], counter[:5]
