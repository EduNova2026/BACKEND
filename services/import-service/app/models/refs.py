from __future__ import annotations

from uuid import UUID

from sqlalchemy import String
from sqlalchemy.dialects.postgresql import UUID as PgUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import RefBase


class UtilisateurRef(RefBase):
    """Table utilisateurs — possédée par identity-service. READ-ONLY ici."""
    __tablename__ = "utilisateurs"

    id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), primary_key=True)
    nom: Mapped[str] = mapped_column(String(100), nullable=False)
    prenom: Mapped[str] = mapped_column(String(100), nullable=False)
    email: Mapped[str] = mapped_column(String(255), nullable=False)


class EtudiantRef(RefBase):
    """Table etudiants — possédée par user-service. READ-ONLY ici."""
    __tablename__ = "etudiants"

    id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), primary_key=True)
    utilisateur_id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), nullable=False)
    promotion_id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), nullable=False)


class EnseignementRef(RefBase):
    """Table enseignements — possédée par user-service. READ-ONLY ici."""
    __tablename__ = "enseignements"

    id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), primary_key=True)
    enseignant_id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), nullable=False)
    groupe_id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), nullable=False)
    matiere_id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), nullable=False)
    annee_scolaire: Mapped[str] = mapped_column(String(9), nullable=False)