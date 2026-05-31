from __future__ import annotations

import asyncio
from types import SimpleNamespace
from uuid import UUID, uuid4
from unittest.mock import AsyncMock, patch

import httpx
import pytest
import pytest_asyncio
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.database import get_replica_session, get_session
from app.main import app as fastapi_app
from app.models import Role, User
from app.redis_client import get_redis
from app.routers import auth as auth_router
from app.services import auth_service
from app.services.jwt_service import validate_token


pytestmark = pytest.mark.asyncio


class FakeSession:
    async def commit(self) -> None:
        return None

    async def refresh(self, obj: object, *args: object, **kwargs: object) -> None:
        return None

    async def flush(self) -> None:
        return None


def _make_user(email: str, password: str = "secret") -> User:
    user = User(
        email=email,
        mdp=password,
        nom="À compléter",
        prenom="À compléter",
        actif=True,
        premier_login=True,
    )
    user.id = uuid4()
    user.roles = []
    return user


def _make_role(libelle: str = "enseignant") -> Role:
    role = Role(libelle=libelle)
    role.id = uuid4()
    role.users = []
    return role


@pytest_asyncio.fixture
async def fake_session() -> FakeSession:
    return FakeSession()


@pytest_asyncio.fixture
async def user_store() -> dict[str, User]:
    return {}


@pytest_asyncio.fixture
async def app(monkeypatch: pytest.MonkeyPatch, redis_client, fake_session: FakeSession, user_store: dict[str, User]):
    async def fake_get_session() -> FakeSession:
        yield fake_session

    async def fake_get_replica_session() -> FakeSession:
        yield fake_session

    async def fake_get_redis():
        return redis_client

    async def fake_get_by_email(email: str, session: object | None = None) -> User | None:
        return user_store.get(email)

    async def fake_create_user(
        session: object,
        email: str,
        mdp: str,
        nom: str,
        prenom: str,
        actif: bool = True,
        premier_login: bool = True,
    ) -> User:
        user = _make_user(email, mdp)
        user.nom = nom
        user.prenom = prenom
        user.actif = actif
        user.premier_login = premier_login
        user_store[email] = user
        return user

    async def fake_ensure_role_exists(session: object, libelle: str) -> Role:
        return _make_role(libelle)

    async def fake_get_user_by_id(session: object, user_id: object) -> User | None:
        for user in user_store.values():
            if str(user.id) == str(user_id):
                return user
        return None

    monkeypatch.setattr(auth_service, "get_by_email", fake_get_by_email)
    monkeypatch.setattr(auth_service, "create_user", fake_create_user)
    monkeypatch.setattr(auth_service, "ensure_role_exists", fake_ensure_role_exists)
    monkeypatch.setattr(auth_router, "_get_user_by_id", fake_get_user_by_id)
    fastapi_app.dependency_overrides[get_session] = fake_get_session
    fastapi_app.dependency_overrides[get_replica_session] = fake_get_replica_session
    fastapi_app.dependency_overrides[get_redis] = fake_get_redis

    try:
        yield fastapi_app
    finally:
        fastapi_app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def client(app):
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as async_client:
        yield async_client


async def _post_login(client: httpx.AsyncClient, email: str, password: str, status_code: int) -> httpx.Response:
    response_payload = SimpleNamespace(status_code=status_code)
    with patch("app.services.auth_service.httpx.AsyncClient") as mocked_async_client:
        mocked_client = AsyncMock()
        mocked_client.post = AsyncMock(return_value=response_payload)
        mocked_async_client.return_value.__aenter__.return_value = mocked_client

        return await client.post(
            "/api/v1/auth/login",
            json={"email": email, "password": password},
        )


