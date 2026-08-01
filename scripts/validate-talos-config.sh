#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
output_dir="${TALOS_OUTPUT_DIR:-${1:-$repo_root/talos/_out}}"

if ! command -v talosctl >/dev/null 2>&1; then
  echo "error: talosctl is required" >&2
  exit 1
fi
if [[ ! -d "$output_dir" ]]; then
  echo "error: generated Talos config directory does not exist: $output_dir" >&2
  echo "Run make talos-config first." >&2
  exit 1
fi

mapfile -t machine_configs < <(find "$output_dir" -maxdepth 1 -type f -name 'talos-*.yaml' -print | sort)
if [[ "${#machine_configs[@]}" -ne 3 ]]; then
  echo "error: expected three generated machine configs in $output_dir; found ${#machine_configs[@]}" >&2
  exit 1
fi
if [[ ! -s "$output_dir/talosconfig" ]]; then
  echo "error: generated talosconfig is missing or empty: $output_dir/talosconfig" >&2
  exit 1
fi

for machine_config in "${machine_configs[@]}"; do
  echo "Validating $machine_config"
  talosctl validate --config "$machine_config" --mode metal --strict
done

echo "Validated all generated Talos machine configs."
