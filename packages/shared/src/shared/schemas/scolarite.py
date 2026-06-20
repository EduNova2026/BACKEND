from __future__ import annotations

from datetime import date, datetime
from typing import ClassVar, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


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
    semestre: int = Field(default=1, ge=1, le=2)
    coefficient: float = Field(default=1.0, gt=0)


class GroupeUpdate(BaseModel):
    model_config: ClassVar[ConfigDict] = ConfigDict(extra="forbid")

    nom: str | None = None
    promotion_id: UUID | None = None
    semestre: int | None = Field(default=None, ge=1, le=2)
    coefficient: float | None = Field(default=None, gt=0)


class GroupeOut(BaseModel):
    model_config: ClassVar[ConfigDict] = ConfigDict(from_attributes=True)

    id: UUID
    nom: str
    promotion_id: UUID
    semestre: int = 1
    coefficient: float = 1.0


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


class ExamenUpdate(BaseModel):
    model_config: ClassVar[ConfigDict] = ConfigDict(extra="forbid")

    nom: str | None = None
    type: str | None = None
    coefficient: float | None = Field(default=None, gt=0)
    note_max: float | None = Field(default=None, gt=0)
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


# --- Moyenne ---


class MoyenneOut(BaseModel):
    model_config: ClassVar[ConfigDict] = ConfigDict(from_attributes=True)

    moyenne: float | None = None
    semestre: int
    note_count: int
    coefficient_total: float


class MoyenneParEtudiant(BaseModel):
    model_config: ClassVar[ConfigDict] = ConfigDict(from_attributes=True)

    etudiant_id: UUID
    moyenne: float | None = None
    semestre: int
    note_count: int
    coefficient_total: float


# --- Export étudiant ---


class EtudiantExportNoteOut(BaseModel):
    model_config: ClassVar[ConfigDict] = ConfigDict(from_attributes=True)

    examen_id: UUID
    examen_nom: str
    examen_type: str
    examen_coefficient: float
    examen_note_max: float
    examen_date: date | None = None
    note_valeur: float | None = None
    note_absent: bool
    note_motif_absence: str | None = None


class EtudiantExportGroupeOut(BaseModel):
    model_config: ClassVar[ConfigDict] = ConfigDict(from_attributes=True)

    groupe_id: UUID
    groupe_nom: str
    semestre: int
    coefficient: float
    notes: list[EtudiantExportNoteOut]


class EtudiantExportOut(BaseModel):
    model_config: ClassVar[ConfigDict] = ConfigDict(from_attributes=True)

    etudiant_id: UUID
    nom: str
    prenom: str
    promotion_id: UUID | None = None
    promotion_nom: str | None = None
    groupes: list[EtudiantExportGroupeOut]


# --- Risque ---

StatutRisque = Literal["Non évalué", "OK", "Suivre", "Risque"]
ReferenceRisque = Literal["promotion", "groupe", "seuil_10"]


class RisqueOut(BaseModel):
    model_config: ClassVar[ConfigDict] = ConfigDict(from_attributes=True)

    score_risque: int | None = Field(default=None, ge=0, le=100)
    statut: StatutRisque
    moyenne: float | None = None
    moyenne_reference: float | None = None
    ecart_moyenne: float | None = None
    semestre: int
    note_count: int
    coefficient_total: float
    absence_count: int
    evaluation_count: int
    absence_rate: float
    score_notes: int | None = Field(default=None, ge=0, le=100)
    score_absences: int = Field(ge=0, le=100)
    reference_scope: ReferenceRisque
    formule_version: str = "risque-v1"


class RisqueParEtudiant(RisqueOut):
    etudiant_id: UUID
