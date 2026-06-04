"""001_initial_scolarite

Creation des tables gerees par scolarite-service :
  - promotions
  - groupes
  - etudiants
  - etudiant_groupes

La FK etudiants.utilisateur_id reference utilisateurs.id qui
est cree par la migration 001_initial du identity-service.
Cette migration DOIT etre executee APRES celle d'identity-service.
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

revision = "001_initial_scolarite"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "promotions",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("nom", sa.String(length=100), nullable=False),
        sa.Column("annee_scolaire", sa.String(length=9), nullable=False),
    )
    op.create_unique_constraint(
        "uq_promotions_nom_annee",
        "promotions",
        ["nom", "annee_scolaire"],
    )

    op.create_table(
        "groupes",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("nom", sa.String(length=100), nullable=False),
        sa.Column(
            "promotion_id",
            UUID(as_uuid=True),
            sa.ForeignKey("promotions.id"),
            nullable=False,
        ),
    )
    op.create_unique_constraint(
        "uq_groupes_promotion_nom",
        "groupes",
        ["promotion_id", "nom"],
    )

    op.create_table(
        "etudiants",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("utilisateur_id", UUID(as_uuid=True), nullable=False),
        sa.Column(
            "promotion_id",
            UUID(as_uuid=True),
            sa.ForeignKey("promotions.id"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["utilisateur_id"],
            ["utilisateurs.id"],
        ),
    )
    op.create_index(
        "ix_etudiants_utilisateur_id",
        "etudiants",
        ["utilisateur_id"],
    )
    op.create_unique_constraint(
        "uq_etudiants_utilisateur_promotion",
        "etudiants",
        ["utilisateur_id", "promotion_id"],
    )

    op.create_table(
        "etudiant_groupes",
        sa.Column(
            "etudiant_id",
            UUID(as_uuid=True),
            sa.ForeignKey("etudiants.id"),
            nullable=False,
        ),
        sa.Column(
            "groupe_id",
            UUID(as_uuid=True),
            sa.ForeignKey("groupes.id"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("etudiant_id", "groupe_id"),
    )


def downgrade() -> None:
    op.drop_table("etudiant_groupes")
    op.drop_constraint("uq_etudiants_utilisateur_promotion", "etudiants", type_="unique")
    op.drop_index("ix_etudiants_utilisateur_id", table_name="etudiants")
    op.drop_table("etudiants")
    op.drop_table("groupes")
    op.drop_table("promotions")
