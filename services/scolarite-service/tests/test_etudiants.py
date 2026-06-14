from uuid import uuid4

import pytest
from httpx import AsyncClient

from app.schemas import PromotionCreate


pytestmark = pytest.mark.asyncio


async def _create_promotion(
    async_client: AsyncClient, nom: str = "ING-E", annee: str = "2025-2026"
) -> str:
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


async def _create_etudiant(
    async_client: AsyncClient,
    promotion_id: str,
    nom: str = "Dupont",
    prenom: str = "Élodie",
) -> dict[str, str]:
    resp = await async_client.post(
        "/api/v1/etudiants/",
        json={
            "nom": nom,
            "prenom": prenom,
            "promotion_id": promotion_id,
        },
    )
    assert resp.status_code == 201
    return resp.json()


async def test_create_etudiant_returns_generated_ids(
    async_client: AsyncClient,
) -> None:
    promotion_id = await _create_promotion(async_client)

    resp = await async_client.post(
        "/api/v1/etudiants/",
        json={"nom": "Dupont", "prenom": "Alice", "promotion_id": promotion_id},
    )

    assert resp.status_code == 201
    data = resp.json()
    assert data["id"]
    assert data["utilisateur_id"]
    assert data["id"] != data["utilisateur_id"]
    assert data["nom"] == "dupont"
    assert data["prenom"] == "alice"
    assert data["promotion_id"] == promotion_id


async def test_create_etudiant_rejects_client_supplied_utilisateur_id(
    async_client: AsyncClient,
) -> None:
    promotion_id = await _create_promotion(async_client, nom="ING-E2")

    resp = await async_client.post(
        "/api/v1/etudiants/",
        json={
            "nom": "Dupont",
            "prenom": "Jean",
            "utilisateur_id": str(uuid4()),
            "promotion_id": promotion_id,
        },
    )

    assert resp.status_code == 422


async def test_create_etudiant_with_unknown_promotion_returns_404(
    async_client: AsyncClient,
) -> None:
    resp = await async_client.post(
        "/api/v1/etudiants/",
        json={"nom": "Martin", "prenom": "Claire", "promotion_id": str(uuid4())},
    )

    assert resp.status_code == 404


async def test_list_etudiants_filters_by_normalized_name(async_client: AsyncClient) -> None:
    promotion_id = await _create_promotion(async_client, nom="ING-E6")
    await _create_etudiant(async_client, promotion_id, nom="Dupont", prenom="Élodie")
    await _create_etudiant(async_client, promotion_id, nom="Martin", prenom="Claire")

    resp = await async_client.get(
        "/api/v1/etudiants/",
        params={"promotion_id": promotion_id, "nom": "dupont", "prenom": "elodie"},
    )

    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    assert data[0]["nom"] == "dupont"
    assert data[0]["prenom"] == "elodie"


async def test_search_etudiants_returns_count(async_client: AsyncClient) -> None:
    promotion_id = await _create_promotion(async_client, nom="ING-E7")
    await _create_etudiant(async_client, promotion_id, nom="Dupont", prenom="Élodie")

    resp = await async_client.get(
        "/api/v1/etudiants/search",
        params={"promotion_id": promotion_id, "nom": "DUPONT", "prenom": "elodie"},
    )

    assert resp.status_code == 200
    assert resp.json()["count"] == 1
    assert resp.json()["items"][0]["prenom"] == "elodie"


async def test_resolve_etudiant_returns_single_match(async_client: AsyncClient) -> None:
    promotion_id = await _create_promotion(async_client, nom="ING-E8")
    created = await _create_etudiant(async_client, promotion_id, nom="Jean-Pierre", prenom="Élodie")

    resp = await async_client.get(
        "/api/v1/etudiants/resolve",
        params={"promotion_id": promotion_id, "nom": "jean pierre", "prenom": "elodie"},
    )

    assert resp.status_code == 200
    assert resp.json()["id"] == created["id"]
    assert created["nom"] == "jean pierre"
    assert created["prenom"] == "elodie"


async def test_resolve_etudiant_without_match_returns_404(async_client: AsyncClient) -> None:
    promotion_id = await _create_promotion(async_client, nom="ING-E9")

    resp = await async_client.get(
        "/api/v1/etudiants/resolve",
        params={"promotion_id": promotion_id, "nom": "Dupont", "prenom": "Alice"},
    )

    assert resp.status_code == 404


async def test_resolve_etudiant_with_homonymes_returns_409(async_client: AsyncClient) -> None:
    promotion_id = await _create_promotion(async_client, nom="ING-E10")
    first = await _create_etudiant(async_client, promotion_id, nom="Dupont", prenom="Alice")
    second = await _create_etudiant(async_client, promotion_id, nom="DUPONT", prenom="Alice")

    resp = await async_client.get(
        "/api/v1/etudiants/resolve",
        params={"promotion_id": promotion_id, "nom": "dupont", "prenom": "alice"},
    )

    assert first["id"] != second["id"]
    assert resp.status_code == 409
    assert resp.json()["detail"]["matches_count"] == 2


