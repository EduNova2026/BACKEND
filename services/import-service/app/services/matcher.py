from __future__ import annotations

import re
import unicodedata
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.refs import EtudiantGroupeRef, EtudiantRef


# Même logique de normalisation que scolarite-service (routers/etudiants.py::normalize_name)
# Les noms sont stockés en minuscules sans accents dans la table etudiants.
# On applique la même transformation sur les noms venant du CSV avant de chercher en base.
def _normalize(value: str) -> str:
    without_accents = "".join(
        char
        for char in unicodedata.normalize("NFKD", value.strip().casefold())
        if not unicodedata.combining(char)
    )
    return re.sub(r"[\s\-']+", " ", without_accents).strip()


async def find_etudiant_by_nom_prenom(
    session: AsyncSession,
    nom: str,
    prenom: str,
) -> UUID | None:
    result = await session.execute(
        select(EtudiantRef.id).where(
            EtudiantRef.nom == _normalize(nom),
            EtudiantRef.prenom == _normalize(prenom),
        )
    )
    return result.scalars().first()


async def find_etudiant_by_nom_prenom_in_groupe(
    session: AsyncSession,
    nom: str,
    prenom: str,
    groupe_id: UUID,
) -> UUID | None:
    result = await session.execute(
        select(EtudiantRef.id)
        .join(EtudiantGroupeRef, EtudiantGroupeRef.etudiant_id == EtudiantRef.id)
        .where(
            EtudiantRef.nom == _normalize(nom),
            EtudiantRef.prenom == _normalize(prenom),
            EtudiantGroupeRef.groupe_id == groupe_id,
        )
    )
    return result.scalars().first()


async def is_etudiant_in_groupe(
    session: AsyncSession,
    etudiant_id: UUID,
    groupe_id: UUID,
) -> bool:
    result = await session.execute(
        select(EtudiantGroupeRef).where(
            EtudiantGroupeRef.etudiant_id == etudiant_id,
            EtudiantGroupeRef.groupe_id == groupe_id,
        )
    )
    return result.first() is not None
