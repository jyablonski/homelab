#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
config_path="${TALOS_CLUSTER_CONFIG:-${1:-$repo_root/talos/cluster.yaml}}"
secrets_path="${TALOS_SECRETS_FILE:-$repo_root/talos/secrets.sops.yaml}"
output_dir="${TALOS_OUTPUT_DIR:-$repo_root/talos/_out}"
common_patch="$repo_root/talos/patches/common.yaml"
longhorn_patch="$repo_root/talos/patches/longhorn.yaml"

for command_name in jq sops talosctl yq; do
  if ! command -v "$command_name" >/dev/null 2>&1; then
    echo "error: $command_name is required" >&2
    exit 1
  fi
done

for required_file in "$config_path" "$secrets_path" "$common_patch" "$longhorn_patch"; do
  if [[ ! -f "$required_file" ]]; then
    echo "error: required file does not exist: $required_file" >&2
    exit 1
  fi
done

yaml_value() {
  local expression="$1"
  local value

  value="$(yq -r "($expression) as \$value | if \$value == null then \"\" else \$value end" "$config_path")"
  if [[ "$value" == "null" ]]; then
    value=""
  fi
  printf '%s' "$value"
}

require_value() {
  local label="$1"
  local value="$2"

  if [[ -z "$value" ]]; then
    echo "error: $label must be set in $config_path" >&2
    exit 1
  fi
}

ipv4_to_int() {
  local address="$1"
  local first second third fourth extra

  IFS=. read -r first second third fourth extra <<< "$address"
  if [[ -n "${extra:-}" || ! "$first" =~ ^[0-9]+$ || ! "$second" =~ ^[0-9]+$ || ! "$third" =~ ^[0-9]+$ || ! "$fourth" =~ ^[0-9]+$ ]]; then
    return 1
  fi
  if ((first > 255 || second > 255 || third > 255 || fourth > 255)); then
    return 1
  fi

  printf '%u' "$(((first << 24) + (second << 16) + (third << 8) + fourth))"
}

validate_ip() {
  local label="$1"
  local address="$2"

  if ! ipv4_to_int "$address" >/dev/null; then
    echo "error: $label is not a valid IPv4 address: $address" >&2
    exit 1
  fi
}

cluster_name="$(yaml_value '.cluster.name')"
talos_version="$(yaml_value '.cluster.talosVersion')"
kubernetes_version="$(yaml_value '.cluster.kubernetesVersion')"
api_vip="$(yaml_value '.cluster.apiVip')"
schematic_id="$(yaml_value '.cluster.schematicId')"
registry_host="$(yaml_value '.cluster.registry.host')"
registry_port="$(yaml_value '.cluster.registry.port')"
network_cidr="$(yaml_value '.network.cidr')"
metallb_start="$(yaml_value '.network.metallbPool.start')"
metallb_end="$(yaml_value '.network.metallbPool.end')"
longhorn_enabled="$(yaml_value '.storage.longhorn.enabled')"

require_value "cluster.name" "$cluster_name"
require_value "cluster.talosVersion" "$talos_version"
require_value "cluster.kubernetesVersion" "$kubernetes_version"
require_value "cluster.apiVip" "$api_vip"
require_value "cluster.schematicId" "$schematic_id"
require_value "cluster.registry.host" "$registry_host"
require_value "cluster.registry.port" "$registry_port"
require_value "network.cidr" "$network_cidr"
require_value "network.metallbPool.start" "$metallb_start"
require_value "network.metallbPool.end" "$metallb_end"

if [[ ! "$schematic_id" =~ ^[a-f0-9]{64}$ ]]; then
  echo "error: cluster.schematicId must be a 64-character lowercase hexadecimal Image Factory ID" >&2
  exit 1
fi
if [[ ! "$registry_port" =~ ^[0-9]+$ ]] || ((registry_port < 1 || registry_port > 65535)); then
  echo "error: cluster.registry.port must be between 1 and 65535" >&2
  exit 1
fi
if [[ "$longhorn_enabled" != "true" && "$longhorn_enabled" != "false" ]]; then
  echo "error: storage.longhorn.enabled must be true or false" >&2
  exit 1
fi

validate_ip "cluster.apiVip" "$api_vip"
validate_ip "network.metallbPool.start" "$metallb_start"
validate_ip "network.metallbPool.end" "$metallb_end"

network_address="${network_cidr%/*}"
network_prefix_length="${network_cidr##*/}"
if [[ "$network_address" == "$network_cidr" || "$network_prefix_length" != "24" ]]; then
  echo "error: network.cidr must be an IPv4 /24 network" >&2
  exit 1
