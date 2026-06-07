from __future__ import annotations

from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from sqlalchemy import ForeignKey, Index, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID as PgUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..database import Base

if TYPE_CHECKING:
    from .etudiant import Etudiant
    from .promotion import Promotion


class Groupe(Base):
    __tablename__ = "groupes"

    id: Mapped[UUID] = mapped_column(
        PgUUID(as_uuid=True), primary_key=True, default=uuid4
    )
    nom: Mapped[str] = mapped_column(String(100), nullable=False)
    promotion_id: Mapped[UUID] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("promotions.id"), nullable=False
    )

    __table_args__ = (
        UniqueConstraint("promotion_id", "nom", name="uq_groupes_promotion_nom"),
        Index("ix_groupes_promotion_id", "promotion_id"),
        Index("ix_groupes_nom", "nom"),
    )

    promotion: Mapped["Promotion"] = relationship(back_populates="groupes")
    etudiants: Mapped[list["Etudiant"]] = relationship(
        secondary="etudiant_groupes",
        back_populates="groupes",
        lazy="selectin",
    )
