from __future__ import annotations

import re
import unicodedata
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import delete, func, insert, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from shared.schemas import ErrorResponse

from app.database import get_replica_session, get_session
from app.dependencies.auth import (
    CurrentUser,
    ensure_can_access_etudiant,
    get_current_user,
    is_responsable_pedagogique,
    require_responsable_pedagogique,
)
from app.models import Etudiant, Groupe, etudiant_groupes
from app.schemas import (
    EtudiantCreate,
    EtudiantGroupeOut,
    EtudiantOut,
    EtudiantSearchResponse,
    EtudiantUpdate,
    GroupeOut,
)
from app.services.promotion_membership import (
    ensure_promotion_reassignment_allowed,
    get_promotion_or_404,
)

router = APIRouter(prefix="/etudiants", tags=["etudiants"])


def normalize_name(value: str) -> str:
    without_accents = "".join(
        char
        for char in unicodedata.normalize("NFKD", value.strip().casefold())
        if not unicodedata.combining(char)
    )
    return re.sub(r"[\s\-']+", " ", without_accents).strip()


def apply_etudiant_name(etudiant: Etudiant, nom: str, prenom: str) -> None:
    etudiant.nom = normalize_name(nom)
    etudiant.prenom = normalize_name(prenom)


async def ensure_promotion_exists(session: AsyncSession, promotion_id: UUID) -> None:
    await get_promotion_or_404(session, promotion_id)


def etudiant_search_query(
    promotion_id: UUID | None,
    nom: str | None,
    prenom: str | None,
):
    query = select(Etudiant)
    if promotion_id is not None:
        query = query.where(Etudiant.promotion_id == promotion_id)
    if nom is not None:
        query = query.where(Etudiant.nom == normalize_name(nom))
    if prenom is not None:
        query = query.where(Etudiant.prenom == normalize_name(prenom))
    return query.order_by(Etudiant.nom, Etudiant.prenom, Etudiant.id)


@router.get(
    "/",
    response_model=list[EtudiantOut],
)
async def list_etudiants(
    promotion_id: UUID | None = None,
    nom: str | None = None,
    prenom: str | None = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    _: CurrentUser = Depends(require_responsable_pedagogique),
    replica_session: AsyncSession = Depends(get_replica_session),
) -> list[EtudiantOut]:
    result = await replica_session.scalars(
        etudiant_search_query(promotion_id, nom, prenom).offset(skip).limit(limit)
    )
    return result.all()


@router.post(
    "/",
    response_model=EtudiantOut,
    status_code=status.HTTP_201_CREATED,
    responses={
        status.HTTP_404_NOT_FOUND: {"model": ErrorResponse},
    },
)
async def create_etudiant(
    payload: EtudiantCreate,
    _: CurrentUser = Depends(require_responsable_pedagogique),
    session: AsyncSession = Depends(get_session),
) -> EtudiantOut:
    await ensure_promotion_exists(session, payload.promotion_id)

    etudiant = Etudiant(
        promotion_id=payload.promotion_id,
        nom=normalize_name(payload.nom),
        prenom=normalize_name(payload.prenom),
    )
    session.add(etudiant)
    await session.commit()
    await session.refresh(etudiant)
    return etudiant


@router.get(
    "/search",
    response_model=EtudiantSearchResponse,
)
async def search_etudiants(
    promotion_id: UUID,
    nom: str,
    prenom: str,
    _: CurrentUser = Depends(require_responsable_pedagogique),
    replica_session: AsyncSession = Depends(get_replica_session),
) -> EtudiantSearchResponse:
    filtered_query = etudiant_search_query(promotion_id, nom, prenom)
    count_query = select(func.count()).select_from(filtered_query.order_by(None).subquery())
    count = await replica_session.scalar(count_query)
    items = (await replica_session.scalars(filtered_query.limit(100))).all()
    return EtudiantSearchResponse(items=items, count=count or 0)


@router.get(
    "/resolve",
    response_model=EtudiantOut,
    responses={
        status.HTTP_404_NOT_FOUND: {"model": ErrorResponse},
    },
)
async def resolve_etudiant(
    promotion_id: UUID,
    nom: str,
    prenom: str,
    _: CurrentUser = Depends(require_responsable_pedagogique),
    replica_session: AsyncSession = Depends(get_replica_session),
) -> EtudiantOut:
    items = (
        await replica_session.scalars(etudiant_search_query(promotion_id, nom, prenom).limit(2))
    ).all()
    if len(items) == 0:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Etudiant not found")
    if len(items) > 1:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "message": "Multiple etudiants match this identity",
                "matches_count": len(items),
            },
        )
    return items[0]


@router.get(
    "/{etudiant_id}",
    response_model=EtudiantOut,
    responses={status.HTTP_404_NOT_FOUND: {"model": ErrorResponse}},
)
async def get_etudiant(
    etudiant_id: UUID,
    current_user: CurrentUser = Depends(get_current_user),
    replica_session: AsyncSession = Depends(get_replica_session),
) -> EtudiantOut:
    etudiant = await replica_session.get(Etudiant, etudiant_id)
    if etudiant is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Etudiant not found")
    await ensure_can_access_etudiant(replica_session, current_user, etudiant_id)
    return etudiant


