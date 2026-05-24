#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
authentik_url="http://authentik.home"

wait_for_url() {
  local url="$1"

  echo "Waiting for ${url}..."
  for ((attempt = 1; attempt <= 60; attempt++)); do
    if curl -fsS --max-time 5 "$url" >/dev/null; then
      return
    fi
    sleep 5
  done

  echo "error: ${url} did not become reachable" >&2
  exit 1
}

load_homelab_admin_password() {
  if [[ -n "${TF_VAR_homelab_admin_password:-}" ]]; then
    return
  fi

  local secrets_file="$repo_root/services/authentik/secrets.sops.yaml"
  if ! command -v sops >/dev/null 2>&1; then
    echo "error: sops is required to read authentik.homelab_admin_password" >&2
    exit 1
  fi

  TF_VAR_homelab_admin_password="$(
    sops -d --extract '["authentik"]["homelab_admin_password"]' "$secrets_file"
  )"
  export TF_VAR_homelab_admin_password

  if [[ -z "${TF_VAR_homelab_admin_password}" ]]; then
    echo "error: authentik.homelab_admin_password is missing from $secrets_file" >&2
    echo "Run: sops $secrets_file" >&2
    exit 1
  fi
}

load_authentik_token() {
  if [[ -n "${TF_VAR_authentik_token:-}" ]]; then
    return
  fi

  echo "Reading Authentik bootstrap token from Helm-managed secret..."
  TF_VAR_authentik_token="$(kubectl -n authentik get secret authentik -o jsonpath='{.data.AUTHENTIK_BOOTSTRAP_TOKEN}' | base64 -d)"
  export TF_VAR_authentik_token

  if [[ -z "${TF_VAR_authentik_token}" ]]; then
    echo "error: AUTHENTIK_BOOTSTRAP_TOKEN is missing from the authentik secret" >&2
    echo "Set TF_VAR_authentik_token or configure authentik.bootstrap_token in services/authentik/secrets.sops.yaml" >&2
    exit 1
  fi
}

wait_for_authentik_api() {
  local token="$1"
  local api_url="${authentik_url}/api/v3/root/config/"
  local status=""

  echo "Waiting for Authentik API to accept the token..."
  for ((attempt = 1; attempt <= 60; attempt++)); do
    status="$(curl -sS -o /dev/null -w '%{http_code}' --max-time 5 \
      -H "Authorization: Bearer ${token}" \
      "$api_url" 2>/dev/null || true)"

    if [[ "$status" == "200" ]]; then
      echo "Authentik API is ready."
      return
    fi

    if [[ "$attempt" -eq 1 || $((attempt % 6)) -eq 0 ]]; then
      echo "Authentik API not ready yet (HTTP ${status:-unreachable}), retrying..."
    fi
    sleep 5
  done

  echo "error: Authentik API did not accept the token within 5 minutes (last HTTP ${status:-unreachable})" >&2
  exit 1
}

if ! command -v terraform >/dev/null 2>&1; then
  echo "error: terraform is required to apply Authentik resources" >&2
  exit 1
fi

echo "Waiting for Authentik..."
kubectl -n kube-system wait --for=condition=available deployment/traefik --timeout=300s
kubectl -n authentik wait --for=condition=available deployment/authentik-server --timeout=300s
kubectl -n authentik wait --for=condition=available deployment/authentik-worker --timeout=300s
kubectl create namespace apps --dry-run=client -o yaml | kubectl apply -f - >/dev/null
wait_for_url "$authentik_url"

load_authentik_token
load_homelab_admin_password
wait_for_authentik_api "$TF_VAR_authentik_token"

echo "Applying Authentik Terraform..."
terraform -chdir="$repo_root/terraform" init -backend=false
terraform -chdir="$repo_root/terraform" apply -auto-approve

echo "Restarting Grafana to pick up OAuth credentials..."
if kubectl -n monitoring get deployment -l app.kubernetes.io/name=grafana -o name | grep -q .; then
  kubectl -n monitoring rollout restart deployment -l app.kubernetes.io/name=grafana
  kubectl -n monitoring rollout status deployment -l app.kubernetes.io/name=grafana --timeout=180s
else
  echo "Grafana deployment not found; skipping rollout restart."
fi

echo "Restarting app deployments to pick up OAuth credentials..."
for deployment in django runner; do
  if kubectl -n apps get deployment "$deployment" >/dev/null 2>&1; then
    kubectl -n apps rollout restart "deployment/$deployment"
    kubectl -n apps rollout status "deployment/$deployment" --timeout=180s
  else
    echo "$deployment deployment not found; skipping rollout restart."
  fi
done
