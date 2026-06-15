from __future__ import annotations

from collections.abc import Callable
from uuid import uuid4

import pytest
from httpx import AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

pytestmark = pytest.mark.asyncio


async def _seed_utilisateur(
    session: AsyncSession,
    utilisateur_id: str,
    email: str,
    actif: bool = True,
) -> None:
    await session.execute(
        text(
            "INSERT INTO utilisateurs (id, email, nom, prenom, actif) "
            "VALUES (:id, :email, :nom, :prenom, :actif)"
        ),
        {
            "id": utilisateur_id.replace("-", ""),
            "email": email,
            "nom": "Durand",
            "prenom": "Alice",
            "actif": actif,
        },
    )
    await session.commit()


async def _seed_role_assignment(
    session: AsyncSession,
    utilisateur_id: str,
    libelle: str,
) -> str:
    role_id = str(uuid4())
    await session.execute(
        text("INSERT INTO roles (id, libelle) VALUES (:id, :libelle)"),
        {"id": role_id.replace("-", ""), "libelle": libelle},
    )
    await session.execute(
        text(
            "INSERT INTO utilisateur_roles (utilisateur_id, role_id) "
            "VALUES (:utilisateur_id, :role_id)"
        ),
        {
            "utilisateur_id": utilisateur_id.replace("-", ""),
            "role_id": role_id.replace("-", ""),
        },
    )
    await session.commit()
    return role_id


async def _create_promotion(async_client: AsyncClient, nom: str) -> str:
    response = await async_client.post(
        "/api/v1/promotions/",
        json={"nom": nom, "annee_scolaire": "2025-2026"},
    )
    assert response.status_code == 201
    return response.json()["id"]


async def _create_groupe(async_client: AsyncClient, promotion_id: str, nom: str) -> str:
    response = await async_client.post(
        "/api/v1/groupes/",
        json={"nom": nom, "promotion_id": promotion_id},
    )
    assert response.status_code == 201
    return response.json()["id"]


async def _create_etudiant(async_client: AsyncClient, promotion_id: str, nom: str) -> str:
    response = await async_client.post(
        "/api/v1/etudiants/",
        json={"nom": nom, "prenom": "Alice", "promotion_id": promotion_id},
    )
    assert response.status_code == 201
    return response.json()["id"]


async def _seed_teacher(
    session: AsyncSession,
    teacher_id: str | None = None,
) -> str:
    teacher_id = teacher_id or str(uuid4())
    await _seed_utilisateur(session, teacher_id, f"teacher-{teacher_id}@example.com")
    await _seed_role_assignment(session, teacher_id, "enseignant")
    return teacher_id


