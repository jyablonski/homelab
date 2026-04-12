#!/usr/bin/env bash
set -euo pipefail

command="${1:-status}"
pihole_dns_ip="${PIHOLE_DNS_IP:-192.168.76.246}"
network_manager_connection="${NM_CONNECTION:-}"

require_command() {
  if ! command -v "$1" >/dev/null 2>&1; then
    echo "error: $1 is required" >&2
    exit 1
  fi
}

default_device() {
  ip route show default | awk '/default/ {print $5; exit}'
}

active_connection() {
  local device

  device="$(default_device)"
  if [[ -z "$device" ]]; then
    echo "error: could not determine the default network device" >&2
    exit 1
  fi

  nmcli -g GENERAL.CONNECTION device show "$device" | head -n1
}

connection_name() {
  if [[ -n "$network_manager_connection" ]]; then
    printf '%s\n' "$network_manager_connection"
    return
  fi

  active_connection
}

reload_connection() {
  local connection

  connection="$(connection_name)"
  nmcli connection up "$connection" >/dev/null
}

status() {
  local connection dns_servers ignore_auto_dns

  connection="$(connection_name)"
  dns_servers="$(nmcli -g ipv4.dns connection show "$connection" | paste -sd ',' -)"
  ignore_auto_dns="$(nmcli -g ipv4.ignore-auto-dns connection show "$connection")"

  echo "Connection: $connection"
  echo "Pi-hole DNS IP: $pihole_dns_ip"
  echo "ipv4.ignore-auto-dns: ${ignore_auto_dns:-<unset>}"
  echo "ipv4.dns: ${dns_servers:-<unset>}"
}

enable() {
  local connection

  connection="$(connection_name)"
  nmcli connection modify "$connection" \
    ipv4.ignore-auto-dns yes \
    ipv4.dns "$pihole_dns_ip"
  reload_connection
  status
}

disable() {
  local connection

  connection="$(connection_name)"
  nmcli connection modify "$connection" \
    ipv4.ignore-auto-dns no \
    ipv4.dns ""
  reload_connection
  status
}

require_command ip
require_command nmcli

case "$command" in
  enable)
    enable
    ;;
  disable)
    disable
    ;;
  status)
    status
    ;;
  *)
    echo "Usage: $0 [enable|disable|status]" >&2
    exit 1
    ;;
esac
