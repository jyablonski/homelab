#!/bin/bash
set -euo pipefail

echo "Adding Helm repositories..."
# helm repo add metrics-server https://kubernetes-sigs.github.io/metrics-server/
helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
helm repo add grafana https://grafana.github.io/helm-charts
helm repo add pajikos http://pajikos.github.io/home-assistant-helm-chart/
helm repo add mojo2600 https://mojo2600.github.io/pihole-kubernetes/
helm repo add metallb https://metallb.github.io/metallb
helm repo add bitnami https://charts.bitnami.com/bitnami

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
  -n monitoring --create-namespace \
  -f services/prometheus/values.yaml

helm upgrade --install grafana grafana/grafana \
  -n monitoring \
  -f services/grafana/values.yaml

kubectl create configmap postgres-bootstrap \
  --namespace=postgres \
  --from-file=services/postgres/bootstrap.sql

helm upgrade --install postgres bitnami/postgresql \
  -n postgres --create-namespace \
  -f services/postgres/values.yaml

# helm upgrade --install metallb metallb/metallb \
#   -n metallb-system --create-namespace

# helm upgrade --install pihole mojo2600/pihole \
#   -n pihole --create-namespace \
#   -f services/pihole/values.yaml


helm upgrade --install home-assistant pajikos/home-assistant \
  -n home-automation --create-namespace \
  -f services/home-assistant/values.yaml

echo "Applying Config Maps ..."
kubectl apply -f services/grafana/dashboards/metrics-dashboard-configmap.yaml
kubectl apply -f services/metallb/config.yaml

kubectl apply -f services/grafana/ingress.yaml
kubectl apply -f services/home-assistant/ingress.yaml
echo "Setup completed successfully!"
