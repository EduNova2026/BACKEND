from __future__ import annotations

from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Etudiant, Promotion, etudiant_groupes


PROMOTION_CHANGE_WITH_GROUPES_DETAIL = (
    "Cannot change promotion while student is assigned to groupes. Remove groupes first."
)


async def get_promotion_or_404(session: AsyncSession, promotion_id: UUID) -> Promotion:
    promotion = await session.get(Promotion, promotion_id)
    if promotion is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Promotion not found")
    return promotion


async def get_etudiant_or_404(session: AsyncSession, etudiant_id: UUID) -> Etudiant:
    etudiant = await session.get(Etudiant, etudiant_id)
    if etudiant is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Etudiant not found")
    return etudiant


async def etudiant_has_groupes(session: AsyncSession, etudiant_id: UUID) -> bool:
    groupe_id = await session.scalar(
        select(etudiant_groupes.c.groupe_id).where(etudiant_groupes.c.etudiant_id == etudiant_id)
    )
    return groupe_id is not None


async def ensure_promotion_reassignment_allowed(
    session: AsyncSession,
    etudiant: Etudiant,
    promotion_id: UUID,
) -> None:
    await get_promotion_or_404(session, promotion_id)
    if etudiant.promotion_id == promotion_id:
        return

    if await etudiant_has_groupes(session, etudiant.id):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=PROMOTION_CHANGE_WITH_GROUPES_DETAIL,
        )
