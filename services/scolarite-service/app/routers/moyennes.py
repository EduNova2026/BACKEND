from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from shared.schemas import ErrorResponse

from app.database import get_replica_session
from app.dependencies.auth import (
    CurrentUser,
    ensure_can_access_etudiant,
    ensure_can_access_groupe,
    get_current_user,
)
from app.models import Etudiant, Examen, Groupe, Note, Promotion
from app.models.etudiant_groupe import etudiant_groupes
from app.schemas import MoyenneOut, MoyenneParEtudiant

router = APIRouter(tags=["moyennes"])


async def _student_group_rows(
    replica_session: AsyncSession,
    etudiant_id: UUID,
):
    return (
        await replica_session.execute(
            select(Groupe.id, Groupe.semestre, Groupe.coefficient)
            .select_from(etudiant_groupes)
            .join(Groupe, etudiant_groupes.c.groupe_id == Groupe.id)
            .where(etudiant_groupes.c.etudiant_id == etudiant_id)
        )
    ).all()


def _note_semestre_coefficient(
    enseignement_id: UUID,
    semestre: int,
    group_rows,
) -> float | None:
    groups_by_id = {row.id: row for row in group_rows}
    matching_groupe = groups_by_id.get(enseignement_id)
    if matching_groupe is not None:
        if matching_groupe.semestre != semestre:
            return None
        return float(matching_groupe.coefficient)

    if any(row.semestre == semestre for row in group_rows):
        return 1.0
    return None


async def _calculate_etudiant_moyenne(
    replica_session: AsyncSession,
    etudiant_id: UUID,
    semestre: int,
) -> MoyenneParEtudiant:
    group_rows = await _student_group_rows(replica_session, etudiant_id)
    note_rows = (
        await replica_session.execute(
            select(
                Note.valeur,
                Examen.coefficient,
                Examen.note_max,
                Examen.enseignement_id,
            )
            .select_from(Note)
            .join(Examen, Note.examen_id == Examen.id)
            .where(
                Note.etudiant_id == etudiant_id,
                Note.absent.is_(False),
                Note.valeur.is_not(None),
                Examen.coefficient > 0,
                Examen.note_max > 0,
            )
        )
    ).all()

    weighted_sum = 0.0
    coefficient_total = 0.0
    note_count = 0
    for row in note_rows:
        groupe_coefficient = _note_semestre_coefficient(
            row.enseignement_id, semestre, group_rows
        )
        if groupe_coefficient is None:
            continue

        effective_coefficient = float(row.coefficient) * groupe_coefficient
        weighted_sum += (float(row.valeur) / float(row.note_max) * 20.0) * effective_coefficient
        coefficient_total += effective_coefficient
        note_count += 1

    if note_count == 0 or coefficient_total == 0:
        return MoyenneParEtudiant(
            etudiant_id=etudiant_id,
            moyenne=None,
            semestre=semestre,
            note_count=0,
            coefficient_total=0.0,
        )

    return MoyenneParEtudiant(
        etudiant_id=etudiant_id,
        moyenne=weighted_sum / coefficient_total,
        semestre=semestre,
        note_count=note_count,
        coefficient_total=coefficient_total,
    )


async def _calculate_enseignement_moyenne(
    replica_session: AsyncSession,
    enseignement_id: UUID,
    semestre: int,
) -> MoyenneOut:
    note_rows = (
        await replica_session.execute(
            select(
                Note.etudiant_id,
                Note.valeur,
                Examen.coefficient,
                Examen.note_max,
                Examen.enseignement_id,
            )
            .select_from(Note)
            .join(Examen, Note.examen_id == Examen.id)
            .where(
                Examen.enseignement_id == enseignement_id,
                Note.absent.is_(False),
                Note.valeur.is_not(None),
                Examen.coefficient > 0,
                Examen.note_max > 0,
            )
        )
    ).all()

    group_rows_by_student: dict[UUID, object] = {}
    weighted_sum = 0.0
    coefficient_total = 0.0
    note_count = 0
    for row in note_rows:
        group_rows = group_rows_by_student.get(row.etudiant_id)
        if group_rows is None:
            group_rows = await _student_group_rows(replica_session, row.etudiant_id)
            group_rows_by_student[row.etudiant_id] = group_rows

        groupe_coefficient = _note_semestre_coefficient(
            row.enseignement_id, semestre, group_rows
        )
        if groupe_coefficient is None:
            continue

        effective_coefficient = float(row.coefficient) * groupe_coefficient
        weighted_sum += (float(row.valeur) / float(row.note_max) * 20.0) * effective_coefficient
        coefficient_total += effective_coefficient
        note_count += 1

    if note_count == 0 or coefficient_total == 0:
        return MoyenneOut(
            moyenne=None,
            semestre=semestre,
            note_count=0,
            coefficient_total=0.0,
        )

    return MoyenneOut(
        moyenne=weighted_sum / coefficient_total,
        semestre=semestre,
        note_count=note_count,
        coefficient_total=coefficient_total,
    )


def _to_moyenne_out(moyenne: MoyenneParEtudiant) -> MoyenneOut:
    return MoyenneOut(
        moyenne=moyenne.moyenne,
        semestre=moyenne.semestre,
        note_count=moyenne.note_count,
        coefficient_total=moyenne.coefficient_total,
    )


