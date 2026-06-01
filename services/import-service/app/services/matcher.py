from __future__ import annotations

from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.refs import EtudiantRef, UtilisateurRef


async def find_etudiant_by_nom_prenom(
    session: AsyncSession,
    nom: str,
    prenom: str,
) -> UUID | None:
    """Cherche un étudiant par nom + prénom (insensible à la casse).

    Retourne l'etudiant.id si trouvé, None sinon.
    """
    result = await session.execute(
        select(EtudiantRef)
        .join(UtilisateurRef, UtilisateurRef.id == EtudiantRef.utilisateur_id)
        .where(
            func.upper(UtilisateurRef.nom) == nom.strip().upper(),
            func.upper(UtilisateurRef.prenom) == prenom.strip().upper(),
        )
    )
    etudiant = result.scalar_one_or_none()
    return etudiant.id if etudiant is not None else None