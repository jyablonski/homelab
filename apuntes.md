# Notes

## K3s Setup

K3s is a lightweight distribution for self-hosted small Kubernetes clusters.

- It uses containerd as a default container runtime instead of Docker
- Kind is a competitor tool, but is mainly for ephemeral short-term testing and not long running clusters

By default, k3s comes with Traefik pre-installed as its built-in ingress controller.

- It installs Traefik into the kube-system namespace using static manifests.



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

kubectl get pods --all-namespaces

kubectl get nodes --all-namespaces

kubectl get pvc --all-namespaces
kubectl delete pvc data-postgres-postgresql-0 -n postgres
```

## MetalLB

MetalLB is a LoadBalancer implementation for bare-metal Kubernetes clusters that don’t have a cloud provider’s load balancer.

Normally, on cloud platforms (AWS, GCP, Azure), when you create a Service of type LoadBalancer, the cloud provider automatically provisions an external IP to expose your service. On bare-metal or local clusters like k3s, this doesn’t happen by default.

MetalLB:

- Assigns and manages a pool of external IP addresses for Kubernetes LoadBalancer services in your cluster
- Makes your LoadBalancer service reachable from your local network
- Listens for LoadBalancer services and announces the assigned IPs via standard network protocols (ARP or BGP). This way, network devices know where to route traffic to reach those IPs.

## Pi-hole

Pi-hole is a network-wide ad blocker and DNS sinkhole. It acts as a DNS server that filters out ads, trackers, and malicious domains for all devices on your network.

Devices on your network query Pi-hole instead of your ISP’s DNS. Pi-hole blocks unwanted domains and returns the correct DNS records for allowed sites. It also offers a web interface to monitor and configure blocking rules.

Pi-hole uses an IP from MetalLB's managed pool. After MetalLB assigns an IP, it announces it to the local network so other devices can send DNS queries to it.


## Keycloak

https://github.com/bitnami/charts/tree/main/bitnami