@router.patch(
    "/{etudiant_id}",
    response_model=EtudiantOut,
    responses={
        status.HTTP_404_NOT_FOUND: {"model": ErrorResponse},
        status.HTTP_409_CONFLICT: {"model": ErrorResponse},
    },
)
async def update_etudiant(
    etudiant_id: UUID,
    payload: EtudiantUpdate,
    current_user: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> EtudiantOut:
    etudiant = await session.get(Etudiant, etudiant_id)
    if etudiant is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Etudiant not found")
    await ensure_can_access_etudiant(session, current_user, etudiant_id)

    update_data = payload.model_dump(exclude_unset=True)

    if "promotion_id" in update_data:
        if not is_responsable_pedagogique(current_user):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions",
            )
        if update_data["promotion_id"] is None:
            await session.execute(
                delete(etudiant_groupes).where(etudiant_groupes.c.etudiant_id == etudiant_id)
            )
        else:
            await ensure_promotion_reassignment_allowed(session, etudiant, update_data["promotion_id"])

    for field, value in update_data.items():
        if field in {"nom", "prenom"}:
            continue
        setattr(etudiant, field, value)
    apply_etudiant_name(
        etudiant,
        update_data.get("nom", etudiant.nom),
        update_data.get("prenom", etudiant.prenom),
    )

    await session.commit()
    await session.refresh(etudiant)
    return etudiant


@router.delete(
    "/{etudiant_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    responses={status.HTTP_404_NOT_FOUND: {"model": ErrorResponse}},
)
async def delete_etudiant(
    etudiant_id: UUID,
    _: CurrentUser = Depends(require_responsable_pedagogique),
    session: AsyncSession = Depends(get_session),
) -> None:
    etudiant = await session.get(Etudiant, etudiant_id)
    if etudiant is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Etudiant not found")

    await session.delete(etudiant)
    await session.commit()


@router.delete(
    "/{etudiant_id}/promotion",
    status_code=status.HTTP_204_NO_CONTENT,
    responses={status.HTTP_404_NOT_FOUND: {"model": ErrorResponse}},
)
async def remove_etudiant_from_promotion(
    etudiant_id: UUID,
    _: CurrentUser = Depends(require_responsable_pedagogique),
    session: AsyncSession = Depends(get_session),
) -> None:
    etudiant = await session.get(Etudiant, etudiant_id)
    if etudiant is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Etudiant not found")

    await session.execute(
        delete(etudiant_groupes).where(etudiant_groupes.c.etudiant_id == etudiant_id)
    )
    etudiant.promotion_id = None
    await session.commit()


@router.get(
    "/{etudiant_id}/groupes",
    response_model=list[GroupeOut],
    responses={status.HTTP_404_NOT_FOUND: {"model": ErrorResponse}},
)
async def list_etudiant_groupes(
    etudiant_id: UUID,
    current_user: CurrentUser = Depends(get_current_user),
    replica_session: AsyncSession = Depends(get_replica_session),
) -> list[GroupeOut]:
    etudiant = await replica_session.scalar(
        select(Etudiant).options(selectinload(Etudiant.groupes)).where(Etudiant.id == etudiant_id)
    )
    if etudiant is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Etudiant not found")
    await ensure_can_access_etudiant(replica_session, current_user, etudiant_id)

    return sorted(etudiant.groupes, key=lambda groupe: groupe.nom)


@router.post(
    "/{etudiant_id}/groupes/{groupe_id}",
    response_model=EtudiantGroupeOut,
    status_code=status.HTTP_201_CREATED,
    responses={
        status.HTTP_400_BAD_REQUEST: {"model": ErrorResponse},
        status.HTTP_404_NOT_FOUND: {"model": ErrorResponse},
        status.HTTP_409_CONFLICT: {"model": ErrorResponse},
    },
)
async def add_etudiant_to_groupe(
    etudiant_id: UUID,
    groupe_id: UUID,
    _: CurrentUser = Depends(require_responsable_pedagogique),
    session: AsyncSession = Depends(get_session),
) -> EtudiantGroupeOut:
    etudiant = await session.get(Etudiant, etudiant_id)
    if etudiant is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Etudiant not found")

    groupe = await session.get(Groupe, groupe_id)
    if groupe is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Groupe not found")
    if groupe.promotion_id != etudiant.promotion_id:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Etudiant can only be assigned to groupes from their promotion",
        )

    link_exists = await session.scalar(
        select(etudiant_groupes.c.etudiant_id).where(
            etudiant_groupes.c.etudiant_id == etudiant_id,
            etudiant_groupes.c.groupe_id == groupe_id,
        )
    )
    if link_exists is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Etudiant already assigned to this groupe",
        )

    await session.execute(
        insert(etudiant_groupes).values(etudiant_id=etudiant_id, groupe_id=groupe_id)
    )
    await session.commit()
    return EtudiantGroupeOut(etudiant_id=etudiant_id, groupe_id=groupe_id)


@router.delete(
    "/{etudiant_id}/groupes/{groupe_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    responses={status.HTTP_404_NOT_FOUND: {"model": ErrorResponse}},
)
async def remove_etudiant_from_groupe(
    etudiant_id: UUID,
    groupe_id: UUID,
    _: CurrentUser = Depends(require_responsable_pedagogique),
    session: AsyncSession = Depends(get_session),
) -> None:
    etudiant = await session.get(Etudiant, etudiant_id)
    if etudiant is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Etudiant not found")

    groupe = await session.get(Groupe, groupe_id)
    if groupe is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Groupe not found")

    deleted = await session.execute(
        delete(etudiant_groupes).where(
            etudiant_groupes.c.etudiant_id == etudiant_id,
            etudiant_groupes.c.groupe_id == groupe_id,
        )
    )
    if deleted.rowcount == 0:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Etudiant is not assigned to this groupe",
        )

    await session.commit()
