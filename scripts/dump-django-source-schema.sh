#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
output="${1:-${repo_root}/apps/django/schema/source.sql}"
mkdir -p "$(dirname "${output}")"
temporary="$(mktemp "${output}.tmp.XXXXXX")"
normalized="${temporary}.normalized"
trap 'rm -f "${temporary}" "${normalized}"' EXIT

# Django-owned tables depend on public auth/session objects and are not downstream contracts.
dump_args=(
  --format=plain
  --schema=source
  --schema-only
  --exclude-table=source.django_session
  --exclude-table=source.feature_flags
  --no-owner
  --no-privileges
  --restrict-key=homelabSourceSchema
)

if [[ -n "${PG_DUMP_CONTAINER:-}" ]]; then
  docker exec "${PG_DUMP_CONTAINER}" \
    pg_dump --username postgres --dbname postgres "${dump_args[@]}" > "${temporary}"
elif [[ -n "${DB_HOST:-}" ]]; then
  PGPASSWORD="${DB_PASSWORD:-}" pg_dump \
    --host "${DB_HOST}" \
    --port "${DB_PORT:-5432}" \
    --username "${DB_USER:-postgres}" \
    "${dump_args[@]}" \
    "${DB_NAME:-postgres}" > "${temporary}"
else
  # These variables expand inside the Postgres container.
  # shellcheck disable=SC2016
  kubectl -n postgres exec statefulset/postgres -- \
    sh -c 'pg_dump --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" --format=plain --schema=source --schema-only --exclude-table=source.django_session --exclude-table=source.feature_flags --no-owner --no-privileges --restrict-key=homelabSourceSchema' \
    > "${temporary}"
fi

sed -i '/^-- Dumped from database version /d; /^-- Dumped by pg_dump version /d' "${temporary}"
awk 'NF { last = NR } { lines[NR] = $0 } END { for (line = 1; line <= last; line++) print lines[line] }' \
  "${temporary}" > "${normalized}"
mv "${normalized}" "${temporary}"
chmod 0644 "${temporary}"
mv "${temporary}" "${output}"
trap - EXIT
echo "Wrote ${output}"
