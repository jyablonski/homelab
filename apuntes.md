# Notes

## K3s Setup

K3s is a lightweight distribution for self-hosted small Kubernetes clusters.

- It uses containerd as a default container runtime instead of Docker
- Kind is a competitor tool, but is mainly for ephemeral short-term testing and not long running clusters

By default, k3s comes with Traefik pre-installed as its built-in ingress controller.

- It installs Traefik into the kube-system namespace using static manifests.

```sh
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

MetalLB operates in two modes:Layer 2 Mode (simpler, good for your setup):

- Assigns IP addresses from a pool you define
- Uses ARP to announce IPs on your local network
- One node "owns" each IP and handles all traffic
- If that node fails, another node takes over the IP

BGP Mode (more advanced):

- Announces routes via BGP protocol
- True load balancing across nodes
- Requires BGP-capable router

## Pi-hole

Pi-hole is a network-wide ad blocker and DNS sinkhole. It acts as a DNS server that filters out ads, trackers, and malicious domains for all devices on your network.

Devices on your network query Pi-hole instead of your ISP’s DNS. Pi-hole blocks unwanted domains and returns the correct DNS records for allowed sites. It also offers a web interface to monitor and configure blocking rules.

Pi-hole uses an IP from MetalLB's managed pool. After MetalLB assigns an IP, it announces it to the local network so other devices can send DNS queries to it.

## Keycloak

https://github.com/bitnami/charts/tree/main/bitnami

## UI Dashboard

Multiple options:

1. [Lens](https://k8slens.dev/)
2. [Official K8s Dashboard](https://kubernetes.io/docs/tasks/access-application-cluster/web-ui-dashboard/)

## Helmfile

Install binary from [here](https://github.com/helmfile/helmfile) and then run `helmfile init` afterwards. there are multiple important commands:

1. `helmfile diff` - shows the difference between what's in the Kubernetes cluster and what's in the `helmfile.yaml`
2. `helmfile sync` - installs or upgrades all helm releases in `helmfile.yaml`, but doesn't delete releases that are not declared in the helmfile anymore
   - Use this to force helm to install everything
3. `helmfile apply` - runs helmfile diff and will sync afterwards if the diff is successful

```sh
helmfile -l debug sync

```

## Cronjobs

```sh
kubectl apply -f services/go-cron-test/cronjob.yaml

kubectl get cronjobs
kubectl get jobs

kubectl get pods --selector=job-name -o wide

```

## Home Assistant

```sh
# Check the PVC was created
kubectl get pvc -n home-automation

# Check the pod is running with the volume mounted
kubectl describe pod -n home-automation -l app.kubernetes.io/name=home-assistant

# see the actual storage
kubectl get pv
```

## PVC

The Flow:

- StorageClass (local-path) = "I know how to create storage on local filesystem"
- PVC = "I need 5GB of storage"
- StorageClass automatically creates a PV to satisfy the PVC
- Pod mounts the PVC → gets persistent data

## Resources

[K3s Homelab Repo Example 1](https://github.com/humansoftware/self-host-saas-k3s)

## Headlamp

```sh
kubectl create token headlamp -n kube-system --duration=87600h
```
