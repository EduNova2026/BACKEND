from collections.abc import AsyncGenerator

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
