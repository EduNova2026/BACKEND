from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import delete, insert, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from shared.schemas import ErrorResponse

from app.database import get_replica_session, get_session
from app.external_models import UtilisateurRef
from app.models import Etudiant, Groupe, Promotion, etudiant_groupes
from app.schemas import (
    EtudiantCreate,
    EtudiantGroupeOut,
    EtudiantOut,
    EtudiantUpdate,
    GroupeOut,
)

router = APIRouter(prefix="/etudiants", tags=["etudiants"])


@router.get(
    "/",
    response_model=list[EtudiantOut],
)
async def list_etudiants(
    replica_session: AsyncSession = Depends(get_replica_session),
) -> list[EtudiantOut]:
    result = await replica_session.scalars(select(Etudiant).order_by(Etudiant.utilisateur_id))
    return result.all()


@router.post(
    "/",
    response_model=EtudiantOut,
    status_code=status.HTTP_201_CREATED,
    responses={status.HTTP_400_BAD_REQUEST: {"model": ErrorResponse}},
)
async def create_etudiant(
    payload: EtudiantCreate,
    session: AsyncSession = Depends(get_session),
) -> EtudiantOut:
    utilisateur = await session.get(UtilisateurRef, payload.utilisateur_id)
    if utilisateur is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Utilisateur not found")
    if not utilisateur.actif:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Utilisateur is inactive")

    promotion = await session.get(Promotion, payload.promotion_id)
    if promotion is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Promotion not found")

    etudiant = Etudiant(
        utilisateur_id=payload.utilisateur_id,
        promotion_id=payload.promotion_id,
    )
    session.add(etudiant)
    await session.commit()
    await session.refresh(etudiant)
    return etudiant


@router.get(
    "/{etudiant_id}",
    response_model=EtudiantOut,
    responses={status.HTTP_404_NOT_FOUND: {"model": ErrorResponse}},
)
async def get_etudiant(
    etudiant_id: UUID,
    replica_session: AsyncSession = Depends(get_replica_session),
) -> EtudiantOut:
    etudiant = await replica_session.get(Etudiant, etudiant_id)
    if etudiant is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Etudiant not found")
    return etudiant


@router.patch(
    "/{etudiant_id}",
    response_model=EtudiantOut,
    responses={
        status.HTTP_400_BAD_REQUEST: {"model": ErrorResponse},
        status.HTTP_404_NOT_FOUND: {"model": ErrorResponse},
    },
)
async def update_etudiant(
    etudiant_id: UUID,
    payload: EtudiantUpdate,
    session: AsyncSession = Depends(get_session),
) -> EtudiantOut:
    etudiant = await session.get(Etudiant, etudiant_id)
    if etudiant is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Etudiant not found")

    update_data = payload.model_dump(exclude_unset=True)
    if "promotion_id" in update_data:
        promotion = await session.get(Promotion, update_data["promotion_id"])
        if promotion is None:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Promotion not found")

    for field, value in update_data.items():
        setattr(etudiant, field, value)

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
    session: AsyncSession = Depends(get_session),
) -> None:
    etudiant = await session.get(Etudiant, etudiant_id)
    if etudiant is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Etudiant not found")

    await session.delete(etudiant)
    await session.commit()


@router.get(
    "/{etudiant_id}/groupes",
    response_model=list[GroupeOut],
    responses={status.HTTP_404_NOT_FOUND: {"model": ErrorResponse}},
)
async def list_etudiant_groupes(
    etudiant_id: UUID,
    replica_session: AsyncSession = Depends(get_replica_session),
) -> list[GroupeOut]:
    etudiant = await replica_session.scalar(
        select(Etudiant)
        .options(selectinload(Etudiant.groupes))
        .where(Etudiant.id == etudiant_id)
    )
    if etudiant is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Etudiant not found")

    return sorted(etudiant.groupes, key=lambda groupe: groupe.nom)


@router.post(
    "/{etudiant_id}/groupes/{groupe_id}",
    response_model=EtudiantGroupeOut,
    status_code=status.HTTP_201_CREATED,
    responses={
        status.HTTP_400_BAD_REQUEST: {"model": ErrorResponse},
        status.HTTP_404_NOT_FOUND: {"model": ErrorResponse},
    },
)
async def add_etudiant_to_groupe(
    etudiant_id: UUID,
    groupe_id: UUID,
    session: AsyncSession = Depends(get_session),
) -> EtudiantGroupeOut:
    etudiant = await session.get(Etudiant, etudiant_id)
    if etudiant is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Etudiant not found")

    groupe = await session.get(Groupe, groupe_id)
    if groupe is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Groupe not found")

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
