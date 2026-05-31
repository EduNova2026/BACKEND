from __future__ import annotations

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from .user import UserOut


class LoginRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    email: EmailStr
    password: str = Field(min_length=6)


class LoginResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str
    expires_in: int
    user: UserOut


class Token(BaseModel):
    access_token: str
    token_type: str


class RefreshRequest(BaseModel):
    refresh_token: str


class RefreshResponse(BaseModel):
    access_token: str
    token_type: str
    expires_in: int
