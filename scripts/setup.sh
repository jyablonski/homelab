#!/bin/bash
set -euo pipefail

echo "Adding Helm repositories..."
helm repo add metrics-server https://kubernetes-sigs.github.io/metrics-server/
helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
helm repo add grafana https://grafana.github.io/helm-charts
helm repo add pajikos http://pajikos.github.io/home-assistant-helm-chart/

echo "Updating Helm repositories..."
helm repo update

echo "Installing/upgrading Helm charts..."

# kubectl delete clusterrole system:metrics-server
# kubectl delete clusterrolebinding system:metrics-server
# helm uninstall metrics-server || true

# kubectl delete clusterrole metrics-server -n kube-system 
# kubectl delete clusterrolebinding metrics-server:system:auth-delegator -n kube-system
# kubectl delete clusterrolebinding metrics-server-auth-reader -n kube-system
# kubectl delete serviceaccount metrics-server -n kube-system
# kubectl delete deployment metrics-server -n kube-system

# helm upgrade --install metrics-server metrics-server/metrics-server
helm upgrade --install prometheus-operator prometheus-community/kube-prometheus-stack \
  -f services/prometheus/values.yaml

helm upgrade --install grafana grafana/grafana \
  -f services/grafana/values.yaml

helm upgrade --install home-assistant pajikos/home-assistant \
  -f services/home-assistant/values.yaml

echo "Applying Grafana dashboards configmap..."
kubectl apply -f services/grafana/dashboards/metrics-dashboard-configmap.yaml

echo "Setup completed successfully!"
