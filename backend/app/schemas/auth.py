from __future__ import annotations

from pydantic import EmailStr, Field, field_validator

from app.schemas.common import ApiModel
from app.schemas.user import UserOut


class PasswordRequest(ApiModel):
    @field_validator("password", check_fields=False)
    @classmethod
    def password_fits_bcrypt(cls, value: str) -> str:
        if len(value.encode("utf-8")) > 72:
            raise ValueError("Password must be at most 72 UTF-8 bytes.")
        return value


class SignupRequest(PasswordRequest):
    name: str = Field(min_length=1, max_length=80)
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)


class LoginRequest(PasswordRequest):
    email: EmailStr
    password: str = Field(min_length=1, max_length=128)


class TokenResponse(ApiModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut
