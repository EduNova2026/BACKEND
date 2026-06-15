from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession
from shared.schemas import ErrorResponse

from app.database import get_replica_session, get_session
from app.dependencies.auth import (
    CurrentUser,
    ADMIN_PEDAGOGIQUE,
    ENSEIGNANT,
    RESPONSABLE_PEDAGOGIQUE,
    get_current_user,
    get_active_user_with_role_or_400,
    is_responsable_pedagogique,
    require_responsable_pedagogique,
)
from app.models import EnseignantGroupe, Groupe, Promotion, ResponsablePromotion
from app.schemas import EnseignantGroupeOut, ResponsablePromotionOut

router = APIRouter(tags=["assignments"])


def _forbidden() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Insufficient permissions",
    )


@router.post(
    "/groupes/{groupe_id}/enseignants/{enseignant_id}",
    response_model=EnseignantGroupeOut,
    status_code=status.HTTP_201_CREATED,
    responses={status.HTTP_400_BAD_REQUEST: {"model": ErrorResponse}},
)
async def assign_enseignant_to_groupe(
    groupe_id: UUID,
    enseignant_id: UUID,
    current_user: CurrentUser = Depends(require_responsable_pedagogique),
    session: AsyncSession = Depends(get_session),
) -> EnseignantGroupeOut:
    groupe = await session.get(Groupe, groupe_id)
    if groupe is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Groupe not found")
    await get_active_user_with_role_or_400(session, enseignant_id, ENSEIGNANT)

    assignment = await session.get(
        EnseignantGroupe,
        {"enseignant_id": enseignant_id, "groupe_id": groupe_id},
    )
    if assignment is None:
        assignment = EnseignantGroupe(
            enseignant_id=enseignant_id,
            groupe_id=groupe_id,
            assigned_by=current_user.id,
        )
        session.add(assignment)
        await session.commit()
        await session.refresh(assignment)
    return assignment


@router.get(
    "/groupes/{groupe_id}/enseignants",
    response_model=list[EnseignantGroupeOut],
    responses={status.HTTP_404_NOT_FOUND: {"model": ErrorResponse}},
)
async def list_groupe_enseignants(
    groupe_id: UUID,
    _: CurrentUser = Depends(require_responsable_pedagogique),
    replica_session: AsyncSession = Depends(get_replica_session),
) -> list[EnseignantGroupeOut]:
    groupe = await replica_session.get(Groupe, groupe_id)
    if groupe is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Groupe not found")

    result = await replica_session.scalars(
        select(EnseignantGroupe)
        .where(EnseignantGroupe.groupe_id == groupe_id)
        .order_by(EnseignantGroupe.created_at)
    )
    return list(result.all())


@router.delete(
    "/groupes/{groupe_id}/enseignants/{enseignant_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    responses={status.HTTP_404_NOT_FOUND: {"model": ErrorResponse}},
)
async def remove_enseignant_from_groupe(
    groupe_id: UUID,
    enseignant_id: UUID,
    _: CurrentUser = Depends(require_responsable_pedagogique),
    session: AsyncSession = Depends(get_session),
) -> None:
    deleted = await session.execute(
        delete(EnseignantGroupe).where(
            EnseignantGroupe.enseignant_id == enseignant_id,
            EnseignantGroupe.groupe_id == groupe_id,
        )
    )
    if deleted.rowcount == 0:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Enseignant assignment not found",
        )
    await session.commit()


@router.get(
    "/enseignants/{enseignant_id}/groupes",
    response_model=list[EnseignantGroupeOut],
)
async def list_enseignant_groupes(
    enseignant_id: UUID,
    current_user: CurrentUser = Depends(get_current_user),
    replica_session: AsyncSession = Depends(get_replica_session),
) -> list[EnseignantGroupeOut]:
    if not is_responsable_pedagogique(current_user) and current_user.id != enseignant_id:
        raise _forbidden()

    result = await replica_session.scalars(
        select(EnseignantGroupe)
        .where(EnseignantGroupe.enseignant_id == enseignant_id)
        .order_by(EnseignantGroupe.created_at)
    )
    return list(result.all())


@router.post(
    "/promotions/{promotion_id}/responsables/{responsable_id}",
    response_model=ResponsablePromotionOut,
    status_code=status.HTTP_201_CREATED,
    responses={status.HTTP_400_BAD_REQUEST: {"model": ErrorResponse}},
)
async def assign_responsable_to_promotion(
    promotion_id: UUID,
    responsable_id: UUID,
    current_user: CurrentUser = Depends(require_responsable_pedagogique),
    session: AsyncSession = Depends(get_session),
) -> ResponsablePromotionOut:
    promotion = await session.get(Promotion, promotion_id)
    if promotion is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Promotion not found")
    await get_active_user_with_role_or_400(session, responsable_id, RESPONSABLE_PEDAGOGIQUE)

    assignment = await session.get(
        ResponsablePromotion,
        {"responsable_id": responsable_id, "promotion_id": promotion_id},
    )
    if assignment is None:
        assignment = ResponsablePromotion(
            responsable_id=responsable_id,
            promotion_id=promotion_id,
            assigned_by=current_user.id,
        )
        session.add(assignment)
        await session.commit()
        await session.refresh(assignment)
    return assignment


@router.get(
    "/promotions/{promotion_id}/responsables",
    response_model=list[ResponsablePromotionOut],
    responses={status.HTTP_404_NOT_FOUND: {"model": ErrorResponse}},
)
async def list_promotion_responsables(
    promotion_id: UUID,
    _: CurrentUser = Depends(require_responsable_pedagogique),
    replica_session: AsyncSession = Depends(get_replica_session),
) -> list[ResponsablePromotionOut]:
    promotion = await replica_session.get(Promotion, promotion_id)
    if promotion is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Promotion not found")

    result = await replica_session.scalars(
        select(ResponsablePromotion)
        .where(ResponsablePromotion.promotion_id == promotion_id)
        .order_by(ResponsablePromotion.created_at)
    )
    return list(result.all())


@router.delete(
    "/promotions/{promotion_id}/responsables/{responsable_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    responses={status.HTTP_404_NOT_FOUND: {"model": ErrorResponse}},
)
async def remove_responsable_from_promotion(
    promotion_id: UUID,
    responsable_id: UUID,
    _: CurrentUser = Depends(require_responsable_pedagogique),
    session: AsyncSession = Depends(get_session),
) -> None:
    deleted = await session.execute(
        delete(ResponsablePromotion).where(
            ResponsablePromotion.responsable_id == responsable_id,
            ResponsablePromotion.promotion_id == promotion_id,
        )
    )
    if deleted.rowcount == 0:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Responsable assignment not found",
        )
    await session.commit()


@router.get(
    "/responsables/{responsable_id}/promotions",
    response_model=list[ResponsablePromotionOut],
)
async def list_responsable_promotions(
    responsable_id: UUID,
    current_user: CurrentUser = Depends(get_current_user),
    replica_session: AsyncSession = Depends(get_replica_session),
) -> list[ResponsablePromotionOut]:
    if not is_responsable_pedagogique(current_user) and current_user.id != responsable_id:
        raise _forbidden()

    result = await replica_session.scalars(
        select(ResponsablePromotion)
        .where(ResponsablePromotion.responsable_id == responsable_id)
        .order_by(ResponsablePromotion.created_at)
    )
    return list(result.all())
