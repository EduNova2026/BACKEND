from __future__ import annotations

from alembic import op

revision = "009_allow_unassigned_etudiants"
down_revision = "008_remove_note_appreciation"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TABLE etudiants ALTER COLUMN promotion_id DROP NOT NULL")


def downgrade() -> None:
    op.execute("DELETE FROM etudiant_groupes WHERE etudiant_id IN (SELECT id FROM etudiants WHERE promotion_id IS NULL)")
    op.execute("DELETE FROM etudiants WHERE promotion_id IS NULL")
    op.execute("ALTER TABLE etudiants ALTER COLUMN promotion_id SET NOT NULL")
