from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "004_normalize_etudiant_names"
down_revision = "003_drop_etudiant_utilisateur_fk"
branch_labels = None
depends_on = None


def _column_names() -> set[str]:
    bind = op.get_bind()
    return {column["name"] for column in sa.inspect(bind).get_columns("etudiants")}


def _index_names() -> set[str]:
    bind = op.get_bind()
    return {index["name"] for index in sa.inspect(bind).get_indexes("etudiants")}


def upgrade() -> None:
    columns = _column_names()
    indexes = _index_names()
    has_normalized_columns = {"nom_normalise", "prenom_normalise"}.issubset(columns)

    if "ix_etudiants_promotion_nom_prenom" in indexes and has_normalized_columns:
        op.drop_index("ix_etudiants_promotion_nom_prenom", table_name="etudiants")

    if has_normalized_columns:
        op.execute(
            "UPDATE etudiants "
            "SET nom = COALESCE(nom_normalise, nom), "
            "prenom = COALESCE(prenom_normalise, prenom)"
        )
        with op.batch_alter_table("etudiants") as batch_op:
            batch_op.drop_column("prenom_normalise")
            batch_op.drop_column("nom_normalise")

    if "ix_etudiants_promotion_nom_prenom" not in _index_names():
        op.create_index(
            "ix_etudiants_promotion_nom_prenom",
            "etudiants",
            ["promotion_id", "nom", "prenom"],
        )


def downgrade() -> None:
    columns = _column_names()
    indexes = _index_names()

    if "ix_etudiants_promotion_nom_prenom" in indexes:
        op.drop_index("ix_etudiants_promotion_nom_prenom", table_name="etudiants")

    with op.batch_alter_table("etudiants") as batch_op:
        if "nom_normalise" not in columns:
            batch_op.add_column(sa.Column("nom_normalise", sa.String(length=100), nullable=True))
        if "prenom_normalise" not in columns:
            batch_op.add_column(sa.Column("prenom_normalise", sa.String(length=100), nullable=True))

    op.execute(
        "UPDATE etudiants "
        "SET nom_normalise = COALESCE(nom_normalise, nom), "
        "prenom_normalise = COALESCE(prenom_normalise, prenom)"
    )

    with op.batch_alter_table("etudiants") as batch_op:
        batch_op.alter_column("nom_normalise", nullable=False)
        batch_op.alter_column("prenom_normalise", nullable=False)

    op.create_index(
        "ix_etudiants_promotion_nom_prenom",
        "etudiants",
        ["promotion_id", "nom_normalise", "prenom_normalise"],
    )
