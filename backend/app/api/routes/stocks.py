from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Query

from app.api.deps import CurrentUser
from app.core.errors import NotFoundError
from app.schemas.market import ComparisonSeries, HistoryResponse, StockMeta, StockState
from app.services.stocks_service import StocksService

router = APIRouter(prefix="/stocks", tags=["stocks"])


@router.get("", response_model=list[StockMeta])
async def list_stocks() -> list[dict]:
    return StocksService().list_stocks()


@router.get("/search", response_model=list[StockMeta])
async def search_stocks(q: str = Query(default=""), limit: int = Query(default=10, le=50)) -> list[dict]:
    return StocksService().search(q, limit)


@router.get("/{symbol}/state", response_model=StockState)
async def stock_state(symbol: str, user: CurrentUser) -> dict:
    state = await StocksService().state(user["_id"], symbol)
    if not state:
        raise NotFoundError(f"Unknown symbol '{symbol}'.")
    return state


@router.get("/{symbol}/history", response_model=HistoryResponse)
async def stock_history(
    symbol: str,
    user: CurrentUser,
    start: datetime | None = None,
    end: datetime | None = None,
    as_of_clock: bool = Query(default=True, description="clip to the demo clock"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=500, ge=1, le=2000),
) -> dict:
    svc = StocksService()
    as_of = await svc.clock.current_timestamp(user["_id"]) if as_of_clock else None
    result = svc.history(symbol, start=start, end=end, as_of=as_of,
                         page=page, page_size=page_size)
    if not result["candles"] and result["total"] == 0:
        raise NotFoundError(f"No data for '{symbol}'.")
    return result


@router.get("/{symbol}/comparison", response_model=ComparisonSeries)
async def stock_comparison(symbol: str, user: CurrentUser,
                           lookback_bars: int = Query(default=60, ge=10, le=300)) -> dict:
    result = await StocksService().comparison(user["_id"], symbol, lookback_bars=lookback_bars)
    if not result:
        raise NotFoundError(f"Unknown symbol '{symbol}'.")
    return result


@router.get("/{symbol}/news")
async def stock_news(symbol: str, user: CurrentUser, limit: int = Query(default=20, le=100)) -> dict:
    svc = StocksService()
    as_of = await svc.clock.current_timestamp(user["_id"])
    return {"symbol": symbol.upper(), "news": await svc.related_news(symbol, as_of=as_of, limit=limit)}


@router.get("/{symbol}/cases")
async def stock_cases(symbol: str, user: CurrentUser) -> dict:
    cases = await StocksService().historical_cases(user["_id"], symbol)
    return {"symbol": symbol.upper(), "cases": cases}
