#!/usr/bin/env bash
# Run ty for each touched app under apps/ (matches .github/workflows/python-quality.yaml).
set -euo pipefail

# Git GUI / IDE commits often use a minimal PATH without ~/.local/bin.
export PATH="${HOME}/.local/bin:${HOME}/.cargo/bin:/usr/local/bin:${PATH}"

uv_bin() {
  if [[ -n "${UV:-}" && -x "${UV}" ]]; then
    printf '%s\n' "${UV}"
    return 0
  fi
  if command -v uv >/dev/null 2>&1; then
    command -v uv
    return 0
  fi
  local candidate
  for candidate in "${HOME}/.local/bin/uv" "${HOME}/.cargo/bin/uv" /usr/bin/uv; do
    if [[ -x "$candidate" ]]; then
      printf '%s\n' "$candidate"
      return 0
    fi
  done
  return 1
}

if ! UV_BIN="$(uv_bin)"; then
  echo "pre-commit-ty: uv not found (install uv or set UV=/path/to/uv)" >&2
  exit 127
fi

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

declare -A services=()
for path in "$@"; do
  rel="$path"
  if [[ "$path" == /* ]]; then
    rel="${path#"$repo_root"/}"
  fi
  [[ "$rel" =~ ^apps/([^/]+)/ ]] || continue
  services["${BASH_REMATCH[1]}"]=1
done

if [[ ${#services[@]} -eq 0 ]]; then
  echo "pre-commit-ty: no apps/* paths in hook file list" >&2
  exit 1
fi

for service in $(printf '%s\n' "${!services[@]}" | sort); do
  app_dir="$repo_root/apps/$service"
  if [[ ! -f "$app_dir/pyproject.toml" ]]; then
    echo "pre-commit-ty: skipping $service (no pyproject.toml)" >&2
    continue
  fi

  echo "ty ($service)..."
  (
    cd "$app_dir"
    "$UV_BIN" sync --locked --all-groups
    "$UV_BIN" run ty check --output-format concise --extra-search-path src src tests
  )
done
