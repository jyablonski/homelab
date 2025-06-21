#!/bin/bash
set -euo pipefail

kubectl create namespace postgres

echo "Running Helmfile..."
helmfile sync

# kubectl apply -f services/go-cron-test/cronjob.yaml