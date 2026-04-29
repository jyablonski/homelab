#!/usr/bin/env bash
set -euo pipefail

if [[ $# -lt 3 || "$2" != "--" ]]; then
  echo "Usage: $0 <label> -- <command> [args...]" >&2
  exit 2
fi

label="$1"
shift 2

log_slug="$(tr -cs '[:alnum:]' '-' <<< "${label,,}" | sed 's/^-//; s/-$//')"
log_file="$(mktemp "${TMPDIR:-/tmp}/homelab-step-${log_slug}.XXXXXX.log")"

spinner_frame() {
  local index="$1"
  local frames=("|" "/" "-" "\\")

  printf '%s' "${frames[index % 4]}"
}

render_line() {
  local symbol="$1"
  local message="$2"

  if [[ -t 1 ]]; then
    printf '\r\033[2K%b %s' "$symbol" "$message"
  else
    printf '%b %s\n' "$symbol" "$message"
  fi
}

"$@" > "$log_file" 2>&1 &
command_pid="$!"

frame=0
while kill -0 "$command_pid" 2>/dev/null; do
  render_line "$(spinner_frame "$frame")" "$label"
  frame=$((frame + 1))
  sleep 1
done

if wait "$command_pid"; then
  if [[ -t 1 ]]; then
    render_line $'\033[32m●\033[0m' "$label"
  else
    render_line "OK" "$label"
  fi
  printf '\n'
else
  exit_code="$?"
  if [[ -t 1 ]]; then
    render_line $'\033[31m●\033[0m' "$label"
  else
    render_line "FAIL" "$label"
  fi
  printf '\n'
  echo "Step failed: ${label} (exit ${exit_code})" >&2
  echo "Logs: ${log_file}" >&2
  echo >&2
  echo "Recent log output:" >&2
  tail -n 40 "$log_file" >&2 || true
  exit "$exit_code"
fi
