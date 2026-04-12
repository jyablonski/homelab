#!/usr/bin/env bash
set -euo pipefail

ingress_ip="${INGRESS_IP:-192.168.76.245}"
hosts_path="${HOSTS_PATH:-/etc/hosts}"

read -r -a ingress_hosts <<< "${INGRESS_HOSTS:-apps.home}"

run_as_root() {
  if [[ "${EUID}" -eq 0 ]]; then
    "$@"
  else
    sudo "$@"
  fi
}

append_mapping() {
  if [[ -w "$hosts_path" ]]; then
    tee -a "$hosts_path" >/dev/null
  else
    run_as_root tee -a "$hosts_path" >/dev/null
  fi
}

replace_hosts_file() {
  local source_path="$1"

  if [[ -w "$hosts_path" ]]; then
    cp "$source_path" "$hosts_path"
  else
    run_as_root cp "$source_path" "$hosts_path"
  fi
}

ensure_hosts_file() {
  if [[ -f "$hosts_path" ]]; then
    return
  fi

  if [[ -w "$(dirname "$hosts_path")" ]]; then
    : > "$hosts_path"
  else
    run_as_root touch "$hosts_path"
  fi
}

host_exists() {
  local host="$1"

  awk -v host="$host" '
    {
      for (i = 2; i <= NF; i++) {
        if ($i == host) {
          found = 1
        }
      }
    }
    END {
      exit(found ? 0 : 1)
    }
  ' "$hosts_path"
}

host_matches_ip() {
  local host="$1"

  awk -v ip="$ingress_ip" -v host="$host" '
    $1 == ip {
      for (i = 2; i <= NF; i++) {
        if ($i == host) {
          found = 1
        }
      }
    }
    END {
      exit(found ? 0 : 1)
    }
  ' "$hosts_path"
}

update_host_mapping() {
  local host="$1"
  local tmp_file

  tmp_file="$(mktemp)"

  awk -v host="$host" '
    /^[[:space:]]*#/ || NF == 0 {
      print
      next
    }
    {
      aliases = ""
      has_host = 0

      for (i = 2; i <= NF; i++) {
        if ($i == host) {
          has_host = 1
          continue
        }

        aliases = aliases (aliases ? OFS : "") $i
      }

      if (!has_host) {
        print
        next
      }

      if (aliases != "") {
        print $1, aliases
      }
    }
  ' "$hosts_path" > "$tmp_file"

  replace_hosts_file "$tmp_file"
  rm -f "$tmp_file"
}

ensure_host_entry() {
  local host="$1"

  if host_exists "$host"; then
    if host_matches_ip "$host"; then
      echo "$hosts_path already maps ${host} to ${ingress_ip}"
      return
    fi

    echo "Updating ${host} in $hosts_path to ${ingress_ip}"
    update_host_mapping "$host"
  fi

  echo "Ensuring ${host} maps to ${ingress_ip} in $hosts_path"
  printf '%s %s\n' "$ingress_ip" "$host" | append_mapping
}

ensure_hosts_file

for host in "${ingress_hosts[@]}"; do
  ensure_host_entry "$host"
done
