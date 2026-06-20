import pytest
from httpx import AsyncClient

from app.schemas import PromotionCreate
from .conftest import build_auth_headers


pytestmark = pytest.mark.asyncio


RISK_FIELDS = {
    "score_risque",
    "statut",
    "moyenne",
    "moyenne_reference",
    "semestre",
    "absence_count",
    "evaluation_count",
    "score_notes",
    "score_absences",
}


async def _create_promotion(
    async_client: AsyncClient,
    nom: str = "RISQUE-PROMO",
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
    nom: str = "Risque",
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
    coefficient: float = 1.0,
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


async def _add_student_with_note(
    async_client: AsyncClient,
    promotion_id: str,
    groupe_id: str,
    note: float,
    nom: str,
) -> str:
    etudiant_id = await _create_etudiant(async_client, promotion_id, nom=nom, prenom="Test")
    await _assign_etudiant_to_groupe(async_client, etudiant_id, groupe_id)
    examen_id = await _create_examen(async_client, groupe_id, f"{nom} DS")
    await _create_note(async_client, etudiant_id, examen_id, note)
    return etudiant_id


def _assert_risque_fields(data: dict[str, object]) -> None:
    assert RISK_FIELDS <= set(data)


def _risques_by_etudiant(data: list[dict[str, object]]) -> dict[str, dict[str, object]]:
    return {str(item["etudiant_id"]): item for item in data}


async def test_etudiant_risque_good_grades_no_absences_ok(async_client: AsyncClient) -> None:
    promotion_id, groupe_id, etudiant_id = await _seed_student_in_semestre(
        async_client, semestre=1, promotion_nom="RISQUE-GOOD"
    )
    examen_id = await _create_examen(async_client, groupe_id, "Good DS")
    await _create_note(async_client, etudiant_id, examen_id, 16.0)

    resp = await async_client.get(f"/api/v1/etudiants/{etudiant_id}/risque", params={"semestre": 1})

    assert resp.status_code == 200
    data = resp.json()
    _assert_risque_fields(data)
    assert data["statut"] == "OK"
    assert data["score_risque"] < 40
    assert data["moyenne"] == pytest.approx(16.0)
    assert data["absence_count"] == 0
    assert data["evaluation_count"] == 1
    assert data["score_absences"] == 0


async def test_etudiant_risque_poor_grades_no_absences_risque(async_client: AsyncClient) -> None:
    promotion_id, groupe_id, etudiant_id = await _seed_student_in_semestre(
        async_client, semestre=1, promotion_nom="RISQUE-POOR"
    )
    examen_id = await _create_examen(async_client, groupe_id, "Poor DS")
    await _create_note(async_client, etudiant_id, examen_id, 8.0)
    await _add_student_with_note(async_client, promotion_id, groupe_id, 16.0, "Reference")

    resp = await async_client.get(f"/api/v1/etudiants/{etudiant_id}/risque", params={"semestre": 1})

    assert resp.status_code == 200
    data = resp.json()
    _assert_risque_fields(data)
    assert data["statut"] == "Risque"
    assert data["score_risque"] >= 70
    assert data["moyenne"] == pytest.approx(8.0)
    assert data["moyenne_reference"] == pytest.approx(12.0)
    assert data["score_notes"] == 100
    assert data["absence_count"] == 0


async def test_etudiant_risque_many_absences_floor_suivre(async_client: AsyncClient) -> None:
    _, groupe_id, etudiant_id = await _seed_student_in_semestre(
        async_client, semestre=1, promotion_nom="RISQUE-ABS"
    )
    present_examen_id = await _create_examen(async_client, groupe_id, "Present")
    await _create_note(async_client, etudiant_id, present_examen_id, 14.0)
    for index in range(3):
        absent_examen_id = await _create_examen(async_client, groupe_id, f"Absent {index}")
        await _create_note(async_client, etudiant_id, absent_examen_id, None, absent=True)

    resp = await async_client.get(f"/api/v1/etudiants/{etudiant_id}/risque", params={"semestre": 1})

    assert resp.status_code == 200
    data = resp.json()
    _assert_risque_fields(data)
    assert data["absence_count"] == 3
    assert data["evaluation_count"] == 4
    assert data["score_absences"] >= 40
    assert data["score_risque"] >= data["score_absences"]
    assert data["statut"] in {"Suivre", "Risque"}


async def test_etudiant_risque_no_notes_non_evalue(async_client: AsyncClient) -> None:
    _, _, etudiant_id = await _seed_student_in_semestre(
        async_client, semestre=1, promotion_nom="RISQUE-NONE"
    )

    resp = await async_client.get(f"/api/v1/etudiants/{etudiant_id}/risque", params={"semestre": 1})

    assert resp.status_code == 200
    data = resp.json()
    _assert_risque_fields(data)
    assert data["score_risque"] is None
    assert data["statut"] == "Non évalué"
    assert data["moyenne"] is None
    assert data["evaluation_count"] == 0
    assert data["score_notes"] is None
    assert data["score_absences"] == 0


async def test_promotion_etudiants_risques_returns_list(async_client: AsyncClient) -> None:
    promotion_id = await _create_promotion(async_client, nom="RISQUE-PROMO-LIST")
    groupe_id = await _create_groupe(async_client, promotion_id, "RISQUE-PROMO-LIST-G1", 1)
    first_etudiant_id = await _add_student_with_note(
        async_client, promotion_id, groupe_id, 15.0, "PromoAlice"
    )
    second_etudiant_id = await _add_student_with_note(
        async_client, promotion_id, groupe_id, 9.0, "PromoBob"
    )

    resp = await async_client.get(
        f"/api/v1/promotions/{promotion_id}/etudiants/risques",
        params={"semestre": 1},
        headers=build_auth_headers(roles=["enseignant"], email="teacher@example.com"),
    )

    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 2
    by_etudiant = _risques_by_etudiant(data)
    assert set(by_etudiant) == {first_etudiant_id, second_etudiant_id}
    for risque in by_etudiant.values():
        _assert_risque_fields(risque)
        assert risque["semestre"] == 1
        assert risque["reference_scope"] == "promotion"


async def test_groupe_etudiants_risques_returns_list(async_client: AsyncClient) -> None:
    promotion_id = await _create_promotion(async_client, nom="RISQUE-GROUPE-LIST")
    groupe_id = await _create_groupe(async_client, promotion_id, "RISQUE-GROUPE-LIST-G1", 1)
    first_etudiant_id = await _add_student_with_note(
        async_client, promotion_id, groupe_id, 12.0, "GroupeAlice"
    )
    second_etudiant_id = await _add_student_with_note(
        async_client, promotion_id, groupe_id, 18.0, "GroupeBob"
    )

    resp = await async_client.get(
        f"/api/v1/groupes/{groupe_id}/etudiants/risques",
        params={"semestre": 1},
        headers=build_auth_headers(),
    )

    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 2
    by_etudiant = _risques_by_etudiant(data)
    assert set(by_etudiant) == {first_etudiant_id, second_etudiant_id}
    for risque in by_etudiant.values():
        _assert_risque_fields(risque)
        assert risque["semestre"] == 1
        assert risque["reference_scope"] == "groupe"


async def test_risques_semestre_query_parameter_filters_s1_vs_s2(
    async_client: AsyncClient,
) -> None:
    promotion_id = await _create_promotion(async_client, nom="RISQUE-FILTER")
    s1_groupe_id = await _create_groupe(async_client, promotion_id, "RISQUE-FILTER-S1", 1)
    s2_groupe_id = await _create_groupe(async_client, promotion_id, "RISQUE-FILTER-S2", 2)
    s1_etudiant_id = await _add_student_with_note(
        async_client, promotion_id, s1_groupe_id, 11.0, "FilterAlice"
    )
    s2_etudiant_id = await _add_student_with_note(
        async_client, promotion_id, s2_groupe_id, 19.0, "FilterBob"
    )

    s1_resp = await async_client.get(
        f"/api/v1/promotions/{promotion_id}/etudiants/risques",
        params={"semestre": 1},
        headers=build_auth_headers(roles=["enseignant"], email="teacher@example.com"),
    )
    s2_resp = await async_client.get(
        f"/api/v1/promotions/{promotion_id}/etudiants/risques",
        params={"semestre": 2},
        headers=build_auth_headers(roles=["enseignant"], email="teacher@example.com"),
    )
    groupe_s1_as_s2_resp = await async_client.get(
        f"/api/v1/groupes/{s1_groupe_id}/etudiants/risques",
        params={"semestre": 2},
        headers=build_auth_headers(),
    )

    assert s1_resp.status_code == 200
    s1_data = s1_resp.json()
    assert len(s1_data) == 1
    assert s1_data[0]["etudiant_id"] == s1_etudiant_id
    assert s1_data[0]["semestre"] == 1

    assert s2_resp.status_code == 200
    s2_data = s2_resp.json()
    assert len(s2_data) == 1
    assert s2_data[0]["etudiant_id"] == s2_etudiant_id
    assert s2_data[0]["semestre"] == 2

    assert groupe_s1_as_s2_resp.status_code == 200
    assert groupe_s1_as_s2_resp.json() == []


async def test_etudiant_risque_uses_semestre_specific_notes(async_client: AsyncClient) -> None:
    promotion_id = await _create_promotion(async_client, nom="RISQUE-STUDENT-FILTER")
    s1_groupe_id = await _create_groupe(async_client, promotion_id, "RISQUE-STUDENT-FILTER-S1", 1)
    s2_groupe_id = await _create_groupe(async_client, promotion_id, "RISQUE-STUDENT-FILTER-S2", 2)
    etudiant_id = await _create_etudiant(async_client, promotion_id, nom="Filter", prenom="Solo")
    await _assign_etudiant_to_groupe(async_client, etudiant_id, s1_groupe_id)
    await _assign_etudiant_to_groupe(async_client, etudiant_id, s2_groupe_id)
    s1_examen_id = await _create_examen(async_client, s1_groupe_id, "Student S1 DS")
    s2_examen_id = await _create_examen(async_client, s2_groupe_id, "Student S2 DS")
    await _create_note(async_client, etudiant_id, s1_examen_id, 9.0)
    await _create_note(async_client, etudiant_id, s2_examen_id, 17.0)

    s1_resp = await async_client.get(
        f"/api/v1/etudiants/{etudiant_id}/risque", params={"semestre": 1}
    )
    s2_resp = await async_client.get(
        f"/api/v1/etudiants/{etudiant_id}/risque", params={"semestre": 2}
    )

    assert s1_resp.status_code == 200
    assert s2_resp.status_code == 200
    s1_data = s1_resp.json()
    s2_data = s2_resp.json()
    assert s1_data["moyenne"] == pytest.approx(9.0)
    assert s1_data["semestre"] == 1
    assert s2_data["moyenne"] == pytest.approx(17.0)
    assert s2_data["semestre"] == 2
    assert s1_data["score_risque"] > s2_data["score_risque"]
