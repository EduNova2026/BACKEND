from __future__ import annotations

from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import Boolean, DateTime, Float, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID as PgUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class Note(Base):
    __tablename__ = "notes"
    __table_args__ = (
        UniqueConstraint("etudiant_id", "examen_id", name="uq_note_etudiant_examen"),
    )

    id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), primary_key=True, default=uuid4)
    etudiant_id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), nullable=False)
    examen_id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), nullable=False)
    matiere_id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), nullable=False)
    valeur: Mapped[float | None] = mapped_column(Float, nullable=True)
    absent: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    motif_absence: Mapped[str | None] = mapped_column(Text, nullable=True)
    appreciation: Mapped[str | None] = mapped_column(Text, nullable=True)
    date_import: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    saisi_par: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), nullable=False)