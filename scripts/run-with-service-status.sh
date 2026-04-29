#!/usr/bin/env bash
set -euo pipefail

if [[ $# -lt 3 || "$2" != "--" ]]; then
  echo "Usage: $0 <bootstrap-label> -- <command> [args...]" >&2
  exit 2
fi

selector="$1"
selector_value="${selector#*=}"
shift 2

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
helmfile_path="$repo_root/helmfile.yaml"
log_file="$(mktemp "${TMPDIR:-/tmp}/homelab-bootstrap-${selector//=/-}.XXXXXX.log")"
release_file="$(mktemp "${TMPDIR:-/tmp}/homelab-bootstrap-releases.XXXXXX")"
rendered_lines=0

cleanup() {
  rm -f "$release_file"
}

trap cleanup EXIT

discover_releases() {
  awk -v selector="$selector_value" '
    function reset_release() {
      name = ""
      namespace = "default"
      bootstrap = ""
    }

    function print_release() {
      if (name != "" && bootstrap == selector) {
        print name "\t" namespace
      }
    }

    /^releases:/ {
      in_releases = 1
      next
    }

    in_releases && /^  - name:/ {
      print_release()
      reset_release()
      name = $0
      sub(/^  - name:[[:space:]]*/, "", name)
      next
    }

    in_releases && /^    namespace:/ {
      namespace = $0
      sub(/^    namespace:[[:space:]]*/, "", namespace)
      next
    }

    in_releases && /^      bootstrap:/ {
      bootstrap = $0
      sub(/^      bootstrap:[[:space:]]*/, "", bootstrap)
      next
    }

    END {
      print_release()
    }
  ' "$helmfile_path" > "$release_file"
}

spinner_frame() {
  local index="$1"
  local frames=("|" "/" "-" "\\")

  printf '%s' "${frames[index % 4]}"
}

release_state() {
  local release="$1"
  local namespace="$2"
  local helm_status=""
  local pod_rows=""

  helm_status="$(helm -n "$namespace" status "$release" -o json 2>/dev/null | jq -r '.info.status // ""' 2>/dev/null || true)"

  if [[ "$helm_status" =~ ^(failed|uninstalled|superseded)$ ]]; then
    printf 'failed\thelm status: %s\n' "$helm_status"
    return
  fi

  pod_rows="$(
    kubectl -n "$namespace" get pods -l "app.kubernetes.io/instance=$release" \
      -o jsonpath='{range .items[*]}{.metadata.name}{"|"}{.status.phase}{"|"}{range .status.containerStatuses[*]}{.ready}{":"}{.state.waiting.reason}{":"}{.state.terminated.reason}{","}{end}{"\n"}{end}' \
      2>/dev/null || true
  )"

  if [[ -n "$pod_rows" ]]; then
    if grep -Eq 'CrashLoopBackOff|ImagePullBackOff|ErrImagePull|CreateContainerConfigError|CreateContainerError|RunContainerError|Error|OOMKilled' <<< "$pod_rows"; then
      printf 'failed\tpod error\n'
      return
    fi

    if awk -F'|' '
      NF >= 3 {
        seen = 1
        if ($2 != "Running" && $2 != "Succeeded") {
          not_ready = 1
        }
        if ($3 ~ /false:/) {
          not_ready = 1
        }
      }
      END {
        exit(seen && !not_ready ? 0 : 1)
      }
    ' <<< "$pod_rows"; then
      printf 'ready\tpods ready\n'
      return
    fi
  fi

  if [[ "$helm_status" == "deployed" && -z "$pod_rows" ]]; then
    printf 'ready\thelm deployed\n'
    return
  fi

  if [[ -n "$helm_status" ]]; then
    printf 'pending\thelm status: %s\n' "$helm_status"
    return
  fi

  printf 'pending\twaiting for release\n'
}

render_status() {
  local frame="$1"
  local failures="$2"
  local lines=()
  local release=""
  local namespace=""
  local state=""
  local detail=""
  local symbol=""
  local color=""
  local reset=""

  if [[ -t 1 ]]; then
    color=$'\033[36m'
    reset=$'\033[0m'
    if [[ "$rendered_lines" -gt 0 ]]; then
      printf '\033[%sA' "$rendered_lines"
    fi
  fi

  lines+=("Cluster bootstrap: ${selector}")
  lines+=("")

  while IFS=$'\t' read -r release namespace; do
    [[ -n "$release" ]] || continue
    IFS=$'\t' read -r state detail < <(release_state "$release" "$namespace")

    case "$state" in
      ready)
        symbol=$'\033[32m●\033[0m'
        ;;
      failed)
        symbol=$'\033[31m●\033[0m'
        ;;
      *)
        symbol="${color}$(spinner_frame "$frame")${reset}"
        ;;
    esac

    if [[ ! -t 1 ]]; then
      case "$state" in
        ready) symbol="OK" ;;
        failed) symbol="FAIL" ;;
        *) symbol="$(spinner_frame "$frame")" ;;
      esac
    fi

    lines+=("  ${symbol} $(printf '%-26s' "$release") ${detail}")
  done < "$release_file"

  lines+=("")
  lines+=("Logs: ${log_file}")

  if [[ "$failures" -ne 0 ]]; then
    lines+=("")
    lines+=("Recent log output:")
    while IFS= read -r release; do
      lines+=("$release")
    done < <(tail -n 40 "$log_file" || true)
  fi

  for release in "${lines[@]}"; do
    if [[ -t 1 ]]; then
      printf '\033[2K%b\n' "$release"
    else
      printf '%b\n' "$release"
    fi
  done

  while [[ "$rendered_lines" -gt "${#lines[@]}" ]]; do
    printf '\033[2K\n'
    rendered_lines=$((rendered_lines - 1))
  done

  if [[ -t 1 ]]; then
    rendered_lines="${#lines[@]}"
  fi
}

discover_releases

if [[ ! -s "$release_file" ]]; then
  echo "No releases found for ${selector}; running command without status UI."
  "$@"
  exit
fi

"$@" > "$log_file" 2>&1 &
command_pid="$!"

frame=0
while kill -0 "$command_pid" 2>/dev/null; do
  render_status "$frame" 0
  frame=$((frame + 1))
  sleep 2
done

if wait "$command_pid"; then
  render_status "$frame" 0
  echo
  echo "Bootstrap phase complete: ${selector}"
else
  exit_code="$?"
  render_status "$frame" 1
  echo
  echo "Bootstrap phase failed: ${selector} (exit ${exit_code})" >&2
  exit "$exit_code"
fi
