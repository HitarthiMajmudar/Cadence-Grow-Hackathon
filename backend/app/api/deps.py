"""Shared FastAPI dependencies."""
from __future__ import annotations

from typing import Annotated

from fastapi import Depends, Header

from app.core.errors import AuthError, NotFoundError
from app.repositories.users import UserRepository


async def get_current_user(
    x_user_id: Annotated[str | None, Header(alias="X-User-Id")] = None,
) -> dict:
    """Demo auth: the frontend sends the user's id in the X-User-Id header.

    This is intentionally lightweight (no passwords / JWT) and clearly labelled
    as demo authentication. The user record still lives in MongoDB.
    """
    if not x_user_id:
        raise AuthError("Missing X-User-Id header. Log in via the demo sign-in screen.")
    user = await UserRepository().get(x_user_id)
    if not user:
        raise NotFoundError("User not found. Please sign in again.", code="user_not_found")
    return user


CurrentUser = Annotated[dict, Depends(get_current_user)]
