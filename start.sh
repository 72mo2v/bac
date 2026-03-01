#!/usr/bin/env bash
set -e

if [ -z "${DATABASE_URL}" ]; then
  echo "ERROR: DATABASE_URL is required in production."
  exit 1
fi

echo "Running database migrations..."
alembic upgrade head

echo "Starting API server..."
exec uvicorn app.main:app --host 0.0.0.0 --port "${PORT:-8000}"
