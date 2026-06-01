from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel, ConfigDict


class LigneErreur(BaseModel):
    ligne: int
    nom: str
    prenom: str
    raison: str


class NoteOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    etudiant_id: UUID
    examen_id: UUID
    matiere_id: UUID
    valeur: float | None
    absent: bool
    motif_absence: str | None
    appreciation: str | None