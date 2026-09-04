from __future__ import annotations

from fastapi import APIRouter, Query

from app.api.deps import CurrentUser
from app.schemas.live_quote import LiveHistoryResponse, LiveQuote, LiveSymbolMatch
from app.services.live_market_service import LiveMarketService

router = APIRouter(prefix="/live", tags=["live-markets"])


@router.get("/search", response_model=list[LiveSymbolMatch])
async def live_search(user: CurrentUser, q: str = Query(min_length=1)) -> list[dict]:
    return await LiveMarketService().search(q)


@router.get("/{symbol}/quote", response_model=LiveQuote)
async def live_quote(symbol: str, user: CurrentUser, exchange: str | None = Query(default=None)) -> dict:
    return await LiveMarketService().quote(symbol, exchange)


@router.get("/{symbol}/history", response_model=LiveHistoryResponse)
async def live_history(
    symbol: str,
    user: CurrentUser,
    exchange: str | None = Query(default=None),
    outputsize: int = Query(default=180, ge=1, le=5000),
) -> dict:
    return await LiveMarketService().history(symbol, exchange, outputsize)
