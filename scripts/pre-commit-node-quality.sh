#!/usr/bin/env bash
# Run ESLint + tsc for each touched Node/TS app under apps/ (matches .github/workflows/node-quality.yaml).
set -euo pipefail

# Git GUI / IDE commits often use a minimal PATH without common Node install locations.
export PATH="${HOME}/.local/bin:/usr/local/bin:${PATH}"

if ! command -v npm >/dev/null 2>&1; then
  echo "pre-commit-node-quality: npm not found" >&2
  exit 127
fi

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

declare -A apps=()
for path in "$@"; do
  rel="$path"
  if [[ "$path" == /* ]]; then
    rel="${path#"$repo_root"/}"
  fi
  [[ "$rel" =~ ^apps/([^/]+)/ ]] || continue
  apps["${BASH_REMATCH[1]}"]=1
done

if [[ ${#apps[@]} -eq 0 ]]; then
  echo "pre-commit-node-quality: no apps/* paths in hook file list" >&2
  exit 1
fi

for app in $(printf '%s\n' "${!apps[@]}" | sort); do
  app_dir="$repo_root/apps/$app"
  if [[ ! -f "$app_dir/package.json" ]]; then
    echo "pre-commit-node-quality: skipping $app (no package.json)" >&2
    continue
  fi

  echo "node quality ($app)..."
  (
    cd "$app_dir"
    # npm ci (not install): install never writes to package-lock.json, so a
    # different npm version on this machine/runner can't reformat it and trip
    # pre-commit's "files were modified by this hook" guard.
    npm ci --no-audit --no-fund
    npm run lint
    npm run typecheck
  )
done
