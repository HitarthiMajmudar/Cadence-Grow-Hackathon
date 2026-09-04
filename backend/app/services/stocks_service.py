"""Stock catalogue, search, per-timestamp state, history and comparison series."""
from __future__ import annotations

import pandas as pd

from app.repositories.cases import CaseRepository
from app.repositories.market import NewsRepository
from app.services.analysis_engine import get_engine
from app.services.demo_clock import DemoClockService


class StocksService:
    def __init__(self) -> None:
        self.engine = get_engine()
        self.clock = DemoClockService()
        self.cases = CaseRepository()
        self.news = NewsRepository()

    def list_stocks(self) -> list[dict]:
        return [
            {
                "symbol": s["symbol"], "name": s["name"], "sector": s["sector"],
                "sector_name": s["sector_name"], "index": s["index"],
                "weight": s["weight"], "currency": s["currency"], "summary": s["summary"],
            }
            for s in self.engine.stocks
        ]

    def search(self, query: str, limit: int = 10) -> list[dict]:
        q = query.strip().lower()
        if not q:
            return self.list_stocks()[:limit]
        scored = []
        for s in self.list_stocks():
            hay = f"{s['symbol']} {s['name']} {s['sector_name']}".lower()
            if q in hay:
                # earlier match / symbol prefix ranks higher
                rank = (0 if s["symbol"].lower().startswith(q) else
                        1 if s["name"].lower().startswith(q) else 2)
                scored.append((rank, hay.index(q), s))
        scored.sort(key=lambda x: (x[0], x[1]))
        return [s for _, _, s in scored[:limit]]

    async def state(self, user_id: str, symbol: str) -> dict | None:
        symbol = symbol.upper()
        if symbol not in self.engine.name_of:
            return None
        ts = await self.clock.current_timestamp(user_id)
        s = self.engine.state_at(symbol, ts)
        cases = await self.cases.list_up_to(ts.to_pydatetime(), symbols=[symbol])
        if cases:
            top = max(cases, key=lambda c: c["attention_score"])
            s["open_case_id"] = top["case_id"]
            s["verdict"] = s["verdict"] or top["verdict"]
        return s

    def history(self, symbol: str, *, start=None, end=None, as_of=None,
                page: int = 1, page_size: int = 500) -> dict:
        symbol = symbol.upper()
        obs = self.engine.observations
        rows = obs[obs["symbol"] == symbol].sort_values("timestamp")
        if as_of is not None:
            rows = rows[rows["timestamp"] <= pd.Timestamp(as_of)]
        if start is not None:
            rows = rows[rows["timestamp"] >= pd.Timestamp(start)]
        if end is not None:
            rows = rows[rows["timestamp"] <= pd.Timestamp(end)]
        total = len(rows)
        page_rows = rows.iloc[(page - 1) * page_size: page * page_size]
        candles = [
            {
                "timestamp": pd.Timestamp(r.timestamp).to_pydatetime(),
                "open": _f(r.open), "high": _f(r.high), "low": _f(r.low),
                "close": _f(r.close), "volume": int(r.volume) if not pd.isna(r.volume) else 0,
                "freshness": r.freshness_status, "source": r.source,
            }
            for r in page_rows.itertuples()
        ]
        return {"symbol": symbol, "interval": "1h", "candles": candles,
                "total": total, "page": page, "page_size": page_size}

    async def comparison(self, user_id: str, symbol: str, *, lookback_bars: int = 60) -> dict | None:
        symbol = symbol.upper()
        if symbol not in self.engine.name_of:
            return None
        ts = await self.clock.current_timestamp(user_id)
        start = self.engine.advance_timestamp(ts, -lookback_bars)
        return self.engine.comparison_series(symbol, start, ts)

    async def related_news(self, symbol: str, *, as_of=None, limit: int = 20) -> list[dict]:
        symbol = symbol.upper()
        out = []
        for n in self.engine.news:
            if symbol in (n.get("symbols") or []):
                nts = pd.Timestamp(n["timestamp"])
                if as_of is not None and nts > pd.Timestamp(as_of):
                    continue
                out.append({
                    "id": n["id"], "timestamp": nts.to_pydatetime(), "headline": n["headline"],
                    "source": n.get("source", "local_wire"), "event_type": n.get("event_type", "other"),
                    "sentiment_label": n.get("sentiment_label", "neutral"),
                    "sentiment_score": float(n.get("sentiment_score", 0.0)),
                    "minutes_from_detection": 0.0, "relevance": 1.0,
                })
        out.sort(key=lambda n: n["timestamp"], reverse=True)
        return out[:limit]

    async def historical_cases(self, user_id: str, symbol: str) -> list[dict]:
        ts = await self.clock.current_timestamp(user_id)
        cases = await self.cases.list_up_to(ts.to_pydatetime(), symbols=[symbol.upper()])
        return sorted(cases, key=lambda c: c["detection_timestamp"], reverse=True)


def _f(x):
    try:
        v = float(x)
        return None if pd.isna(v) else round(v, 2)
    except (TypeError, ValueError):
        return None
