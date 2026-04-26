#!/usr/bin/env bash
set -euo pipefail

if [[ "${API_WAIT_FOR_DB:-true}" == "true" ]]; then
  echo "Waiting for database to be ready..."
  until python -c "from database import ping_database; ping_database()" 2>/dev/null; do
    echo "Database is unavailable - sleeping"
    sleep 1
  done
  echo "Database is ready!"
fi

exec "$@"
