#!/usr/bin/env sh
set -eu

echo "Waiting for database..."

for attempt in $(seq 1 30); do
  if python -c "from sqlalchemy import create_engine, text; from app.core.config import settings; engine = create_engine(settings.database_url); conn = engine.connect(); conn.execute(text('SELECT 1')); conn.close()" >/dev/null 2>&1; then
    echo "Database is ready."
    alembic upgrade head
    exec uvicorn app.main:app --host 0.0.0.0 --port 8000
  fi
  echo "Database not ready yet, retrying..."
  sleep 2
done

echo "Database did not become ready in time."
exit 1
