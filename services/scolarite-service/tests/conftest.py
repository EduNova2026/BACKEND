from __future__ import annotations

from collections.abc import AsyncIterator
from datetime import datetime, timedelta, UTC
import os
from uuid import uuid4

import jwt
import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

os.environ.setdefault("APP_NAME", "scolarite-service")
os.environ.setdefault("JWT_SECRET", "test-secret")

from app.database import Base, get_replica_session, get_session
from app.main import app
from app import models as _models  # noqa: F401
from app.external_models import external_metadata


def build_auth_headers(
    user_id: str | None = None,
    roles: list[str] | None = None,
    email: str = "admin@example.com",
) -> dict[str, str]:
    token = jwt.encode(
        {
            "user_id": user_id or str(uuid4()),
            "email": email,
            "roles": roles or ["admin_pedagogique"],
            "token_type": "access",
            "iat": datetime.now(UTC),
            "exp": datetime.now(UTC) + timedelta(hours=1),
        },
        os.environ["JWT_SECRET"],
        algorithm="HS256",
    )
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def auth_headers_factory():
    return build_auth_headers


@pytest_asyncio.fixture(scope="session")
async def test_engine() -> AsyncIterator[AsyncEngine]:
    engine = create_async_engine(
        "sqlite+aiosqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
        await connection.run_sync(external_metadata.create_all)

    yield engine

    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.drop_all)
        await connection.run_sync(external_metadata.drop_all)

    await engine.dispose()


@pytest_asyncio.fixture(autouse=True)
async def clean_test_data(test_engine: AsyncEngine) -> AsyncIterator[None]:
    async with test_engine.begin() as connection:
        for table in reversed(Base.metadata.sorted_tables):
            await connection.execute(table.delete())
        for table in reversed(external_metadata.sorted_tables):
            await connection.execute(table.delete())

    yield

    async with test_engine.begin() as connection:
        for table in reversed(Base.metadata.sorted_tables):
            await connection.execute(table.delete())
        for table in reversed(external_metadata.sorted_tables):
            await connection.execute(table.delete())


@pytest_asyncio.fixture
async def db_session(test_engine: AsyncEngine) -> AsyncIterator[AsyncSession]:
    session_factory = async_sessionmaker(test_engine, expire_on_commit=False)

    async with session_factory() as session:
        yield session
        await session.rollback()


@pytest_asyncio.fixture
async def async_client(test_engine: AsyncEngine) -> AsyncIterator[AsyncClient]:
    session_factory = async_sessionmaker(test_engine, expire_on_commit=False)

    async def override_get_session() -> AsyncIterator[AsyncSession]:
        async with session_factory() as session:
            yield session

    async def override_get_replica_session() -> AsyncIterator[AsyncSession]:
        async with session_factory() as session:
            yield session

    app.dependency_overrides[get_session] = override_get_session
    app.dependency_overrides[get_replica_session] = override_get_replica_session

    transport = ASGITransport(app=app)
    async with AsyncClient(
        transport=transport,
        base_url="http://test",
        headers=build_auth_headers(),
    ) as client:
        yield client

    app.dependency_overrides.clear()
