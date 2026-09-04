"""
Market analysis engine — the "brain".

Builds the trailing-safe feature matrix for every stock once, scores every bar,
and turns score episodes into Investigation Cases (verdict + Evidence Court +
deterministic explanation + retrospective news sequence).

The running API uses this in-memory for live per-timestamp state; the seed
script uses it to persist cases + features to MongoDB.
"""
from __future__ import annotations

import hashlib
import logging
from datetime import datetime, timedelta

import numpy as np
import pandas as pd

from app.data import loader
from app.ml.anomaly import add_isolation_forest, statistical_flags
from app.ml.detectives import CourtContext, court_tally, run_court
from app.ml.explain import build_explanation
from app.ml.features import FeatureEngine
from app.ml.scoring import score_row
from app.ml.scoring_config import case_rules, load_config, source_priority
from app.ml.sentiment import analyze_sentiment, classify_event_type, model_is_trained
from app.ml.verdict import decide_verdict
from app.schemas.common import Verdict

logger = logging.getLogger("market_detective.engine")

SCORE_COLS = ["attention_score", "confidence", "severity", "signal_agreement"]


class AnalysisEngine:
    def __init__(self) -> None:
        self.meta = loader.load_meta()
        self.stocks = loader.load_stocks()
        self.sectors = loader.load_sectors()
        self.news = self._prepare_news(loader.load_news())
        self.quality_events = loader.load_quality_events()
        self.market_symbol = self.meta["market_index"]
        self.bars_per_day = self.meta["bars_per_day"]
        self.name_of = {s["symbol"]: s["name"] for s in self.stocks}
        self.sector_of = {s["symbol"]: s["sector"] for s in self.stocks}
        self.sector_name = {s["id"]: s["name"] for s in self.sectors["sectors"]}

        obs = loader.load_observations()
        self.observations = obs
        self._timeline = sorted(obs["timestamp"].unique().tolist())

        fe = FeatureEngine(obs, self.stocks, self.sectors, self.news, self.market_symbol)
        feats = fe.compute()
        feats = add_isolation_forest(feats)
        self.features = self._score(feats)
        self._by_symbol = {s: g.sort_values("timestamp").reset_index(drop=True)
                           for s, g in self.features.groupby("symbol")}
        self._cases: list[dict] | None = None
        self._related_news_cache: dict[str, tuple] = {}
        logger.info(
            "AnalysisEngine ready: %d stocks, %d scored bars, sentiment=%s",
            len(self._by_symbol), len(self.features),
            "tfidf_logreg" if model_is_trained() else "rules",
        )

    # ------------------------------------------------------------------ #
    # setup helpers
    # ------------------------------------------------------------------ #
    def _prepare_news(self, news: list[dict]) -> list[dict]:
        out = []
        for n in news:
            item = dict(n)
            if "event_type" not in item or not item["event_type"]:
                item["event_type"] = classify_event_type(item["headline"])
            # keep generated sentiment but re-derive label via the local model for consistency
            model = analyze_sentiment(item["headline"])
            item.setdefault("sentiment_score", model["score"])
            item["sentiment_label"] = model["label"]
            item["model_sentiment_score"] = model["score"]
            out.append(item)
        return out

    def _score(self, feats: pd.DataFrame) -> pd.DataFrame:
        # iterate dict records (≈10x faster than Series-based .apply over many rows)
        records = feats.to_dict("records")
        results = [score_row(r) for r in records]
        feats = feats.copy()
        feats["attention_score"] = [r.score for r in results]
        feats["confidence"] = [r.confidence for r in results]
        feats["severity"] = [r.severity for r in results]
        feats["signal_agreement"] = [r.signal_agreement for r in results]
        feats["_score_obj"] = results
        return feats

    # ------------------------------------------------------------------ #
    # timeline utilities
    # ------------------------------------------------------------------ #
    def timeline(self) -> list[pd.Timestamp]:
        return list(self._timeline)

    def clamp_timestamp(self, ts: datetime | pd.Timestamp) -> pd.Timestamp:
        ts = pd.Timestamp(ts)
        lo, hi = self._timeline[0], self._timeline[-1]
        return max(lo, min(ts, hi))

    def bar_index(self, ts: datetime | pd.Timestamp) -> int:
        ts = pd.Timestamp(ts)
        idx = np.searchsorted(self._timeline, ts, side="right") - 1
        return int(max(0, min(idx, len(self._timeline) - 1)))

    def advance_timestamp(self, ts: datetime | pd.Timestamp, bars: int) -> pd.Timestamp:
        i = self.bar_index(ts)
        return self._timeline[min(i + bars, len(self._timeline) - 1)]

    def bars_between(self, a: datetime | pd.Timestamp, b: datetime | pd.Timestamp) -> int:
        return self.bar_index(b) - self.bar_index(a)

    # ------------------------------------------------------------------ #
    # per-symbol state at a timestamp
    # ------------------------------------------------------------------ #
    def symbol_frame(self, symbol: str) -> pd.DataFrame:
        return self._by_symbol.get(symbol, pd.DataFrame())

    def row_at(self, symbol: str, ts: datetime | pd.Timestamp) -> pd.Series | None:
        g = self._by_symbol.get(symbol)
        if g is None or g.empty:
            return None
        ts = pd.Timestamp(ts)
        sub = g[g["timestamp"] <= ts]
        if sub.empty:
            return None
        return sub.iloc[-1]

    def observation_at(self, symbol: str, ts: datetime | pd.Timestamp) -> dict | None:
        o = self.observations
        sub = o[(o["symbol"] == symbol) & (o["timestamp"] <= pd.Timestamp(ts))]
        if sub.empty:
            return None
        return sub.sort_values("timestamp").iloc[-1].to_dict()

    def spark(self, symbol: str, ts: datetime | pd.Timestamp, n: int = 24) -> list[float]:
        g = self._by_symbol.get(symbol)
        if g is None or g.empty:
            return []
        sub = g[g["timestamp"] <= pd.Timestamp(ts)].tail(n)
        return [round(float(x), 2) for x in sub["close"].ffill().tolist()]

    def state_at(self, symbol: str, ts: datetime | pd.Timestamp) -> dict:
        ts = pd.Timestamp(ts)
        row = self.row_at(symbol, ts)
        g = self._by_symbol.get(symbol, pd.DataFrame())
        prev_close = None
        price = None
        day_volume = 0
        if not g.empty:
            sub = g[g["timestamp"] <= ts]
            if len(sub) >= 1:
                price = _f(sub.iloc[-1]["close"])
            if len(sub) >= 2:
                prev_close = _f(sub.iloc[-2]["close"])
            day = ts.normalize()
            day_volume = int(sub[sub["timestamp"] >= day]["volume"].sum())

        change_abs = (price - prev_close) if (price is not None and prev_close) else None
        change_pct = (change_abs / prev_close * 100.0) if (change_abs is not None and prev_close) else None

        score = float(row["attention_score"]) if row is not None else 0.0
        confidence = float(row["confidence"]) if row is not None else 60.0
        severity = str(row["severity"]) if row is not None else "minimal"
        freshness = str(row["freshness_status"]) if row is not None else "fresh"

        verdict = None
        if row is not None and score >= case_rules()["min_attention_score"] - 12:
            verdict = self._verdict_at(symbol, ts, row)[0]

        return {
            "symbol": symbol,
            "name": self.name_of.get(symbol, symbol),
            "sector": self.sector_of.get(symbol, ""),
            "sector_name": self.sector_name.get(self.sector_of.get(symbol, ""), ""),
            "as_of": ts.to_pydatetime(),
            "price": price,
            "previous_close": prev_close,
            "change_pct": round(change_pct, 2) if change_pct is not None else None,
            "change_abs": round(change_abs, 2) if change_abs is not None else None,
            "day_volume": day_volume,
            "attention_score": round(score, 1),
            "confidence": round(confidence, 1),
            "severity": severity,
            "verdict": verdict,
            "freshness": freshness,
            "spark": self.spark(symbol, ts),
        }

    # ------------------------------------------------------------------ #
    # retrospective news context
    # ------------------------------------------------------------------ #
    def _related_news(self, symbol: str) -> tuple:
        cached = self._related_news_cache.get(symbol)
        if cached is None:
            rel = sorted(
                (n for n in self.news if symbol in (n.get("symbols") or [])),
                key=lambda n: n["timestamp"],
            )
            cached = tuple(rel)
            self._related_news_cache[symbol] = cached
        return cached

    def news_context(self, symbol: str, ts: pd.Timestamp, window_bars: int | None = None) -> CourtContext:
        window_bars = window_bars or load_config()["features"]["news_window_bars"]
        rel = self._related_news(symbol)
        ts = pd.Timestamp(ts)
        i = self.bar_index(ts)
        lo = self._timeline[max(0, i - window_bars)]
        forward_limit = self._timeline[min(len(self._timeline) - 1, i + 3 * self.bars_per_day)]

        wide_lo = self._timeline[max(0, i - 2 * window_bars)]
        trailing = [n for n in rel if lo < pd.Timestamp(n["timestamp"]) <= ts]
        material_trailing = [n for n in rel if wide_lo < pd.Timestamp(n["timestamp"]) <= ts
                             and _is_material(n)]
        after = [n for n in rel if ts < pd.Timestamp(n["timestamp"]) <= forward_limit]
        near = [n for n in rel if lo < pd.Timestamp(n["timestamp"])
                <= self._timeline[min(len(self._timeline) - 1, i + self.bars_per_day)]]

        first_after_bars = None
        first_after_material = False
        if after and not material_trailing:
            material_after = [n for n in after if _is_material(n)]
            nxt = material_after[0] if material_after else after[0]
            first_after_bars = self.bars_between(ts, pd.Timestamp(nxt["timestamp"]))
            first_after_material = _is_material(nxt)

        # "dominant" sentiment = the strongest curated (research) headline if any,
        # else the mean of nearby headlines
        curated = [n for n in near if n.get("source") == "research_primary"]
        if curated:
            dominant = max(curated, key=lambda n: abs(float(n.get("sentiment_score", 0.0))))
            dominant = float(dominant.get("sentiment_score", 0.0))
        else:
            sentiments = [float(n.get("sentiment_score", 0.0)) for n in near]
            dominant = float(np.mean(sentiments)) if sentiments else 0.0

        return CourtContext(
            related_news=[_news_public(n) for n in trailing] or [_news_public(n) for n in near[:2]],
            first_related_news_after_bars=first_after_bars,
            first_related_news_after_material=first_after_material,
            news_before_move=bool(material_trailing),
            trailing_news_window_clear=not material_trailing,
            dominant_news_sentiment=dominant,
            bars_per_day=self.bars_per_day,
        )

    def _verdict_at(self, symbol: str, ts: pd.Timestamp, row: pd.Series) -> tuple[str, dict, list, CourtContext]:
        ctx = self.news_context(symbol, ts)
        flags = statistical_flags(row)
        findings = run_court(row, ctx)
        verdict, meta = decide_verdict(row, flags, findings, ctx, float(row["attention_score"]))
        return verdict.value if isinstance(verdict, Verdict) else str(verdict), meta, findings, ctx

    # ------------------------------------------------------------------ #
    # case generation
    # ------------------------------------------------------------------ #
    def _episodes(self, g: pd.DataFrame) -> list[int]:
        rules = case_rules()
        thr = rules["min_attention_score"]
        soft = thr - rules.get("soft_margin", 15)
        cooldown = rules["event_cooldown_bars"]
        context_verdicts = set(rules["context_verdicts"])

        score = g["attention_score"].to_numpy()
        cum_z = g["ret_cum_zscore"].abs().fillna(0).to_numpy()
        cum_move = g["ret_cum_short"].abs().fillna(0).to_numpy()
        vol_ratio = g["volume_ratio"].fillna(1).to_numpy()
        # a bar is a candidate if attention is elevated OR a genuinely large move
        # happened OR turnover is extreme (so context + headline-noise still surface)
        big_move = (cum_z >= rules["big_move_cum_zscore"]) | (cum_move >= rules["big_move_cum_pct"])
        extreme_vol = vol_ratio >= rules["extreme_volume_ratio"]
        candidate = (score >= soft) | big_move | extreme_vol
        idxs = np.where(candidate)[0]
        if len(idxs) == 0:
            return []

        episodes: list[list[int]] = []
        cur = [int(idxs[0])]
        for j in idxs[1:]:
            if j - cur[-1] <= cooldown:
                cur.append(int(j))
            else:
                episodes.append(cur)
                cur = [int(j)]
        episodes.append(cur)

        fresh_now = g["freshness_status"].to_numpy()

        picks: list[int] = []
        for ep in episodes:
            sub = g.iloc[ep]
            # detection bar = the peak-attention bar of the episode
            peak = int(sub["attention_score"].fillna(0).idxmax())
            peak_row = g.loc[peak]
            # a bar in or just after a stale/missing run is a catch-up artifact,
            # not a real event
            recent_fresh = fresh_now[max(0, peak - 6): peak + 1]
            if any(f in ("stale", "missing") for f in recent_fresh):
                continue
            pk_score = float(peak_row["attention_score"])
            pk_conf = float(peak_row["confidence"])
            pk_big = (abs(float(peak_row.get("ret_cum_zscore", 0) or 0)) >= rules["big_move_cum_zscore"] - 0.5
                      or abs(float(peak_row.get("ret_cum_short", 0) or 0)) >= rules["big_move_cum_pct"] - 0.005)
            pk_evol = float(peak_row.get("volume_ratio", 1) or 1) >= rules["extreme_volume_ratio"]

            # Path A: attention-driven case
            if pk_score >= thr and pk_conf >= rules["min_confidence"]:
                picks.append(peak)
                continue
            v, meta = self._verdict_at(peak_row["symbol"], peak_row["timestamp"], peak_row)[:2]
            reason = meta.get("reason")
            # Path B: large explained move (context) — surfaced almost regardless
            # of the (deliberately low) attention score, because the user WILL
            # notice a 6% move and ask "why"; but a small organic sector drift
            # should not spawn a case.
            if v in context_verdicts and (pk_big or pk_score >= thr - 6):
                picks.append(peak)
            # Path C: verdicts we always surface when the episode is notable, but
            # only for the specific triggers that make them worth a case
            elif v == "Price activity before recorded news":
                picks.append(peak)
            elif v == "Conflicting evidence" and reason == "news_price_contradiction" \
                    and (pk_score >= soft or pk_big):
                picks.append(peak)
            elif v == "Volatility-regime change" and (pk_score >= soft - 10 or pk_big):
                picks.append(peak)
            elif v == "Headline noise" and pk_evol:
                picks.append(peak)
        return picks

    def generate_cases(self, force: bool = False) -> list[dict]:
        if self._cases is not None and not force:
            return self._cases
        cases: list[dict] = []
        for symbol, g in self._by_symbol.items():
            g = g.reset_index(drop=True)
            for idx in self._episodes(g):
                cases.append(self._build_case(symbol, g, idx))
        cases = self._dedupe_context_clusters(cases)
        cases.sort(key=lambda c: c["detection_timestamp"])
        self._cases = cases
        logger.info("generated %d investigation cases", len(cases))
        return cases

    def _dedupe_context_clusters(self, cases: list[dict]) -> list[dict]:
        """A market-wide / sector-wide event hits many stocks at once. Keep only
        the few most-affected representatives per (verdict, sector, day) so the
        dashboard stays readable, and record how many peers moved with them."""
        context = set(case_rules()["context_verdicts"])
        keep: list[dict] = []
        buckets: dict[tuple, list[dict]] = {}
        for c in cases:
            if c["verdict"] not in context:
                keep.append(c)
                continue
            day = pd.Timestamp(c["detection_timestamp"]).normalize()
            key = (c["verdict"], c["sector"] if c["verdict"] == "Sector-driven movement" else "*", day)
            buckets.setdefault(key, []).append(c)
        for key, group in buckets.items():
            group.sort(key=lambda c: abs(c["metrics"].get("ret_cum_short") or 0), reverse=True)
            cap = 2 if key[0] == "Sector-driven movement" else 3
            peers = len(group)
            for c in group[:cap]:
                c["peers_in_move"] = peers - 1
                keep.append(c)
        return keep

    def _build_case(self, symbol: str, g: pd.DataFrame, idx: int) -> dict:
        row = g.loc[idx]
        ts = pd.Timestamp(row["timestamp"])
        rules = case_rules()
        comp_bars = rules["comparison_window_bars"]
        start_i = max(0, idx - comp_bars)
        comparison_start = pd.Timestamp(g.loc[start_i, "timestamp"])

        score_obj = row["_score_obj"]
        ctx = self.news_context(symbol, ts)
        flags = statistical_flags(row)
        findings = run_court(row, ctx)
        verdict_enum, meta = decide_verdict(row, flags, findings, ctx, float(row["attention_score"]))
        verdict = verdict_enum.value if isinstance(verdict_enum, Verdict) else str(verdict_enum)
        head, body = build_explanation(row, verdict_enum, findings, ctx,
                                       float(row["attention_score"]), float(row["confidence"]))

        related = self._case_related_news(symbol, ts)
        data_quality = self._case_data_quality(symbol, ts, row, score_obj)

        window = g.iloc[start_i: idx + 1]
        price_series = [
            {"timestamp": pd.Timestamp(r.timestamp).isoformat(),
             "close": _f(r.close), "volume": int(r.volume),
             "attention_score": round(float(r.attention_score), 1)}
            for r in window.itertuples()
        ]
        spark = [round(float(x), 2) for x in window["close"].ffill().tolist()]

        case_id = _case_id(symbol, ts, verdict)
        metrics = {
            k: _f(row.get(k)) for k in (
                "return_pct", "return_zscore", "ret_cum_zscore", "volume_ratio", "volume_zscore",
                "volatility_ratio", "vol_regime_strength", "dist_from_ma", "drawdown",
                "breakout_strength", "breakdown_strength",
                "sector_adjusted_return", "market_adjusted_return",
                "sector_adj_cum", "market_adj_cum",
                "sector_ret_cum_short", "market_ret_cum_short", "ret_cum_short",
                "news_count", "news_sentiment", "news_sentiment_shift", "iso_forest_score",
            )
        }

        return {
            "case_id": case_id,
            "symbol": symbol,
            "company_name": self.name_of.get(symbol, symbol),
            "sector": self.sector_of.get(symbol, ""),
            "sector_name": self.sector_name.get(self.sector_of.get(symbol, ""), ""),
            "detection_timestamp": ts.to_pydatetime(),
            "comparison_start": comparison_start.to_pydatetime(),
            "comparison_end": ts.to_pydatetime(),
            "attention_score": round(float(row["attention_score"]), 1),
            "confidence": round(float(row["confidence"]), 1),
            "severity": str(row["severity"]),
            "verdict": verdict,
            "verdict_reason": meta.get("reason"),
            "headline_explanation": head,
            "explanation": body,
            "score_components": [c.__dict__ for c in score_obj.components],
            "breakdown": score_obj.as_dict(),
            "detectives": [
                {"detective": f.detective, "key": f.key, "finding": f.finding,
                 "evidence": f.evidence, "confidence": f.confidence, "status": f.status}
                for f in findings
            ],
            "court_tally": court_tally(findings),
            "supporting_evidence": score_obj.supporting_evidence,
            "counter_evidence": score_obj.counter_evidence,
            "related_news": related,
            "data_quality": data_quality,
            "metrics": metrics,
            "spark": spark,
            "price_series": price_series,
            "created_at": datetime.utcnow(),
            "dataset_timestamp": ts.to_pydatetime(),
        }

    def _case_related_news(self, symbol: str, ts: pd.Timestamp) -> list[dict]:
        rel = self._related_news(symbol)
        i = self.bar_index(ts)
        lo = self._timeline[max(0, i - 2 * load_config()["features"]["news_window_bars"])]
        hi = self._timeline[min(len(self._timeline) - 1, i + 3 * self.bars_per_day)]
        out = []
        for n in rel:
            nts = pd.Timestamp(n["timestamp"])
            if lo <= nts <= hi:
                out.append({
                    "id": n["id"],
                    "timestamp": nts.to_pydatetime(),
                    "headline": n["headline"],
                    "source": n.get("source", "local_wire"),
                    "event_type": n.get("event_type", "other"),
                    "sentiment_label": n.get("sentiment_label", "neutral"),
                    "sentiment_score": float(n.get("sentiment_score", 0.0)),
                    "minutes_from_detection": round((nts - ts).total_seconds() / 60.0, 1),
                    "relevance": 1.0 if symbol in (n.get("symbols") or []) else 0.4,
                })
        return out

    def _case_data_quality(self, symbol: str, ts: pd.Timestamp, row, score_obj) -> dict:
        i = self.bar_index(ts)
        lo = self._timeline[max(0, i - 8)]
        events = [
            {**e, "timestamp": pd.Timestamp(e["timestamp"]).to_pydatetime()}
            for e in self.quality_events
            if e["symbol"] == symbol and lo <= pd.Timestamp(e["timestamp"]) <= ts
        ]
        freshness = str(row["freshness_status"])
        penalty = float(load_config()["confidence"]["base"] - row["confidence"])
        resolved_source = None
        conflict_detail = None
        sources = [str(row.get("source", "research_primary"))]
        for e in events:
            if e["status"] == "conflicting":
                conflict_detail = e["details"]
                names = [s["name"] if isinstance(s, dict) else s for s in e["sources"]]
                sources = names
                resolved_source = min(
                    names, key=lambda s: source_priority().get(s, 50)
                )
        return {
            "freshness": freshness,
            "confidence_penalty": round(max(0.0, penalty), 1),
            "warnings": list(score_obj.data_quality_warnings),
            "sources_considered": sources,
            "resolved_source": resolved_source,
            "conflict_detail": conflict_detail,
            "events": events,
        }

    # ------------------------------------------------------------------ #
    # comparison series (stock vs sector vs market)
    # ------------------------------------------------------------------ #
    def comparison_series(self, symbol: str, start: pd.Timestamp, end: pd.Timestamp) -> dict:
        g = self._by_symbol.get(symbol)
        if g is None or g.empty:
            return {}
        start, end = pd.Timestamp(start), pd.Timestamp(end)
        window = g[(g["timestamp"] >= start) & (g["timestamp"] <= end)].reset_index(drop=True)
        if window.empty:
            window = g.tail(60).reset_index(drop=True)

        peers = [s for s in loader.sector_members()[self.sector_of[symbol]] if s != symbol]
        obs = self.observations
        idx_series = obs[obs["symbol"] == self.market_symbol].set_index("timestamp")["close"]

        def rebased(series: pd.Series) -> list[float]:
            series = series.reindex(window["timestamp"]).ffill().bfill()
            base = series.iloc[0] or 1.0
            return [round(float(x / base * 100.0), 3) for x in series]

        stock_close = window.set_index("timestamp")["close"].ffill()
        peer_close = (
            obs[obs["symbol"].isin(peers)]
            .pivot_table(index="timestamp", columns="symbol", values="close")
            .reindex(window["timestamp"]).ffill().bfill()
        )
        sector_idx = peer_close.div(peer_close.iloc[0]).mean(axis=1) * 100.0 if not peer_close.empty \
            else pd.Series(100.0, index=window["timestamp"])

        stock_r = rebased(stock_close)
        market_r = rebased(idx_series)
        sector_r = [round(float(x), 3) for x in sector_idx.tolist()]

        points = [
            {"timestamp": pd.Timestamp(t).isoformat(),
             "stock_indexed": s, "sector_indexed": se, "market_indexed": m}
            for t, s, se, m in zip(window["timestamp"], stock_r, sector_r, market_r, strict=False)
        ]
        stock_ret = stock_r[-1] / stock_r[0] - 1 if stock_r else 0
        sector_ret = sector_r[-1] / sector_r[0] - 1 if sector_r else 0
        market_ret = market_r[-1] / market_r[0] - 1 if market_r else 0

        who_first, detail = self._first_mover(window, symbol)
        return {
            "symbol": symbol, "sector": self.sector_of[symbol],
            "market_index": self.market_symbol,
            "start": window["timestamp"].iloc[0].to_pydatetime(),
            "end": window["timestamp"].iloc[-1].to_pydatetime(),
            "points": points,
            "stock_return_pct": round(stock_ret * 100, 2),
            "sector_return_pct": round(sector_ret * 100, 2),
            "market_return_pct": round(market_ret * 100, 2),
            "who_moved_first": who_first,
            "first_mover_detail": detail,
        }

    def _first_mover(self, window: pd.DataFrame, symbol: str) -> tuple[str | None, str]:
        if len(window) < 4:
            return None, "Not enough bars in the window to judge sequencing."
        r = window.copy()
        # apples-to-apples: 3-bar cumulative move for every leg
        stock_c = r["ret"].rolling(3, min_periods=1).sum().abs()
        sector_c = r["sector_return"].rolling(3, min_periods=1).sum().abs()
        market_c = r["market_return"].rolling(3, min_periods=1).sum().abs()
        thr = 0.02
        stock_first = r["timestamp"][stock_c >= thr].min()
        sector_first = r["timestamp"][sector_c >= thr].min()
        market_first = r["timestamp"][market_c >= thr].min()
        candidates = {"stock": stock_first, "sector": sector_first, "market": market_first}
        candidates = {k: v for k, v in candidates.items() if pd.notna(v)}
        if not candidates:
            return None, "No leg moved more than 2% in the window — nothing led."
        first = min(candidates, key=candidates.get)
        label = {"stock": self.name_of.get(symbol, symbol),
                 "sector": f"the {self.sector_name.get(self.sector_of[symbol], '')} sector",
                 "market": "the market index"}[first]
        return first, f"{label} moved decisively first at {pd.Timestamp(candidates[first]):%d %b %H:%M}."

    # ------------------------------------------------------------------ #
    def dataset_health(self, current_ts: pd.Timestamp) -> dict:
        obs = self.observations
        upto = obs[obs["timestamp"] <= pd.Timestamp(current_ts)]
        recent = upto[upto["timestamp"] >= pd.Timestamp(current_ts) - timedelta(days=3)]
        missing = int((recent["freshness_status"] == "missing").sum())
        stale = int((recent["freshness_status"] == "stale").sum())
        conflicting = int((recent["freshness_status"] == "conflicting").sum())
        issues = sorted(set(
            recent[recent["freshness_status"].isin(["missing", "stale", "conflicting"])]["symbol"]
        ) - {self.market_symbol})
        overall = "fresh"
        if missing:
            overall = "missing"
        elif stale:
            overall = "stale"
        elif conflicting:
            overall = "conflicting"
        return {
            "missing_bars": missing, "stale_bars": stale, "conflicting_bars": conflicting,
            "symbols_with_issues": issues, "freshness_overall": overall,
            "total_observations": int(len(upto)),
            "symbols_tracked": len(self._by_symbol),
        }


