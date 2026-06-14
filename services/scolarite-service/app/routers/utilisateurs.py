from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from shared.schemas import ErrorResponse, UserActivationUpdate
from shared.schemas.user import UserOut

from app.database import get_replica_session, get_session
from app.dependencies import CurrentUser, require_responsable_pedagogique
from app.external_models import RoleRef, UtilisateurRef, utilisateur_roles

router = APIRouter(prefix="/utilisateurs", tags=["utilisateurs"])


async def _fetch_roles_by_utilisateur_id(
    replica_session: AsyncSession,
    utilisateur_ids: list[UUID],
) -> dict[UUID, list[str]]:
    if not utilisateur_ids:
        return {}

    roles_result = await replica_session.execute(
        select(utilisateur_roles.c.utilisateur_id, RoleRef.libelle)
        .join(RoleRef, RoleRef.id == utilisateur_roles.c.role_id)
        .where(utilisateur_roles.c.utilisateur_id.in_(utilisateur_ids))
        .order_by(RoleRef.libelle)
    )

    roles_by_utilisateur_id: dict[UUID, list[str]] = {}
    for row in roles_result.all():
        utilisateur_id = UUID(str(row.utilisateur_id))
        roles_by_utilisateur_id.setdefault(utilisateur_id, []).append(str(row.libelle))
    return roles_by_utilisateur_id


@router.get("/", response_model=list[UserOut])
async def list_utilisateurs(
    search: str | None = None,
    role: str | None = None,
    actif: bool | None = None,
    _: CurrentUser = Depends(require_responsable_pedagogique),
    replica_session: AsyncSession = Depends(get_replica_session),
) -> list[UserOut]:
    stmt = select(UtilisateurRef)

    if search:
        search_pattern = f"%{search}%"
        stmt = stmt.where(
            or_(
                UtilisateurRef.nom.ilike(search_pattern),
                UtilisateurRef.prenom.ilike(search_pattern),
                UtilisateurRef.email.ilike(search_pattern),
            )
        )

    if role:
        stmt = (
            stmt.join(
                utilisateur_roles,
                utilisateur_roles.c.utilisateur_id == UtilisateurRef.id,
            )
            .join(RoleRef, RoleRef.id == utilisateur_roles.c.role_id)
            .where(RoleRef.libelle == role)
            .distinct()
        )

    if actif is not None:
        stmt = stmt.where(UtilisateurRef.actif == actif)

    users = (await replica_session.scalars(stmt.order_by(UtilisateurRef.nom))).all()
    utilisateur_ids = [UUID(str(user.id)) for user in users]
    roles_by_utilisateur_id = await _fetch_roles_by_utilisateur_id(
        replica_session,
        utilisateur_ids,
    )

    return [
        UserOut(
            id=utilisateur_id,
            email=user.email,
            nom=user.nom,
            prenom=user.prenom,
            roles=roles_by_utilisateur_id.get(utilisateur_id, []),
            actif=user.actif,
            premier_login=False,
        )
        for user, utilisateur_id in zip(users, utilisateur_ids, strict=True)
    ]


@router.get(
    "/{utilisateur_id}",
    response_model=UserOut,
    responses={status.HTTP_404_NOT_FOUND: {"model": ErrorResponse}},
)
async def get_utilisateur(
    utilisateur_id: UUID,
    _: CurrentUser = Depends(require_responsable_pedagogique),
    replica_session: AsyncSession = Depends(get_replica_session),
) -> UserOut:
    utilisateur = await replica_session.get(UtilisateurRef, utilisateur_id)
    if utilisateur is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Utilisateur not found")

    roles_by_utilisateur_id = await _fetch_roles_by_utilisateur_id(
        replica_session,
        [utilisateur_id],
    )

    return UserOut(
        id=UUID(str(utilisateur.id)),
        email=utilisateur.email,
        nom=utilisateur.nom,
        prenom=utilisateur.prenom,
        roles=roles_by_utilisateur_id.get(utilisateur_id, []),
        actif=utilisateur.actif,
        premier_login=False,
    )


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
