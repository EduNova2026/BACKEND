from __future__ import annotations

from datetime import date, datetime
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from sqlalchemy import Date, DateTime, Float, Index, String, func
from sqlalchemy.dialects.postgresql import UUID as PgUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..database import Base

if TYPE_CHECKING:
    from .note import Note


class Examen(Base):
    __tablename__ = "examens"
    __table_args__ = (
        Index("ix_examens_enseignement_id", "enseignement_id"),
        Index("ix_examens_code_aurion", "code_aurion"),
    )

    id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), primary_key=True, default=uuid4)
    enseignement_id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), nullable=False)
    nom: Mapped[str] = mapped_column(String(200), nullable=False)
    type: Mapped[str] = mapped_column(String(20), nullable=False, default="examen")
    coefficient: Mapped[float] = mapped_column(Float, nullable=False, default=1.0)
    note_max: Mapped[float] = mapped_column(Float, nullable=False, default=20.0)
    date_examen: Mapped[date | None] = mapped_column(Date, nullable=True)
    code_aurion: Mapped[str | None] = mapped_column(String(100), nullable=True)
    cree_par: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    notes: Mapped[list["Note"]] = relationship(back_populates="examen")
