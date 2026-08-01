#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
secrets_path="${TALOS_SECRETS_FILE:-$repo_root/talos/secrets.sops.yaml}"

for command_name in sops talosctl; do
  if ! command -v "$command_name" >/dev/null 2>&1; then
    echo "error: $command_name is required" >&2
    exit 1
  fi
done

if [[ -e "$secrets_path" ]]; then
  echo "error: $secrets_path already exists; refusing to replace the cluster identity" >&2
  exit 1
fi

secrets_dir="$(dirname "$secrets_path")"
mkdir -p "$secrets_dir"

work_dir="$(mktemp -d "${TMPDIR:-/tmp}/homelab-talos-secrets.XXXXXX")"
trap 'rm -rf "$work_dir"' EXIT
umask 077

plain_path="$work_dir/secrets.yaml"
encrypted_path="$work_dir/secrets.sops.yaml"

talosctl gen secrets --output-file "$plain_path"
sops --encrypt --filename-override "$secrets_path" "$plain_path" > "$encrypted_path"
install -m 600 "$encrypted_path" "$secrets_path"

echo "Created encrypted Talos cluster identity at $secrets_path"
echo "Back up this file and the SOPS age keys outside the cluster before provisioning nodes."
