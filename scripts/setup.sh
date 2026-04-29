#!/bin/bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

create_namespace() {
  kubectl create namespace "$1" --dry-run=client -o yaml | kubectl apply -f - >/dev/null
}

discover_local_apps() {
  local app_dir

  for app_dir in "$repo_root"/apps/*; do
    [[ -d "$app_dir" ]] || continue
    [[ -f "$app_dir/Dockerfile" ]] || continue
    [[ -f "$app_dir/values.yaml" ]] || continue
    basename "$app_dir"
  done
}

wait_for_registry() {
  local registry_ip=""
  echo "Waiting for registry deployment to become available..."
  kubectl -n registry wait --for=condition=available deployment/registry-docker-registry --timeout=180s

  echo "Waiting for registry service IP assignment..."
  for ((attempt = 1; attempt <= 60; attempt++)); do
    registry_ip="$(kubectl -n registry get svc registry-docker-registry -o jsonpath='{.status.loadBalancer.ingress[0].ip}' 2>/dev/null || true)"
    if [[ -n "$registry_ip" ]]; then
      break
    fi
    sleep 5
  done

  if [[ -z "$registry_ip" ]]; then
    echo "error: registry service never received a LoadBalancer IP" >&2
    exit 1
  fi

  echo "Waiting for registry endpoint at http://$registry_ip:5000/v2/ ..."
  for ((attempt = 1; attempt <= 60; attempt++)); do
    if curl -fsS "http://$registry_ip:5000/v2/" >/dev/null; then
      echo "Registry is ready at http://$registry_ip:5000"
      return
    fi
    sleep 5
  done

  echo "error: registry endpoint did not become ready" >&2
  exit 1
}

build_and_push_local_apps() {
  local apps=()
  local app

  mapfile -t apps < <(discover_local_apps)

  if [[ ${#apps[@]} -eq 0 ]]; then
    echo "No app-owned workload images found under apps/"
    return
  fi

  for app in "${apps[@]}"; do
    echo "Building and pushing app image: $app"
    bash "$repo_root/scripts/service-image.sh" build-push "$app"
  done
}

# these namespaces have postsync hooks or extra manifests that expect them to exist
create_namespace postgres
create_namespace home-automation
create_namespace metallb-system

echo "Running Helmfile infra bootstrap..."
"$repo_root/scripts/run-with-service-status.sh" bootstrap=infra -- helmfile sync --selector bootstrap=infra

wait_for_registry
build_and_push_local_apps

echo "Running Helmfile app bootstrap..."
"$repo_root/scripts/run-with-service-status.sh" bootstrap=app -- helmfile sync --selector bootstrap=app

# this works to apply the cron job, but ive disabled for now
# feel free to use it to test loki for logs querying as an example
# kubectl apply -f apps/go-cron-test/cronjob.yaml
