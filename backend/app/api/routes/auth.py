from __future__ import annotations

from fastapi import APIRouter, status

from app.api.deps import CurrentUser
from app.core.errors import AuthError
from app.core.security import create_access_token, hash_password, verify_password
from app.repositories.users import DEFAULT_PREFERENCES, UserRepository
from app.schemas.auth import LoginRequest, SignupRequest, TokenResponse
from app.schemas.user import UpdatePreferencesRequest, UserOut
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
    }


@router.post("/signup", response_model=TokenResponse, response_model_by_alias=False,
             status_code=status.HTTP_201_CREATED)
async def signup(body: SignupRequest) -> dict:
    """Create a real account, seed a default watchlist + replay clock, and
    return a bearer token."""
    users = UserRepository()
    user = await users.create(body.name, str(body.email), hash_password(body.password))

    wl_service = WatchlistService()
    wl = await wl_service.ensure_default(user["_id"])
    prefs = {**DEFAULT_PREFERENCES, **(user.get("preferences") or {})}
    if not prefs.get("default_watchlist_id"):
        await users.update_preferences(user["_id"], {"default_watchlist_id": wl["_id"]})
        user = await users.get(user["_id"])  # type: ignore[assignment]

    await DemoClockService().get(user["_id"])
    token = create_access_token(user["_id"])
    return {"access_token": token, "user": _shape_user(user)}


@router.post("/login", response_model=TokenResponse, response_model_by_alias=False)
async def login(body: LoginRequest) -> dict:
    users = UserRepository()
    user = await users.by_email(str(body.email))
    if not user or not verify_password(body.password, user.get("password_hash", "")):
        raise AuthError("Invalid email or password.", code="invalid_credentials")
    await users.touch_login(user["_id"])
    token = create_access_token(user["_id"])
    return {"access_token": token, "user": _shape_user(user)}


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT, response_model=None)
async def logout() -> None:
    """Tokens are stateless JWTs with no server-side revocation in this scope —
    the frontend simply discards its stored token. Kept as a real endpoint so
    logout has a clear place to grow (e.g. a token blacklist) later."""
    return None


@router.get("/me", response_model=UserOut, response_model_by_alias=False)
async def me(user: CurrentUser) -> dict:
    return _shape_user(user)


@router.patch("/me/preferences", response_model=UserOut, response_model_by_alias=False)
async def update_preferences(body: UpdatePreferencesRequest, user: CurrentUser) -> dict:
    updated = await UserRepository().update_preferences(
        user["_id"], body.model_dump(exclude_none=True))
    return _shape_user(updated)
