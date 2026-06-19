from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from shared.schemas import ErrorResponse

from app.cache import cache_delete_pattern, cache_get_json, cache_set_json
from app.config import settings
from app.database import get_replica_session, get_session
from app.dependencies.auth import (
    ADMIN_PEDAGOGIQUE,
    CurrentUser,
    ENSEIGNANT,
    get_current_user,
    is_responsable_pedagogique,
    require_responsable_pedagogique,
)
from app.models import EnseignantGroupe, Groupe, Promotion, ResponsablePromotion
from app.schemas import EtudiantOut, GroupeOut, PromotionCreate, PromotionOut, PromotionUpdate
from app.services.promotion_membership import (
    ensure_promotion_reassignment_allowed,
    get_etudiant_or_404,
    get_promotion_or_404,
)

router = APIRouter(prefix="/promotions", tags=["promotions"])


@router.get(
    "/",
    response_model=list[PromotionOut],
)
async def list_promotions(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    current_user: CurrentUser = Depends(get_current_user),
    replica_session: AsyncSession = Depends(get_replica_session),
) -> list[PromotionOut]:
    if current_user.has_role(ADMIN_PEDAGOGIQUE):
        cache_key = f"scolarite:promotions:list:{skip}:{limit}"
        cached = await cache_get_json(cache_key)
        if cached is not None:
            return [PromotionOut.model_validate(item) for item in cached]

        result = await replica_session.scalars(
            select(Promotion).order_by(Promotion.nom).offset(skip).limit(limit)
        )
        promotions = result.all()
        response = [PromotionOut.model_validate(promotion) for promotion in promotions]
        await cache_set_json(cache_key, response, settings.cache_reference_ttl_seconds)
        return response

    if is_responsable_pedagogique(current_user):
        cache_key = (
            f"scolarite:promotions:list:rp:{current_user.id}:{skip}:{limit}"
        )
        cached = await cache_get_json(cache_key)
        if cached is not None:
            return [PromotionOut.model_validate(item) for item in cached]

        result = await replica_session.scalars(
            select(Promotion)
            .join(
                ResponsablePromotion,
                ResponsablePromotion.promotion_id == Promotion.id,
            )
            .where(ResponsablePromotion.responsable_id == current_user.id)
            .order_by(Promotion.nom)
            .offset(skip)
            .limit(limit)
        )
        promotions = result.all()
        response = [PromotionOut.model_validate(promotion) for promotion in promotions]
        await cache_set_json(cache_key, response, settings.cache_reference_ttl_seconds)
        return response

    if current_user.has_role(ENSEIGNANT):
        result = await replica_session.scalars(
            select(Promotion)
            .join(Groupe, Groupe.promotion_id == Promotion.id)
            .join(EnseignantGroupe, EnseignantGroupe.groupe_id == Groupe.id)
            .where(EnseignantGroupe.enseignant_id == current_user.id)
            .distinct()
            .order_by(Promotion.nom)
            .offset(skip)
            .limit(limit)
        )
        return [PromotionOut.model_validate(promotion) for promotion in result.all()]

    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Insufficient permissions",
    )


@router.post(
    "/",
    response_model=PromotionOut,
    status_code=status.HTTP_201_CREATED,
    responses={status.HTTP_400_BAD_REQUEST: {"model": ErrorResponse}},
)
async def create_promotion(
    payload: PromotionCreate,
    _: CurrentUser = Depends(require_responsable_pedagogique),
    session: AsyncSession = Depends(get_session),
) -> PromotionOut:
    duplicate = await session.scalar(
        select(Promotion).where(
            Promotion.nom == payload.nom,
            Promotion.annee_scolaire == payload.annee_scolaire,
        )
    )
    if duplicate is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Promotion already exists for this school year",
        )

    promotion = Promotion(nom=payload.nom, annee_scolaire=payload.annee_scolaire)
    session.add(promotion)
    await session.commit()
    await session.refresh(promotion)
    await cache_delete_pattern("scolarite:promotions:list:*")
    return promotion


@router.get(
    "/{promotion_id}",
    response_model=PromotionOut,
    responses={status.HTTP_404_NOT_FOUND: {"model": ErrorResponse}},
)
async def get_promotion(
    promotion_id: UUID,
    _: CurrentUser = Depends(require_responsable_pedagogique),
    replica_session: AsyncSession = Depends(get_replica_session),
) -> PromotionOut:
    promotion = await replica_session.get(Promotion, promotion_id)
    if promotion is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Promotion not found")
    return promotion


