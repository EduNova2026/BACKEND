from uuid import uuid4

import pytest
from httpx import AsyncClient

from app.schemas import PromotionCreate
from .conftest import build_auth_headers


pytestmark = pytest.mark.asyncio


async def _create_promotion(
    async_client: AsyncClient,
    nom: str = "MOY-PROMO",
    annee: str = "2025-2026",
) -> str:
    resp = await async_client.post(
        "/api/v1/promotions/",
        json=PromotionCreate(nom=nom, annee_scolaire=annee).model_dump(),
    )
    assert resp.status_code == 201
    return resp.json()["id"]


async def _create_groupe(
    async_client: AsyncClient,
    promotion_id: str,
    nom: str,
    semestre: int,
    coefficient: float = 1.0,
) -> str:
    resp = await async_client.post(
        "/api/v1/groupes/",
        json={
            "nom": nom,
            "promotion_id": promotion_id,
            "semestre": semestre,
            "coefficient": coefficient,
        },
    )
    assert resp.status_code == 201
    return resp.json()["id"]


async def _create_etudiant(
    async_client: AsyncClient,
    promotion_id: str,
    nom: str = "Dupont",
    prenom: str = "Alice",
) -> str:
    resp = await async_client.post(
        "/api/v1/etudiants/",
        json={"nom": nom, "prenom": prenom, "promotion_id": promotion_id},
    )
    assert resp.status_code == 201
    return resp.json()["id"]


async def _assign_etudiant_to_groupe(
    async_client: AsyncClient,
    etudiant_id: str,
    groupe_id: str,
) -> None:
    resp = await async_client.post(f"/api/v1/etudiants/{etudiant_id}/groupes/{groupe_id}")
    assert resp.status_code == 201


async def _create_examen(
    async_client: AsyncClient,
    enseignement_id: str,
    nom: str,
    coefficient: float,
    note_max: float = 20.0,
) -> str:
    resp = await async_client.post(
        "/api/v1/examens/",
        json={
            "enseignement_id": enseignement_id,
            "nom": nom,
            "type": "examen",
            "coefficient": coefficient,
            "note_max": note_max,
        },
    )
    assert resp.status_code == 201
    return resp.json()["id"]


async def _create_note(
    async_client: AsyncClient,
    etudiant_id: str,
    examen_id: str,
    valeur: float | None,
    absent: bool = False,
) -> str:
    resp = await async_client.post(
        "/api/v1/notes/",
        json={
            "etudiant_id": etudiant_id,
            "examen_id": examen_id,
            "valeur": valeur,
            "absent": absent,
        },
    )
    assert resp.status_code == 201
    return resp.json()["id"]


async def _seed_student_in_semestre(
    async_client: AsyncClient,
    semestre: int,
    promotion_nom: str,
) -> tuple[str, str, str]:
    promotion_id = await _create_promotion(async_client, nom=promotion_nom)
    groupe_id = await _create_groupe(
        async_client,
        promotion_id,
        nom=f"{promotion_nom}-G{semestre}",
        semestre=semestre,
    )
    etudiant_id = await _create_etudiant(async_client, promotion_id)
    await _assign_etudiant_to_groupe(async_client, etudiant_id, groupe_id)
    return promotion_id, groupe_id, etudiant_id


def _assert_moyenne_payload(
    data: dict[str, object],
    expected_moyenne: float,
    expected_semestre: int,
    expected_note_count: int,
    expected_coefficient_total: float,
) -> None:
    assert data["moyenne"] == pytest.approx(expected_moyenne)
    assert data["semestre"] == expected_semestre
    assert data["note_count"] == expected_note_count
    assert data["coefficient_total"] == pytest.approx(expected_coefficient_total)


def _moyennes_by_etudiant(data: list[dict[str, object]]) -> dict[str, dict[str, object]]:
    return {str(item["etudiant_id"]): item for item in data}


