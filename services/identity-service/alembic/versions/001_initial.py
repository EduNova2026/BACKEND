from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID


revision = "001_initial"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "utilisateurs",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("mdp", sa.String(length=255), nullable=True),
        sa.Column("nom", sa.String(length=100), nullable=False),
        sa.Column("prenom", sa.String(length=100), nullable=False),
        sa.Column("actif", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("premier_login", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )
    op.create_index(
        "ix_utilisateurs_email",
        "utilisateurs",
        ["email"],
        unique=True,
    )

    op.create_table(
        "roles",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("libelle", sa.String(length=50), nullable=False),
        sa.UniqueConstraint("libelle", name="uq_roles_libelle"),
    )

    op.create_table(
        "utilisateur_roles",
        sa.Column(
            "utilisateur_id",
            UUID(as_uuid=True),
            sa.ForeignKey("utilisateurs.id"),
            nullable=False,
        ),
        sa.Column(
            "role_id",
            UUID(as_uuid=True),
            sa.ForeignKey("roles.id"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("utilisateur_id", "role_id", name="pk_utilisateur_roles"),
    )


def downgrade() -> None:
    op.drop_table("utilisateur_roles")
    op.drop_index("ix_utilisateurs_email", table_name="utilisateurs")
    op.drop_table("roles")
    op.drop_table("utilisateurs")
