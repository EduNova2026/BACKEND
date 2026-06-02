# EDU'NOVA Backend

Workspace for the backend services of EDU'NOVA. Managed with UV and FastAPI.

## Service layout

- `services/api-gateway` — public entry point; proxies auth requests to Identity Service.
- `services/identity-service` — authentication and user identity.
- `services/mauria-mock` — local trusted stand-in for Mauria in development.
- `packages/shared` — shared schemas and contracts.

## Authentication flow

- The frontend talks to the API Gateway only.
- The Gateway forwards `/api/v1/auth/login`, `/api/v1/auth/logout`, `/api/v1/auth/me`, and `/api/v1/auth/refresh` to Identity Service.
- Identity Service verifies credentials against Mauria.
- On first login, it creates the user from the email local-part, parsing `prenom` and `nom`, sets `actif=true`, and initializes `premier_login=true`.
- After the first successful login, `premier_login` becomes `false`.
- If `actif=false`, login is rejected after successful Mauria auth with `Votre compte est désactivé veuillez contacter un administrateur`.
- No local password is stored: `mdp` is a nullable legacy column, and the identity-service migration `alembic/versions/002_backfill_premier_login.py` clears it.

## Identity Service deployment

The Docker entrypoint applies Alembic before starting Uvicorn:

```bash
uv run --no-dev alembic -c alembic/alembic.ini upgrade head
```

Run migrations before or with deployment.

## Local development

Run shared checks from `backend/`:

```bash
uv run pytest
uv run ruff check .
uv run ruff format .
```

Service-level run commands and env vars are documented in `services/api-gateway/README.md` and `services/identity-service/README.md`.