async def test_etudiant_moyenne_semestre_1(async_client: AsyncClient) -> None:
    promotion_id, groupe_id, etudiant_id = await _seed_student_in_semestre(
        async_client, semestre=1, promotion_nom="MOY-E-S1"
    )
    second_s1_groupe_id = await _create_groupe(async_client, promotion_id, "MOY-E-S1-B", 1)
    await _assign_etudiant_to_groupe(async_client, etudiant_id, second_s1_groupe_id)
    enseignement_id = str(uuid4())
    examen_1_id = await _create_examen(async_client, enseignement_id, "DS 1", 2.0, 20.0)
    examen_2_id = await _create_examen(async_client, enseignement_id, "DS 2", 1.0, 10.0)
    await _create_note(async_client, etudiant_id, examen_1_id, 15.0)
    await _create_note(async_client, etudiant_id, examen_2_id, 8.0)

    resp = await async_client.get(f"/api/v1/etudiants/{etudiant_id}/moyenne", params={"semestre": 1})

    assert resp.status_code == 200
    expected = (((15.0 / 20.0) * 20.0) * 2.0 + ((8.0 / 10.0) * 20.0) * 1.0) / 3.0
    _assert_moyenne_payload(resp.json(), expected, 1, 2, 3.0)
    assert groupe_id != second_s1_groupe_id


async def test_etudiant_moyenne_semestre_2(async_client: AsyncClient) -> None:
    _, _, etudiant_id = await _seed_student_in_semestre(
        async_client, semestre=2, promotion_nom="MOY-E-S2"
    )
    enseignement_id = str(uuid4())
    examen_1_id = await _create_examen(async_client, enseignement_id, "Rattrapage", 3.0, 30.0)
    examen_2_id = await _create_examen(async_client, enseignement_id, "Projet", 1.0, 20.0)
    await _create_note(async_client, etudiant_id, examen_1_id, 24.0)
    await _create_note(async_client, etudiant_id, examen_2_id, 10.0)

    s1_resp = await async_client.get(
        f"/api/v1/etudiants/{etudiant_id}/moyenne", params={"semestre": 1}
    )
    s2_resp = await async_client.get(
        f"/api/v1/etudiants/{etudiant_id}/moyenne", params={"semestre": 2}
    )

    assert s1_resp.status_code == 200
    assert s1_resp.json()["moyenne"] is None
    assert s2_resp.status_code == 200
    expected = (((24.0 / 30.0) * 20.0) * 3.0 + ((10.0 / 20.0) * 20.0) * 1.0) / 4.0
    _assert_moyenne_payload(s2_resp.json(), expected, 2, 2, 4.0)


async def test_etudiant_moyenne_absent_ignored(async_client: AsyncClient) -> None:
    _, _, etudiant_id = await _seed_student_in_semestre(
        async_client, semestre=1, promotion_nom="MOY-E-ABSENT"
    )
    enseignement_id = str(uuid4())
    valid_examen_id = await _create_examen(async_client, enseignement_id, "DS", 2.0)
    absent_examen_id = await _create_examen(async_client, enseignement_id, "Absent", 5.0)
    await _create_note(async_client, etudiant_id, valid_examen_id, 14.0)
    await _create_note(async_client, etudiant_id, absent_examen_id, 20.0, absent=True)

    resp = await async_client.get(f"/api/v1/etudiants/{etudiant_id}/moyenne", params={"semestre": 1})

    assert resp.status_code == 200
    _assert_moyenne_payload(resp.json(), 14.0, 1, 1, 2.0)


async def test_etudiant_moyenne_null_ignored(async_client: AsyncClient) -> None:
    _, _, etudiant_id = await _seed_student_in_semestre(
        async_client, semestre=1, promotion_nom="MOY-E-NULL"
    )
    enseignement_id = str(uuid4())
    valid_examen_id = await _create_examen(async_client, enseignement_id, "DS", 1.0)
    null_examen_id = await _create_examen(async_client, enseignement_id, "Non saisi", 4.0)
    await _create_note(async_client, etudiant_id, valid_examen_id, 16.0)
    await _create_note(async_client, etudiant_id, null_examen_id, None, absent=True)

    resp = await async_client.get(f"/api/v1/etudiants/{etudiant_id}/moyenne", params={"semestre": 1})

    assert resp.status_code == 200
    _assert_moyenne_payload(resp.json(), 16.0, 1, 1, 1.0)


async def test_etudiant_moyenne_404(async_client: AsyncClient) -> None:
    _, _, etudiant_id = await _seed_student_in_semestre(
        async_client, semestre=1, promotion_nom="MOY-E-404"
    )

    empty_resp = await async_client.get(
        f"/api/v1/etudiants/{etudiant_id}/moyenne", params={"semestre": 1}
    )
    unknown_resp = await async_client.get(
        f"/api/v1/etudiants/{uuid4()}/moyenne", params={"semestre": 1}
    )

    assert empty_resp.status_code == 200
    assert empty_resp.json()["moyenne"] is None
    assert unknown_resp.status_code == 404


