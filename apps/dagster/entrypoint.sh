#!/usr/bin/env bash
set -euo pipefail

# The webserver and daemon need the Dagster metadata database before they start.
# The code server does not, but the wait is harmless and keeps one entrypoint.
if [[ "${DAGSTER_WAIT_FOR_DB:-true}" == "true" ]]; then
  echo "Waiting for Dagster metadata database to be ready..."
  until python -c "
import os, psycopg2
psycopg2.connect(
    host=os.environ['DAGSTER_POSTGRES_HOST'],
    port=os.environ.get('DAGSTER_POSTGRES_PORT', '5432'),
    dbname=os.environ['DAGSTER_POSTGRES_DB'],
    user=os.environ['DAGSTER_POSTGRES_USER'],
    password=os.environ['DAGSTER_POSTGRES_PASSWORD'],
    connect_timeout=3,
).close()
" 2>/dev/null; do
    echo "Database is unavailable - sleeping"
    sleep 1
  done
  echo "Database is ready!"
fi

exec "$@"
