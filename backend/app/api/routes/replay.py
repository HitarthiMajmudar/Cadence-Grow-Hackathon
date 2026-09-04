from __future__ import annotations

from datetime import datetime

import pandas as pd
from fastapi import APIRouter, Query

from app.api.deps import CurrentUser
from app.core.errors import NotFoundError
from app.repositories.cases import CaseRepository
from app.schemas.replay import ReplayResponse
from app.services.demo_clock import DemoClockService
from app.services.replay import ReplayService

router = APIRouter(prefix="/replay", tags=["replay"])


async def _range(user_id: str, symbol: str, start: datetime | None, end: datetime | None,
                 lookback_bars: int) -> tuple[datetime, datetime]:
    clock = DemoClockService()
    engine = clock.engine
    current = await clock.current_timestamp(user_id)

    if start is not None or end is not None:
        end_ts = pd.Timestamp(end) if end is not None else current
        start_ts = pd.Timestamp(start) if start is not None else engine.advance_timestamp(end_ts, -lookback_bars)
        return start_ts.to_pydatetime(), end_ts.to_pydatetime()

    # default: place the most recent case for this symbol ~70% through the window
    # so the anomaly plays back mid-replay with runway for the news marker after
    cases = await CaseRepository().list_up_to(current.to_pydatetime(), symbols=[symbol])
    if cases:
        det = pd.Timestamp(max(cases, key=lambda c: c["detection_timestamp"])["detection_timestamp"])
        tail = max(10, round(lookback_bars * 0.3))
        end_ts = min(engine.advance_timestamp(det, tail), current)
    else:
        end_ts = current
    start_ts = engine.advance_timestamp(end_ts, -lookback_bars)
    return start_ts.to_pydatetime(), end_ts.to_pydatetime()


@router.get("/{symbol}", response_model=ReplayResponse)
async def get_replay(
    symbol: str,
    user: CurrentUser,
    start: datetime | None = None,
    end: datetime | None = None,
    lookback_bars: int = Query(default=75, ge=14, le=400),
) -> dict:
    s, e = await _range(user["_id"], symbol, start, end, lookback_bars)
    payload = await ReplayService().build(symbol, s, e)
    if not payload:
        raise NotFoundError(f"No replay data for '{symbol}'.")
    return payload


@router.get("/{symbol}/anomaly-markers")
async def anomaly_markers(symbol: str, user: CurrentUser,
                          start: datetime | None = None, end: datetime | None = None,
                          lookback_bars: int = Query(default=75, ge=14, le=400)) -> dict:
    s, e = await _range(user["_id"], symbol, start, end, lookback_bars)
    return {"symbol": symbol.upper(), "markers": await ReplayService().anomaly_markers(symbol, s, e)}


@router.get("/{symbol}/news-markers")
async def news_markers(symbol: str, user: CurrentUser,
                       start: datetime | None = None, end: datetime | None = None,
                       lookback_bars: int = Query(default=75, ge=14, le=400)) -> dict:
    s, e = await _range(user["_id"], symbol, start, end, lookback_bars)
    return {"symbol": symbol.upper(), "markers": await ReplayService().news_markers(symbol, s, e)}


@router.get("/{symbol}/score-evolution")
async def score_evolution(symbol: str, user: CurrentUser,
                          start: datetime | None = None, end: datetime | None = None,
                          lookback_bars: int = Query(default=75, ge=14, le=400)) -> dict:
    s, e = await _range(user["_id"], symbol, start, end, lookback_bars)
    return {"symbol": symbol.upper(), "points": await ReplayService().score_evolution(symbol, s, e)}