async def _post_login_real_db(
    client: httpx.AsyncClient, email: str, password: str, status_code: int
) -> httpx.Response:
    response_payload = SimpleNamespace(status_code=status_code)

    with patch("app.services.auth_service.httpx.AsyncClient") as mocked_async_client:
        mocked_client = AsyncMock()
        mocked_client.post = AsyncMock(return_value=response_payload)
        mocked_async_client.return_value.__aenter__.return_value = mocked_client

        return await client.post(
            "/api/v1/auth/login",
            json={"email": email, "password": password},
        )


async def _get_user_by_email(db_session, email: str) -> User | None:
    result = await db_session.execute(
        select(User).options(selectinload(User.roles)).where(User.email == email)
    )
    return result.scalar_one_or_none()


async def test_login_success(client: httpx.AsyncClient, user_store: dict[str, User]) -> None:
    response = await _post_login(client, email="alice@junia.com", password="secret", status_code=200)

    assert response.status_code == 200

    data = response.json()
    assert data["token_type"] == "bearer"
    assert data["access_token"]
    assert data["refresh_token"]
    assert validate_token(data["access_token"])["token_type"] == "access"
    assert validate_token(data["refresh_token"])["token_type"] == "refresh"

    user = data["user"]
    assert user["email"] == "alice@junia.com"
    assert user["nom"] == "À compléter"
    assert user["prenom"] == "À compléter"
    assert user["roles"] == ["enseignant"]
    assert user["actif"] is True
    assert user["premier_login"] is True
    assert "alice@junia.com" in user_store
    assert user_store["alice@junia.com"].id == UUID(user["id"])


async def test_login_success_real_db(async_client: httpx.AsyncClient, db_session, redis_client) -> None:
    response = await _post_login_real_db(async_client, email="alice@junia.com", password="secret", status_code=200)

    assert response.status_code == 200

    data = response.json()
    assert data["token_type"] == "bearer"
    assert data["access_token"]
    assert data["refresh_token"]
    assert validate_token(data["access_token"])["token_type"] == "access"
    assert validate_token(data["refresh_token"])["token_type"] == "refresh"

    user = await _get_user_by_email(db_session, "alice@junia.com")
    assert user is not None
    assert user.id == UUID(data["user"]["id"])
    assert user.email == "alice@junia.com"
    assert user.nom == "À compléter"
    assert user.prenom == "À compléter"
    assert user.actif is True
    assert user.premier_login is True
    assert user.created_at is not None
    assert [role.libelle for role in user.roles] == ["enseignant"]

    role_result = await db_session.execute(select(Role).where(Role.libelle == "enseignant"))
    role = role_result.scalar_one_or_none()
    assert role is not None
    assert user.roles[0].id == role.id
    assert redis_client.store[f"identity:session:{user.id}"]


async def test_login_invalid_credentials(client: httpx.AsyncClient) -> None:
    response = await _post_login(client, email="alice@junia.com", password="wrongpw", status_code=500)

    assert response.status_code == 401
    assert response.json()["detail"] == "Authentication failed"


