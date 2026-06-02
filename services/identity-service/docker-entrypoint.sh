#!/bin/sh
set -eu

cd /app/services/identity-service

echo "Running identity-service Alembic migrations..."

attempt=1
until uv run --no-dev alembic -c alembic/alembic.ini upgrade head; do
    if [ "$attempt" -ge 30 ]; then
        echo "Alembic migrations failed after $attempt attempts"
        exit 1
    fi

    echo "Alembic migration attempt $attempt failed; retrying in 2s..."
    attempt=$((attempt + 1))
    sleep 2
done

echo "Starting identity-service..."
exec uv run --no-dev uvicorn app.main:app --host 0.0.0.0 --port 8000
