from uuid import UUID, uuid4

import pytest
from httpx import AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


pytestmark = pytest.mark.asyncio


async def _seed_utilisateur(
    session: AsyncSession,
    *,
    email: str,
    nom: str,
    prenom: str,
    actif: bool = True,
) -> str:
    utilisateur_id = uuid4()
    await session.execute(
        text(
            "INSERT INTO utilisateurs (id, email, nom, prenom, actif) "
            "VALUES (:id, :email, :nom, :prenom, :actif)"
        ),
        {
            "id": utilisateur_id.hex,
            "email": email,
            "nom": nom,
            "prenom": prenom,
            "actif": actif,
        },
    )
    await session.commit()
    return str(utilisateur_id)


async def _seed_role(session: AsyncSession, libelle: str) -> str:
    role_id = uuid4()
    await session.execute(
        text("INSERT INTO roles (id, libelle) VALUES (:id, :libelle)"),
        {"id": role_id.hex, "libelle": libelle},
    )
    await session.commit()
    return str(role_id)


async def _assign_role(session: AsyncSession, utilisateur_id: str, role_id: str) -> None:
    await session.execute(
        text(
            "INSERT INTO utilisateur_roles (utilisateur_id, role_id) "
            "VALUES (:utilisateur_id, :role_id)"
        ),
        {
            "utilisateur_id": UUID(utilisateur_id).hex,
            "role_id": UUID(role_id).hex,
        },
    )
    await session.commit()


async def test_list_utilisateurs_filters_and_returns_roles(
    async_client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    responsable_id = await _seed_role(db_session, "responsable_pedagogique")
    enseignant_id = await _seed_role(db_session, "enseignant")
    matching_user_id = await _seed_utilisateur(
        db_session,
        email="alice.durand@example.com",
        nom="Durand",
        prenom="Alice",
    )
    inactive_user_id = await _seed_utilisateur(
        db_session,
        email="alice.inactive@example.com",
        nom="Inactive",
        prenom="Alice",
        actif=False,
    )
    await _assign_role(db_session, matching_user_id, responsable_id)
    await _assign_role(db_session, matching_user_id, enseignant_id)
    await _assign_role(db_session, inactive_user_id, responsable_id)

    resp = await async_client.get(
        "/api/v1/utilisateurs/",
        params={"search": "alice", "role": "responsable_pedagogique", "actif": "true"},
    )

    assert resp.status_code == 200
    data = resp.json()
    assert [user["id"] for user in data] == [matching_user_id]
    assert data[0]["email"] == "alice.durand@example.com"
    assert data[0]["roles"] == ["enseignant", "responsable_pedagogique"]
    assert data[0]["actif"] is True
    assert data[0]["premier_login"] is False


async def test_get_utilisateur_returns_detail_with_roles(
    async_client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    utilisateur_id = await _seed_utilisateur(
        db_session,
        email="bob.martin@example.com",
        nom="Martin",
        prenom="Bob",
    )
    role_id = await _seed_role(db_session, "admin_pedagogique")
    await _assign_role(db_session, utilisateur_id, role_id)

    resp = await async_client.get(f"/api/v1/utilisateurs/{utilisateur_id}")

    assert resp.status_code == 200
    data = resp.json()
    assert data == {
        "id": utilisateur_id,
        "email": "bob.martin@example.com",
        "nom": "Martin",
        "prenom": "Bob",
        "roles": ["admin_pedagogique"],
        "actif": True,
        "premier_login": False,
    }


async def test_get_utilisateur_returns_404_when_missing(async_client: AsyncClient) -> None:
    resp = await async_client.get(f"/api/v1/utilisateurs/{uuid4()}")

    assert resp.status_code == 404