async def test_login_invalid_email_domain(client: httpx.AsyncClient) -> None:
    response = await client.post(
        "/api/v1/auth/login",
        json={"email": "alice@gmail.com", "password": "secret"},
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Invalid email domain"


async def test_login_rate_limit(client: httpx.AsyncClient) -> None:
    responses = []
    for _ in range(6):
        responses.append(await _post_login(client, email="alice@junia.com", password="secret", status_code=500))

    assert [response.status_code for response in responses[:5]] == [401, 401, 401, 401, 401]
    assert responses[5].status_code == 429
    assert responses[5].json()["detail"] == "Too many login attempts"


async def test_logout(client: httpx.AsyncClient, redis_client) -> None:
    login_response = await _post_login(client, email="alice@junia.com", password="secret", status_code=200)
    login_data = login_response.json()
    access_token = login_data["access_token"]
    refresh_token = login_data["refresh_token"]
    user_id = str(validate_token(access_token)["user_id"])

    response = await client.post("/api/v1/auth/logout", headers={"Authorization": f"Bearer {access_token}"})

    assert response.status_code == 204
    assert redis_client.store[f"identity:blacklist:{access_token}"] == "1"
    assert redis_client.store[f"identity:blacklist:{refresh_token}"] == "1"
    assert f"identity:session:{user_id}" not in redis_client.store


async def test_logout_real_db(async_client: httpx.AsyncClient, db_session, redis_client) -> None:
    login_response = await _post_login_real_db(async_client, email="alice@junia.com", password="secret", status_code=200)
    login_data = login_response.json()
    access_token = login_data["access_token"]
    refresh_token = login_data["refresh_token"]
    user_id = str(validate_token(access_token)["user_id"])

    response = await async_client.post("/api/v1/auth/logout", headers={"Authorization": f"Bearer {access_token}"})

    assert response.status_code == 204
    assert redis_client.store[f"identity:blacklist:{access_token}"] == "1"
    assert redis_client.store[f"identity:blacklist:{refresh_token}"] == "1"
    assert f"identity:session:{user_id}" not in redis_client.store

    user = await _get_user_by_email(db_session, "alice@junia.com")
    assert user is not None
    assert [role.libelle for role in user.roles] == ["enseignant"]


async def test_me(client: httpx.AsyncClient) -> None:
    login_response = await _post_login(client, email="alice@junia.com", password="secret", status_code=200)
    login_data = login_response.json()
    access_token = login_data["access_token"]

    response = await client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {access_token}"})

    assert response.status_code == 200
    data = response.json()
    assert data["email"] == "alice@junia.com"
    assert data["roles"] == ["enseignant"]
    assert data["actif"] is True
    assert data["premier_login"] is True


async def test_me_real_db(async_client: httpx.AsyncClient, db_session, redis_client) -> None:
    login_response = await _post_login_real_db(async_client, email="alice@junia.com", password="secret", status_code=200)
    login_data = login_response.json()
    access_token = login_data["access_token"]

    response = await async_client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {access_token}"})

    assert response.status_code == 200
    data = response.json()

    user = await _get_user_by_email(db_session, "alice@junia.com")
    assert user is not None
    assert data["id"] == str(user.id)
    assert data["email"] == user.email
    assert data["nom"] == user.nom
    assert data["prenom"] == user.prenom
    assert data["roles"] == [role.libelle for role in user.roles]
    assert data["actif"] is user.actif
    assert data["premier_login"] is user.premier_login


async def test_me_invalid_token(client: httpx.AsyncClient) -> None:
    response = await client.get("/api/v1/auth/me", headers={"Authorization": "Bearer invalid-token"})

    assert response.status_code == 401
    assert response.json()["detail"] == "Token is invalid or expired"


async def test_refresh_token(client: httpx.AsyncClient) -> None:
    login_response = await _post_login(client, email="alice@junia.com", password="secret", status_code=200)
    login_data = login_response.json()
    refresh_token = login_data["refresh_token"]

    await asyncio.sleep(1.1)

    response = await client.post("/api/v1/auth/refresh", json={"refresh_token": refresh_token})

    assert response.status_code == 200
    data = response.json()
    assert data["token_type"] == "bearer"
    assert data["expires_in"] > 0
    assert data["access_token"]
    assert data["access_token"] != login_data["access_token"]
    assert validate_token(data["access_token"])["token_type"] == "access"
    assert validate_token(data["access_token"])["user_id"] == validate_token(refresh_token)["user_id"]


async def test_refresh_token_after_logout_rejected(client: httpx.AsyncClient) -> None:
    login_response = await _post_login(client, email="alice@junia.com", password="secret", status_code=200)
    login_data = login_response.json()
    access_token = login_data["access_token"]
    refresh_token = login_data["refresh_token"]

    logout_response = await client.post("/api/v1/auth/logout", headers={"Authorization": f"Bearer {access_token}"})
    assert logout_response.status_code == 204

    response = await client.post("/api/v1/auth/refresh", json={"refresh_token": refresh_token})

    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid refresh token"
