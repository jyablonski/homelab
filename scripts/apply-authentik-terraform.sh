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

if [[ -z "${TF_VAR_authentik_token:-}" ]]; then
  cat <<'MSG'
Skipping Authentik Terraform: TF_VAR_authentik_token is not set.
Finish Authentik initial setup, create an API token, then run:
  export TF_VAR_authentik_token='<token>'
  make authentik-apply
MSG
  exit 0
fi

if ! command -v terraform >/dev/null 2>&1; then
  echo "error: terraform is required when TF_VAR_authentik_token is set" >&2
  exit 1
fi

echo "Waiting for Authentik server..."
kubectl -n kube-system wait --for=condition=available deployment/traefik --timeout=300s
kubectl -n authentik wait --for=condition=available deployment/authentik-server --timeout=300s
wait_for_url "$authentik_url"

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

echo "Restarting Headlamp to pick up OAuth credentials..."
if kubectl -n kube-system get deployment headlamp >/dev/null 2>&1; then
  kubectl -n kube-system rollout restart deployment/headlamp
  kubectl -n kube-system rollout status deployment/headlamp --timeout=180s
else
  echo "Headlamp deployment not found; skipping rollout restart."
fi
