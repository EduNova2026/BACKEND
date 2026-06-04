from __future__ import annotations

from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import DateTime, Integer, String, func
from sqlalchemy.dialects.postgresql import JSONB, UUID as PgUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class ImportJob(Base):
    __tablename__ = "imports_csv"

    id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), primary_key=True, default=uuid4)
    importe_par: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), nullable=False)
    nom_fichier: Mapped[str] = mapped_column(String(255), nullable=False)
    type_import: Mapped[str | None] = mapped_column(String(30), nullable=True)
    statut: Mapped[str] = mapped_column(String(20), nullable=False, default="en_cours")
    lignes_total: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    lignes_ok: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    lignes_erreur: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    erreurs_detail: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )