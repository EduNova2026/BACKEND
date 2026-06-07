from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import DateTime, ForeignKey, Index, func
from sqlalchemy.dialects.postgresql import UUID as PgUUID
from sqlalchemy.orm import Mapped, mapped_column

from ..database import Base


class EnseignantGroupe(Base):
    __tablename__ = "enseignant_groupes"

    enseignant_id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), primary_key=True)
    groupe_id: Mapped[UUID] = mapped_column(
        PgUUID(as_uuid=True),
        ForeignKey("groupes.id", ondelete="CASCADE"),
        primary_key=True,
    )
    assigned_by: Mapped[UUID | None] = mapped_column(PgUUID(as_uuid=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    __table_args__ = (Index("ix_enseignant_groupes_enseignant_id", "enseignant_id"),)
