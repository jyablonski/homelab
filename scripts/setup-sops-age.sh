#!/usr/bin/env bash
set -euo pipefail

primary_key_path="${SOPS_AGE_KEY_FILE:-$HOME/.config/sops/age/keys.txt}"
backup_key_path="${1:-}"

if ! command -v age-keygen >/dev/null 2>&1; then
  echo "error: age-keygen is required" >&2
  exit 1
fi

if [[ -z "$backup_key_path" ]]; then
  echo "Usage: $0 <backup-key-output-path>" >&2
  echo "" >&2
  echo "Example:" >&2
  echo "  $0 /path/to/encrypted-backup/homelab-sops-age-backup.txt" >&2
  exit 1
fi

tilde_prefix="$(printf '\176/')"
if [[ "$backup_key_path" == "$tilde_prefix"* ]]; then
  backup_key_path="$HOME/${backup_key_path#"~/"}"
fi

if [[ -e "$primary_key_path" ]]; then
  echo "error: primary age key already exists at $primary_key_path" >&2
  echo "Refusing to overwrite it." >&2
  exit 1
fi

if [[ -e "$backup_key_path" ]]; then
  echo "error: backup age key already exists at $backup_key_path" >&2
  echo "Refusing to overwrite it." >&2
  exit 1
fi

mkdir -p "$(dirname "$primary_key_path")"
mkdir -p "$(dirname "$backup_key_path")"

age-keygen -o "$primary_key_path" >/dev/null
age-keygen -o "$backup_key_path" >/dev/null

primary_recipient="$(age-keygen -y "$primary_key_path")"
backup_recipient="$(age-keygen -y "$backup_key_path")"

chmod 600 "$primary_key_path" "$backup_key_path"

cat <<EOF
Created primary age key:
  $primary_key_path

Created backup age key:
  $backup_key_path

Store the backup key somewhere durable and private.

Add this to .sops.yaml:

creation_rules:
  - path_regex: .*\\.sops\\.ya?ml$
    age: >-
      $primary_recipient,
      $backup_recipient
EOF
