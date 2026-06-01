from __future__ import annotations

from contextlib import asynccontextmanager
from typing import Any, AsyncIterator

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_replica_session, get_session
from app.models import Role, User


@asynccontextmanager
async def _acquire_session(session: AsyncSession | None, *, read_only: bool = False) -> AsyncIterator[AsyncSession]:
    if session is not None:
        yield session
        return

    session_factory = get_replica_session if read_only else get_session
    session_iterator = session_factory()
    resolved_session = await anext(session_iterator)
    try:
        yield resolved_session
    finally:
        await session_iterator.aclose()


async def get_by_email(email: str, session: AsyncSession | None = None) -> User | None:
    async with _acquire_session(session, read_only=True) as db_session:
        result = await db_session.execute(select(User).where(User.email == email))
        return result.scalar_one_or_none()


async def create_user(
    session: AsyncSession,
    email: str,
    nom: str,
    prenom: str,
    actif: bool = True,
    premier_login: bool = True,
) -> User:
    user = User(
        email=email,
        mdp=None,
        nom=nom,
        prenom=prenom,
        actif=actif,
        premier_login=premier_login,
    )
    session.add(user)
    await session.flush()
    return user


async def update_user(session: AsyncSession, user: User, **kwargs: Any) -> User:
    for field, value in kwargs.items():
        if field == "mdp":
            user.mdp = None
            continue
        if hasattr(user, field) and value is not None:
            setattr(user, field, value)

    await session.flush()
    await session.commit()
    await session.refresh(user)
    return user


async def ensure_role_exists(session: AsyncSession, libelle: str) -> Role:
    result = await session.execute(select(Role).where(Role.libelle == libelle))
    role = result.scalar_one_or_none()
    if role is not None:
        return role

    role = Role(libelle=libelle)
    session.add(role)
    await session.flush()
    return role


def get_user_roles(user: User) -> list[str]:
    return [role.libelle for role in user.roles]
