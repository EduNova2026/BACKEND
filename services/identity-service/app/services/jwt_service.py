from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

import jwt

from app.config import settings


def _encode_token(payload: dict[str, Any], expires_delta: timedelta) -> str:
    now = datetime.utcnow()
    token_payload = {
        **payload,
        "iat": now,
        "exp": now + expires_delta,
    }
    return jwt.encode(
        token_payload,
        settings.jwt_secret,
        algorithm=settings.jwt_algorithm,
    )


def generate_access_token(user_id: int | str, email: str, roles: list[str] | tuple[str, ...]) -> str:
    return _encode_token(
        {
            "user_id": user_id,
            "email": email,
            "roles": list(roles),
            "token_type": "access",
        },
        timedelta(minutes=settings.jwt_access_expiration_minutes),
    )


def generate_refresh_token(user_id: int | str) -> str:
    return _encode_token(
        {
            "user_id": user_id,
            "token_type": "refresh",
        },
        timedelta(days=settings.jwt_refresh_expiration_days),
    )


def validate_token(token: str) -> dict[str, Any]:
    try:
        return jwt.decode(
            token,
            settings.jwt_secret,
            algorithms=[settings.jwt_algorithm],
        )
    except jwt.ExpiredSignatureError as exc:
        raise jwt.ExpiredSignatureError("Token has expired") from exc
    except jwt.InvalidTokenError as exc:
        raise jwt.InvalidTokenError("Invalid token") from exc


def refresh_access_token(refresh_token: str) -> str:
    payload = validate_token(refresh_token)
    if payload.get("token_type") != "refresh":
        raise jwt.InvalidTokenError("Invalid refresh token")

    return generate_access_token(
        payload["user_id"],
        payload.get("email", ""),
        payload.get("roles", []),
    )
