from __future__ import annotations

from alembic import op

revision = "003_drop_etudiant_utilisateur_fk"
down_revision = "002_etudiant_identity_name"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        op.execute(
            "DO $$ BEGIN "
            "IF EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'etudiants_utilisateur_id_fkey') THEN "
            "ALTER TABLE etudiants DROP CONSTRAINT etudiants_utilisateur_id_fkey; "
            "END IF; "
            "IF EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'uq_etudiants_utilisateur_promotion') THEN "
            "ALTER TABLE etudiants DROP CONSTRAINT uq_etudiants_utilisateur_promotion; "
            "END IF; "
            "IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'uq_etudiants_utilisateur_id') THEN "
            "ALTER TABLE etudiants ADD CONSTRAINT uq_etudiants_utilisateur_id UNIQUE (utilisateur_id); "
            "END IF; "
            "END $$"
        )
        return

    op.drop_constraint("etudiants_utilisateur_id_fkey", "etudiants", type_="foreignkey")
    op.drop_constraint("uq_etudiants_utilisateur_promotion", "etudiants", type_="unique")
    op.create_unique_constraint("uq_etudiants_utilisateur_id", "etudiants", ["utilisateur_id"])


def downgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        op.execute(
            "DO $$ BEGIN "
            "IF EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'uq_etudiants_utilisateur_id') THEN "
            "ALTER TABLE etudiants DROP CONSTRAINT uq_etudiants_utilisateur_id; "
            "END IF; "
            "IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'etudiants_utilisateur_id_fkey') THEN "
            "ALTER TABLE etudiants ADD CONSTRAINT etudiants_utilisateur_id_fkey "
            "FOREIGN KEY (utilisateur_id) REFERENCES utilisateurs(id); "
            "END IF; "
            "IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'uq_etudiants_utilisateur_promotion') THEN "
            "ALTER TABLE etudiants ADD CONSTRAINT uq_etudiants_utilisateur_promotion "
            "UNIQUE (utilisateur_id, promotion_id); "
            "END IF; "
            "END $$"
        )
        return

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
