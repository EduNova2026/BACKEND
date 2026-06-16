from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "011_add_coefficient_to_groupes"
down_revision = "010_add_semestre_to_groupes"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "groupes",
        sa.Column("coefficient", sa.Float(), nullable=False, server_default="1.0"),
    )


def downgrade() -> None:
    op.drop_column("groupes", "coefficient")
