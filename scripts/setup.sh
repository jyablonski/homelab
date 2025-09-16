#!/bin/bash
set -euo pipefail

# these 3 have postsync hooks, so the namespaces have to be created here first before helmfile runs
kubectl create namespace postgres
kubectl create namespace home-automation
kubectl create namespace metallb-system

echo "Running Helmfile..."
helmfile sync

# kubectl apply -f services/go-cron-test/cronjob.yaml