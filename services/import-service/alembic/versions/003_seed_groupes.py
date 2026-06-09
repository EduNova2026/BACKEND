"""003_seed_groupes

SEED DES GROUPES POUR LA DÉMO — import-service
-----------------------------------------------
Crée un groupe de démo et lie :
  - les 25 étudiants de la promo ISEN 2026 à ce groupe (etudiant_groupes)
  - l'enseignant de test à ce groupe (enseignant_groupes)

Pourquoi ici ?
  scolarite-service vérifie via ensure_can_access_etudiant que l'enseignant
  appartient à un groupe qui contient l'étudiant avant de créer des notes.
  Sans ce seed, l'import renvoie "Insufficient permissions" même avec un JWT valide.

L'UUID de l'enseignant (_ENSEIGNANT_ID) correspond à l'utilisateur de test
présent dans la table utilisateurs (role enseignant).
"""

from __future__ import annotations

from alembic import op

revision = "003_seed_groupes"
down_revision = "002_seed_etudiants"
branch_labels = None
depends_on = None

_PROMO_ID     = "aaaaaaaa-0000-0000-0000-000000000001"
_GROUPE_ID    = "aaaaaaaa-0000-0000-0000-000000000003"
# UUID issu du JWT de l'enseignant de test (mouhamad.damen@student.junia.com)
_ENSEIGNANT_ID = "5fea5f5f-b2ba-4f23-94f9-d2546ce04816"


def upgrade() -> None:
    # 1. Créer le groupe de démo, lié à la promotion ISEN 2026
    op.execute(f"""
        INSERT INTO groupes (id, nom, promotion_id)
        VALUES ('{_GROUPE_ID}', 'Groupe A', '{_PROMO_ID}')
        ON CONFLICT DO NOTHING
    """)

    # 2. Lier tous les étudiants de la promo à ce groupe
    # (les étudiants ont été insérés en migration 002 avec le même promotion_id)
    op.execute(f"""
        INSERT INTO etudiant_groupes (etudiant_id, groupe_id)
        SELECT id, '{_GROUPE_ID}'
        FROM etudiants
        WHERE promotion_id = '{_PROMO_ID}'
        ON CONFLICT DO NOTHING
    """)

    # 3. Lier l'enseignant de test au groupe
    # → permet à ensure_can_access_etudiant de passer pour cet enseignant
    op.execute(f"""
        INSERT INTO enseignant_groupes (enseignant_id, groupe_id)
        VALUES ('{_ENSEIGNANT_ID}', '{_GROUPE_ID}')
        ON CONFLICT DO NOTHING
    """)


def downgrade() -> None:
    op.execute(
        f"DELETE FROM enseignant_groupes "
        f"WHERE enseignant_id = '{_ENSEIGNANT_ID}' AND groupe_id = '{_GROUPE_ID}'"
    )
    op.execute(f"DELETE FROM etudiant_groupes WHERE groupe_id = '{_GROUPE_ID}'")
    op.execute(f"DELETE FROM groupes WHERE id = '{_GROUPE_ID}'")
