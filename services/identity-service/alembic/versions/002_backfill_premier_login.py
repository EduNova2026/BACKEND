from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "002_backfill_premier_login"
down_revision = "001_initial"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.alter_column("utilisateurs", "mdp", existing_type=sa.String(length=255), nullable=True)
    op.execute("UPDATE utilisateurs SET mdp = null")
    op.execute("UPDATE utilisateurs SET premier_login = false WHERE actif = true")


def downgrade() -> None:
    op.execute("UPDATE utilisateurs SET premier_login = true WHERE actif = true")
    op.execute("UPDATE utilisateurs SET mdp = '' WHERE mdp IS NULL")
    op.alter_column("utilisateurs", "mdp", existing_type=sa.String(length=255), nullable=False)
