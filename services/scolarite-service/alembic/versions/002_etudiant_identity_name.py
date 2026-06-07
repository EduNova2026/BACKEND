from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "002_etudiant_identity_name"
down_revision = "001_initial_scolarite"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("etudiants", sa.Column("nom", sa.String(length=100), nullable=True))
    op.add_column("etudiants", sa.Column("prenom", sa.String(length=100), nullable=True))

    op.execute(
        "UPDATE etudiants "
        "SET nom = lower(trim(utilisateurs.nom)), "
        "prenom = lower(trim(utilisateurs.prenom)) "
        "FROM utilisateurs "
        "WHERE etudiants.utilisateur_id = utilisateurs.id"
    )

    op.alter_column("etudiants", "nom", nullable=False)
    op.alter_column("etudiants", "prenom", nullable=False)
    op.drop_constraint("etudiants_utilisateur_id_fkey", "etudiants", type_="foreignkey")
    op.drop_constraint("uq_etudiants_utilisateur_promotion", "etudiants", type_="unique")
    op.create_unique_constraint(
        "uq_etudiants_utilisateur_id",
        "etudiants",
        ["utilisateur_id"],
    )
    op.create_index("ix_etudiants_promotion_id", "etudiants", ["promotion_id"])
    op.create_index(
        "ix_etudiants_promotion_nom_prenom",
        "etudiants",
        ["promotion_id", "nom", "prenom"],
    )


def downgrade() -> None:
    op.drop_index("ix_etudiants_promotion_nom_prenom", table_name="etudiants")
    op.drop_index("ix_etudiants_promotion_id", table_name="etudiants")

    op.drop_constraint("uq_etudiants_utilisateur_id", "etudiants", type_="unique")
    op.create_foreign_key(
        "etudiants_utilisateur_id_fkey",
        "etudiants",
        "utilisateurs",
        ["utilisateur_id"],
        ["id"],
    )
    op.create_unique_constraint(
        "uq_etudiants_utilisateur_promotion",
        "etudiants",
        ["utilisateur_id", "promotion_id"],
    )

    op.drop_column("etudiants", "prenom")
    op.drop_column("etudiants", "nom")
