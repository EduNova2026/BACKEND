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

    op.create_table(
        "examens",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("enseignement_id", UUID(as_uuid=True), nullable=False),
        sa.Column("nom", sa.String(200), nullable=False),
        sa.Column("type", sa.String(20), nullable=False, server_default="examen"),
        sa.Column("coefficient", sa.Float(), nullable=False, server_default="1.0"),
        sa.Column("note_max", sa.Float(), nullable=False, server_default="20.0"),
        sa.Column("date_examen", sa.Date(), nullable=True),
        sa.Column("code_aurion", sa.String(100), nullable=True),
        sa.Column("cree_par", UUID(as_uuid=True), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )

    op.create_table(
        "notes",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("etudiant_id", UUID(as_uuid=True), nullable=False),
        sa.Column("examen_id", UUID(as_uuid=True), nullable=False),
        sa.Column("matiere_id", UUID(as_uuid=True), nullable=False),
        sa.Column("valeur", sa.Float(), nullable=True),
        sa.Column("absent", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("motif_absence", sa.Text(), nullable=True),
        sa.Column("appreciation", sa.Text(), nullable=True),
        sa.Column(
            "date_import",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column("saisi_par", UUID(as_uuid=True), nullable=False),
        sa.UniqueConstraint("etudiant_id", "examen_id", name="uq_note_etudiant_examen"),
    )


def downgrade() -> None:
    op.drop_table("notes")
    op.drop_table("examens")
    op.drop_table("imports_csv")