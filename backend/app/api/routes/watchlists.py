from __future__ import annotations

from fastapi import APIRouter, Response, status

from app.api.deps import CurrentUser
from app.core.errors import ConflictError, NotFoundError
from app.repositories.watchlists import WatchlistRepository
from app.schemas.watchlist import (
    ATTENTION_BUDGETS,
    SymbolRequest,
    WatchlistCreate,
    WatchlistDetail,
    WatchlistOut,
    WatchlistRename,
    WatchlistSettings,
)
from app.services.analysis_engine import get_engine
from app.services.watchlist_service import WatchlistService

router = APIRouter(prefix="/watchlists", tags=["watchlists"])
MAX_WATCHLISTS = 12
MAX_SYMBOLS = 30


def _shape(wl: dict) -> dict:
    return {**wl, "id": wl["_id"]}


def _validate_symbol(symbol: str) -> str:
    sym = symbol.strip().upper()
    if sym not in get_engine().name_of:
        raise NotFoundError(f"Unknown symbol '{sym}'.", code="unknown_symbol")
    return sym


@router.get("", response_model=list[WatchlistOut], response_model_by_alias=False)
async def list_watchlists(user: CurrentUser) -> list[dict]:
    return [_shape(w) for w in await WatchlistRepository().list_for_user(user["_id"])]


@router.post("", response_model=WatchlistDetail, response_model_by_alias=False,
             status_code=status.HTTP_201_CREATED)
async def create_watchlist(body: WatchlistCreate, user: CurrentUser) -> dict:
    repo = WatchlistRepository()
    if await repo.count_for_user(user["_id"]) >= MAX_WATCHLISTS:
        raise ConflictError(f"You can have at most {MAX_WATCHLISTS} watchlists.")
    if body.daily_attention_budget not in ATTENTION_BUDGETS:
        raise ConflictError(f"Unknown attention budget '{body.daily_attention_budget}'.")
    symbols = [_validate_symbol(s) for s in body.symbols][:MAX_SYMBOLS]
    wl = await repo.create(user["_id"], body.name, symbols,
                           body.attention_threshold, body.daily_attention_budget)
    return await WatchlistService().detail(user["_id"], wl["_id"])  # type: ignore[return-value]


@router.get("/{watchlist_id}", response_model=WatchlistDetail, response_model_by_alias=False)
async def get_watchlist(watchlist_id: str, user: CurrentUser) -> dict:
    detail = await WatchlistService().detail(user["_id"], watchlist_id)
    if not detail:
        raise NotFoundError("Watchlist not found.")
    return detail


@router.patch("/{watchlist_id}", response_model=WatchlistOut, response_model_by_alias=False)
async def rename_watchlist(watchlist_id: str, body: WatchlistRename, user: CurrentUser) -> dict:
    wl = await WatchlistRepository().rename(user["_id"], watchlist_id, body.name)
    if not wl:
        raise NotFoundError("Watchlist not found.")
    return _shape(wl)


@router.delete("/{watchlist_id}", status_code=status.HTTP_204_NO_CONTENT,
               response_class=Response)
async def delete_watchlist(watchlist_id: str, user: CurrentUser) -> Response:
    repo = WatchlistRepository()
    if await repo.count_for_user(user["_id"]) <= 1:
        raise ConflictError("You must keep at least one watchlist.")
    if not await repo.delete_for_user(user["_id"], watchlist_id):
        raise NotFoundError("Watchlist not found.")
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/{watchlist_id}/symbols", response_model=WatchlistDetail,
             response_model_by_alias=False)
async def add_symbol(watchlist_id: str, body: SymbolRequest, user: CurrentUser) -> dict:
    sym = _validate_symbol(body.symbol)
    repo = WatchlistRepository()
    wl = await repo.get_for_user(user["_id"], watchlist_id)
    if not wl:
        raise NotFoundError("Watchlist not found.")
    if len(wl.get("symbols", [])) >= MAX_SYMBOLS:
        raise ConflictError(f"A watchlist can hold at most {MAX_SYMBOLS} symbols.")
    await repo.add_symbol(user["_id"], watchlist_id, sym)
    return await WatchlistService().detail(user["_id"], watchlist_id)  # type: ignore[return-value]


@router.delete("/{watchlist_id}/symbols/{symbol}", response_model=WatchlistDetail,
               response_model_by_alias=False)
async def remove_symbol(watchlist_id: str, symbol: str, user: CurrentUser) -> dict:
    wl = await WatchlistRepository().remove_symbol(user["_id"], watchlist_id, symbol)
    if not wl:
        raise NotFoundError("Watchlist not found.")
    return await WatchlistService().detail(user["_id"], watchlist_id)  # type: ignore[return-value]


@router.patch("/{watchlist_id}/settings", response_model=WatchlistOut,
              response_model_by_alias=False)
async def update_settings(watchlist_id: str, body: WatchlistSettings, user: CurrentUser) -> dict:
    if body.daily_attention_budget and body.daily_attention_budget not in ATTENTION_BUDGETS:
        raise ConflictError(f"Unknown attention budget '{body.daily_attention_budget}'.")
    wl = await WatchlistRepository().update_settings(
        user["_id"], watchlist_id,
        attention_threshold=body.attention_threshold,
        daily_attention_budget=body.daily_attention_budget)
    if not wl:
        raise NotFoundError("Watchlist not found.")
    return _shape(wl)


@router.get("/meta/attention-budgets")
async def attention_budgets() -> dict:
    return {"budgets": [{"id": k, "label": v} for k, v in ATTENTION_BUDGETS.items()]}
