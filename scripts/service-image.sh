#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'EOF'
Usage:
  scripts/service-image.sh build <app> [tag] [registry] [namespace]
  scripts/service-image.sh push <app> [tag] [registry] [namespace]
  scripts/service-image.sh build-push <app> [tag] [registry] [namespace]
  scripts/service-image.sh image-ref <app> [tag] [registry] [namespace]

Defaults:
  tag: dev
  registry: registry.home:5000
  namespace: homelab
EOF
}

if [[ $# -lt 2 ]]; then
  usage
  exit 1
fi

action="$1"
service="$2"
tag="${3:-dev}"
registry="${4:-registry.home:5000}"
namespace="${5:-homelab}"

if ! command -v git >/dev/null 2>&1; then
  echo "error: git is required but not found in PATH"
  exit 1
fi

repo_root="$(git rev-parse --show-toplevel)"
service_dir="$repo_root/apps/$service"
dockerfile="$service_dir/Dockerfile"
image_ref="$registry/$namespace/$service:$tag"

if [[ ! -d "$service_dir" ]]; then
  echo "error: app directory not found: $service_dir"
  exit 1
fi

if [[ ! -f "$dockerfile" ]]; then
  echo "error: Dockerfile not found: $dockerfile"
  exit 1
fi

case "$action" in
  build)
    if ! command -v docker >/dev/null 2>&1; then
      echo "error: docker is required but not found in PATH"
      exit 1
    fi
    echo "Building $image_ref from $service_dir"
    docker build -t "$image_ref" "$service_dir"
    ;;
  push)
    if ! command -v docker >/dev/null 2>&1; then
      echo "error: docker is required but not found in PATH"
      exit 1
    fi
    echo "Pushing $image_ref"
    docker push "$image_ref"
    ;;
  build-push)
    if ! command -v docker >/dev/null 2>&1; then
      echo "error: docker is required but not found in PATH"
      exit 1
    fi
    echo "Building $image_ref from $service_dir"
    docker build -t "$image_ref" "$service_dir"
    echo "Pushing $image_ref"
    docker push "$image_ref"
    ;;
  image-ref)
    echo "$image_ref"
    ;;
  *)
    usage
    exit 1
    ;;
esac
