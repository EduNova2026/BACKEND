# Identity Service

FastAPI microservice for EDU'NOVA authentication and user identity.

Phase 1 provides the service skeleton, SQLAlchemy models for the DBML `utilisateurs`, `roles`, and `utilisateur_roles` tables, PostgreSQL/Redis configuration, and Docker integration. In practice, this phase already covers the auth flow, JWT session handling, role seeding, and the initial read/write path against the primary and replica databases.

## Service overview

The Identity Service handles login, logout, token refresh, and current-user lookup for EDU'NOVA. It uses:

- FastAPI for the HTTP API
- SQLAlchemy with async PostgreSQL sessions
- Redis for session storage, rate limiting, and token blacklisting
- JWT for access and refresh tokens
- Mauria as the external authentication check during login

## Architecture overview

- `app/main.py` wires FastAPI, CORS, health checks, and startup role seeding.
- `app/routers/auth.py` exposes the auth endpoints.
- `app/services/auth_service.py` coordinates Mauria login, user provisioning, rate limiting, and token issuance.
- `app/services/jwt_service.py` signs and validates JWTs.
- `app/services/user_service.py` hashes passwords and manages users/roles.
- `app/database.py` manages the primary and replica PostgreSQL sessions.
- `app/redis_client.py` provides the Redis client used by auth flows.

## API endpoints

- `GET /health` - health check.
- `POST /api/v1/auth/login` - authenticate a user and return access + refresh tokens.
- `POST /api/v1/auth/logout` - blacklist the current access token and related refresh token.
- `GET /api/v1/auth/me` - return the current authenticated user profile.
- `POST /api/v1/auth/refresh` - exchange a valid refresh token for a new access token.

## Environment variables

The service inherits shared app settings and adds its own database/auth variables. Set them through Doppler or your deployment environment.

| Variable | Purpose |
| --- | --- |
| `APP_NAME` | Service name shown in health responses and docs |
| `APP_ENV` | Runtime environment (`development`, `production`, etc.) |
| `APP_VERSION` | Service version |
| `LOG_LEVEL` | Logging verbosity |
| `DATABASE_URL` | Primary PostgreSQL async connection string |
| `DATABASE_REPLICA_URL` | Replica PostgreSQL async connection string |
| `REDIS_URL` | Redis connection string |
| `MAURIA_API_URL` | Base URL of the Mauria auth API |
| `MAURIA_LOGIN_PATH` | Mauria login path appended to the base URL |
| `ALLOW_STUDENT_BYPASS` | Enables the student-domain bypass used in development |
| `CORS_ALLOW_ORIGINS` | Comma-separated CORS allow-list |
| `JWT_SECRET` | JWT signing secret (set securely; do not commit it) |
| `JWT_ALGORITHM` | JWT signing algorithm |
| `JWT_ACCESS_EXPIRATION_MINUTES` | Access token lifetime |
| `JWT_REFRESH_EXPIRATION_DAYS` | Refresh token lifetime |
| `RATE_LIMIT_LOGIN_MAX` | Maximum login attempts per window |
| `RATE_LIMIT_LOGIN_WINDOW` | Login rate-limit window in seconds |

## Database schema

The service uses PostgreSQL with a primary database and a replica for read traffic.

- `utilisateurs`
  - `id` UUID primary key
  - `email` unique indexed email address
  - `mdp` nullable legacy column; passwords are not stored because authentication is delegated to Mauria
  - `nom`, `prenom`
  - `actif`, `premier_login`
  - `created_at`
- `roles`
  - `id` UUID primary key
  - `libelle` unique role label
- `utilisateur_roles`
  - join table between users and roles
  - composite primary key: `utilisateur_id`, `role_id`

At startup, the service seeds the default roles: `enseignant`, `admin_pedagogique`, and `responsable_pedagogique`.

## Local development

Run the service from the `backend/services/identity-service` directory.

### With Docker

The container listens on port `8000` inside the Docker network only. It is not published on localhost; external clients must call the API Gateway on `http://localhost:8000`.

### Without Docker

```bash
uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Make sure PostgreSQL, the replica, and Redis are available, and that the required environment variables are set before starting the app.

## Test running instructions

```bash
uv run pytest
```

Run this from `backend/services/identity-service`. The auth tests cover login, logout, refresh, `/me`, and rate limiting behavior.
