from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel, ConfigDict


class RoleOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    libelle: str


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    email: str
    nom: str
    prenom: str
    roles: list[str]
    actif: bool
    premier_login: bool


class UserCreate(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    email: str
    mdp: str
    nom: str
    prenom: str
    actif: bool = True
    premier_login: bool = True
