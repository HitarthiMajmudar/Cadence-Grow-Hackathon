"""Shared FastAPI dependencies."""
from __future__ import annotations

from typing import Annotated

from fastapi import Depends, Header

from app.core.errors import AuthError, NotFoundError
from app.core.security import decode_access_token
from app.repositories.users import UserRepository


async def get_current_user(
    authorization: Annotated[str | None, Header()] = None,
) -> dict:
    """Real auth: the frontend sends a JWT as `Authorization: Bearer <token>`,
    obtained from POST /auth/signup or /auth/login."""
    if not authorization or not authorization.lower().startswith("bearer "):
        raise AuthError("Missing or invalid Authorization header. Please log in.")
    token = authorization.split(" ", 1)[1].strip()
    user_id = decode_access_token(token)
    user = await UserRepository().get(user_id)
    if not user:
        raise NotFoundError("User not found. Please sign in again.", code="user_not_found")
    return user


CurrentUser = Annotated[dict, Depends(get_current_user)]
