#!/usr/bin/env bash
set -euo pipefail

registry_host="${REGISTRY_HOST:-registry.home}"
registry_ip="${REGISTRY_IP:-192.168.76.250}"
registry_port="${REGISTRY_PORT:-5000}"
registry_ref="${registry_host}:${registry_port}"

docker_config_path="/etc/docker/daemon.json"
k3s_registry_config_path="/etc/rancher/k3s/registries.yaml"
hosts_path="/etc/hosts"

docker_changed=0
k3s_changed=0

run_as_root() {
  if [[ "${EUID}" -eq 0 ]]; then
    "$@"
  else
    sudo "$@"
  fi
}

file_exists() {
  local target_path="$1"

  run_as_root test -f "$target_path"
}

file_has_content() {
  local target_path="$1"

  run_as_root test -s "$target_path"
}

file_contains_fixed() {
  local target_path="$1"
  local pattern="$2"

  run_as_root grep -Fq "$pattern" "$target_path"
}

write_file_as_root() {
  local target_path="$1"
  local tmp_file

  tmp_file="$(mktemp)"
  cat > "$tmp_file"
  run_as_root mkdir -p "$(dirname "$target_path")"
  run_as_root cp "$tmp_file" "$target_path"
  rm -f "$tmp_file"
}

ensure_hosts_entry() {
  if grep -Eq "[[:space:]]${registry_host}([[:space:]]|$)" "$hosts_path"; then
    if grep -Eq "^${registry_ip}[[:space:]]+${registry_host}([[:space:]]|$)" "$hosts_path"; then
      echo "$hosts_path already maps ${registry_host} to ${registry_ip}"
      return
    fi

    echo "error: $hosts_path already contains ${registry_host} with a different value" >&2
    echo "Update $hosts_path manually before re-running this script." >&2
    exit 1
  fi

  echo "Adding ${registry_host} to $hosts_path"
  printf '%s %s\n' "$registry_ip" "$registry_host" | run_as_root tee -a "$hosts_path" >/dev/null
}

ensure_docker_config() {
  if file_exists "$docker_config_path"; then
    if file_contains_fixed "$docker_config_path" "\"${registry_ref}\""; then
      echo "$docker_config_path already trusts ${registry_ref}"
      return
    fi

    if ! file_has_content "$docker_config_path"; then
      :
    else
      echo "error: $docker_config_path already exists but does not include ${registry_ref}" >&2
      echo "Merge the insecure registry entry manually instead of overwriting the file." >&2
      exit 1
    fi
  fi

  echo "Writing $docker_config_path"
  write_file_as_root "$docker_config_path" <<EOF
{
  "insecure-registries": ["${registry_ref}"]
}
EOF
  docker_changed=1
}

ensure_k3s_registry_config() {
  if file_exists "$k3s_registry_config_path"; then
    if file_contains_fixed "$k3s_registry_config_path" "\"${registry_ref}\"" && file_contains_fixed "$k3s_registry_config_path" "\"http://${registry_ref}\""; then
      echo "$k3s_registry_config_path already trusts ${registry_ref}"
      return
    fi

    if ! file_has_content "$k3s_registry_config_path"; then
      :
    else
      echo "error: $k3s_registry_config_path already exists but does not include ${registry_ref}" >&2
      echo "Merge the mirror configuration manually instead of overwriting the file." >&2
      exit 1
    fi
  fi

  echo "Writing $k3s_registry_config_path"
  write_file_as_root "$k3s_registry_config_path" <<EOF
mirrors:
  "${registry_ref}":
    endpoint:
      - "http://${registry_ref}"
EOF
  k3s_changed=1
}

restart_docker_if_needed() {
  if [[ "$docker_changed" -eq 0 ]]; then
    return
  fi

  if command -v systemctl >/dev/null 2>&1; then
    echo "Restarting docker"
    run_as_root systemctl restart docker
  fi
}

restart_k3s_if_needed() {
  if [[ "$k3s_changed" -eq 0 ]]; then
    return
  fi

  if command -v systemctl >/dev/null 2>&1 && systemctl list-unit-files | grep -q '^k3s\.service'; then
    echo "Restarting k3s"
    run_as_root systemctl restart k3s
  fi
}

ensure_hosts_entry
ensure_docker_config
ensure_k3s_registry_config
restart_docker_if_needed
restart_k3s_if_needed