fi
validate_ip "network.cidr address" "$network_address"

network_base_int="$(ipv4_to_int "$network_address")"
network_base_int="$((network_base_int & 0xFFFFFF00))"

require_same_network() {
  local label="$1"
  local address="$2"
  local address_int

  address_int="$(ipv4_to_int "$address")"
  if (((address_int & 0xFFFFFF00) != network_base_int)); then
    echo "error: $label is outside $network_cidr: $address" >&2
    exit 1
  fi
}

require_same_network "cluster.apiVip" "$api_vip"
require_same_network "network.metallbPool.start" "$metallb_start"
require_same_network "network.metallbPool.end" "$metallb_end"

metallb_start_int="$(ipv4_to_int "$metallb_start")"
metallb_end_int="$(ipv4_to_int "$metallb_end")"
api_vip_int="$(ipv4_to_int "$api_vip")"
if ((metallb_start_int > metallb_end_int)); then
  echo "error: the MetalLB pool start must not be greater than its end" >&2
  exit 1
fi
if ((api_vip_int >= metallb_start_int && api_vip_int <= metallb_end_int)); then
  echo "error: cluster.apiVip overlaps the MetalLB pool" >&2
  exit 1
fi

node_count="$(yq -r '.nodes | length' "$config_path")"
if [[ "$node_count" != "3" ]]; then
  echo "error: exactly three control-plane nodes are required; found $node_count" >&2
  exit 1
fi

node_names=()
node_addresses=()
node_interfaces=()
node_install_disk_serials=()
node_install_disk_wwids=()
node_longhorn_selectors=()
node_longhorn_max_sizes=()
node_ephemeral_max_sizes=()

for ((index = 0; index < node_count; index++)); do
  hostname="$(yaml_value ".nodes[$index].hostname")"
  address="$(yaml_value ".nodes[$index].address")"
  interface_name="$(yaml_value ".nodes[$index].interface")"
  install_disk_serial="$(yaml_value ".nodes[$index].installDiskSelector.serial")"
  install_disk_wwid="$(yaml_value ".nodes[$index].installDiskSelector.wwid")"
  longhorn_selector="$(yaml_value ".nodes[$index].longhorn.diskSelector")"
  longhorn_max_size="$(yaml_value ".nodes[$index].longhorn.maxSize")"
  ephemeral_max_size="$(yaml_value ".nodes[$index].longhorn.ephemeralMaxSize")"

  require_value "nodes[$index].hostname" "$hostname"
  require_value "nodes[$index].address" "$address"
  require_value "nodes[$index].interface" "$interface_name"
  validate_ip "nodes[$index].address" "$address"
  require_same_network "nodes[$index].address" "$address"

  if [[ ! "$hostname" =~ ^[a-z0-9]([-a-z0-9]*[a-z0-9])?$ ]]; then
    echo "error: nodes[$index].hostname is not a valid lowercase hostname: $hostname" >&2
    exit 1
  fi
  if [[ -z "$install_disk_serial" && -z "$install_disk_wwid" ]]; then
    echo "error: nodes[$index].installDiskSelector.serial or .wwid must be set" >&2
    exit 1
  fi

  address_int="$(ipv4_to_int "$address")"
  if ((address_int >= metallb_start_int && address_int <= metallb_end_int)); then
    echo "error: nodes[$index].address overlaps the MetalLB pool: $address" >&2
    exit 1
  fi
  if [[ "$address" == "$api_vip" ]]; then
    echo "error: nodes[$index].address must not equal cluster.apiVip" >&2
    exit 1
  fi

  if [[ "$longhorn_enabled" == "true" ]]; then
    require_value "nodes[$index].longhorn.diskSelector" "$longhorn_selector"
    require_value "nodes[$index].longhorn.maxSize" "$longhorn_max_size"
    if [[ "$longhorn_selector" == "system_disk" ]]; then
      require_value "nodes[$index].longhorn.ephemeralMaxSize" "$ephemeral_max_size"
    fi
  fi

  node_names+=("$hostname")
  node_addresses+=("$address")
  node_interfaces+=("$interface_name")
  node_install_disk_serials+=("$install_disk_serial")
  node_install_disk_wwids+=("$install_disk_wwid")
  node_longhorn_selectors+=("$longhorn_selector")
  node_longhorn_max_sizes+=("$longhorn_max_size")
  node_ephemeral_max_sizes+=("$ephemeral_max_size")
done

if [[ "$(printf '%s\n' "${node_names[@]}" | sort -u | wc -l)" -ne "$node_count" ]]; then
  echo "error: node hostnames must be unique" >&2
  exit 1