async def test_promotion_moyenne_semestre_1(async_client: AsyncClient) -> None:
    promotion_id = await _create_promotion(async_client, nom="MOY-P-S1")
    s1_groupe_id = await _create_groupe(async_client, promotion_id, "MOY-P-S1-A", 1)
    s2_groupe_id = await _create_groupe(async_client, promotion_id, "MOY-P-S2-A", 2)
    first_etudiant_id = await _create_etudiant(async_client, promotion_id, nom="Martin", prenom="Claire")
    second_etudiant_id = await _create_etudiant(async_client, promotion_id, nom="Durand", prenom="Paul")
    s2_etudiant_id = await _create_etudiant(async_client, promotion_id, nom="Petit", prenom="Lea")
    await _assign_etudiant_to_groupe(async_client, first_etudiant_id, s1_groupe_id)
    await _assign_etudiant_to_groupe(async_client, second_etudiant_id, s1_groupe_id)
    await _assign_etudiant_to_groupe(async_client, s2_etudiant_id, s2_groupe_id)
    enseignement_id = str(uuid4())
    examen_1_id = await _create_examen(async_client, enseignement_id, "DS A", 2.0)
    examen_2_id = await _create_examen(async_client, enseignement_id, "DS B", 1.0)
    s2_examen_id = await _create_examen(async_client, enseignement_id, "DS S2", 5.0)
    await _create_note(async_client, first_etudiant_id, examen_1_id, 12.0)
    await _create_note(async_client, first_etudiant_id, examen_2_id, 18.0)
    await _create_note(async_client, second_etudiant_id, examen_1_id, 10.0)
    await _create_note(async_client, s2_etudiant_id, s2_examen_id, 20.0)

    resp = await async_client.get(
        f"/api/v1/promotions/{promotion_id}/moyenne",
        params={"semestre": 1},
        headers=build_auth_headers(roles=["enseignant"], email="teacher@example.com"),
    )

    assert resp.status_code == 200
    first_average = ((12.0 * 2.0) + (18.0 * 1.0)) / 3.0
    second_average = 10.0
    expected = (first_average + second_average) / 2.0
    _assert_moyenne_payload(resp.json(), expected, 1, 3, 5.0)


async def test_promotion_moyenne_404(async_client: AsyncClient) -> None:
    empty_promotion_id = await _create_promotion(async_client, nom="MOY-P-404")

    empty_resp = await async_client.get(
        f"/api/v1/promotions/{empty_promotion_id}/moyenne", params={"semestre": 1}
    )
    unknown_resp = await async_client.get(
        f"/api/v1/promotions/{uuid4()}/moyenne", params={"semestre": 1}
    )

    assert empty_resp.status_code == 200
    assert empty_resp.json()["moyenne"] is None
    assert unknown_resp.status_code == 404


async def test_promotion_etudiants_moyennes_batch(async_client: AsyncClient) -> None:
    promotion_id = await _create_promotion(async_client, nom="MOY-BATCH-P")
    groupe_id = await _create_groupe(async_client, promotion_id, "MOY-BATCH-P-G1", 1)
    first_etudiant_id = await _create_etudiant(async_client, promotion_id, nom="Batch", prenom="Alice")
    second_etudiant_id = await _create_etudiant(async_client, promotion_id, nom="Batch", prenom="Bob")
    await _assign_etudiant_to_groupe(async_client, first_etudiant_id, groupe_id)
    await _assign_etudiant_to_groupe(async_client, second_etudiant_id, groupe_id)
    examen_id = await _create_examen(async_client, groupe_id, "Batch DS", 2.0)
    await _create_note(async_client, first_etudiant_id, examen_id, 15.0)
    await _create_note(async_client, second_etudiant_id, examen_id, 10.0)

    resp = await async_client.get(
        f"/api/v1/promotions/{promotion_id}/etudiants/moyennes",
        params={"semestre": 1},
        headers=build_auth_headers(roles=["enseignant"], email="teacher@example.com"),
    )

    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 2
    by_etudiant = _moyennes_by_etudiant(data)
    assert set(by_etudiant) == {first_etudiant_id, second_etudiant_id}
    _assert_moyenne_payload(by_etudiant[first_etudiant_id], 15.0, 1, 1, 2.0)
    _assert_moyenne_payload(by_etudiant[second_etudiant_id], 10.0, 1, 1, 2.0)


