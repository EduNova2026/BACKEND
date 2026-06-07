from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "007_add_notes"
down_revision = "006_roles_assignments"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "examens",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("enseignement_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("nom", sa.String(200), nullable=False),
        sa.Column("type", sa.String(20), nullable=False, server_default="examen"),
        sa.Column("coefficient", sa.Float(), nullable=False, server_default="1.0"),
        sa.Column("note_max", sa.Float(), nullable=False, server_default="20.0"),
        sa.Column("date_examen", sa.Date(), nullable=True),
        sa.Column("code_aurion", sa.String(100), nullable=True),
        sa.Column("cree_par", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )
    op.create_index("ix_examens_enseignement_id", "examens", ["enseignement_id"])
    op.create_index("ix_examens_code_aurion", "examens", ["code_aurion"])

    op.create_table(
        "notes",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("etudiant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("examen_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("valeur", sa.Float(), nullable=True),
        sa.Column("absent", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("motif_absence", sa.Text(), nullable=True),
        sa.Column(
            "date_saisie",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("saisi_par", postgresql.UUID(as_uuid=True), nullable=False),
        sa.ForeignKeyConstraint(["etudiant_id"], ["etudiants.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["examen_id"], ["examens.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("etudiant_id", "examen_id", name="uq_note_etudiant_examen"),
    )
    op.create_index("ix_notes_etudiant_id", "notes", ["etudiant_id"])
    op.create_index("ix_notes_examen_id", "notes", ["examen_id"])


def downgrade() -> None:
    op.drop_index("ix_notes_examen_id", table_name="notes")
    op.drop_index("ix_notes_etudiant_id", table_name="notes")
    op.drop_table("notes")
    op.drop_index("ix_examens_code_aurion", table_name="examens")
    op.drop_index("ix_examens_enseignement_id", table_name="examens")
    op.drop_table("examens")
