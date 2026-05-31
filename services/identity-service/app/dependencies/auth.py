from __future__ import annotations

from collections.abc import Callable

import jwt
from fastapi import Depends, HTTPException, Request, status
from redis.asyncio import Redis

from app.redis_client import get_redis
from app.services.jwt_service import validate_token


async def get_current_user(request: Request, redis: Redis = Depends(get_redis)) -> dict[str, object]:
    authorization = request.headers.get("Authorization", "")
    if not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
        )

    token = authorization.removeprefix("Bearer ").strip()
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
        )

    blacklist_key = f"identity:blacklist:{token}"
    if await redis.get(blacklist_key):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token is invalid or expired",
        )

    try:
        payload = validate_token(token)
    except (jwt.ExpiredSignatureError, jwt.InvalidTokenError) as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token is invalid or expired",
        ) from exc

    user_id = payload.get("user_id")
    email = payload.get("email")
    roles = payload.get("roles")

    if user_id is None or not isinstance(email, str) or not isinstance(roles, list):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token is invalid or expired",
        )

    return {
        "id": user_id,
        "email": email,
        "roles": roles,
    }


def require_role(*roles: str) -> Callable:
    async def dependency(current_user: dict[str, object] = Depends(get_current_user)) -> dict[str, object]:
        user_roles = current_user.get("roles", [])
        if not isinstance(user_roles, list) or not any(role in user_roles for role in roles):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions",
            )

        return current_user

    return dependency
