from uuid import uuid4

import pytest
from httpx import AsyncClient

from app.schemas import PromotionCreate


pytestmark = pytest.mark.asyncio


async def _create_promotion(async_client: AsyncClient, nom: str = "ING-G", annee: str = "2025-2026") -> str:
    resp = await async_client.post(
        "/api/v1/promotions/",
        json=PromotionCreate(nom=nom, annee_scolaire=annee).model_dump(),
    )
    assert resp.status_code == 201
    return resp.json()["id"]


async def test_create_groupe_returns_201(async_client: AsyncClient) -> None:
    promotion_id = await _create_promotion(async_client)

    resp = await async_client.post(
        "/api/v1/groupes/",
        json={"nom": "G1", "promotion_id": promotion_id},
    )

    assert resp.status_code == 201
    data = resp.json()
    assert data["nom"] == "G1"
    assert data["promotion_id"] == promotion_id


async def test_list_groupes_for_promotion(async_client: AsyncClient) -> None:
    promotion_id = await _create_promotion(async_client, nom="ING-H")
    await async_client.post(
        "/api/v1/groupes/",
        json={"nom": "G2", "promotion_id": promotion_id},
    )

    resp = await async_client.get(f"/api/v1/promotions/{promotion_id}/groupes")

    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    assert len(data) == 1
    assert data[0]["nom"] == "G2"


async def test_create_groupe_with_unknown_promotion_returns_400(async_client: AsyncClient) -> None:
    resp = await async_client.post(
        "/api/v1/groupes/",
        json={"nom": "G3", "promotion_id": str(uuid4())},
    )

    assert resp.status_code == 400


async def test_get_update_delete_groupe_flow(async_client: AsyncClient) -> None:
    promotion_id = await _create_promotion(async_client, nom="ING-I")
    promotion_id_2 = await _create_promotion(async_client, nom="ING-J")
    created = await async_client.post(
        "/api/v1/groupes/",
        json={"nom": "G4", "promotion_id": promotion_id},
    )
    groupe_id = created.json()["id"]

    get_resp = await async_client.get(f"/api/v1/groupes/{groupe_id}")
    assert get_resp.status_code == 200
    assert get_resp.json()["id"] == groupe_id

    patch_resp = await async_client.patch(
        f"/api/v1/groupes/{groupe_id}",
        json={"nom": "G4-B", "promotion_id": promotion_id_2},
    )
    assert patch_resp.status_code == 200
    assert patch_resp.json()["nom"] == "G4-B"
    assert patch_resp.json()["promotion_id"] == promotion_id_2

    delete_resp = await async_client.delete(f"/api/v1/groupes/{groupe_id}")
    assert delete_resp.status_code == 204


async def test_get_non_existent_groupe_returns_404(async_client: AsyncClient) -> None:
    resp = await async_client.get(f"/api/v1/groupes/{uuid4()}")

    assert resp.status_code == 404
