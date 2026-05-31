from sqlalchemy import Column, ForeignKey, Table
from sqlalchemy.dialects.postgresql import UUID as PgUUID

from ..database import Base


user_roles = Table(
    "utilisateur_roles",
    Base.metadata,
    Column("utilisateur_id", PgUUID(as_uuid=True), ForeignKey("utilisateurs.id"), primary_key=True),
    Column("role_id", PgUUID(as_uuid=True), ForeignKey("roles.id"), primary_key=True),
)
