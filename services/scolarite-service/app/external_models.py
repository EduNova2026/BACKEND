"""Stubs read-only pour les tables gerees par identity-service.

Ces modeles utilisent une metadata separee (ExternalBase) pour que Alembic
ne tente jamais de creer, modifier ou supprimer ces tables. Ils servent
uniquement a lire/ecrire les donnees depuis le runtime SQLAlchemy.
"""

from __future__ import annotations

from sqlalchemy import Boolean, Column, MetaData, String, Table
from sqlalchemy.dialects.postgresql import UUID as PgUUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

external_metadata = MetaData()


class ExternalBase(DeclarativeBase):
    metadata = external_metadata


class UtilisateurRef(ExternalBase):
    __tablename__ = "utilisateurs"

    id: Mapped[str] = mapped_column(PgUUID(as_uuid=True), primary_key=True)
    email: Mapped[str] = mapped_column(String, nullable=False)
    nom: Mapped[str] = mapped_column(String, nullable=False)
    prenom: Mapped[str] = mapped_column(String, nullable=False)
    actif: Mapped[bool] = mapped_column(Boolean, nullable=False)


class RoleRef(ExternalBase):
    __tablename__ = "roles"

    id: Mapped[str] = mapped_column(PgUUID(as_uuid=True), primary_key=True)
    libelle: Mapped[str] = mapped_column(String, nullable=False)


# Table de jointure utilisateur_roles (pas un modele ORM, mais une Table SQLAlchemy)
utilisateur_roles = Table(
    "utilisateur_roles",
    external_metadata,
    Column("utilisateur_id", PgUUID(as_uuid=True), primary_key=True),
    Column("role_id", PgUUID(as_uuid=True), primary_key=True),
)
