from __future__ import annotations

from uuid import uuid4

import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.asyncio


async def _create_promotion(async_client: AsyncClient) -> str:
    response = await async_client.post(
        "/api/v1/promotions/",
        json={"nom": "NOTE-PROMO", "annee_scolaire": "2025-2026"},
    )
    assert response.status_code == 201
    return response.json()["id"]


async def _create_etudiant(async_client: AsyncClient, promotion_id: str) -> str:
    response = await async_client.post(
        "/api/v1/etudiants/",
        json={"nom": "Martin", "prenom": "Claire", "promotion_id": promotion_id},
    )
    assert response.status_code == 201
    return response.json()["id"]


def _note_payload(etudiant_id: str, enseignement_id: str) -> dict[str, object]:
    return {
        "etudiant_id": etudiant_id,
        "examen_id": enseignement_id,
        "valeur": 15.5,
        "absent": False,
    }


async def _create_examen(async_client: AsyncClient, enseignement_id: str, code_aurion: str | None = None) -> str:
    payload = {
        "enseignement_id": enseignement_id,
        "nom": "Contrôle continu 1",
        "type": "examen",
        "coefficient": 1,
        "note_max": 20,
    }
    if code_aurion is not None:
        payload["code_aurion"] = code_aurion
    response = await async_client.post("/api/v1/examens/", json=payload)
    assert response.status_code == 201
    return response.json()["id"]


async def test_create_get_update_delete_note(async_client: AsyncClient) -> None:
    promotion_id = await _create_promotion(async_client)
    etudiant_id = await _create_etudiant(async_client, promotion_id)
    enseignement_id = str(uuid4())
    examen_id = await _create_examen(async_client, enseignement_id)

    create_response = await async_client.post(
        "/api/v1/notes/",
        json=_note_payload(etudiant_id, examen_id),
    )
    assert create_response.status_code == 201
    note = create_response.json()
    assert note["etudiant_id"] == etudiant_id
    assert note["examen_id"] == examen_id
    assert note["examen"]["enseignement_id"] == enseignement_id
    assert note["valeur"] == 15.5

    get_response = await async_client.get(f"/api/v1/notes/{note['id']}")
    assert get_response.status_code == 200
    assert get_response.json()["id"] == note["id"]

    update_response = await async_client.patch(
        f"/api/v1/notes/{note['id']}",
        json={"valeur": 16.0},
    )
    assert update_response.status_code == 200
    assert update_response.json()["valeur"] == 16.0

    delete_response = await async_client.delete(f"/api/v1/notes/{note['id']}")
    assert delete_response.status_code == 204

    missing_response = await async_client.get(f"/api/v1/notes/{note['id']}")
    assert missing_response.status_code == 404


async def test_create_notes_batch_and_filter(async_client: AsyncClient) -> None:
    promotion_id = await _create_promotion(async_client)
    etudiant_id = await _create_etudiant(async_client, promotion_id)
    enseignement_id = str(uuid4())
    examen_id = await _create_examen(async_client, enseignement_id, "AURION-001")

    response = await async_client.post(
        "/api/v1/notes/batch",
        json={
            "examen_id": examen_id,
            "notes": [
                {
                    "etudiant_id": etudiant_id,
                    "valeur": 12.0,
                    "absent": False,
                }
            ],
        },
    )

    assert response.status_code == 201
    assert response.json()[0]["examen_id"] == examen_id

    list_response = await async_client.get(
        "/api/v1/notes/",
        params={"etudiant_id": etudiant_id, "enseignement_id": enseignement_id},
    )
    assert list_response.status_code == 200
    assert len(list_response.json()) == 1
