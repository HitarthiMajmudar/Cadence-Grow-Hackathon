"""Market Time Machine — builds the animated-replay payload for a symbol/date range."""
from __future__ import annotations

import numpy as np
import pandas as pd

from app.ml.scoring_config import case_rules
from app.repositories.cases import CaseRepository
from app.services.analysis_engine import get_engine


class ReplayService:
    def __init__(self) -> None:
        self.engine = get_engine()
        self.cases = CaseRepository()

    async def build(self, symbol: str, start, end, *, max_frames: int = 320) -> dict | None:
        symbol = symbol.upper()
        g = self.engine.symbol_frame(symbol)
        if g is None or g.empty:
            return None
        start = pd.Timestamp(start)
        end = pd.Timestamp(end)
        if end <= start:
            end = self.engine.timeline()[-1]

        window = g[(g["timestamp"] >= start) & (g["timestamp"] <= end)].reset_index(drop=True)
        if window.empty:
            window = g.tail(80).reset_index(drop=True)
        if len(window) > max_frames:
            step = int(np.ceil(len(window) / max_frames))
            window = window.iloc[::step].reset_index(drop=True)

        comp = self.engine.comparison_series(symbol, window["timestamp"].iloc[0],
                                             window["timestamp"].iloc[-1])
        comp_by_ts = {pd.Timestamp(p["timestamp"]): p for p in comp.get("points", [])}

        cases = await self.cases.list_between(
            (window["timestamp"].iloc[0] - pd.Timedelta(hours=1)).to_pydatetime(),
            window["timestamp"].iloc[-1].to_pydatetime(),
            symbols=[symbol],
        )
        case_by_bar = {}
        for c in cases:
            idx = _nearest_index(window["timestamp"], pd.Timestamp(c["detection_timestamp"]))
            case_by_bar[idx] = c

        news = [n for n in self.engine.news if symbol in (n.get("symbols") or [])]
        news_markers = []
        news_by_bar: dict[int, list[str]] = {}
        for n in news:
            nts = pd.Timestamp(n["timestamp"])
            if window["timestamp"].iloc[0] <= nts <= window["timestamp"].iloc[-1]:
                idx = _nearest_index(window["timestamp"], nts)
                news_by_bar.setdefault(idx, []).append(n["id"])
                news_markers.append({
                    "id": n["id"], "timestamp": nts.to_pydatetime(), "frame_index": idx,
                    "headline": n["headline"], "event_type": n.get("event_type", "other"),
                    "sentiment_label": n.get("sentiment_label", "neutral"),
                    "sentiment_score": float(n.get("sentiment_score", 0.0)),
                })

        thr = case_rules()["min_attention_score"]
        frames = []
        anomaly_markers = []
        score_evolution = []
        first_close = None
        for i, r in window.iterrows():
            ts = pd.Timestamp(r["timestamp"])
            close = _f(r["close"])
            if first_close is None and close is not None:
                first_close = close
            cp = comp_by_ts.get(ts, {})
            score = float(r["attention_score"])
            case = case_by_bar.get(i)
            verdict = case["verdict"] if case else self._frame_verdict(symbol, ts, r, score, thr)
            level = _anomaly_level(score, thr, bool(case))
            frame = {
                "index": int(i),
                "timestamp": ts.to_pydatetime(),
                "close": close,
                "volume": int(r["volume"]) if not pd.isna(r["volume"]) else 0,
                "stock_indexed": cp.get("stock_indexed", 100.0),
                "sector_indexed": cp.get("sector_indexed", 100.0),
                "market_indexed": cp.get("market_indexed", 100.0),
                "attention_score": round(score, 1),
                "confidence": round(float(r["confidence"]), 1),
                "verdict": verdict,
                "severity": str(r["severity"]),
                "freshness": str(r["freshness_status"]),
                "return_zscore": _f(r["return_zscore"]) or 0.0,
                "volume_ratio": _f(r["volume_ratio"]) or 1.0,
                "is_anomaly": level != "none",
                "anomaly_level": level,
                "case_id": case["case_id"] if case else None,
                "news_ids": news_by_bar.get(i, []),
            }
            frames.append(frame)
            score_evolution.append({"timestamp": ts.to_pydatetime(), "attention_score": round(score, 1),
                                    "confidence": round(float(r["confidence"]), 1)})
            if level != "none":
                anomaly_markers.append({
                    "frame_index": int(i), "timestamp": ts.to_pydatetime(), "level": level,
                    "attention_score": round(score, 1), "verdict": verdict,
                    "case_id": case["case_id"] if case else None,
                    "label": f"{verdict} · score {round(score)}",
                })

        meta = self.engine.meta
        return {
            "symbol": symbol,
            "company_name": self.engine.name_of.get(symbol, symbol),
            "sector": self.engine.sector_of.get(symbol, ""),
            "market_index": self.engine.market_symbol,
            "start": window["timestamp"].iloc[0].to_pydatetime(),
            "end": window["timestamp"].iloc[-1].to_pydatetime(),
            "frame_count": len(frames),
            "bars_per_day": self.engine.bars_per_day,
            "frames": frames,
            "news_markers": sorted(news_markers, key=lambda m: m["frame_index"]),
            "anomaly_markers": anomaly_markers,
            "score_evolution": score_evolution,
            "who_moved_first": comp.get("who_moved_first"),
            "first_mover_detail": comp.get("first_mover_detail", ""),
            "dataset_label": meta.get("label", "Offline Research Dataset"),
        }

    def _frame_verdict(self, symbol, ts, row, score, thr) -> str:
        if score < thr - 18:
            return "Normal movement"
        return self.engine._verdict_at(symbol, ts, row)[0]

    async def anomaly_markers(self, symbol: str, start, end) -> list[dict]:
        payload = await self.build(symbol, start, end)
        return payload["anomaly_markers"] if payload else []

    async def news_markers(self, symbol: str, start, end) -> list[dict]:
        payload = await self.build(symbol, start, end)
        return payload["news_markers"] if payload else []

    async def score_evolution(self, symbol: str, start, end) -> list[dict]:
        payload = await self.build(symbol, start, end)
        return payload["score_evolution"] if payload else []


def _f(x) -> float | None:
    try:
        if x is None:
            return None
        v = float(x)
        return None if np.isnan(v) else round(v, 4)
    except (TypeError, ValueError):
        return None


def _nearest_index(timestamps: pd.Series, ts: pd.Timestamp) -> int:
    diffs = (timestamps - ts).abs()
    return int(diffs.values.argmin())


def _anomaly_level(score: float, threshold: float, has_case: bool) -> str:
    if score >= threshold + 14 or (has_case and score >= threshold):
        return "serious"
    if score >= threshold - 6:
        return "moderate"
    return "none"
