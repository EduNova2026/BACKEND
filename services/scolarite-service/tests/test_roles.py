from uuid import uuid4

import pytest
from httpx import AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


pytestmark = pytest.mark.asyncio


async def _seed_utilisateur(session: AsyncSession, email: str = "role-user@example.com") -> str:
    utilisateur_id = uuid4()
    await session.execute(
        text(
            "INSERT INTO utilisateurs (id, email, nom, prenom, actif) "
            "VALUES (:id, :email, :nom, :prenom, :actif)"
        ),
        {
            "id": utilisateur_id.hex,
            "email": email,
            "nom": "Durand",
            "prenom": "Alice",
            "actif": True,
        },
    )
    await session.commit()
    return str(utilisateur_id)


async def _seed_role(session: AsyncSession, libelle: str = "admin_pedagogique") -> str:
    role_id = uuid4()
    await session.execute(
        text("INSERT INTO roles (id, libelle) VALUES (:id, :libelle)"),
        {"id": role_id.hex, "libelle": libelle},
    )
    await session.commit()
    return str(role_id)


async def test_list_roles(async_client: AsyncClient, db_session: AsyncSession) -> None:
    role_id = await _seed_role(db_session, libelle="enseignant")

    resp = await async_client.get("/api/v1/roles/")

    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    assert any(role["id"] == role_id for role in data)


async def test_assign_role_to_user_returns_created(
    async_client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    utilisateur_id = await _seed_utilisateur(db_session)
    role_id = await _seed_role(db_session)

    resp = await async_client.post(
        f"/api/v1/roles/utilisateurs/{utilisateur_id}/roles",
        json={"role_id": role_id},
    )

    assert resp.status_code in {200, 201}
    data = resp.json()
    assert data["utilisateur_id"] == utilisateur_id
    assert data["role_id"] == role_id


async def test_list_user_roles(async_client: AsyncClient, db_session: AsyncSession) -> None:
    utilisateur_id = await _seed_utilisateur(db_session, email="roles-list@example.com")
    role_id = await _seed_role(db_session, libelle="responsable_pedagogique")
    await async_client.post(
        f"/api/v1/roles/utilisateurs/{utilisateur_id}/roles",
        json={"role_id": role_id},
    )

    resp = await async_client.get(f"/api/v1/roles/utilisateurs/{utilisateur_id}/roles")

    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    assert len(data) == 1
    assert data[0]["role_id"] == role_id


async def test_assign_same_role_twice_is_idempotent(
    async_client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    utilisateur_id = await _seed_utilisateur(db_session, email="roles-dup@example.com")
    role_id = await _seed_role(db_session, libelle="enseignant")

    first = await async_client.post(
        f"/api/v1/roles/utilisateurs/{utilisateur_id}/roles",
        json={"role_id": role_id},
    )
    assert first.status_code in {200, 201}

    second = await async_client.post(
        f"/api/v1/roles/utilisateurs/{utilisateur_id}/roles",
        json={"role_id": role_id},
    )

    assert second.status_code in {200, 201}


async def test_remove_role_from_user(async_client: AsyncClient, db_session: AsyncSession) -> None:
    utilisateur_id = await _seed_utilisateur(db_session, email="roles-remove@example.com")
    role_id = await _seed_role(db_session, libelle="admin_pedagogique")
    await async_client.post(
        f"/api/v1/roles/utilisateurs/{utilisateur_id}/roles",
        json={"role_id": role_id},
    )

    resp = await async_client.delete(f"/api/v1/roles/utilisateurs/{utilisateur_id}/roles/{role_id}")

    assert resp.status_code == 204


async def test_assign_non_existent_role_returns_400(
    async_client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    utilisateur_id = await _seed_utilisateur(db_session, email="roles-no-role@example.com")

    resp = await async_client.post(
        f"/api/v1/roles/utilisateurs/{utilisateur_id}/roles",
        json={"role_id": str(uuid4())},
    )

    assert resp.status_code == 400


async def test_assign_role_to_non_existent_user_returns_400(
    async_client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    role_id = await _seed_role(db_session, libelle="enseignant")

    resp = await async_client.post(
        f"/api/v1/roles/utilisateurs/{uuid4()}/roles",
        json={"role_id": role_id},
    )

    assert resp.status_code == 400
