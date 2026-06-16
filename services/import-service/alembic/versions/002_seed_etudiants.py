from __future__ import annotations

from alembic import op

revision = "002_seed_etudiants"
down_revision = "001_initial"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        CREATE TABLE IF NOT EXISTS enseignements (
            id            UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
            enseignant_id UUID        NOT NULL,
            groupe_id     UUID        NOT NULL,
            matiere_id    UUID        NOT NULL,
            annee_scolaire VARCHAR(9) NOT NULL
        )
    """)


def downgrade() -> None:
    pass
