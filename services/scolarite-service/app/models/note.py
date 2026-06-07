from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Index, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID as PgUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..database import Base

if TYPE_CHECKING:
    from .etudiant import Etudiant
    from .examen import Examen


class Note(Base):
    __tablename__ = "notes"
    __table_args__ = (
        UniqueConstraint("etudiant_id", "examen_id", name="uq_note_etudiant_examen"),
        Index("ix_notes_etudiant_id", "etudiant_id"),
        Index("ix_notes_examen_id", "examen_id"),
    )

    id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), primary_key=True, default=uuid4)
    etudiant_id: Mapped[UUID] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("etudiants.id", ondelete="CASCADE"), nullable=False
    )
    examen_id: Mapped[UUID] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("examens.id", ondelete="CASCADE"), nullable=False
    )
    valeur: Mapped[float | None] = mapped_column(Float, nullable=True)
    absent: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    motif_absence: Mapped[str | None] = mapped_column(Text, nullable=True)
    date_saisie: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    saisi_par: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), nullable=False)

    etudiant: Mapped["Etudiant"] = relationship(back_populates="notes")
    examen: Mapped["Examen"] = relationship(back_populates="notes", lazy="selectin")
