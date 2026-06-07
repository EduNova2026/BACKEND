from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB, UUID

revision = "001_initial"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "imports_csv",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("importe_par", UUID(as_uuid=True), nullable=False),
        sa.Column("nom_fichier", sa.String(255), nullable=False),
        sa.Column("type_import", sa.String(30), nullable=True),
        sa.Column("statut", sa.String(20), nullable=False, server_default="en_cours"),
        sa.Column("lignes_total", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("lignes_ok", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("lignes_erreur", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("erreurs_detail", JSONB(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )


def downgrade() -> None:
    op.drop_table("imports_csv")
