from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from shared.schemas import ErrorResponse

from app.database import get_session
from app.dependencies.auth import CurrentUser, require_responsable_pedagogique
from app.external_models import UtilisateurRef
from app.schemas import UserActivationUpdate

router = APIRouter(prefix="/utilisateurs", tags=["utilisateurs"])


@router.patch(
    "/{utilisateur_id}/activation",
    response_model=dict[str, UUID | bool],
    responses={status.HTTP_404_NOT_FOUND: {"model": ErrorResponse}},
)
async def update_utilisateur_activation(
    utilisateur_id: UUID,
    payload: UserActivationUpdate,
    _: CurrentUser = Depends(require_responsable_pedagogique),
    session: AsyncSession = Depends(get_session),
) -> dict[str, UUID | bool]:
    utilisateur = await session.get(UtilisateurRef, utilisateur_id)
    if utilisateur is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Utilisateur not found")

    utilisateur.actif = payload.actif
    await session.commit()
    return {"utilisateur_id": utilisateur_id, "actif": utilisateur.actif}
