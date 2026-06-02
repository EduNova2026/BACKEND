#!/bin/sh
set -eu

cd /app/services/scolarite-service

echo "Waiting for PostgreSQL to be reachable..."

MAX_ATTEMPTS=30
attempt=1

until python -c "
import socket, os, re
url = os.environ['DATABASE_URL']
m = re.search(r'@([^:/]+):?(\d+)?/', url)
host = m.group(1)
port = int(m.group(2) or 5432)
sock = socket.create_connection((host, port), timeout=3)
sock.close()
"; do
    if [ "$attempt" -ge "$MAX_ATTEMPTS" ]; then
        echo "PostgreSQL not reachable after $MAX_ATTEMPTS attempts"
        exit 1
    fi
    echo "Waiting for PostgreSQL... attempt $attempt/$MAX_ATTEMPTS"
    attempt=$((attempt + 1))
    sleep 2
done

echo "PostgreSQL reachable, running scolarite-service migrations..."
uv run --no-dev alembic -c alembic/alembic.ini upgrade head

echo "Starting scolarite-service..."
exec uv run --no-dev uvicorn app.main:app --host 0.0.0.0 --port 8000
