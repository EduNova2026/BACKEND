from __future__ import annotations

from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from sqlalchemy import ForeignKey
from sqlalchemy.dialects.postgresql import UUID as PgUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..database import Base

if TYPE_CHECKING:
    from .groupe import Groupe
    from .promotion import Promotion


class Etudiant(Base):
    __tablename__ = "etudiants"

    id: Mapped[UUID] = mapped_column(
        PgUUID(as_uuid=True), primary_key=True, default=uuid4
    )
    utilisateur_id: Mapped[UUID] = mapped_column(
        PgUUID(as_uuid=True), nullable=False, index=True
    )
    promotion_id: Mapped[UUID] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("promotions.id"), nullable=False
    )

    promotion: Mapped["Promotion"] = relationship(back_populates="etudiants")
    groupes: Mapped[list["Groupe"]] = relationship(
        secondary="etudiant_groupes",
        back_populates="etudiants",
        lazy="selectin",
    )
