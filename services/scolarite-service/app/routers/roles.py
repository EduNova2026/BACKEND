from __future__ import annotations

from typing import Any, cast
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import delete, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.engine import CursorResult
from sqlalchemy.ext.asyncio import AsyncSession
from shared.schemas import ErrorResponse

from app.cache import cache_get_json, cache_set_json
from app.config import settings
from app.database import get_replica_session, get_session
from app.dependencies.auth import CurrentUser, require_responsable_pedagogique
from app.external_models import RoleRef, UtilisateurRef, utilisateur_roles
from app.schemas import RoleAssignmentCreate, UtilisateurRoleOut

router = APIRouter(prefix="/roles", tags=["roles"])


@router.get(
    "/",
    response_model=list[dict[str, UUID | str]],
)
async def list_roles(
    _: CurrentUser = Depends(require_responsable_pedagogique),
    replica_session: AsyncSession = Depends(get_replica_session),
) -> list[dict[str, UUID | str]]:
    cache_key = "scolarite:roles:all"
    cached = await cache_get_json(cache_key)
    if cached is not None:
        return cast(list[dict[str, UUID | str]], cached)

    roles = await replica_session.scalars(select(RoleRef).order_by(RoleRef.libelle))
    response: list[dict[str, UUID | str]] = [
        {"id": role.id, "libelle": role.libelle} for role in roles.all()
    ]
    await cache_set_json(cache_key, response, settings.cache_roles_ttl_seconds)
    return response


@router.get(
    "/utilisateurs/{utilisateur_id}/roles",
    response_model=list[UtilisateurRoleOut],
    responses={status.HTTP_404_NOT_FOUND: {"model": ErrorResponse}},
)
async def list_utilisateur_roles(
    utilisateur_id: UUID,
    _: CurrentUser = Depends(require_responsable_pedagogique),
    replica_session: AsyncSession = Depends(get_replica_session),
) -> list[UtilisateurRoleOut]:
    utilisateur = await replica_session.get(UtilisateurRef, utilisateur_id)
    if utilisateur is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Utilisateur not found")

    result = await replica_session.execute(
        select(utilisateur_roles.c.utilisateur_id, RoleRef.id, RoleRef.libelle)
        .join(RoleRef, RoleRef.id == utilisateur_roles.c.role_id)
        .where(utilisateur_roles.c.utilisateur_id == utilisateur_id)
        .order_by(RoleRef.libelle)
    )
    return [
        UtilisateurRoleOut(
            utilisateur_id=row.utilisateur_id,
            role_id=row.id,
            libelle=row.libelle,
        )
        for row in result.all()
    ]


@router.post(
    "/utilisateurs/{utilisateur_id}/roles",
    response_model=UtilisateurRoleOut,
    status_code=status.HTTP_201_CREATED,
    responses={status.HTTP_400_BAD_REQUEST: {"model": ErrorResponse}},
)
async def assign_role_to_utilisateur(
    utilisateur_id: UUID,
    payload: RoleAssignmentCreate,
    _: CurrentUser = Depends(require_responsable_pedagogique),
    session: AsyncSession = Depends(get_session),
) -> UtilisateurRoleOut:
    utilisateur = await session.get(UtilisateurRef, utilisateur_id)
    if utilisateur is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Utilisateur not found")
    if not utilisateur.actif:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Utilisateur is inactive")

    role = await session.get(RoleRef, payload.role_id)
    if role is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Role not found")

    stmt = pg_insert(utilisateur_roles).values(
        utilisateur_id=utilisateur_id,
        role_id=payload.role_id,
    ).on_conflict_do_nothing(
        index_elements=["utilisateur_id", "role_id"],
    )
    await session.execute(stmt)
    await session.commit()

    return UtilisateurRoleOut(
        utilisateur_id=utilisateur_id,
        role_id=payload.role_id,
        libelle=role.libelle,
    )


@router.delete(
    "/utilisateurs/{utilisateur_id}/roles/{role_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    responses={status.HTTP_404_NOT_FOUND: {"model": ErrorResponse}},
)
async def remove_role_from_utilisateur(
    utilisateur_id: UUID,
    role_id: UUID,
    _: CurrentUser = Depends(require_responsable_pedagogique),
    session: AsyncSession = Depends(get_session),
) -> None:
    utilisateur = await session.get(UtilisateurRef, utilisateur_id)
    if utilisateur is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Utilisateur not found")

    role = await session.get(RoleRef, role_id)
    if role is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Role not found")

    deleted = cast(
        CursorResult[Any],
        await session.execute(
            delete(utilisateur_roles).where(
                utilisateur_roles.c.utilisateur_id == utilisateur_id,
                utilisateur_roles.c.role_id == role_id,
            )
        ),
    )
    if deleted.rowcount == 0:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Role assignment not found")

    await session.commit()
