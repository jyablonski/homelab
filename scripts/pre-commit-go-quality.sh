#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

if ! command -v go >/dev/null 2>&1; then
  echo "pre-commit-go-quality: go not found" >&2
  exit 127
fi

# Some IDE/pre-commit environments expose a read-only shared Go cache.
export GOCACHE="${GOCACHE:-${TMPDIR:-/tmp}/homelab-go-cache}"

cd "$repo_root/apps/tools"

case "${1:-}" in
  test)
    go tool gotestsum --format=short -- ./...
    ;;
  deadcode)
    go tool deadcode -test ./...
    ;;
  golint)
    output="$(go tool golint ./...)"
    if [[ -n "$output" ]]; then
      printf '%s\n' "$output" >&2
      exit 1
    fi
    ;;
  *)
    echo "usage: $0 {test|deadcode|golint}" >&2
    exit 2
    ;;
esac