async def test_groupe_etudiants_moyennes_batch(async_client: AsyncClient) -> None:
    promotion_id = await _create_promotion(async_client, nom="MOY-BATCH-G")
    groupe_id = await _create_groupe(async_client, promotion_id, "MOY-BATCH-G-G1", 1)
    first_etudiant_id = await _create_etudiant(async_client, promotion_id, nom="Groupe", prenom="Alice")
    second_etudiant_id = await _create_etudiant(async_client, promotion_id, nom="Groupe", prenom="Bob")
    await _assign_etudiant_to_groupe(async_client, first_etudiant_id, groupe_id)
    await _assign_etudiant_to_groupe(async_client, second_etudiant_id, groupe_id)
    examen_id = await _create_examen(async_client, groupe_id, "Groupe DS", 1.0)
    await _create_note(async_client, first_etudiant_id, examen_id, 12.0)
    await _create_note(async_client, second_etudiant_id, examen_id, 18.0)

    resp = await async_client.get(
        f"/api/v1/groupes/{groupe_id}/etudiants/moyennes",
        params={"semestre": 1},
        headers=build_auth_headers(),
    )

    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 2
    by_etudiant = _moyennes_by_etudiant(data)
    assert set(by_etudiant) == {first_etudiant_id, second_etudiant_id}
    _assert_moyenne_payload(by_etudiant[first_etudiant_id], 12.0, 1, 1, 1.0)
    _assert_moyenne_payload(by_etudiant[second_etudiant_id], 18.0, 1, 1, 1.0)


async def test_promotion_moyenne_uses_groupe_coefficients(async_client: AsyncClient) -> None:
    promotion_id = await _create_promotion(async_client, nom="MOY-BATCH-COEFF")
    first_groupe_id = await _create_groupe(
        async_client, promotion_id, "MOY-BATCH-COEFF-G1", 1, coefficient=1.0
    )
    second_groupe_id = await _create_groupe(
        async_client, promotion_id, "MOY-BATCH-COEFF-G2", 1, coefficient=2.0
    )
    etudiant_id = await _create_etudiant(async_client, promotion_id, nom="Coeff", prenom="Alice")
    await _assign_etudiant_to_groupe(async_client, etudiant_id, first_groupe_id)
    await _assign_etudiant_to_groupe(async_client, etudiant_id, second_groupe_id)
    first_examen_id = await _create_examen(async_client, first_groupe_id, "Coeff DS 1", 1.0)
    second_examen_id = await _create_examen(async_client, second_groupe_id, "Coeff DS 2", 1.0)
    await _create_note(async_client, etudiant_id, first_examen_id, 10.0)
    await _create_note(async_client, etudiant_id, second_examen_id, 20.0)

    resp = await async_client.get(
        f"/api/v1/promotions/{promotion_id}/moyenne",
        params={"semestre": 1},
        headers=build_auth_headers(roles=["enseignant"], email="teacher@example.com"),
    )

    assert resp.status_code == 200
    expected = ((10.0 * 1.0) + (20.0 * 2.0)) / 3.0
    _assert_moyenne_payload(resp.json(), expected, 1, 2, 3.0)


async def test_promotion_etudiants_moyennes_includes_students_without_notes(
    async_client: AsyncClient,
) -> None:
    promotion_id = await _create_promotion(async_client, nom="MOY-BATCH-NONE")
    groupe_id = await _create_groupe(async_client, promotion_id, "MOY-BATCH-NONE-G1", 1)
    graded_etudiant_id = await _create_etudiant(async_client, promotion_id, nom="Notes", prenom="Alice")
    empty_etudiant_id = await _create_etudiant(async_client, promotion_id, nom="Notes", prenom="Bob")
    await _assign_etudiant_to_groupe(async_client, graded_etudiant_id, groupe_id)
    await _assign_etudiant_to_groupe(async_client, empty_etudiant_id, groupe_id)
    examen_id = await _create_examen(async_client, groupe_id, "Only one note", 1.0)
    await _create_note(async_client, graded_etudiant_id, examen_id, 14.0)

    resp = await async_client.get(
        f"/api/v1/promotions/{promotion_id}/etudiants/moyennes",
        params={"semestre": 1},
        headers=build_auth_headers(roles=["enseignant"], email="teacher@example.com"),
    )

    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 2
    by_etudiant = _moyennes_by_etudiant(data)
    _assert_moyenne_payload(by_etudiant[graded_etudiant_id], 14.0, 1, 1, 1.0)
    assert by_etudiant[empty_etudiant_id]["moyenne"] is None
    assert by_etudiant[empty_etudiant_id]["semestre"] == 1
    assert by_etudiant[empty_etudiant_id]["note_count"] == 0
    assert by_etudiant[empty_etudiant_id]["coefficient_total"] == 0.0


