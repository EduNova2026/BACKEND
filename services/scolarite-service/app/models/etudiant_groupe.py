from sqlalchemy import Column, ForeignKey, Index, Table
from sqlalchemy.dialects.postgresql import UUID as PgUUID

from ..database import Base

etudiant_groupes = Table(
    "etudiant_groupes",
    Base.metadata,
    Column(
        "etudiant_id",
        PgUUID(as_uuid=True),
        ForeignKey("etudiants.id"),
        primary_key=True,
    ),
    Column(
        "groupe_id",
        PgUUID(as_uuid=True),
        ForeignKey("groupes.id"),
        primary_key=True,
    ),
    Index("ix_etudiant_groupes_groupe_id", "groupe_id"),
)
