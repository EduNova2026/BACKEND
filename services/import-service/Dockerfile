FROM python:3.12-slim AS runtime

COPY --from=ghcr.io/astral-sh/uv:0.11.17 /uv /uvx /usr/local/bin/

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_SYSTEM_PYTHON=1 \
    PYTHONPATH=/app/services/import-service:/app/packages/shared/src

WORKDIR /app

COPY pyproject.toml ./
COPY uv.lock ./
COPY packages/shared/pyproject.toml packages/shared/pyproject.toml
COPY packages/shared/src packages/shared/src
COPY services/api-gateway/pyproject.toml services/api-gateway/pyproject.toml
COPY services/identity-service/pyproject.toml services/identity-service/pyproject.toml
COPY services/scolarite-service/pyproject.toml services/scolarite-service/pyproject.toml
COPY services/import-service/pyproject.toml services/import-service/pyproject.toml
COPY services/import-service/app services/import-service/app
COPY services/import-service/alembic services/import-service/alembic

RUN uv sync --no-dev --package import-service

EXPOSE 8000

COPY services/import-service/docker-entrypoint.sh /docker-entrypoint.sh
RUN chmod +x /docker-entrypoint.sh

ENTRYPOINT ["/docker-entrypoint.sh"]