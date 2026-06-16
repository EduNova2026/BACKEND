from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "010_add_semestre_to_groupes"
down_revision = "009_allow_unassigned_etudiants"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "groupes",
        sa.Column("semestre", sa.Integer(), nullable=False, server_default="1"),
    )


def downgrade() -> None:
    op.drop_column("groupes", "semestre")