@router.patch(
    "/{promotion_id}",
    response_model=PromotionOut,
    responses={
        status.HTTP_400_BAD_REQUEST: {"model": ErrorResponse},
        status.HTTP_404_NOT_FOUND: {"model": ErrorResponse},
    },
)
async def update_promotion(
    promotion_id: UUID,
    payload: PromotionUpdate,
    _: CurrentUser = Depends(require_responsable_pedagogique),
    session: AsyncSession = Depends(get_session),
) -> PromotionOut:
    promotion = await session.get(Promotion, promotion_id)
    if promotion is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Promotion not found")

    update_data = payload.model_dump(exclude_unset=True)
    if not update_data:
        return promotion

    candidate_nom = update_data.get("nom", promotion.nom)
    candidate_annee = update_data.get("annee_scolaire", promotion.annee_scolaire)
    duplicate = await session.scalar(
        select(Promotion).where(
            Promotion.nom == candidate_nom,
            Promotion.annee_scolaire == candidate_annee,
            Promotion.id != promotion_id,
        )
    )
    if duplicate is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Promotion already exists for this school year",
        )

    for field, value in update_data.items():
        setattr(promotion, field, value)

    await session.commit()
    await session.refresh(promotion)
    await cache_delete_pattern("scolarite:promotions:list:*")
    return promotion


@router.delete(
    "/{promotion_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    responses={status.HTTP_404_NOT_FOUND: {"model": ErrorResponse}},
)
async def delete_promotion(
    promotion_id: UUID,
    _: CurrentUser = Depends(require_responsable_pedagogique),
    session: AsyncSession = Depends(get_session),
) -> None:
    promotion = await session.get(Promotion, promotion_id)
    if promotion is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Promotion not found")

    await session.delete(promotion)
    await session.commit()
    await cache_delete_pattern("scolarite:promotions:list:*")


@router.get(
    "/{promotion_id}/groupes",
    response_model=list[GroupeOut],
    responses={status.HTTP_404_NOT_FOUND: {"model": ErrorResponse}},
)
async def list_promotion_groupes(
    promotion_id: UUID,
    _: CurrentUser = Depends(require_responsable_pedagogique),
    replica_session: AsyncSession = Depends(get_replica_session),
) -> list[GroupeOut]:
    cache_key = f"scolarite:promotions:{promotion_id}:groupes"
    cached = await cache_get_json(cache_key)
    if cached is not None:
        return [GroupeOut.model_validate(item) for item in cached]

    promotion = await replica_session.scalar(
        select(Promotion)
        .options(selectinload(Promotion.groupes))
        .where(Promotion.id == promotion_id)
    )
    if promotion is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Promotion not found")

    response = [
        GroupeOut.model_validate(groupe)
        for groupe in sorted(promotion.groupes, key=lambda groupe: groupe.nom)
    ]
    await cache_set_json(cache_key, response, settings.cache_reference_ttl_seconds)
    return response


@router.get(
    "/{promotion_id}/etudiants",
    response_model=list[EtudiantOut],
    responses={status.HTTP_404_NOT_FOUND: {"model": ErrorResponse}},
)
async def list_promotion_etudiants(
    promotion_id: UUID,
    _: CurrentUser = Depends(require_responsable_pedagogique),
    replica_session: AsyncSession = Depends(get_replica_session),
) -> list[EtudiantOut]:
    promotion = await replica_session.scalar(
        select(Promotion)
        .options(selectinload(Promotion.etudiants))
        .where(Promotion.id == promotion_id)
    )
    if promotion is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Promotion not found")

    return sorted(promotion.etudiants, key=lambda etudiant: str(etudiant.utilisateur_id))


@router.post(
    "/{promotion_id}/etudiants/{etudiant_id}",
    response_model=EtudiantOut,
    responses={
        status.HTTP_404_NOT_FOUND: {"model": ErrorResponse},
        status.HTTP_409_CONFLICT: {"model": ErrorResponse},
    },
)
async def enroll_etudiant_in_promotion(
    promotion_id: UUID,
    etudiant_id: UUID,
    _: CurrentUser = Depends(require_responsable_pedagogique),
    session: AsyncSession = Depends(get_session),
) -> EtudiantOut:
    etudiant = await get_etudiant_or_404(session, etudiant_id)
    await ensure_promotion_reassignment_allowed(session, etudiant, promotion_id)

    etudiant.promotion_id = promotion_id
    await session.commit()
    await session.refresh(etudiant)
    return etudiant


@router.delete(
    "/{promotion_id}/etudiants/{etudiant_id}",
    responses={
        status.HTTP_404_NOT_FOUND: {"model": ErrorResponse},
        status.HTTP_409_CONFLICT: {"model": ErrorResponse},
    },
)
async def unenroll_etudiant_from_promotion(
    promotion_id: UUID,
    etudiant_id: UUID,
    _: CurrentUser = Depends(require_responsable_pedagogique),
    session: AsyncSession = Depends(get_session),
) -> None:
    await get_promotion_or_404(session, promotion_id)
    etudiant = await get_etudiant_or_404(session, etudiant_id)
    if etudiant.promotion_id != promotion_id:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Etudiant is not enrolled in this promotion",
        )

    raise HTTPException(
        status_code=status.HTTP_409_CONFLICT,
        detail=(
            "Cannot remove student from promotion because promotion_id is required. "
            "Reassign the student to another promotion or delete the student."
        ),
    )
