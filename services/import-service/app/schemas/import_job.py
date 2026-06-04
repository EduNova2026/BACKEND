from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class ImportJobOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    nom_fichier: str
    type_import: str | None
    statut: str
    lignes_total: int
    lignes_ok: int
    lignes_erreur: int
    erreurs_detail: list[dict[str, Any]] | None
    created_at: datetime