from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from shared.schemas import ErrorResponse

from app.database import get_replica_session, get_session
from app.models import Groupe, Promotion
from app.schemas import EtudiantOut, GroupeCreate, GroupeOut, GroupeUpdate

router = APIRouter(prefix="/groupes", tags=["groupes"])


@router.get(
    "/",
    response_model=list[GroupeOut],
)
async def list_groupes(
    replica_session: AsyncSession = Depends(get_replica_session),
) -> list[GroupeOut]:
    result = await replica_session.scalars(select(Groupe).order_by(Groupe.nom))
    return result.all()


@router.post(
    "/",
    response_model=GroupeOut,
    status_code=status.HTTP_201_CREATED,
    responses={status.HTTP_400_BAD_REQUEST: {"model": ErrorResponse}},
)
async def create_groupe(
    payload: GroupeCreate,
    session: AsyncSession = Depends(get_session),
) -> GroupeOut:
    promotion = await session.get(Promotion, payload.promotion_id)
    if promotion is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Promotion not found")

    groupe = Groupe(nom=payload.nom, promotion_id=payload.promotion_id)
    session.add(groupe)
    await session.commit()
    await session.refresh(groupe)
    return groupe


@router.get(
    "/{groupe_id}",
    response_model=GroupeOut,
    responses={status.HTTP_404_NOT_FOUND: {"model": ErrorResponse}},
)
async def get_groupe(
    groupe_id: UUID,
    replica_session: AsyncSession = Depends(get_replica_session),
) -> GroupeOut:
    groupe = await replica_session.get(Groupe, groupe_id)
    if groupe is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Groupe not found")
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
    session: AsyncSession = Depends(get_session),
) -> GroupeOut:
    groupe = await session.get(Groupe, groupe_id)
    if groupe is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Groupe not found")

    update_data = payload.model_dump(exclude_unset=True)
    if "promotion_id" in update_data:
        promotion = await session.get(Promotion, update_data["promotion_id"])
        if promotion is None:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Promotion not found")

    for field, value in update_data.items():
        setattr(groupe, field, value)

    await session.commit()
    await session.refresh(groupe)
    return groupe


@router.delete(
    "/{groupe_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    responses={status.HTTP_404_NOT_FOUND: {"model": ErrorResponse}},
)
async def delete_groupe(
    groupe_id: UUID,
    session: AsyncSession = Depends(get_session),
) -> None:
    groupe = await session.get(Groupe, groupe_id)
    if groupe is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Groupe not found")

    await session.delete(groupe)
    await session.commit()


@router.get(
    "/{groupe_id}/etudiants",
    response_model=list[EtudiantOut],
    responses={status.HTTP_404_NOT_FOUND: {"model": ErrorResponse}},
)
async def list_groupe_etudiants(
    groupe_id: UUID,
    replica_session: AsyncSession = Depends(get_replica_session),
) -> list[EtudiantOut]:
    groupe = await replica_session.scalar(
        select(Groupe)
        .options(selectinload(Groupe.etudiants))
        .where(Groupe.id == groupe_id)
    )
    if groupe is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Groupe not found")

    return sorted(groupe.etudiants, key=lambda etudiant: str(etudiant.utilisateur_id))
