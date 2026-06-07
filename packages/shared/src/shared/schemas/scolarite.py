from __future__ import annotations

from typing import ClassVar
from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


# --- Promotion ---


class PromotionCreate(BaseModel):
    model_config: ClassVar[ConfigDict] = ConfigDict(extra="forbid")

    nom: str
    annee_scolaire: str


class PromotionUpdate(BaseModel):
    model_config: ClassVar[ConfigDict] = ConfigDict(extra="forbid")

    nom: str | None = None
    annee_scolaire: str | None = None


class PromotionOut(BaseModel):
    model_config: ClassVar[ConfigDict] = ConfigDict(from_attributes=True)

    id: UUID
    nom: str
    annee_scolaire: str


# --- Groupe ---


class GroupeCreate(BaseModel):
    model_config: ClassVar[ConfigDict] = ConfigDict(extra="forbid")

    nom: str
    promotion_id: UUID


class GroupeUpdate(BaseModel):
    model_config: ClassVar[ConfigDict] = ConfigDict(extra="forbid")

    nom: str | None = None
    promotion_id: UUID | None = None


class GroupeOut(BaseModel):
    model_config: ClassVar[ConfigDict] = ConfigDict(from_attributes=True)

    id: UUID
    nom: str
    promotion_id: UUID


# --- Etudiant ---


class EtudiantCreate(BaseModel):
    model_config: ClassVar[ConfigDict] = ConfigDict(extra="forbid")

    nom: str
    prenom: str
    promotion_id: UUID


class EtudiantUpdate(BaseModel):
    model_config: ClassVar[ConfigDict] = ConfigDict(extra="forbid")

    nom: str | None = None
    prenom: str | None = None
    promotion_id: UUID | None = None


class EtudiantOut(BaseModel):
    model_config: ClassVar[ConfigDict] = ConfigDict(from_attributes=True)

    id: UUID
    nom: str
    prenom: str
    promotion_id: UUID
    utilisateur_id: UUID


class EtudiantSearchResponse(BaseModel):
    items: list[EtudiantOut]
    count: int


# --- EtudiantGroupe (join table, no separate PK) ---


class EtudiantGroupeOut(BaseModel):
    model_config: ClassVar[ConfigDict] = ConfigDict(from_attributes=True)

    etudiant_id: UUID
    groupe_id: UUID


class EnseignantGroupeOut(BaseModel):
    model_config: ClassVar[ConfigDict] = ConfigDict(from_attributes=True)

    enseignant_id: UUID
    groupe_id: UUID
    assigned_by: UUID | None = None
    created_at: datetime


class ResponsablePromotionOut(BaseModel):
    model_config: ClassVar[ConfigDict] = ConfigDict(from_attributes=True)

    responsable_id: UUID
    promotion_id: UUID
    assigned_by: UUID | None = None
    created_at: datetime


class UserActivationUpdate(BaseModel):
    model_config: ClassVar[ConfigDict] = ConfigDict(extra="forbid")

    actif: bool


# --- Utilisateur Role Assignment ---


class RoleAssignmentCreate(BaseModel):
    model_config: ClassVar[ConfigDict] = ConfigDict(extra="forbid")

    role_id: UUID


class UtilisateurRoleOut(BaseModel):
    model_config: ClassVar[ConfigDict] = ConfigDict(from_attributes=True)

    utilisateur_id: UUID
    role_id: UUID
    libelle: str | None = None
