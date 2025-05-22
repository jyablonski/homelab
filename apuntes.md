# Notes

## K3s Setup

``` sh
curl -sfL https://get.k3s.io | sh -
sudo kubectl get nodes

mkdir -p ~/.kube
sudo cp /etc/rancher/k3s/k3s.yaml ~/.kube/config
sudo chown $USER:$USER ~/.kube/config

helm repo add pajikos http://pajikos.github.io/home-assistant-helm-chart/
helm repo update
helm install home-assistant pajikos/home-assistant

helm list

helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
helm install kube-prometheus-stack prometheus-community/kube-prometheus-stack --namespace monitoring --create-namespace

kubectl get apiservice v1beta1.metrics.k8s.io
kubectl top nodes

# http://prometheus-server:80
kubectl create configmap grafana-metrics-dashboard \
  --from-file=services/grafana/dashboards/metrics.json \
  --namespace kube-system \
  --dry-run=client -o yaml > grafana-dashboard-configmap.yaml
```