async def test_promotion_etudiants_moyennes_semestre_filter_excludes_s2_students(
    async_client: AsyncClient,
) -> None:
    promotion_id = await _create_promotion(async_client, nom="MOY-BATCH-FILTER")
    s1_groupe_id = await _create_groupe(async_client, promotion_id, "MOY-BATCH-FILTER-S1", 1)
    s2_groupe_id = await _create_groupe(async_client, promotion_id, "MOY-BATCH-FILTER-S2", 2)
    s1_etudiant_id = await _create_etudiant(async_client, promotion_id, nom="Filter", prenom="Alice")
    s2_etudiant_id = await _create_etudiant(async_client, promotion_id, nom="Filter", prenom="Bob")
    await _assign_etudiant_to_groupe(async_client, s1_etudiant_id, s1_groupe_id)
    await _assign_etudiant_to_groupe(async_client, s2_etudiant_id, s2_groupe_id)
    s1_examen_id = await _create_examen(async_client, s1_groupe_id, "S1 DS", 1.0)
    s2_examen_id = await _create_examen(async_client, s2_groupe_id, "S2 DS", 1.0)
    await _create_note(async_client, s1_etudiant_id, s1_examen_id, 13.0)
    await _create_note(async_client, s2_etudiant_id, s2_examen_id, 19.0)

    resp = await async_client.get(
        f"/api/v1/promotions/{promotion_id}/etudiants/moyennes",
        params={"semestre": 1},
        headers=build_auth_headers(roles=["enseignant"], email="teacher@example.com"),
    )

    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    by_etudiant = _moyennes_by_etudiant(data)
    assert set(by_etudiant) == {s1_etudiant_id}
    _assert_moyenne_payload(by_etudiant[s1_etudiant_id], 13.0, 1, 1, 1.0)


async def test_enseignement_moyenne_semestre_1(async_client: AsyncClient) -> None:
    promotion_id = await _create_promotion(async_client, nom="MOY-ENS-S1")
    s1_groupe_id = await _create_groupe(async_client, promotion_id, "MOY-ENS-S1-A", 1)
    s2_groupe_id = await _create_groupe(async_client, promotion_id, "MOY-ENS-S2-A", 2)
    first_etudiant_id = await _create_etudiant(async_client, promotion_id, nom="Bernard", prenom="Nina")
    second_etudiant_id = await _create_etudiant(async_client, promotion_id, nom="Leroy", prenom="Hugo")
    s2_etudiant_id = await _create_etudiant(async_client, promotion_id, nom="Moreau", prenom="Iris")
    await _assign_etudiant_to_groupe(async_client, first_etudiant_id, s1_groupe_id)
    await _assign_etudiant_to_groupe(async_client, second_etudiant_id, s1_groupe_id)
    await _assign_etudiant_to_groupe(async_client, s2_etudiant_id, s2_groupe_id)
    enseignement_id = str(uuid4())
    other_enseignement_id = str(uuid4())
    examen_1_id = await _create_examen(async_client, enseignement_id, "Algo DS", 2.0)
    examen_2_id = await _create_examen(async_client, enseignement_id, "Algo TP", 1.0, 10.0)
    other_examen_id = await _create_examen(async_client, other_enseignement_id, "Maths", 10.0)
    s2_examen_id = await _create_examen(async_client, enseignement_id, "Algo S2", 5.0)
    await _create_note(async_client, first_etudiant_id, examen_1_id, 15.0)
    await _create_note(async_client, second_etudiant_id, examen_2_id, 7.0)
    await _create_note(async_client, first_etudiant_id, other_examen_id, 20.0)
    await _create_note(async_client, s2_etudiant_id, s2_examen_id, 20.0)

    resp = await async_client.get(
        f"/api/v1/enseignements/{enseignement_id}/moyenne",
        params={"semestre": 1},
        headers=build_auth_headers(roles=["enseignant"], email="teacher@example.com"),
    )

    assert resp.status_code == 200
    expected = (((15.0 / 20.0) * 20.0) * 2.0 + ((7.0 / 10.0) * 20.0) * 1.0) / 3.0
    _assert_moyenne_payload(resp.json(), expected, 1, 2, 3.0)


async def test_enseignement_moyenne_404(async_client: AsyncClient) -> None:
    unknown_resp = await async_client.get(
        f"/api/v1/enseignements/{uuid4()}/moyenne", params={"semestre": 1}
    )

    assert unknown_resp.status_code == 200
    assert unknown_resp.json()["moyenne"] is None
