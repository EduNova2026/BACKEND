FROM python:3.12-slim AS runtime

COPY --from=ghcr.io/astral-sh/uv:0.11.17 /uv /uvx /usr/local/bin/

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_SYSTEM_PYTHON=1 \
    PYTHONPATH=/app/services/identity-service:/app/packages/shared/src

WORKDIR /app

COPY pyproject.toml ./
COPY uv.lock ./
COPY packages/shared/pyproject.toml packages/shared/pyproject.toml
COPY packages/shared/src packages/shared/src
COPY services/api-gateway/pyproject.toml services/api-gateway/pyproject.toml
COPY services/api-gateway/app services/api-gateway/app
COPY services/identity-service/pyproject.toml services/identity-service/pyproject.toml
COPY services/identity-service/app services/identity-service/app
COPY services/identity-service/alembic services/identity-service/alembic

RUN uv sync --no-dev --package identity-service

EXPOSE 8000

CMD ["uv", "run", "--no-dev", "--package", "identity-service", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
