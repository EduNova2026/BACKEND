from __future__ import annotations

from datetime import date, datetime
from typing import ClassVar
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
    promotion_id: UUID | None
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


class NoteItemCreate(BaseModel):
    model_config: ClassVar[ConfigDict] = ConfigDict(extra="forbid")

    etudiant_id: UUID
    valeur: float | None = None
    absent: bool = False
    motif_absence: str | None = None


class ExamenCreate(BaseModel):
    model_config: ClassVar[ConfigDict] = ConfigDict(extra="forbid")

    enseignement_id: UUID
    nom: str
    type: str = "examen"
    coefficient: float = 1.0
    note_max: float = 20.0
    date_examen: date | None = None
    code_aurion: str | None = None


class ExamenOut(BaseModel):
    model_config: ClassVar[ConfigDict] = ConfigDict(from_attributes=True)

    id: UUID
    enseignement_id: UUID
    nom: str
    type: str
    coefficient: float
    note_max: float
    date_examen: date | None = None
    code_aurion: str | None = None
    cree_par: UUID
    created_at: datetime


class NoteCreate(NoteItemCreate):
    examen_id: UUID


class NoteBatchCreate(BaseModel):
    model_config: ClassVar[ConfigDict] = ConfigDict(extra="forbid")

    examen_id: UUID
    notes: list[NoteItemCreate]


class NoteUpdate(BaseModel):
    model_config: ClassVar[ConfigDict] = ConfigDict(extra="forbid")

    valeur: float | None = None
    absent: bool | None = None
    motif_absence: str | None = None


class NoteOut(BaseModel):
    model_config: ClassVar[ConfigDict] = ConfigDict(from_attributes=True)

    id: UUID
    etudiant_id: UUID
    examen_id: UUID
    examen: ExamenOut
    valeur: float | None = None
    absent: bool
    motif_absence: str | None = None
    date_saisie: datetime
    saisi_par: UUID


# --- Utilisateur Role Assignment ---


class RoleAssignmentCreate(BaseModel):
    model_config: ClassVar[ConfigDict] = ConfigDict(extra="forbid")

    role_id: UUID


class UtilisateurRoleOut(BaseModel):
    model_config: ClassVar[ConfigDict] = ConfigDict(from_attributes=True)

    utilisateur_id: UUID
    role_id: UUID
    libelle: str | None = None
