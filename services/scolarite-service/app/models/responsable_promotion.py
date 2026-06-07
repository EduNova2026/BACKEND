from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import DateTime, ForeignKey, Index, func
from sqlalchemy.dialects.postgresql import UUID as PgUUID
from sqlalchemy.orm import Mapped, mapped_column

from ..database import Base


class ResponsablePromotion(Base):
    __tablename__ = "responsable_promotions"

    responsable_id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), primary_key=True)
    promotion_id: Mapped[UUID] = mapped_column(
        PgUUID(as_uuid=True),
        ForeignKey("promotions.id", ondelete="CASCADE"),
        primary_key=True,
    )
    assigned_by: Mapped[UUID | None] = mapped_column(PgUUID(as_uuid=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    __table_args__ = (Index("ix_responsable_promotions_responsable_id", "responsable_id"),)
