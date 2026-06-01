from __future__ import annotations

import json
from typing import Any

import httpx
from fastapi import HTTPException, status
from pydantic import EmailStr, TypeAdapter
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.config import settings
from app.models import User
from app.schemas.auth import LoginResponse
from app.schemas.user import UserOut
from app.services.jwt_service import generate_access_token, generate_refresh_token
from app.services.user_service import create_user, ensure_role_exists, get_by_email, get_user_roles


_email_adapter = TypeAdapter(EmailStr)


def _normalize_email(email: str) -> str:
    try:
        validated = _email_adapter.validate_python(email)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid email address") from exc

    return str(validated).strip().lower()


async def _check_login_rate_limit(redis_client: Any, client_ip: str) -> str:
    rate_limit_key = f"identity:login:rate-limit:{client_ip}"
    attempts = await redis_client.incr(rate_limit_key)

    if attempts == 1:
        await redis_client.expire(rate_limit_key, settings.rate_limit_login_window)

    if attempts > settings.rate_limit_login_max:
        raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail="Too many login attempts")

    return rate_limit_key


async def _call_mauria_login(email: str, password: str, base_url: str | None = None) -> None:
    mauria_base_url = base_url if base_url is not None else settings.mauria_api_url
    url = f"{mauria_base_url}{settings.mauria_login_path}"

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(url, json={"email": email, "password": password})
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication failed") from exc

    if response.status_code != status.HTTP_200_OK:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication failed")


async def _get_managed_user(session: AsyncSession, user_id: Any) -> User | None:
    result = await session.execute(
        select(User).options(selectinload(User.roles)).where(User.id == user_id)
    )
    return result.scalar_one_or_none()


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


async def _store_session(redis_client: Any, user: User, access_token: str, refresh_token: str) -> None:
    ttl_seconds = settings.jwt_refresh_expiration_days * 86400
    session_key = f"identity:session:{user.id}"
    payload = {
        "user_id": str(user.id),
        "email": user.email,
        "roles": get_user_roles(user),
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
    }
    await redis_client.set(session_key, json.dumps(payload), ex=ttl_seconds)


async def login(
    email: str,
    password: str,
    session: AsyncSession,
    replica_session: AsyncSession,
    redis_client: Any,
    client_ip: str,
) -> LoginResponse:
    normalized_email = _normalize_email(email)
    rate_limit_key = await _check_login_rate_limit(redis_client, client_ip)

    email_domain = normalized_email.rsplit("@", maxsplit=1)[-1]
    if email_domain == "student.junia.com" and settings.allow_student_bypass:
        mauria_allowed = True
    else:
        mauria_allowed = email_domain in {"junia.com", "ext.junia.com"}

    if not mauria_allowed:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid email domain")

    if email_domain == "student.junia.com" and settings.allow_student_bypass:
        await _call_mauria_login(
            normalized_email,
            password,
            base_url=settings.mauria_mock_url or settings.mauria_api_url,
        )
    else:
        await _call_mauria_login(normalized_email, password)

    existing_user = await get_by_email(normalized_email, replica_session)
    if existing_user is None:
        user = await create_user(
            session=session,
            email=normalized_email,
            mdp=password,
            nom="À compléter",
            prenom="À compléter",
            actif=True,
            premier_login=True,
        )
        await session.refresh(user, attribute_names=["roles"])
    else:
        user = await _get_managed_user(session, existing_user.id)
        if user is None:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
        if not user.actif:
            user.actif = True

    teacher_role = await ensure_role_exists(session, "enseignant")
    if all(role.libelle != teacher_role.libelle for role in user.roles):
        user.roles.append(teacher_role)

    await session.commit()
    await session.refresh(user)

    access_token = generate_access_token(str(user.id), user.email, get_user_roles(user))
    refresh_token = generate_refresh_token(str(user.id))
    await _store_session(redis_client, user, access_token, refresh_token)
    await redis_client.delete(rate_limit_key)

    return LoginResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
        expires_in=settings.jwt_access_expiration_minutes * 60,
        user=_build_user_out(user),
    )
