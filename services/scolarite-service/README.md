# Scolarite Service

FastAPI microservice for EDU'NOVA academic catalogue and student management.

Manages promotions, student groups, student enrollment, and user-role assignment. All write operations go to the primary database while reads can optionally use a replica. The service exposes its API exclusively through the API Gateway.

## Service overview

The Scolarite Service handles the academic structure of EDU'NOVA: promotions, TD groups, student records, and role attribution. It uses:

- FastAPI for the HTTP API
- SQLAlchemy with async PostgreSQL sessions (primary + replica)
- Alembic for database migrations (with a dedicated version table to avoid collisions with identity-service)
- Shared Pydantic schemas for request/response validation
- External table stubs to read/write identity-service tables without owning their migrations

## Architecture overview

- `app/main.py` wires FastAPI, CORS, security headers, health checks, and router registration.
- `app/routers/promotions.py` exposes CRUD endpoints for promotions, plus sub-resources for groupes and etudiants.
- `app/routers/groupes.py` exposes CRUD endpoints for groupes, plus the etudiant listing sub-resource.
- `app/routers/etudiants.py` exposes CRUD endpoints for etudiants and manages the many-to-many relationship with groupes.
- `app/routers/roles.py` exposes role listing, user-role assignment, and revocation using identity-service tables.
- `app/models/` contains SQLAlchemy ORM models for the four owned tables.
- `app/external_models.py` declares read-only stubs for identity-service tables with a separate metadata so Alembic never migrates them.
- `app/database.py` manages the primary and replica PostgreSQL sessions with dependency injection.
- `app/config.py` exposes Pydantic settings with Doppler as the configuration source.
- `alembic/` holds the migration environment and the initial migration that creates the four owned tables.

## API endpoints

All routes are prefixed with `/api/v1`. The API Gateway proxies every request under `/scolarite/{path}` to this service.

### Promotions

- `GET /promotions/` — list all promotions (sorted by name).
- `POST /promotions/` — create a promotion. Rejects duplicate `(nom, annee_scolaire)` pairs.
- `GET /promotions/{promotion_id}` — get a promotion by ID.
- `PATCH /promotions/{promotion_id}` — update a promotion's name or academic year. Rejects duplicates.
- `DELETE /promotions/{promotion_id}` — delete a promotion.
- `GET /promotions/{promotion_id}/groupes` — list groupes belonging to a promotion.
- `GET /promotions/{promotion_id}/etudiants` — list etudiants enrolled in a promotion.

### Groupes

- `GET /groupes/` — list all groupes (sorted by name).
- `POST /groupes/` — create a groupe. Requires a valid `promotion_id`.
- `GET /groupes/{groupe_id}` — get a groupe by ID.
- `PATCH /groupes/{groupe_id}` — update a groupe's name or promotion.
- `DELETE /groupes/{groupe_id}` — delete a groupe.
- `GET /groupes/{groupe_id}/etudiants` — list etudiants assigned to a groupe.

### Etudiants

- `GET /etudiants/` — list all etudiants (sorted by `utilisateur_id`).
- `POST /etudiants/` — create an etudiant record. Validates that the referenced utilisateur exists and is active, and that the promotion exists.
- `GET /etudiants/{etudiant_id}` — get an etudiant by ID.
- `PATCH /etudiants/{etudiant_id}` — update an etudiant's promotion.
- `DELETE /etudiants/{etudiant_id}` — delete an etudiant record.
- `GET /etudiants/{etudiant_id}/groupes` — list groupes the etudiant belongs to.
- `POST /etudiants/{etudiant_id}/groupes/{groupe_id}` — assign an etudiant to a groupe. Rejects duplicate assignments.
- `DELETE /etudiants/{etudiant_id}/groupes/{groupe_id}` — remove an etudiant from a groupe.

### Roles

- `GET /roles/` — list all roles defined by identity-service.
- `GET /roles/utilisateurs/{utilisateur_id}/roles` — get the roles assigned to a user.
- `POST /roles/utilisateurs/{utilisateur_id}/roles` — assign a role to a user. Validates that the user exists and is active, and that the role exists. Idempotent: repeated assignments are silently accepted.
- `DELETE /roles/utilisateurs/{utilisateur_id}/roles/{role_id}` — revoke a role from a user.

## Environment variables

The service inherits shared app settings and adds its own database variables. Set them through Doppler or your deployment environment.

| Variable | Purpose |
| --- | --- |
| `APP_NAME` | Service name shown in health responses and docs |
| `APP_ENV` | Runtime environment (`development`, `production`, etc.) |
| `APP_VERSION` | Service version |
| `LOG_LEVEL` | Logging verbosity |
| `DATABASE_URL` | Primary PostgreSQL async connection string (asyncpg) |
| `DATABASE_REPLICA_URL` | Replica PostgreSQL async connection string (optional; falls back to primary) |
| `CORS_ALLOW_ORIGINS` | Comma-separated CORS allow-list |
| `API_PREFIX` | Prefix for all API routes (default: `/api/v1`) |

## Database schema

The service owns four tables and references three more from identity-service via external stubs. Alembic uses a dedicated version table (`alembic_version_scolarite`) to stay independent from identity-service migrations.

### Owned tables (migrated by this service)

- `promotions`
  - `id` UUID primary key
  - `nom` promotion name
  - `annee_scolaire` academic year (e.g. `"2025-2026"`)
  - Unique on `(nom, annee_scolaire)`
- `groupes`
  - `id` UUID primary key
  - `nom` group name
  - `promotion_id` foreign key to `promotions`
  - Unique on `(promotion_id, nom)`
- `etudiants`
  - `id` UUID primary key
  - `utilisateur_id` UUID referencing `utilisateurs.id` (identity-service table)
  - `promotion_id` foreign key to `promotions`
  - Unique on `(utilisateur_id, promotion_id)`, indexed on `utilisateur_id`
- `etudiant_groupes`
  - `etudiant_id` foreign key to `etudiants`
  - `groupe_id` foreign key to `groupes`
  - Composite primary key on `(etudiant_id, groupe_id)`

### External tables (read/write via stubs, never migrated)

- `utilisateurs` — read to validate user existence and active status before creating student records or assigning roles.
- `roles` — read for role listing. Roles are seeded by identity-service at startup.
- `utilisateur_roles` — write for role assignment with `ON CONFLICT DO NOTHING` to ensure idempotent behavior.

The external table stubs live in `app/external_models.py` and use a separate `external_metadata` that is never passed to Alembic's `target_metadata`. This prevents the service from accidentally creating, altering, or dropping identity-service tables.

## Local development

Run the service from the `backend/services/scolarite-service` directory.

### With Docker

The container listens on port `8000` inside the Docker network only. It is not published on localhost; external clients must call the API Gateway on `http://localhost:8000/scolarite/...`.

The entrypoint waits for PostgreSQL to become reachable (up to 30 attempts), then runs Alembic migrations once before starting the application.

### Without Docker

```bash
uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Make sure PostgreSQL is available and the required environment variables are set before starting the app.

## Test running instructions

```bash
uv run pytest
```

Run this from `backend/services/scolarite-service`. The test suite uses an in-memory SQLite database and covers all CRUD operations, validation rules (duplicate detection, inactive utilisateur rejection, missing FK references), and role assignment idempotency.
