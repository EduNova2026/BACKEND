from collections.abc import AsyncGenerator

from sqlalchemy import insert, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from .config import settings


class Base(DeclarativeBase):
    pass


def create_engine_from_url(url: str):
    return create_async_engine(url, pool_pre_ping=True)


engine = create_engine_from_url(settings.database_url) if settings.database_url else None
replica_engine = (
    create_engine_from_url(settings.database_replica_url)
    if settings.database_replica_url
    else engine
)

SessionLocal = async_sessionmaker(engine, expire_on_commit=False) if engine else None
ReplicaSessionLocal = (
    async_sessionmaker(replica_engine, expire_on_commit=False) if replica_engine else None
)


async def get_session() -> AsyncGenerator[AsyncSession]:
    if SessionLocal is None:
        raise RuntimeError("DATABASE_URL is not configured")

    async with SessionLocal() as session:
        yield session


async def get_replica_session() -> AsyncGenerator[AsyncSession]:
    if ReplicaSessionLocal is None:
        raise RuntimeError("DATABASE_REPLICA_URL is not configured")

    async with ReplicaSessionLocal() as session:
        yield session


async def seed_roles() -> None:
    if SessionLocal is None:
        raise RuntimeError("DATABASE_URL is not configured")

    from .models import Role

    role_names = ["enseignant", "admin_pedagogique", "responsable_pedagogique"]

    async with SessionLocal() as session:
        existing_roles = await session.scalars(
            select(Role.libelle).where(Role.libelle.in_(role_names))
        )
        existing_role_names = set(existing_roles.all())
        missing_role_names = [name for name in role_names if name not in existing_role_names]

        if not missing_role_names:
            return

        await session.execute(insert(Role), [{"libelle": name} for name in missing_role_names])
        await session.commit()
