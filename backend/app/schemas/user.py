from __future__ import annotations

from datetime import datetime

from pydantic import Field

from app.schemas.common import ApiModel


class UserPreferences(ApiModel):
    default_watchlist_id: str | None = None
    attention_threshold: int = 55
    daily_attention_budget: str = "top_3"
    reduced_motion: bool = False
    theme: str = "dark"


class UserOut(ApiModel):
    id: str = Field(alias="_id")
    name: str
    email: str
    created_at: datetime
    last_login_at: datetime
    preferences: UserPreferences


class UpdatePreferencesRequest(ApiModel):
    attention_threshold: int | None = Field(default=None, ge=0, le=100)
    daily_attention_budget: str | None = None
    reduced_motion: bool | None = None
    theme: str | None = None
    default_watchlist_id: str | None = None
