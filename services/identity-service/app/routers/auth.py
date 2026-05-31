from __future__ import annotations

import json
from datetime import datetime, timezone
from math import ceil
from uuid import UUID

import jwt
from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.config import settings
from app.database import get_replica_session, get_session
from app.dependencies.auth import get_current_user
from app.models import User
from app.redis_client import get_redis
from app.schemas.auth import LoginRequest, LoginResponse, RefreshRequest, RefreshResponse
from app.schemas.user import UserOut
from app.services.auth_service import login as auth_login
from app.services.jwt_service import generate_access_token, validate_token
from app.services.user_service import get_user_roles


router = APIRouter(prefix="/auth", tags=["auth"])


def _build_user_out(user: User) -> UserOut:
    return UserOut(
        id=user.id,
        email=user.email,
        nom=user.nom,
        prenom=user.prenom,
        roles=get_user_roles(user),
        actif=user.actif,
        premier_login=user.premier_login,
    )


def _extract_bearer_token(request: Request) -> str:
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

    return token


def _coerce_user_id(user_id: object) -> object:
    try:
        return UUID(str(user_id))
    except (TypeError, ValueError):
        return user_id


def _token_ttl_seconds(payload: dict[str, object]) -> int:
    exp = payload.get("exp")
    if not isinstance(exp, (int, float)):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token is invalid or expired",
        )

    expires_at = datetime.fromtimestamp(exp, tz=timezone.utc)
    ttl_seconds = ceil((expires_at - datetime.now(timezone.utc)).total_seconds())
    if ttl_seconds <= 0:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token is invalid or expired",
        )

    return ttl_seconds


async def _get_user_by_id(session: AsyncSession, user_id: object) -> User | None:
    result = await session.execute(
        select(User).options(selectinload(User.roles)).where(User.id == _coerce_user_id(user_id))
    )
    return result.scalar_one_or_none()


@router.post("/login", response_model=LoginResponse)
async def login(
    payload: LoginRequest,
    session: AsyncSession = Depends(get_session),
    replica_session: AsyncSession = Depends(get_replica_session),
    redis=Depends(get_redis),
) -> LoginResponse:
    return await auth_login(
        email=payload.email,
        password=payload.password,
        session=session,
        replica_session=replica_session,
        redis_client=redis,
    )


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(request: Request, redis=Depends(get_redis)) -> Response:
    token = _extract_bearer_token(request)

    try:
        payload = validate_token(token)
    except (jwt.ExpiredSignatureError, jwt.InvalidTokenError) as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token is invalid or expired",
        ) from exc

    blacklist_key = f"identity:blacklist:{token}"
    if await redis.get(blacklist_key):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token is invalid or expired",
        )

    ttl_seconds = _token_ttl_seconds(payload)
    await redis.set(blacklist_key, "1", ex=ttl_seconds)

    user_id = payload.get("user_id")
    if user_id is not None:
        session_key = f"identity:session:{user_id}"
        session_data = await redis.get(session_key)
        if session_data:
            try:
                session_payload = json.loads(session_data)
            except json.JSONDecodeError:
                session_payload = {}

            refresh_token = session_payload.get("refresh_token")
            if isinstance(refresh_token, str) and refresh_token:
                try:
                    refresh_payload = validate_token(refresh_token)
                except (jwt.ExpiredSignatureError, jwt.InvalidTokenError):
                    refresh_payload = None
                if refresh_payload is not None:
                    refresh_blacklist_key = f"identity:blacklist:{refresh_token}"
                    refresh_ttl_seconds = _token_ttl_seconds(refresh_payload)
                    await redis.set(refresh_blacklist_key, "1", ex=refresh_ttl_seconds)

            await redis.delete(session_key)

    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/me", response_model=UserOut)
async def me(
    current_user: dict[str, object] = Depends(get_current_user),
    replica_session: AsyncSession = Depends(get_replica_session),
) -> UserOut:
    user = await _get_user_by_id(replica_session, current_user.get("id"))
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token is invalid or expired",
        )

    return _build_user_out(user)


@router.post("/refresh", response_model=RefreshResponse)
async def refresh(
    payload: RefreshRequest,
    redis=Depends(get_redis),
    replica_session: AsyncSession = Depends(get_replica_session),
) -> RefreshResponse:
    blacklist_key = f"identity:blacklist:{payload.refresh_token}"
    if await redis.get(blacklist_key):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token",
        )

    try:
        token_payload = validate_token(payload.refresh_token)
    except (jwt.ExpiredSignatureError, jwt.InvalidTokenError) as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token",
        ) from exc

    if token_payload.get("token_type") != "refresh":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token",
        )

    user = await _get_user_by_id(replica_session, token_payload.get("user_id"))
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token",
        )

    access_token = generate_access_token(str(user.id), user.email, get_user_roles(user))
    return RefreshResponse(
        access_token=access_token,
        token_type="bearer",
        expires_in=settings.jwt_access_expiration_minutes * 60,
    )
