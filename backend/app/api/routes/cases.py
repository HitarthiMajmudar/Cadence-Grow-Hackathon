from __future__ import annotations

from fastapi import APIRouter, Query

from app.api.deps import CurrentUser
from app.core.errors import NotFoundError
from app.repositories.snapshots import VisitSnapshotRepository
from app.repositories.watchlists import WatchlistRepository
from app.schemas.case import (
    CaseFeedbackRequest,
    CaseStatusUpdate,
    StoryCardData,
)
from app.services.cases_service import CasesService
from app.services.demo_clock import DemoClockService

router = APIRouter(prefix="/cases", tags=["cases"])


async def _watchlist_scope(user_id: str, watchlist_id: str | None):
    repo = WatchlistRepository()
    if watchlist_id:
        wl = await repo.get_for_user(user_id, watchlist_id)
    else:
        wls = await repo.list_for_user(user_id)
        wl = wls[0] if wls else None
    return wl


@router.get("")
async def list_cases(
    user: CurrentUser,
    watchlist_id: str | None = Query(default=None),
    scope: str = Query(default="watchlist", pattern="^(watchlist|all)$"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=100, ge=1, le=500),
    threshold: int | None = Query(default=None, ge=0, le=100),
    budget: str | None = Query(default=None),
) -> dict:
    svc = CasesService()
    clock = DemoClockService()
    ts = await clock.current_timestamp(user["_id"])
    wl = await _watchlist_scope(user["_id"], watchlist_id)
    symbols = None if (scope == "all" or not wl) else wl["symbols"]
    use_threshold = threshold if threshold is not None else (wl["attention_threshold"] if wl else 55)
    use_budget = budget or (wl["daily_attention_budget"] if wl else "top_3")

    seen: set[str] = set()
    if wl:
        snap = await VisitSnapshotRepository().latest(user["_id"], wl["_id"])
        if snap:
            seen = set(snap["seen_case_ids"])

    return await svc.ranked_for_watchlist(
        user["_id"], symbols=symbols, dataset_ts=ts,
        threshold=use_threshold, budget=use_budget, seen_ids=seen,
        page=page, page_size=page_size)


@router.get("/recent")
async def recent_cases(user: CurrentUser, limit: int = Query(default=6, le=20)) -> dict:
    return {"cases": await CasesService().recently_viewed(user["_id"], limit)}


@router.get("/{case_id}")
async def case_detail(case_id: str, user: CurrentUser) -> dict:
    detail = await CasesService().get_detail(user["_id"], case_id)
    if not detail:
        raise NotFoundError("Case not found.")
    return detail


@router.patch("/{case_id}/status")
async def update_case_status(case_id: str, body: CaseStatusUpdate, user: CurrentUser) -> dict:
    state = await CasesService().set_status(user["_id"], case_id, body.status)
    if not state:
        raise NotFoundError("Case not found.")
    return {"case_id": case_id, "status": state["status"], "updated_at": state["updated_at"]}


@router.post("/{case_id}/feedback")
async def submit_feedback(case_id: str, body: CaseFeedbackRequest, user: CurrentUser) -> dict:
    svc = CasesService()
    case = await svc.cases.get_by_case_id(case_id)
    if not case:
        raise NotFoundError("Case not found.")
    fb = await svc.add_feedback(user["_id"], case_id, body.feedback, body.note)
    return {"case_id": case_id, "feedback": fb["feedback"], "created_at": fb["created_at"],
            "summary": await svc.feedback.summary(case_id)}


@router.get("/{case_id}/story-card", response_model=StoryCardData)
async def story_card(case_id: str, user: CurrentUser) -> dict:
    card = await CasesService().story_card(case_id)
    if not card:
        raise NotFoundError("Case not found.")
    return card
