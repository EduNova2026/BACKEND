from __future__ import annotations

from alembic import op

revision = "008_remove_note_appreciation"
down_revision = "007_add_notes"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TABLE notes DROP COLUMN IF EXISTS appreciation")


def downgrade() -> None:
    op.execute("ALTER TABLE notes ADD COLUMN IF NOT EXISTS appreciation TEXT")