async def test_rp_can_assign_teacher_to_group(
    async_client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    teacher_id = await _seed_teacher(db_session)
    promotion_id = await _create_promotion(async_client, "AUTH-A")
    groupe_id = await _create_groupe(async_client, promotion_id, "AUTH-G1")

    response = await async_client.post(f"/api/v1/groupes/{groupe_id}/enseignants/{teacher_id}")

    assert response.status_code == 201
    assert response.json()["enseignant_id"] == teacher_id
    assert response.json()["groupe_id"] == groupe_id


async def test_admin_pedagogique_can_assign_teacher_to_group(
    async_client: AsyncClient,
    db_session: AsyncSession,
    auth_headers_factory: Callable[..., dict[str, str]],
) -> None:
    admin_id = str(uuid4())
    await _seed_utilisateur(db_session, admin_id, "admin@example.com")
    await _seed_role_assignment(db_session, admin_id, "admin_pedagogique")
    teacher_id = await _seed_teacher(db_session)
    promotion_id = await _create_promotion(async_client, "AUTH-ADMIN-A")
    groupe_id = await _create_groupe(async_client, promotion_id, "AUTH-ADMIN-G1")

    response = await async_client.post(
        f"/api/v1/groupes/{groupe_id}/enseignants/{teacher_id}",
        headers=auth_headers_factory(user_id=admin_id, roles=["admin_pedagogique"]),
    )

    assert response.status_code == 201
    assert response.json()["enseignant_id"] == teacher_id
    assert response.json()["groupe_id"] == groupe_id


async def test_non_rp_cannot_assign_teacher_to_group(
    async_client: AsyncClient,
    db_session: AsyncSession,
    auth_headers_factory: Callable[..., dict[str, str]],
) -> None:
    teacher_id = await _seed_teacher(db_session)
    promotion_id = await _create_promotion(async_client, "AUTH-B")
    groupe_id = await _create_groupe(async_client, promotion_id, "AUTH-G2")

    response = await async_client.post(
        f"/api/v1/groupes/{groupe_id}/enseignants/{teacher_id}",
        headers=auth_headers_factory(user_id=teacher_id, roles=["enseignant"]),
    )

    assert response.status_code == 403


async def test_teacher_can_access_only_assigned_group_and_students(
    async_client: AsyncClient,
    db_session: AsyncSession,
    auth_headers_factory: Callable[..., dict[str, str]],
) -> None:
    teacher_id = await _seed_teacher(db_session)
    promotion_id = await _create_promotion(async_client, "AUTH-C")
    assigned_group_id = await _create_groupe(async_client, promotion_id, "AUTH-G3")
    other_group_id = await _create_groupe(async_client, promotion_id, "AUTH-G4")
    assigned_student_id = await _create_etudiant(async_client, promotion_id, "Durand")
    other_student_id = await _create_etudiant(async_client, promotion_id, "Martin")
    await async_client.post(f"/api/v1/etudiants/{assigned_student_id}/groupes/{assigned_group_id}")
    await async_client.post(f"/api/v1/etudiants/{other_student_id}/groupes/{other_group_id}")
    await async_client.post(f"/api/v1/groupes/{assigned_group_id}/enseignants/{teacher_id}")
    teacher_headers = auth_headers_factory(user_id=teacher_id, roles=["enseignant"])

    assigned_group = await async_client.get(
        f"/api/v1/groupes/{assigned_group_id}",
        headers=teacher_headers,
    )
    other_group = await async_client.get(
        f"/api/v1/groupes/{other_group_id}",
        headers=teacher_headers,
    )
    assigned_students = await async_client.get(
        f"/api/v1/groupes/{assigned_group_id}/etudiants",
        headers=teacher_headers,
    )
    assigned_student = await async_client.get(
        f"/api/v1/etudiants/{assigned_student_id}",
        headers=teacher_headers,
    )
    other_student = await async_client.get(
        f"/api/v1/etudiants/{other_student_id}",
        headers=teacher_headers,
    )
    update_student = await async_client.patch(
        f"/api/v1/etudiants/{assigned_student_id}",
        json={"prenom": "Alicia"},
        headers=teacher_headers,
    )

    assert assigned_group.status_code == 200
    assert other_group.status_code == 403
    assert assigned_students.status_code == 200
    assert assigned_students.json()[0]["id"] == assigned_student_id
    assert assigned_student.status_code == 200
    assert other_student.status_code == 403
    assert update_student.status_code == 200
    assert update_student.json()["prenom"] == "alicia"


async def test_teacher_cannot_assign_student_to_group(
    async_client: AsyncClient,
    db_session: AsyncSession,
    auth_headers_factory: Callable[..., dict[str, str]],
) -> None:
    teacher_id = await _seed_teacher(db_session)
    promotion_id = await _create_promotion(async_client, "AUTH-D")
    groupe_id = await _create_groupe(async_client, promotion_id, "AUTH-G5")
    etudiant_id = await _create_etudiant(async_client, promotion_id, "Bernard")

    response = await async_client.post(
        f"/api/v1/etudiants/{etudiant_id}/groupes/{groupe_id}",
        headers=auth_headers_factory(user_id=teacher_id, roles=["enseignant"]),
    )

    assert response.status_code == 403


async def test_admin_pedagogique_can_assign_promotion_to_responsable(
    async_client: AsyncClient,
    db_session: AsyncSession,
    auth_headers_factory: Callable[..., dict[str, str]],
) -> None:
    admin_id = str(uuid4())
    responsable_id = str(uuid4())
    await _seed_utilisateur(db_session, admin_id, "admin@example.com")
    await _seed_utilisateur(db_session, responsable_id, "responsable@example.com")
    await _seed_role_assignment(db_session, admin_id, "admin_pedagogique")
    await _seed_role_assignment(db_session, responsable_id, "responsable_pedagogique")

    promotion_id = await _create_promotion(async_client, "AUTH-PROMO")

    response = await async_client.post(
        f"/api/v1/promotions/{promotion_id}/responsables/{responsable_id}",
        headers=auth_headers_factory(user_id=admin_id, roles=["admin_pedagogique"]),
    )

    assert response.status_code == 201
    assert response.json()["responsable_id"] == responsable_id
    assert response.json()["promotion_id"] == promotion_id


async def test_admin_pedagogique_cannot_assign_promotion_to_admin(
    async_client: AsyncClient,
    db_session: AsyncSession,
    auth_headers_factory: Callable[..., dict[str, str]],
) -> None:
    admin_id = str(uuid4())
    target_id = str(uuid4())
    await _seed_utilisateur(db_session, admin_id, "admin@example.com")
    await _seed_utilisateur(db_session, target_id, "target@example.com")
    await _seed_role_assignment(db_session, admin_id, "admin_pedagogique")
    await _seed_role_assignment(db_session, target_id, "admin_pedagogique")

    promotion_id = await _create_promotion(async_client, "AUTH-PROMO2")

    response = await async_client.post(
        f"/api/v1/promotions/{promotion_id}/responsables/{target_id}",
        headers=auth_headers_factory(user_id=admin_id, roles=["admin_pedagogique"]),
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Utilisateur does not have any of the required roles: responsable_pedagogique"


async def test_non_rp_cannot_assign_or_remove_roles(
    async_client: AsyncClient,
    db_session: AsyncSession,
    auth_headers_factory: Callable[..., dict[str, str]],
) -> None:
    teacher_id = await _seed_teacher(db_session)
    user_id = str(uuid4())
    await _seed_utilisateur(db_session, user_id, "target@example.com")
    role_id = await _seed_role_assignment(db_session, str(uuid4()), "admin_pedagogique")

    assign = await async_client.post(
        f"/api/v1/roles/utilisateurs/{user_id}/roles",
        json={"role_id": role_id},
        headers=auth_headers_factory(user_id=teacher_id, roles=["enseignant"]),
    )
    remove = await async_client.delete(
        f"/api/v1/roles/utilisateurs/{user_id}/roles/{role_id}",
        headers=auth_headers_factory(user_id=teacher_id, roles=["enseignant"]),
    )

    assert assign.status_code == 403
    assert remove.status_code == 403


async def test_rp_can_deactivate_account_and_non_rp_cannot(
    async_client: AsyncClient,
    db_session: AsyncSession,
    auth_headers_factory: Callable[..., dict[str, str]],
) -> None:
    teacher_id = await _seed_teacher(db_session)
    target_id = str(uuid4())
    await _seed_utilisateur(db_session, target_id, "activate-target@example.com")

    rp_response = await async_client.patch(
        f"/api/v1/utilisateurs/{target_id}/activation",
        json={"actif": False},
    )
    non_rp_response = await async_client.patch(
        f"/api/v1/utilisateurs/{target_id}/activation",
        json={"actif": True},
        headers=auth_headers_factory(user_id=teacher_id, roles=["enseignant"]),
    )

    assert rp_response.status_code == 200
    assert rp_response.json() == {"utilisateur_id": target_id, "actif": False}
    assert non_rp_response.status_code == 403
