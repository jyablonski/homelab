#!/usr/bin/env bash
set -euo pipefail

for cmd in kubeconform kube-linter mktemp; do
  if ! command -v "$cmd" >/dev/null 2>&1; then
    echo "error: $cmd is required but not found in PATH"
    exit 1
  fi
done

standalone_manifests=(
  services/grafana/ingress.yaml
  services/home-assistant/ingress.yaml
  services/metallb/ip-pool.yaml
  services/go-cron-test/cronjob.yaml
)

tmp_manifest="$(mktemp)"
trap 'rm -f "$tmp_manifest"' EXIT

for manifest in "${standalone_manifests[@]}"; do
  cat "$manifest" >> "$tmp_manifest"
  printf '\n---\n' >> "$tmp_manifest"
done

echo "Validating standalone Kubernetes manifests..."
kubeconform \
  -strict \
  -summary \
  -ignore-missing-schemas \
  -kubernetes-version 1.31.0 \
  "$tmp_manifest"

kube-linter lint --config .kube-linter.yaml "$tmp_manifest"
