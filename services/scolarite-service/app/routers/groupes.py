from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from shared.schemas import ErrorResponse

from app.cache import cache_delete, cache_delete_pattern, cache_get_json, cache_set_json
from app.config import settings
from app.database import get_replica_session, get_session
from app.dependencies.auth import (
    CurrentUser,
    ensure_can_access_groupe,
    get_current_user,
    require_responsable_pedagogique,
)
from app.models import Groupe, Promotion
from app.schemas import EtudiantOut, GroupeCreate, GroupeOut, GroupeUpdate

router = APIRouter(prefix="/groupes", tags=["groupes"])


@router.get(
    "/",
    response_model=list[GroupeOut],
)
async def list_groupes(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    _: CurrentUser = Depends(require_responsable_pedagogique),
    replica_session: AsyncSession = Depends(get_replica_session),
) -> list[GroupeOut]:
    cache_key = f"scolarite:groupes:list:{skip}:{limit}"
    cached = await cache_get_json(cache_key)
    if cached is not None:
        return [GroupeOut.model_validate(item) for item in cached]

    result = await replica_session.scalars(
        select(Groupe).order_by(Groupe.nom).offset(skip).limit(limit)
    )
    groupes = result.all()
    response = [GroupeOut.model_validate(groupe) for groupe in groupes]
    await cache_set_json(cache_key, response, settings.cache_reference_ttl_seconds)
    return response


@router.post(
    "/",
    response_model=GroupeOut,
    status_code=status.HTTP_201_CREATED,
    responses={status.HTTP_400_BAD_REQUEST: {"model": ErrorResponse}},
)
async def create_groupe(
    payload: GroupeCreate,
    _: CurrentUser = Depends(require_responsable_pedagogique),
    session: AsyncSession = Depends(get_session),
) -> GroupeOut:
    promotion = await session.get(Promotion, payload.promotion_id)
    if promotion is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Promotion not found")

    groupe = Groupe(nom=payload.nom, promotion_id=payload.promotion_id)
    session.add(groupe)
    await session.commit()
    await session.refresh(groupe)
    await cache_delete_pattern("scolarite:groupes:list:*")
    await cache_delete(f"scolarite:promotions:{groupe.promotion_id}:groupes")
    return groupe


@router.get(
    "/{groupe_id}",
    response_model=GroupeOut,
    responses={status.HTTP_404_NOT_FOUND: {"model": ErrorResponse}},
)
async def get_groupe(
    groupe_id: UUID,
    current_user: CurrentUser = Depends(get_current_user),
    replica_session: AsyncSession = Depends(get_replica_session),
) -> GroupeOut:
    groupe = await replica_session.get(Groupe, groupe_id)
    if groupe is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Groupe not found")
    await ensure_can_access_groupe(replica_session, current_user, groupe_id)
    return groupe


@router.patch(
    "/{groupe_id}",
    response_model=GroupeOut,
    responses={
        status.HTTP_400_BAD_REQUEST: {"model": ErrorResponse},
        status.HTTP_404_NOT_FOUND: {"model": ErrorResponse},
    },
)
async def update_groupe(
    groupe_id: UUID,
    payload: GroupeUpdate,
    _: CurrentUser = Depends(require_responsable_pedagogique),
    session: AsyncSession = Depends(get_session),
) -> GroupeOut:
    groupe = await session.get(Groupe, groupe_id)
    if groupe is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Groupe not found")

    previous_promotion_id = groupe.promotion_id
    update_data = payload.model_dump(exclude_unset=True)
    if "promotion_id" in update_data:
        promotion = await session.get(Promotion, update_data["promotion_id"])
        if promotion is None:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Promotion not found")

    for field, value in update_data.items():
        setattr(groupe, field, value)

    await session.commit()
    await session.refresh(groupe)
    await cache_delete_pattern("scolarite:groupes:list:*")
    await cache_delete(
        f"scolarite:promotions:{previous_promotion_id}:groupes",
        f"scolarite:promotions:{groupe.promotion_id}:groupes",
    )
    return groupe


@router.delete(
    "/{groupe_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    responses={status.HTTP_404_NOT_FOUND: {"model": ErrorResponse}},
)
async def delete_groupe(
    groupe_id: UUID,
    _: CurrentUser = Depends(require_responsable_pedagogique),
    session: AsyncSession = Depends(get_session),
) -> None:
    groupe = await session.get(Groupe, groupe_id)
    if groupe is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Groupe not found")

    await session.delete(groupe)
    await session.commit()
    await cache_delete_pattern("scolarite:groupes:list:*")
    await cache_delete(f"scolarite:promotions:{groupe.promotion_id}:groupes")


@router.get(
    "/{groupe_id}/etudiants",
    response_model=list[EtudiantOut],
    responses={status.HTTP_404_NOT_FOUND: {"model": ErrorResponse}},
)
async def list_groupe_etudiants(
    groupe_id: UUID,
    current_user: CurrentUser = Depends(get_current_user),
    replica_session: AsyncSession = Depends(get_replica_session),
) -> list[EtudiantOut]:
    groupe = await replica_session.scalar(
        select(Groupe)
        .options(selectinload(Groupe.etudiants))
        .where(Groupe.id == groupe_id)
    )
    if groupe is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Groupe not found")
    await ensure_can_access_groupe(replica_session, current_user, groupe_id)

    return sorted(groupe.etudiants, key=lambda etudiant: str(etudiant.utilisateur_id))
