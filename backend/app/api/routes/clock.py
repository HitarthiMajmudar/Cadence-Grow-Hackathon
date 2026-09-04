from __future__ import annotations

from fastapi import APIRouter

from app.api.deps import CurrentUser
from app.repositories.cases import CaseRepository
from app.repositories.watchlists import WatchlistRepository
from app.schemas.clock import AdvanceClockRequest, ClockAdvanceResult, DemoClockOut
from app.services.demo_clock import DemoClockService

router = APIRouter(prefix="/demo-clock", tags=["demo-clock"])


@router.get("", response_model=DemoClockOut)
async def get_clock(user: CurrentUser) -> dict:
    return await DemoClockService().get(user["_id"])


@router.post("/advance", response_model=ClockAdvanceResult)
async def advance_clock(user: CurrentUser, body: AdvanceClockRequest | None = None) -> dict:
    bars = body.bars if body else None
    result = await DemoClockService().advance(user["_id"], bars)
    from_ts = result.pop("_advanced_from")
    advanced = result.pop("_advanced_bars")

    # new cases revealed by the jump, across the user's watchlist symbols
    wls = await WatchlistRepository().list_for_user(user["_id"])
    symbols = sorted({s for w in wls for s in w.get("symbols", [])}) or None
    new_cases = await CaseRepository().list_between(
        from_ts.to_pydatetime(), result["current_dataset_timestamp"], symbols=symbols)

    return {
        "clock": result,
        "advanced_bars": advanced,
        "market_hours_advanced": float(advanced),
        "from_timestamp": from_ts.to_pydatetime(),
        "to_timestamp": result["current_dataset_timestamp"],
        "new_case_ids": [c["case_id"] for c in new_cases],
    }


@router.post("/reset", response_model=DemoClockOut)
async def reset_clock(user: CurrentUser) -> dict:
    return await DemoClockService().reset(user["_id"])
