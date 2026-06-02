from uuid import uuid4

import pytest
from httpx import AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas import PromotionCreate


pytestmark = pytest.mark.asyncio


async def _seed_utilisateur(session: AsyncSession) -> str:
    utilisateur_id = uuid4()
    await session.execute(
        text(
            "INSERT INTO utilisateurs (id, email, nom, prenom, actif) "
            "VALUES (:id, :email, :nom, :prenom, :actif)"
        ),
        {
            "id": utilisateur_id.hex,
            "email": "test@example.com",
            "nom": "Dupont",
            "prenom": "Jean",
            "actif": True,
        },
    )
    await session.commit()
    return str(utilisateur_id)


async def _create_promotion(async_client: AsyncClient, nom: str = "ING-E", annee: str = "2025-2026") -> str:
    resp = await async_client.post(
        "/api/v1/promotions/",
        json=PromotionCreate(nom=nom, annee_scolaire=annee).model_dump(),
    )
    assert resp.status_code == 201
    return resp.json()["id"]


async def _create_groupe(async_client: AsyncClient, promotion_id: str, nom: str = "GE1") -> str:
    resp = await async_client.post(
        "/api/v1/groupes/",
        json={"nom": nom, "promotion_id": promotion_id},
    )
    assert resp.status_code == 201
    return resp.json()["id"]


async def test_create_etudiant_returns_201(async_client: AsyncClient, db_session: AsyncSession) -> None:
    utilisateur_id = await _seed_utilisateur(db_session)
    promotion_id = await _create_promotion(async_client)

    resp = await async_client.post(
        "/api/v1/etudiants/",
        json={"utilisateur_id": utilisateur_id, "promotion_id": promotion_id},
    )

    assert resp.status_code == 201
    data = resp.json()
    assert data["utilisateur_id"] == utilisateur_id
    assert data["promotion_id"] == promotion_id
    assert "id" in data


async def test_create_etudiant_with_unknown_utilisateur_returns_400(async_client: AsyncClient) -> None:
    promotion_id = await _create_promotion(async_client, nom="ING-E2")

    resp = await async_client.post(
        "/api/v1/etudiants/",
        json={"utilisateur_id": str(uuid4()), "promotion_id": promotion_id},
    )

    assert resp.status_code == 400


async def test_create_etudiant_with_unknown_promotion_returns_400(
    async_client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    utilisateur_id = await _seed_utilisateur(db_session)

    resp = await async_client.post(
        "/api/v1/etudiants/",
        json={"utilisateur_id": utilisateur_id, "promotion_id": str(uuid4())},
    )

    assert resp.status_code == 400


async def test_list_etudiants_returns_entries(async_client: AsyncClient, db_session: AsyncSession) -> None:
    utilisateur_id = await _seed_utilisateur(db_session)
    promotion_id = await _create_promotion(async_client, nom="ING-E3")
    await async_client.post(
        "/api/v1/etudiants/",
        json={"utilisateur_id": utilisateur_id, "promotion_id": promotion_id},
    )

    resp = await async_client.get("/api/v1/etudiants/")

    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    assert len(data) == 1


async def test_get_update_delete_etudiant_flow(async_client: AsyncClient, db_session: AsyncSession) -> None:
    utilisateur_id = await _seed_utilisateur(db_session)
    promotion_id_1 = await _create_promotion(async_client, nom="ING-E4")
    promotion_id_2 = await _create_promotion(async_client, nom="ING-E5")
    created = await async_client.post(
        "/api/v1/etudiants/",
        json={"utilisateur_id": utilisateur_id, "promotion_id": promotion_id_1},
    )
    assert created.status_code == 201
    etudiant_id = created.json()["id"]

    get_resp = await async_client.get(f"/api/v1/etudiants/{etudiant_id}")
    assert get_resp.status_code == 200
    assert get_resp.json()["id"] == etudiant_id

    patch_resp = await async_client.patch(
        f"/api/v1/etudiants/{etudiant_id}",
        json={"promotion_id": promotion_id_2},
    )
    assert patch_resp.status_code == 200
    assert patch_resp.json()["promotion_id"] == promotion_id_2

    delete_resp = await async_client.delete(f"/api/v1/etudiants/{etudiant_id}")
    assert delete_resp.status_code == 204


async def test_assign_etudiant_to_groupe(async_client: AsyncClient, db_session: AsyncSession) -> None:
    utilisateur_id = await _seed_utilisateur(db_session)
    promotion_id = await _create_promotion(async_client, nom="ING-E6")
    groupe_id = await _create_groupe(async_client, promotion_id, nom="GE2")
    created = await async_client.post(
        "/api/v1/etudiants/",
        json={"utilisateur_id": utilisateur_id, "promotion_id": promotion_id},
    )
    assert created.status_code == 201
    etudiant_id = created.json()["id"]

    resp = await async_client.post(f"/api/v1/etudiants/{etudiant_id}/groupes/{groupe_id}")

    assert resp.status_code == 201
    assert resp.json()["etudiant_id"] == etudiant_id
    assert resp.json()["groupe_id"] == groupe_id


async def test_remove_etudiant_from_groupe(async_client: AsyncClient, db_session: AsyncSession) -> None:
    utilisateur_id = await _seed_utilisateur(db_session)
    promotion_id = await _create_promotion(async_client, nom="ING-E7")
    groupe_id = await _create_groupe(async_client, promotion_id, nom="GE3")
    created = await async_client.post(
        "/api/v1/etudiants/",
        json={"utilisateur_id": utilisateur_id, "promotion_id": promotion_id},
    )
    assert created.status_code == 201
    etudiant_id = created.json()["id"]
    await async_client.post(f"/api/v1/etudiants/{etudiant_id}/groupes/{groupe_id}")

    resp = await async_client.delete(f"/api/v1/etudiants/{etudiant_id}/groupes/{groupe_id}")

    assert resp.status_code == 204


async def test_duplicate_groupe_assignment_returns_expected_status(
    async_client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    utilisateur_id = await _seed_utilisateur(db_session)
    promotion_id = await _create_promotion(async_client, nom="ING-E8")
    groupe_id = await _create_groupe(async_client, promotion_id, nom="GE4")
    created = await async_client.post(
        "/api/v1/etudiants/",
        json={"utilisateur_id": utilisateur_id, "promotion_id": promotion_id},
    )
    assert created.status_code == 201
    etudiant_id = created.json()["id"]
    first = await async_client.post(f"/api/v1/etudiants/{etudiant_id}/groupes/{groupe_id}")
    assert first.status_code == 201

    resp = await async_client.post(f"/api/v1/etudiants/{etudiant_id}/groupes/{groupe_id}")

    assert resp.status_code in {200, 400, 409}