def _f(x) -> float | None:
    try:
        if x is None:
            return None
        v = float(x)
        return None if np.isnan(v) else round(v, 4)
    except (TypeError, ValueError):
        return None


MATERIAL_EVENT_TYPES = {
    "earnings", "acquisition", "regulation", "legal_issue", "leadership",
}


MATERIAL_SOURCES = {"research_primary"}


def _is_material(n: dict) -> bool:
    """A headline is 'material' if it establishes that information was on the record.

    Only the curated research feed ('research_primary') counts. The synthetic
    'local_wire' is treated as unverified background chatter, so ordinary noise
    never masks a genuine price-before-news sequence. (See docs/MODEL_CARD.md.)
    """
    return n.get("source") in MATERIAL_SOURCES


def _news_public(n: dict) -> dict:
    return {
        "id": n.get("id"),
        "headline": n.get("headline"),
        "event_type": n.get("event_type", "other"),
        "sentiment_label": n.get("sentiment_label", "neutral"),
        "sentiment_score": float(n.get("sentiment_score", 0.0)),
        "timestamp": n.get("timestamp"),
    }


def _case_id(symbol: str, ts: pd.Timestamp, verdict: str) -> str:
    key = f"{symbol}|{pd.Timestamp(ts).isoformat()}|{verdict}"
    return "CASE-" + hashlib.sha1(key.encode()).hexdigest()[:12].upper()


# --------------------------------------------------------------------------- #
# process-wide singleton
# --------------------------------------------------------------------------- #
_engine: AnalysisEngine | None = None


def get_engine() -> AnalysisEngine:
    global _engine
    if _engine is None:
        _engine = AnalysisEngine()
    return _engine


def reset_engine() -> None:
    global _engine
    _engine = None
