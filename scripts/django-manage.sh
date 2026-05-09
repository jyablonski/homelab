#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'EOF'
Run Django manage.py inside the cluster deployment (apps/django).

Usage:
  scripts/django-manage.sh <manage.py arguments...>

Examples:
  scripts/django-manage.sh migrate
  scripts/django-manage.sh migrate core 0003_reminders_table
  scripts/django-manage.sh showmigrations

Same via Make (optional ARGS for a single Make variable):
  make django-manage ARGS=migrate
EOF
}

if [[ "${1:-}" == "-h" ]] || [[ "${1:-}" == "--help" ]]; then
  usage
  exit 0
fi

exec kubectl exec -n apps deploy/django -- python src/manage.py "$@"
