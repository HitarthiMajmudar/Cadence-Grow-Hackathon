from __future__ import annotations

from pydantic import EmailStr, Field

from app.schemas.common import ApiModel
from app.schemas.user import UserOut


class SignupRequest(ApiModel):
    name: str = Field(min_length=1, max_length=80)
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)


class LoginRequest(ApiModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=128)


class TokenResponse(ApiModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut
