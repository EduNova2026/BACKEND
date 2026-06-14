"""002_seed_etudiants

SEED DE DONNÉES INITIALES — import-service
-------------------------------------------
Ce fichier insère les données de base nécessaires au fonctionnement de l'import CSV.
Il ne crée PAS de tables (c'est le rôle des autres services).
Il INSERT uniquement des données dans des tables déjà existantes (créées par scolarite-service).

Tables concernées (possédées par scolarite-service, pas par nous) :
  - promotions  : on insère la promo ISEN 2026
  - etudiants   : on insère les 25 étudiants du fichier Aurion

Pourquoi ici et pas dans scolarite-service ?
  - Ces étudiants sont les données métier spécifiques à notre démo/projet
  - On ne veut pas toucher au code d'un autre membre de l'équipe
  - Cette migration est idempotente (ON CONFLICT DO NOTHING) : safe à relancer

Format des noms :
  - Stockés en minuscules sans accents (normalisés par scolarite-service)
  - Exemple : "Inès" → "ines", "EL MANSOURI" → "el mansouri"
  - Le matcher (matcher.py) applique la même normalisation sur les noms du CSV
"""

from __future__ import annotations

from alembic import op

revision = "002_seed_etudiants"
down_revision = "001_initial"
branch_labels = None
depends_on = None

# UUID fixe pour la promotion — ne pas changer, référencé par les étudiants
_PROMO_ID = "aaaaaaaa-0000-0000-0000-000000000001"

# 25 étudiants du fichier "Fichier Aurion.csv" — noms normalisés (minuscules, sans accents)
_ETUDIANTS = [
    ("amari",        "amine"),
    ("bachiri",      "sarah"),
    ("belkacem",     "yanis"),
    ("benali",       "ines"),
    ("bertrand",     "noe"),
    ("bouaziz",      "lina"),
    ("caron",        "mila"),
    ("cherif",       "rayan"),
    ("dumont",       "clara"),
    ("el mansouri",  "nora"),
    ("faure",        "mehdi"),
    ("garnier",      "emma"),
    ("haddad",       "adam"),
    ("kaci",         "aya"),
    ("laurent",      "jules"),
    ("leblanc",      "yasmine"),
    ("lenoir",       "nassim"),
    ("leroy",        "sofia"),
    ("martin",       "hugo"),
    ("moreau",       "camille"),
    ("nacer",        "ilyes"),
    ("perrin",       "lea"),
    ("rousseau",     "malik"),
    ("simon",        "chloe"),
    ("vincent",      "paul"),
]


def upgrade() -> None:
    # Création de la table enseignements si elle n'existe pas encore.
    # Cette table sera à terme possédée par un autre service (programme-service ou scolarite-service).
    # On utilise IF NOT EXISTS pour éviter tout conflit si l'autre service la crée aussi.
    op.execute("""
        CREATE TABLE IF NOT EXISTS enseignements (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            enseignant_id UUID NOT NULL,
            groupe_id UUID NOT NULL,
            matiere_id UUID NOT NULL,
            annee_scolaire VARCHAR(9) NOT NULL
        )
    """)

    # Enseignement de démo — UUID fixe pour pouvoir l'utiliser dans les tests
    op.execute(f"""
        INSERT INTO enseignements (id, enseignant_id, groupe_id, matiere_id, annee_scolaire)
        VALUES (
            'ccd17754-7d12-4d44-a642-99a5f2be6b0b',
            'aaaaaaaa-0000-0000-0000-000000000002',
            'aaaaaaaa-0000-0000-0000-000000000003',
            'aaaaaaaa-0000-0000-0000-000000000004',
            '2025-2026'
        )
        ON CONFLICT DO NOTHING
    """)

    # Insertion de la promotion — ON CONFLICT DO NOTHING = idempotent
    op.execute(f"""
        INSERT INTO promotions (id, nom, annee_scolaire)
        VALUES ('{_PROMO_ID}', 'ISEN 2026', '2025-2026')
        ON CONFLICT DO NOTHING
    """)

    # Insertion des étudiants — un par un pour garder la lisibilité
    # utilisateur_id est requis (NOT NULL) mais sans FK depuis migration 003 du scolarite-service
    # On génère un UUID aléatoire pour chaque étudiant
    for nom, prenom in _ETUDIANTS:
        op.execute(f"""
            INSERT INTO etudiants (id, utilisateur_id, nom, prenom, promotion_id)
            SELECT
                gen_random_uuid(),
                gen_random_uuid(),
                '{nom}',
                '{prenom}',
                '{_PROMO_ID}'
            WHERE NOT EXISTS (
                SELECT 1 FROM etudiants
                WHERE nom = '{nom}' AND prenom = '{prenom}'
            )
        """)


def downgrade() -> None:
    op.execute("DELETE FROM enseignements WHERE id = 'ccd17754-7d12-4d44-a642-99a5f2be6b0b'")
    op.execute(f"DELETE FROM etudiants WHERE promotion_id = '{_PROMO_ID}'")
    op.execute(f"DELETE FROM promotions WHERE id = '{_PROMO_ID}'")
