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

MetalLB operates in two modes:Layer 2 Mode (simpler):

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
- Pod mounts the PVC -> gets persistent data

## Resources

[K3s Homelab Repo Example 1](https://github.com/humansoftware/self-host-saas-k3s)

## Headlamp

```sh
kubectl create token headlamp -n kube-system --duration=87600h
```

## Authentik

Authentik is an identity provider that enables Single Sign-On (SSO) across the homelab services. Instead of managing separate usernames and passwords for each service, you log in once through Authentik.

Status: Deployed but not configured. Won't be used until the homelab runs 24/7 on dedicated hardware.

### Setup Instructions (Future)

Once the cluster is running 24/7:

Option 1: Manual Setup

1. Access Authentik at `http://localhost:30080/if/flow/initial-setup/`
2. Set admin password and create an API token
3. Create OAuth applications for each service (Grafana, Headlamp, Prometheus)
4. Copy Client ID and Secret for each application
5. Update `values.yaml` files for each service with the credentials
6. Run `helmfile sync` to apply OAuth configuration
7. Services will now show "Sign in with Authentik" option

Option 2: Automated Setup with Terraform

1. Access Authentik and create an API token (Admin Interface -> Tokens)
2. Export the token: `export TF_VAR_authentik_token='your-token'`
3. Run `make terraform-init && make terraform-apply`
4. Terraform will automatically:
   - Create OAuth applications for Grafana and Headlamp
   - Generate and store credentials in Kubernetes secrets
   - Configure services to use Authentik SSO
5. Run `helmfile sync` to pick up the new configuration

Note - for option 2, you'd also have to update the makefile command to do the following:

1. Spin up the cluster & all srevices
2. Verify that authentik & postgres are up
3. Run `terraform apply` in that terraform repo
4. Run `helmfile sync` to update the services after the secrets get built by terraform

Services with SSO Support:

- Grafana (native OAuth2 support)
- Headlamp (native OIDC support)
- Prometheus (requires Traefik Forward Auth - more complex setup)

## Scratch

```sh
helm show values headlamp/headlamp | grep -A 20 configp -A 20 config
```

## Headlamp Token

- `kubectl create token headlamp -n kube-system --duration=8760h`

- you have to generate a token that lasts a long time because headlamp doesn't support insecure auth yet for some fucking dumbass reason

## Cron Jobs

```sh
kubectl get cronjobs
kubectl get jobs
```
