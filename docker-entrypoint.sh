#!/bin/sh
set -e

# Wait for the database to accept connections before migrating - useful
# when the DB is a separately-provisioned service that might still be
# starting up on first deploy. Gives up after ~30s and lets alembic's own
# error surface instead of hanging forever.
echo "Waiting for the database..."
for i in $(seq 1 15); do
  if python -c "
from app.core.config import settings
from sqlalchemy import create_engine
create_engine(settings.sqlalchemy_database_url).connect().close()
" 2>/dev/null; then
    echo "Database is up."
    break
  fi
  echo "  not ready yet ($i/15)..."
  sleep 2
done

echo "Running migrations..."
alembic upgrade head

echo "Starting server on port ${PORT:-8000}..."
exec uvicorn app.main:app --host 0.0.0.0 --port "${PORT:-8000}"
