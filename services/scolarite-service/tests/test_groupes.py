from uuid import uuid4

import pytest
from httpx import AsyncClient

from app.schemas import PromotionCreate
from .conftest import build_auth_headers


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
        headers=build_auth_headers(),
    )

    assert resp.status_code == 201
    data = resp.json()
    assert data["nom"] == "G1"
    assert data["promotion_id"] == promotion_id
    assert data["semestre"] == 1
    assert data["coefficient"] == 1.0


async def test_create_groupe_with_semestre_2(async_client: AsyncClient) -> None:
    promotion_id = await _create_promotion(async_client, nom="ING-G-S2")

    resp = await async_client.post(
        "/api/v1/groupes/",
        json={"nom": "G1-S2", "promotion_id": promotion_id, "semestre": 2},
    )

    assert resp.status_code == 201
    data = resp.json()
    assert data["nom"] == "G1-S2"
    assert data["promotion_id"] == promotion_id
    assert data["semestre"] == 2


async def test_create_groupe_with_coefficient(async_client: AsyncClient) -> None:
    promotion_id = await _create_promotion(async_client, nom="ING-G-COEFF")

    resp = await async_client.post(
        "/api/v1/groupes/",
        json={"nom": "G1-COEFF", "promotion_id": promotion_id, "coefficient": 2.5},
        headers=build_auth_headers(),
    )

    assert resp.status_code == 201
    data = resp.json()
    assert data["nom"] == "G1-COEFF"
    assert data["promotion_id"] == promotion_id
    assert data["semestre"] == 1
    assert data["coefficient"] == 2.5


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


async def test_create_groupe_with_invalid_semestre_returns_422(async_client: AsyncClient) -> None:
    promotion_id = await _create_promotion(async_client, nom="ING-G-INVALID-S3")

    resp = await async_client.post(
        "/api/v1/groupes/",
        json={"nom": "G3-S3", "promotion_id": promotion_id, "semestre": 3},
    )

    assert resp.status_code == 422


async def test_create_groupe_with_semestre_0_returns_422(async_client: AsyncClient) -> None:
    promotion_id = await _create_promotion(async_client, nom="ING-G-INVALID-S0")

    resp = await async_client.post(
        "/api/v1/groupes/",
        json={"nom": "G3-S0", "promotion_id": promotion_id, "semestre": 0},
    )

    assert resp.status_code == 422


async def test_create_groupe_with_coefficient_0_returns_422(async_client: AsyncClient) -> None:
    promotion_id = await _create_promotion(async_client, nom="ING-G-INVALID-C0")

    resp = await async_client.post(
        "/api/v1/groupes/",
        json={"nom": "G3-C0", "promotion_id": promotion_id, "coefficient": 0},
        headers=build_auth_headers(),
    )

    assert resp.status_code == 422


async def test_create_groupe_with_negative_coefficient_returns_422(
    async_client: AsyncClient,
) -> None:
    promotion_id = await _create_promotion(async_client, nom="ING-G-INVALID-CNEG")

    resp = await async_client.post(
        "/api/v1/groupes/",
        json={"nom": "G3-CNEG", "promotion_id": promotion_id, "coefficient": -1},
        headers=build_auth_headers(),
    )

    assert resp.status_code == 422


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
    assert get_resp.json()["semestre"] == 1
    assert get_resp.json()["coefficient"] == 1.0

    patch_resp = await async_client.patch(
        f"/api/v1/groupes/{groupe_id}",
        json={
            "nom": "G4-B",
            "promotion_id": promotion_id_2,
            "semestre": 2,
            "coefficient": 2.5,
        },
        headers=build_auth_headers(),
    )
    assert patch_resp.status_code == 200
    assert patch_resp.json()["nom"] == "G4-B"
    assert patch_resp.json()["promotion_id"] == promotion_id_2
    assert patch_resp.json()["semestre"] == 2
    assert patch_resp.json()["coefficient"] == 2.5

    delete_resp = await async_client.delete(f"/api/v1/groupes/{groupe_id}")
    assert delete_resp.status_code == 204


async def test_get_non_existent_groupe_returns_404(async_client: AsyncClient) -> None:
    resp = await async_client.get(f"/api/v1/groupes/{uuid4()}")

    assert resp.status_code == 404


async def test_patch_groupe_semestre(async_client: AsyncClient) -> None:
    promotion_id = await _create_promotion(async_client, nom="ING-G-PATCH-S2")
    created = await async_client.post(
        "/api/v1/groupes/",
        json={"nom": "G5", "promotion_id": promotion_id},
    )
    groupe_id = created.json()["id"]
    assert created.json()["semestre"] == 1

    patch_resp = await async_client.patch(
        f"/api/v1/groupes/{groupe_id}",
        json={"semestre": 2},
    )

    assert patch_resp.status_code == 200
    data = patch_resp.json()
    assert data["id"] == groupe_id
    assert data["nom"] == "G5"
    assert data["promotion_id"] == promotion_id
    assert data["semestre"] == 2
