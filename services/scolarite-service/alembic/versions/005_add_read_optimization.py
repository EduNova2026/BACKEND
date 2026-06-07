from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "005_read_optimization_indexes"
down_revision = "004_normalize_etudiant_names"
branch_labels = None
depends_on = None


def _index_names(table_name: str) -> set[str]:
    bind = op.get_bind()
    return {index["name"] for index in sa.inspect(bind).get_indexes(table_name)}


def upgrade() -> None:
    promotion_indexes = _index_names("promotions")
    if "ix_promotions_nom" not in promotion_indexes:
        op.create_index("ix_promotions_nom", "promotions", ["nom"])

    groupe_indexes = _index_names("groupes")
    if "ix_groupes_promotion_id" not in groupe_indexes:
        op.create_index("ix_groupes_promotion_id", "groupes", ["promotion_id"])
    if "ix_groupes_nom" not in groupe_indexes:
        op.create_index("ix_groupes_nom", "groupes", ["nom"])

    etudiant_indexes = _index_names("etudiants")
    if "ix_etudiants_promotion_id" not in etudiant_indexes:
        op.create_index("ix_etudiants_promotion_id", "etudiants", ["promotion_id"])
    if "ix_etudiants_nom_prenom" not in etudiant_indexes:
        op.create_index("ix_etudiants_nom_prenom", "etudiants", ["nom", "prenom"])

    etudiant_groupe_indexes = _index_names("etudiant_groupes")
    if "ix_etudiant_groupes_groupe_id" not in etudiant_groupe_indexes:
        op.create_index(
            "ix_etudiant_groupes_groupe_id",
            "etudiant_groupes",
            ["groupe_id"],
        )


def downgrade() -> None:
    etudiant_groupe_indexes = _index_names("etudiant_groupes")
    if "ix_etudiant_groupes_groupe_id" in etudiant_groupe_indexes:
        op.drop_index("ix_etudiant_groupes_groupe_id", table_name="etudiant_groupes")

    etudiant_indexes = _index_names("etudiants")
    if "ix_etudiants_nom_prenom" in etudiant_indexes:
        op.drop_index("ix_etudiants_nom_prenom", table_name="etudiants")
    if "ix_etudiants_promotion_id" in etudiant_indexes:
        op.drop_index("ix_etudiants_promotion_id", table_name="etudiants")

    groupe_indexes = _index_names("groupes")
    if "ix_groupes_nom" in groupe_indexes:
        op.drop_index("ix_groupes_nom", table_name="groupes")
    if "ix_groupes_promotion_id" in groupe_indexes:
        op.drop_index("ix_groupes_promotion_id", table_name="groupes")

    promotion_indexes = _index_names("promotions")
    if "ix_promotions_nom" in promotion_indexes:
        op.drop_index("ix_promotions_nom", table_name="promotions")