async def _promotion_etudiant_ids(
    replica_session: AsyncSession,
    promotion_id: UUID,
    semestre: int,
) -> list[UUID]:
    result = await replica_session.execute(
        select(Etudiant.id)
        .select_from(Etudiant)
        .join(etudiant_groupes, etudiant_groupes.c.etudiant_id == Etudiant.id)
        .join(Groupe, etudiant_groupes.c.groupe_id == Groupe.id)
        .where(Etudiant.promotion_id == promotion_id, Groupe.semestre == semestre)
        .distinct()
    )
    return list(result.scalars().all())


@router.get(
    "/etudiants/{etudiant_id}/moyenne",
    response_model=MoyenneOut,
    responses={status.HTTP_404_NOT_FOUND: {"model": ErrorResponse}},
)
async def get_etudiant_moyenne(
    etudiant_id: UUID,
    semestre: int = Query(1, ge=1, le=2),
    current_user: CurrentUser = Depends(get_current_user),
    replica_session: AsyncSession = Depends(get_replica_session),
) -> MoyenneOut:
    etudiant = await replica_session.get(Etudiant, etudiant_id)
    if etudiant is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Etudiant not found")

    await ensure_can_access_etudiant(replica_session, current_user, etudiant_id)

    moyenne = await _calculate_etudiant_moyenne(replica_session, etudiant_id, semestre)
    return _to_moyenne_out(moyenne)


@router.get(
    "/promotions/{promotion_id}/moyenne",
    response_model=MoyenneOut,
    responses={status.HTTP_404_NOT_FOUND: {"model": ErrorResponse}},
)
async def get_promotion_moyenne(
    promotion_id: UUID,
    semestre: int = Query(1, ge=1, le=2),
    _current_user: CurrentUser = Depends(get_current_user),
    replica_session: AsyncSession = Depends(get_replica_session),
) -> MoyenneOut:
    promotion = await replica_session.get(Promotion, promotion_id)
    if promotion is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Promotion not found")

    student_ids = await _promotion_etudiant_ids(replica_session, promotion_id, semestre)
    moyennes = [
        await _calculate_etudiant_moyenne(replica_session, student_id, semestre)
        for student_id in student_ids
    ]
    non_empty_moyennes = [moyenne for moyenne in moyennes if moyenne.moyenne is not None]

    if not non_empty_moyennes:
        return MoyenneOut(
            moyenne=None,
            semestre=semestre,
            note_count=0,
            coefficient_total=0.0,
        )

    return MoyenneOut(
        moyenne=sum(float(moyenne.moyenne) for moyenne in non_empty_moyennes)
        / len(non_empty_moyennes),
        semestre=semestre,
        note_count=sum(moyenne.note_count for moyenne in non_empty_moyennes),
        coefficient_total=sum(moyenne.coefficient_total for moyenne in non_empty_moyennes),
    )


@router.get(
    "/promotions/{promotion_id}/etudiants/moyennes",
    response_model=list[MoyenneParEtudiant],
    responses={status.HTTP_404_NOT_FOUND: {"model": ErrorResponse}},
)
async def list_promotion_etudiants_moyennes(
    promotion_id: UUID,
    semestre: int = Query(1, ge=1, le=2),
    _current_user: CurrentUser = Depends(get_current_user),
    replica_session: AsyncSession = Depends(get_replica_session),
) -> list[MoyenneParEtudiant]:
    promotion = await replica_session.get(Promotion, promotion_id)
    if promotion is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Promotion not found")

    student_ids = await _promotion_etudiant_ids(replica_session, promotion_id, semestre)
    return [
        await _calculate_etudiant_moyenne(replica_session, student_id, semestre)
        for student_id in student_ids
    ]


@router.get(
    "/groupes/{groupe_id}/etudiants/moyennes",
    response_model=list[MoyenneParEtudiant],
    responses={status.HTTP_404_NOT_FOUND: {"model": ErrorResponse}},
)
async def list_groupe_etudiants_moyennes(
    groupe_id: UUID,
    semestre: int = Query(1, ge=1, le=2),
    current_user: CurrentUser = Depends(get_current_user),
    replica_session: AsyncSession = Depends(get_replica_session),
) -> list[MoyenneParEtudiant]:
    groupe = await replica_session.get(Groupe, groupe_id)
    if groupe is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Groupe not found")
    await ensure_can_access_groupe(replica_session, current_user, groupe_id)

    if groupe.semestre != semestre:
        return []

    result = await replica_session.execute(
        select(Etudiant.id)
        .select_from(Etudiant)
        .join(etudiant_groupes, etudiant_groupes.c.etudiant_id == Etudiant.id)
        .where(etudiant_groupes.c.groupe_id == groupe_id)
        .order_by(Etudiant.nom, Etudiant.prenom)
    )
    student_ids = list(result.scalars().all())
    return [
        await _calculate_etudiant_moyenne(replica_session, student_id, semestre)
        for student_id in student_ids
    ]


@router.get(
    "/enseignements/{enseignement_id}/moyenne",
    response_model=MoyenneOut,
    responses={status.HTTP_404_NOT_FOUND: {"model": ErrorResponse}},
)
async def get_enseignement_moyenne(
    enseignement_id: UUID,
    semestre: int = Query(1, ge=1, le=2),
    _current_user: CurrentUser = Depends(get_current_user),
    replica_session: AsyncSession = Depends(get_replica_session),
) -> MoyenneOut:
    return await _calculate_enseignement_moyenne(
        replica_session, enseignement_id, semestre
    )