async def test_get_update_delete_etudiant_flow(async_client: AsyncClient) -> None:
    promotion_id_1 = await _create_promotion(async_client, nom="ING-E11")
    promotion_id_2 = await _create_promotion(async_client, nom="ING-E12")
    created = await _create_etudiant(async_client, promotion_id_1, nom="Durand", prenom="Alice")
    etudiant_id = created["id"]

    get_resp = await async_client.get(f"/api/v1/etudiants/{etudiant_id}")
    assert get_resp.status_code == 200
    assert get_resp.json()["id"] == etudiant_id

    patch_resp = await async_client.patch(
        f"/api/v1/etudiants/{etudiant_id}",
        json={"nom": "Durant", "prenom": "Alicia", "promotion_id": promotion_id_2},
    )
    assert patch_resp.status_code == 200
    assert patch_resp.json()["nom"] == "durant"
    assert patch_resp.json()["prenom"] == "alicia"
    assert patch_resp.json()["promotion_id"] == promotion_id_2

    delete_resp = await async_client.delete(f"/api/v1/etudiants/{etudiant_id}")
    assert delete_resp.status_code == 204


async def test_assign_etudiant_to_groupe(async_client: AsyncClient) -> None:
    promotion_id = await _create_promotion(async_client, nom="ING-E13")
    groupe_id = await _create_groupe(async_client, promotion_id, nom="GE2")
    etudiant_id = (await _create_etudiant(async_client, promotion_id))["id"]

    resp = await async_client.post(f"/api/v1/etudiants/{etudiant_id}/groupes/{groupe_id}")

    assert resp.status_code == 201
    assert resp.json()["etudiant_id"] == etudiant_id
    assert resp.json()["groupe_id"] == groupe_id


async def test_remove_etudiant_from_groupe(async_client: AsyncClient) -> None:
    promotion_id = await _create_promotion(async_client, nom="ING-E14")
    groupe_id = await _create_groupe(async_client, promotion_id, nom="GE3")
    etudiant_id = (await _create_etudiant(async_client, promotion_id))["id"]
    await async_client.post(f"/api/v1/etudiants/{etudiant_id}/groupes/{groupe_id}")

    resp = await async_client.delete(f"/api/v1/etudiants/{etudiant_id}/groupes/{groupe_id}")

    assert resp.status_code == 204


async def test_remove_etudiant_from_promotion_clears_groupes(async_client: AsyncClient) -> None:
    promotion_id = await _create_promotion(async_client, nom="ING-E14B")
    groupe_id = await _create_groupe(async_client, promotion_id, nom="GE3B")
    etudiant_id = (await _create_etudiant(async_client, promotion_id))["id"]
    assign_resp = await async_client.post(f"/api/v1/etudiants/{etudiant_id}/groupes/{groupe_id}")
    assert assign_resp.status_code == 201

    resp = await async_client.delete(f"/api/v1/etudiants/{etudiant_id}/promotion")

    assert resp.status_code == 204
    get_resp = await async_client.get(f"/api/v1/etudiants/{etudiant_id}")
    assert get_resp.status_code == 200
    assert get_resp.json()["promotion_id"] is None
    groupes_resp = await async_client.get(f"/api/v1/etudiants/{etudiant_id}/groupes")
    assert groupes_resp.status_code == 200
    assert groupes_resp.json() == []


async def test_duplicate_groupe_assignment_returns_expected_status(
    async_client: AsyncClient,
) -> None:
    promotion_id = await _create_promotion(async_client, nom="ING-E15")
    groupe_id = await _create_groupe(async_client, promotion_id, nom="GE4")
    etudiant_id = (await _create_etudiant(async_client, promotion_id))["id"]
    first = await async_client.post(f"/api/v1/etudiants/{etudiant_id}/groupes/{groupe_id}")
    assert first.status_code == 201

    resp = await async_client.post(f"/api/v1/etudiants/{etudiant_id}/groupes/{groupe_id}")

    assert resp.status_code in {200, 400, 409}


async def test_patch_etudiant_rejects_promotion_change_when_groupes_exist(
    async_client: AsyncClient,
) -> None:
    first_promotion_id = await _create_promotion(async_client, nom="ING-E16")
    second_promotion_id = await _create_promotion(async_client, nom="ING-E17")
    groupe_id = await _create_groupe(async_client, first_promotion_id, nom="GE5")
    etudiant_id = (await _create_etudiant(async_client, first_promotion_id))["id"]
    assign_resp = await async_client.post(f"/api/v1/etudiants/{etudiant_id}/groupes/{groupe_id}")
    assert assign_resp.status_code == 201

    resp = await async_client.patch(
        f"/api/v1/etudiants/{etudiant_id}",
        json={"promotion_id": second_promotion_id},
    )

    assert resp.status_code == 409
    assert resp.json()["detail"] == (
        "Cannot change promotion while student is assigned to groupes. Remove groupes first."
    )


async def test_assign_etudiant_to_groupe_from_another_promotion_returns_409(
    async_client: AsyncClient,
) -> None:
    etudiant_promotion_id = await _create_promotion(async_client, nom="ING-E18")
    groupe_promotion_id = await _create_promotion(async_client, nom="ING-E19")
    etudiant_id = (await _create_etudiant(async_client, etudiant_promotion_id))["id"]
    groupe_id = await _create_groupe(async_client, groupe_promotion_id, nom="GE6")

    resp = await async_client.post(f"/api/v1/etudiants/{etudiant_id}/groupes/{groupe_id}")

    assert resp.status_code == 409
    assert resp.json()["detail"] == "Etudiant can only be assigned to groupes from their promotion"
