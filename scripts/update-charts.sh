#!/usr/bin/env bash
# Check helm chart versions in helmfile.yaml against latest available.
#
# Usage:
#   ./scripts/update-charts.sh
#   make update-charts

set -euo pipefail

HELMFILE="$(git rev-parse --show-toplevel)/helmfile.yaml"

for cmd in helm yq jq; do
  if ! command -v "$cmd" &>/dev/null; then
    echo "error: $cmd is required but not found in PATH"
    exit 1
  fi
done


# ── Sync repos ────────────────────────────────────────────────────────────────

echo "Updating helm repos..."
yq_raw() { yq "$1" "$2" | sed 's/^"//; s/"$//'; }

while read -r name && read -r url; do
  helm repo add "$name" "$url" --force-update &>/dev/null || true
done < <(yq_raw '.repositories[] | (.name, .url)' "$HELMFILE")
helm repo update &>/dev/null
echo

# ── Check versions ────────────────────────────────────────────────────────────

updates=()
current=()

while read -r release_name && read -r chart && read -r version; do
  [[ "$chart" == "./"* ]] && continue  # skip local charts

  latest=$(helm search repo "$chart" -o json 2>/dev/null \
    | jq -r --arg c "$chart" '.[] | select(.name == $c) | .version' \
    | head -1)

  if [[ -z "$latest" ]]; then
    echo "warn: could not resolve $chart"
    continue
  fi

  if [[ "$latest" != "$version" ]]; then
    updates+=("$release_name" "$chart" "$version" "$latest")
  else
    current+=("$release_name" "$chart" "$version" "$latest")
  fi
done < <(yq_raw '.releases[] | select(has("version")) | (.name, .chart, .version)' "$HELMFILE")

# ── Output ────────────────────────────────────────────────────────────────────

print_table() {
  local -n rows=$1
  printf "  %-22s %-48s %-14s %s\n" "Release" "Chart" "Current" "Latest"
  printf "  %s\n" "$(printf '%.0s-' {1..88})"
  for (( i=0; i<${#rows[@]}; i+=4 )); do
    printf "  %-22s %-48s %-14s %s\n" \
      "${rows[i]}" "${rows[i+1]}" "${rows[i+2]}" "${rows[i+3]}"
  done
}

if [[ ${#current[@]} -gt 0 ]]; then
  echo "Up to date ($(( ${#current[@]} / 4 ))):"
  print_table current
  echo
fi

if [[ ${#updates[@]} -eq 0 ]]; then
  echo "All charts are up to date."
  exit 0
fi

echo "Updates available ($(( ${#updates[@]} / 4 ))):"
print_table updates
echo

read -r -p "Apply all updates to helmfile.yaml? [y/N] " confirm
[[ "${confirm,,}" != "y" ]] && { echo "Aborted."; exit 0; }

echo
echo "Applying updates..."
for (( i=0; i<${#updates[@]}; i+=4 )); do
  name="${updates[i]}"
  current_ver="${updates[i+2]}"
  latest="${updates[i+3]}"
  echo "  [$name] $current_ver -> $latest"
  sed -i "/name: $name/,/version:/ s/version: $current_ver/version: $latest/" "$HELMFILE"
done
echo
echo "Updated $(( ${#updates[@]} / 4 )) chart(s) in helmfile.yaml"

read -r -p "Run helmfile sync now? [y/N] " sync
[[ "${sync,,}" == "y" ]] && helmfile sync || echo "Run 'helmfile sync' or 'make sync' when ready."
