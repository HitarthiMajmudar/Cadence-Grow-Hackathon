from __future__ import annotations

from fastapi import APIRouter, Query

from app.api.deps import CurrentUser
from app.core.errors import NotFoundError
from app.repositories.watchlists import WatchlistRepository
from app.schemas.briefing import BriefingResponse, MarkSeenRequest
from app.services.briefing import BriefingService

router = APIRouter(prefix="/briefings", tags=["briefings"])


async def _resolve_watchlist(user_id: str, watchlist_id: str | None) -> dict:
    repo = WatchlistRepository()
    if watchlist_id:
        wl = await repo.get_for_user(user_id, watchlist_id)
    else:
        wls = await repo.list_for_user(user_id)
        wl = wls[0] if wls else None
    if not wl:
        raise NotFoundError("Watchlist not found.")
    return wl


@router.get("", response_model=BriefingResponse)
async def get_briefing(user: CurrentUser, watchlist_id: str | None = Query(default=None)) -> dict:
    wl = await _resolve_watchlist(user["_id"], watchlist_id)
    briefing = await BriefingService().generate(user["_id"], wl["_id"])
    if not briefing:
        raise NotFoundError("Could not build briefing.")
    return briefing


@router.post("/mark-seen")
async def mark_seen(body: MarkSeenRequest, user: CurrentUser) -> dict:
    snap = await BriefingService().mark_seen(user["_id"], body.watchlist_id, body.seen_case_ids)
    if not snap:
        raise NotFoundError("Watchlist not found.")
    return {
        "acknowledged_at": snap["acknowledged_at"],
        "dataset_timestamp": snap["dataset_timestamp"],
        "seen_case_ids": snap["seen_case_ids"],
        "watchlist_id": snap["watchlist_id"],
    }
