from __future__ import annotations

from fastapi import APIRouter

from app.api.deps import CurrentUser
from app.repositories.users import DEFAULT_PREFERENCES, UserRepository
from app.schemas.user import DemoLoginRequest, UpdatePreferencesRequest, UserOut
from app.services.demo_clock import DemoClockService
from app.services.watchlist_service import WatchlistService

router = APIRouter(prefix="/auth", tags=["auth"])


def _shape_user(u: dict) -> dict:
    return {
        "_id": u["_id"],
        "name": u["name"],
        "email": u["email"],
        "created_at": u["created_at"],
        "last_login_at": u["last_login_at"],
        "preferences": {**DEFAULT_PREFERENCES, **(u.get("preferences") or {})},
        "is_seeded": u.get("is_seeded", False),
    }


@router.post("/demo-login", response_model=UserOut, response_model_by_alias=False)
async def demo_login(body: DemoLoginRequest) -> dict:
    """Create or retrieve a demo user by email, then ensure a default watchlist + clock."""
    users = UserRepository()
    user, _created = await users.get_or_create(body.name, str(body.email))

    wl_service = WatchlistService()
    wl = await wl_service.ensure_default(user["_id"])
    prefs = {**DEFAULT_PREFERENCES, **(user.get("preferences") or {})}
    if not prefs.get("default_watchlist_id"):
        await users.update_preferences(user["_id"], {"default_watchlist_id": wl["_id"]})
        user = await users.get(user["_id"])  # type: ignore[assignment]

    await DemoClockService().get(user["_id"])
    return _shape_user(user)


@router.get("/me", response_model=UserOut, response_model_by_alias=False)
async def me(user: CurrentUser) -> dict:
    return _shape_user(user)


@router.patch("/me/preferences", response_model=UserOut, response_model_by_alias=False)
async def update_preferences(body: UpdatePreferencesRequest, user: CurrentUser) -> dict:
    updated = await UserRepository().update_preferences(
        user["_id"], body.model_dump(exclude_none=True))
    return _shape_user(updated)


@router.get("/demo-accounts", response_model=list[UserOut], response_model_by_alias=False)
async def demo_accounts() -> list[dict]:
    return [_shape_user(u) for u in await UserRepository().list_seeded()]