fi
if [[ "$(printf '%s\n' "${node_addresses[@]}" | sort -u | wc -l)" -ne "$node_count" ]]; then
  echo "error: node addresses must be unique" >&2
  exit 1
fi

if [[ -e "$output_dir" && -n "$(find "$output_dir" -mindepth 1 -maxdepth 1 -print -quit 2>/dev/null)" ]]; then
  echo "error: output directory is not empty: $output_dir" >&2
  echo "Remove it explicitly before regenerating machine configs." >&2
  exit 1
fi

work_dir="$(mktemp -d "${TMPDIR:-/tmp}/homelab-talos-config.XXXXXX")"
trap 'rm -rf "$work_dir"' EXIT
umask 077

plain_secrets="$work_dir/secrets.yaml"
generated_dir="$work_dir/generated"
registry_patch="$work_dir/registry.patch.json"
mkdir -p "$generated_dir"

sops --decrypt --output "$plain_secrets" "$secrets_path"

registry_ref="${registry_host}:${registry_port}"
jq -n --arg registry "$registry_ref" --arg endpoint "http://$registry_ref" '{machine: {registries: {mirrors: {($registry): {endpoints: [$endpoint]}}}}}' > "$registry_patch"

talosctl gen config "$cluster_name" "https://${api_vip}:6443" \
  --with-secrets "$plain_secrets" \
  --talos-version "$talos_version" \
  --kubernetes-version "$kubernetes_version" \
  --install-disk /dev/sda \
  --install-image "factory.talos.dev/metal-installer/${schematic_id}:${talos_version}" \
  --output "$generated_dir" \
  --output-types controlplane,talosconfig \
  --with-docs=false \
  --with-examples=false \
  --config-patch "@$common_patch" \
  --config-patch "@$registry_patch"

for ((index = 0; index < node_count; index++)); do
  node_patch="$work_dir/${node_names[$index]}.patch.json"
  node_config="$work_dir/${node_names[$index]}.yaml"

  jq -n \
    --arg install_disk_serial "${node_install_disk_serials[$index]}" \
    --arg install_disk_wwid "${node_install_disk_wwids[$index]}" \
    --arg interface_name "${node_interfaces[$index]}" \
    --arg api_vip "$api_vip" \
    '{machine: {network: {interfaces: [{interface: $interface_name, dhcp: true, vip: {ip: $api_vip}}]}, install: {diskSelector: ({serial: $install_disk_serial, wwid: $install_disk_wwid} | with_entries(select(.value != "")))}}}' \
    > "$node_patch"
  printf '%s\n' '---' >> "$node_patch"
  jq -n \
    --arg hostname "${node_names[$index]}" \
    '{apiVersion: "v1alpha1", kind: "HostnameConfig", hostname: $hostname, auto: "off"}' \
    >> "$node_patch"

  patch_args=(--patch "@$node_patch")
  if [[ "$longhorn_enabled" == "true" ]]; then
    patch_args+=(--patch "@$longhorn_patch")
  fi
  talosctl machineconfig patch "$generated_dir/controlplane.yaml" "${patch_args[@]}" --output "$node_config"

  if [[ "$longhorn_enabled" == "true" ]]; then
    if [[ -n "${node_ephemeral_max_sizes[$index]}" ]]; then
      printf '%s\n' '---' >> "$node_config"
      jq -n \
        --arg max_size "${node_ephemeral_max_sizes[$index]}" \
        '{apiVersion: "v1alpha1", kind: "VolumeConfig", name: "EPHEMERAL", provisioning: {maxSize: $max_size}}' \
        >> "$node_config"
    fi

    printf '%s\n' '---' >> "$node_config"
    jq -n \
      --arg selector "${node_longhorn_selectors[$index]}" \
      --arg max_size "${node_longhorn_max_sizes[$index]}" \
      '{apiVersion: "v1alpha1", kind: "UserVolumeConfig", name: "longhorn", provisioning: {diskSelector: {match: $selector}, maxSize: $max_size}}' \
      >> "$node_config"
  fi
done

talosctl --talosconfig "$generated_dir/talosconfig" config endpoint "${node_addresses[@]}"

install -d -m 700 "$output_dir"
for node_name in "${node_names[@]}"; do
  install -m 600 "$work_dir/$node_name.yaml" "$output_dir/$node_name.yaml"
done
install -m 600 "$generated_dir/talosconfig" "$output_dir/talosconfig"

echo "Generated three control-plane configs and talosconfig in $output_dir"
echo "These files contain cluster credentials and must remain uncommitted."
