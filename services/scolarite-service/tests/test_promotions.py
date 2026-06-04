from uuid import uuid4

import pytest
from httpx import AsyncClient

from app.schemas import PromotionCreate


pytestmark = pytest.mark.asyncio


async def _create_promotion(
    async_client: AsyncClient, nom: str = "ING-P", annee: str = "2025-2026"
) -> str:
    resp = await async_client.post(
        "/api/v1/promotions/",
        json=PromotionCreate(nom=nom, annee_scolaire=annee).model_dump(),
    )
    assert resp.status_code == 201
    return resp.json()["id"]


async def _create_etudiant(async_client: AsyncClient, promotion_id: str) -> str:
    resp = await async_client.post(
        "/api/v1/etudiants/",
        json={"nom": "Dupont", "prenom": "Alice", "promotion_id": promotion_id},
    )
    assert resp.status_code == 201
    return resp.json()["id"]


async def _create_groupe(async_client: AsyncClient, promotion_id: str) -> str:
    resp = await async_client.post(
        "/api/v1/groupes/",
        json={"nom": "TD1", "promotion_id": promotion_id},
    )
    assert resp.status_code == 201
    return resp.json()["id"]


async def test_create_promotion_returns_201(async_client: AsyncClient) -> None:
    payload = PromotionCreate(nom="ING1", annee_scolaire="2025-2026").model_dump()

    resp = await async_client.post("/api/v1/promotions/", json=payload)

    assert resp.status_code == 201
    data = resp.json()
    assert data["nom"] == "ING1"
    assert data["annee_scolaire"] == "2025-2026"
    assert "id" in data


async def test_list_promotions_returns_created_items(async_client: AsyncClient) -> None:
    await async_client.post(
        "/api/v1/promotions/",
        json=PromotionCreate(nom="ING2", annee_scolaire="2025-2026").model_dump(),
    )

    resp = await async_client.get("/api/v1/promotions/")

    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    assert len(data) == 1
    assert data[0]["nom"] == "ING2"


async def test_get_promotion_by_id_returns_200(async_client: AsyncClient) -> None:
    created = await async_client.post(
        "/api/v1/promotions/",
        json=PromotionCreate(nom="ING3", annee_scolaire="2026-2027").model_dump(),
    )
    promotion_id = created.json()["id"]

    resp = await async_client.get(f"/api/v1/promotions/{promotion_id}")

    assert resp.status_code == 200
    assert resp.json()["id"] == promotion_id


async def test_update_promotion_returns_updated_entity(async_client: AsyncClient) -> None:
    created = await async_client.post(
        "/api/v1/promotions/",
        json=PromotionCreate(nom="ING4", annee_scolaire="2026-2027").model_dump(),
    )
    promotion_id = created.json()["id"]

    resp = await async_client.patch(
        f"/api/v1/promotions/{promotion_id}",
        json={"nom": "ING4-A", "annee_scolaire": "2027-2028"},
    )

    assert resp.status_code == 200
    data = resp.json()
    assert data["id"] == promotion_id
    assert data["nom"] == "ING4-A"
    assert data["annee_scolaire"] == "2027-2028"


async def test_delete_promotion_returns_204(async_client: AsyncClient) -> None:
    created = await async_client.post(
        "/api/v1/promotions/",
        json=PromotionCreate(nom="ING5", annee_scolaire="2026-2027").model_dump(),
    )
    promotion_id = created.json()["id"]

    resp = await async_client.delete(f"/api/v1/promotions/{promotion_id}")

    assert resp.status_code == 204


async def test_create_duplicate_promotion_returns_400(async_client: AsyncClient) -> None:
    payload = PromotionCreate(nom="ING6", annee_scolaire="2026-2027").model_dump()
    await async_client.post("/api/v1/promotions/", json=payload)

    resp = await async_client.post("/api/v1/promotions/", json=payload)

    assert resp.status_code == 400


async def test_get_non_existent_promotion_returns_404(async_client: AsyncClient) -> None:
    resp = await async_client.get(f"/api/v1/promotions/{uuid4()}")

    assert resp.status_code == 404


async def test_enroll_etudiant_in_promotion_reassigns_when_no_groupes(
    async_client: AsyncClient,
) -> None:
    first_promotion_id = await _create_promotion(async_client, nom="ING7")
    second_promotion_id = await _create_promotion(async_client, nom="ING8")
    etudiant_id = await _create_etudiant(async_client, first_promotion_id)

    resp = await async_client.post(
        f"/api/v1/promotions/{second_promotion_id}/etudiants/{etudiant_id}"
    )

    assert resp.status_code == 200
    assert resp.json()["promotion_id"] == second_promotion_id


async def test_enroll_etudiant_in_same_promotion_is_idempotent(
    async_client: AsyncClient,
) -> None:
    promotion_id = await _create_promotion(async_client, nom="ING9")
    etudiant_id = await _create_etudiant(async_client, promotion_id)

    resp = await async_client.post(f"/api/v1/promotions/{promotion_id}/etudiants/{etudiant_id}")

    assert resp.status_code == 200
    assert resp.json()["promotion_id"] == promotion_id


async def test_enroll_etudiant_rejects_promotion_change_when_groupes_exist(
    async_client: AsyncClient,
) -> None:
    first_promotion_id = await _create_promotion(async_client, nom="ING10")
    second_promotion_id = await _create_promotion(async_client, nom="ING11")
    etudiant_id = await _create_etudiant(async_client, first_promotion_id)
    groupe_id = await _create_groupe(async_client, first_promotion_id)
    assign_resp = await async_client.post(f"/api/v1/etudiants/{etudiant_id}/groupes/{groupe_id}")
    assert assign_resp.status_code == 201

    resp = await async_client.post(
        f"/api/v1/promotions/{second_promotion_id}/etudiants/{etudiant_id}"
    )

    assert resp.status_code == 409
    assert resp.json()["detail"] == (
        "Cannot change promotion while student is assigned to groupes. Remove groupes first."
    )


async def test_unenroll_etudiant_from_required_promotion_returns_409(
    async_client: AsyncClient,
) -> None:
    promotion_id = await _create_promotion(async_client, nom="ING12")
    etudiant_id = await _create_etudiant(async_client, promotion_id)

    resp = await async_client.delete(f"/api/v1/promotions/{promotion_id}/etudiants/{etudiant_id}")

    assert resp.status_code == 409
    assert "promotion_id is required" in resp.json()["detail"]
