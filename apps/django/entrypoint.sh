#!/usr/bin/env bash
set -euo pipefail

echo "Waiting for database to be ready..."
until python -c "import psycopg2; psycopg2.connect(host='${DB_HOST}', port=${DB_PORT}, user='${DB_USER}', password='${DB_PASSWORD}', dbname='${DB_NAME}')" 2>/dev/null; do
  echo "Database is unavailable - sleeping"
  sleep 1
done

echo "Database is ready!"

echo "Checking for missing migrations..."
if ! python src/manage.py makemigrations --check --dry-run > /dev/null 2>&1; then
    echo "ERROR: Missing migrations detected!"
    echo "Run 'python src/manage.py makemigrations' locally and commit the migration files."
    exit 1
fi
echo "All migrations are up to date."

echo "Running migrations..."
python src/manage.py migrate --noinput

echo "Starting Django server..."
exec "$@"
