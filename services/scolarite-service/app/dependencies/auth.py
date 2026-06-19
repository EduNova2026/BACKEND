from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from uuid import UUID

import jwt
from fastapi import Depends, HTTPException, Request, status
from sqlalchemy import exists, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import get_replica_session, get_session
from app.external_models import RoleRef, UtilisateurRef, utilisateur_roles
from app.models import EnseignantGroupe, Etudiant, etudiant_groupes

ADMIN_PEDAGOGIQUE = "admin_pedagogique"
RESPONSABLE_PEDAGOGIQUE = "responsable_pedagogique"
ENSEIGNANT = "enseignant"

_ADMIN_OR_RP = (ADMIN_PEDAGOGIQUE, RESPONSABLE_PEDAGOGIQUE)


@dataclass(frozen=True)
class CurrentUser:
    id: UUID
    email: str
    roles: tuple[str, ...]

    def has_role(self, role: str) -> bool:
        return role in self.roles


def _unauthorized() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid authentication credentials",
    )


async def get_current_user(request: Request) -> CurrentUser:
    authorization = request.headers.get("Authorization", "")
    if not authorization.startswith("Bearer "):
        raise _unauthorized()

    token = authorization.removeprefix("Bearer ").strip()
    if not token:
        raise _unauthorized()

    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
    except (jwt.ExpiredSignatureError, jwt.InvalidTokenError) as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token is invalid or expired",
        ) from exc

    user_id = payload.get("user_id")
    email = payload.get("email")
    roles = payload.get("roles")
    if user_id is None or not isinstance(email, str) or not isinstance(roles, list):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token is invalid or expired",
        )

    try:
        parsed_user_id = UUID(str(user_id))
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token is invalid or expired",
        ) from exc

    role_names = tuple(role for role in roles if isinstance(role, str))
    if len(role_names) != len(roles):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token is invalid or expired",
        )

    return CurrentUser(id=parsed_user_id, email=email, roles=role_names)


def require_role(*roles: str) -> Callable[..., object]:
    async def dependency(current_user: CurrentUser = Depends(get_current_user)) -> CurrentUser:
        if not any(current_user.has_role(role) for role in roles):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions",
            )
        return current_user

    return dependency


async def require_responsable_pedagogique(
    current_user: CurrentUser = Depends(get_current_user),
) -> CurrentUser:
    if not any(current_user.has_role(role) for role in _ADMIN_OR_RP):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions",
        )
    return current_user


async def require_admin_pedagogique(
    current_user: CurrentUser = Depends(get_current_user),
) -> CurrentUser:
    if not any(current_user.has_role(role) for role in _ADMIN_OR_RP):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions",
        )
    return current_user


def is_responsable_pedagogique(current_user: CurrentUser) -> bool:
    return any(current_user.has_role(role) for role in _ADMIN_OR_RP)


async def user_has_role(session: AsyncSession, utilisateur_id: UUID, role_libelle: str) -> bool:
    return bool(
        await session.scalar(
            select(
                exists().where(
                    utilisateur_roles.c.utilisateur_id == utilisateur_id,
                    utilisateur_roles.c.role_id == RoleRef.id,
                    RoleRef.libelle == role_libelle,
                )
            )
        )
    )


async def get_active_user_with_role_or_400(
    session: AsyncSession,
    utilisateur_id: UUID,
    role_libelle: str,
    *or_roles: str,
) -> UtilisateurRef:
    utilisateur = await session.get(UtilisateurRef, utilisateur_id)
    if utilisateur is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Utilisateur not found")
    if not utilisateur.actif:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Utilisateur is inactive")
    allowed = (role_libelle, *or_roles)
    has_any = False
    for r in allowed:
        if await user_has_role(session, utilisateur_id, r):
            has_any = True
            break
    if not has_any:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Utilisateur does not have any of the required roles: {', '.join(allowed)}",
        )
    return utilisateur


async def can_access_groupe(
    session: AsyncSession,
    current_user: CurrentUser,
    groupe_id: UUID,
) -> bool:
    if is_responsable_pedagogique(current_user):
        return True
    if not current_user.has_role(ENSEIGNANT):
        return False
    return bool(
        await session.scalar(
            select(
                exists().where(
                    EnseignantGroupe.enseignant_id == current_user.id,
                    EnseignantGroupe.groupe_id == groupe_id,
                )
            )
        )
    )


async def ensure_can_access_groupe(
    session: AsyncSession,
    current_user: CurrentUser,
    groupe_id: UUID,
) -> None:
    if not await can_access_groupe(session, current_user, groupe_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions",
        )


async def can_access_etudiant(
    session: AsyncSession,
    current_user: CurrentUser,
    etudiant_id: UUID,
) -> bool:
    if is_responsable_pedagogique(current_user):
        return True
    if not current_user.has_role(ENSEIGNANT):
        return False
    return bool(
        await session.scalar(
            select(
                exists().where(
                    etudiant_groupes.c.etudiant_id == etudiant_id,
                    etudiant_groupes.c.groupe_id == EnseignantGroupe.groupe_id,
                    EnseignantGroupe.enseignant_id == current_user.id,
                )
            )
        )
    )


async def ensure_can_access_etudiant(
    session: AsyncSession,
    current_user: CurrentUser,
    etudiant_id: UUID,
) -> None:
    if not await can_access_etudiant(session, current_user, etudiant_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions",
        )


async def require_groupe_access(
    groupe_id: UUID,
    current_user: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_replica_session),
) -> CurrentUser:
    await ensure_can_access_groupe(session, current_user, groupe_id)
    return current_user


async def require_etudiant_access(
    etudiant_id: UUID,
    current_user: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_replica_session),
) -> CurrentUser:
    etudiant = await session.get(Etudiant, etudiant_id)
    if etudiant is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Etudiant not found")
    await ensure_can_access_etudiant(session, current_user, etudiant_id)
    return current_user


async def require_etudiant_write_access(
    etudiant_id: UUID,
    current_user: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> CurrentUser:
    etudiant = await session.get(Etudiant, etudiant_id)
    if etudiant is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Etudiant not found")
    await ensure_can_access_etudiant(session, current_user, etudiant_id)
    return current_user
