from __future__ import annotations

from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from sqlalchemy import String
from sqlalchemy.dialects.postgresql import UUID as PgUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..database import Base

if TYPE_CHECKING:
    from .groupe import Groupe
    from .etudiant import Etudiant


class Promotion(Base):
    __tablename__ = "promotions"

    id: Mapped[UUID] = mapped_column(
        PgUUID(as_uuid=True), primary_key=True, default=uuid4
    )
    nom: Mapped[str] = mapped_column(String(100), nullable=False)
    annee_scolaire: Mapped[str] = mapped_column(String(9), nullable=False)

    groupes: Mapped[list["Groupe"]] = relationship(
        back_populates="promotion", lazy="selectin"
    )
    etudiants: Mapped[list["Etudiant"]] = relationship(
        back_populates="promotion", lazy="selectin"
    )
