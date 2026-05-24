# K3s server config

`config.yaml` is copied to `/etc/rancher/k3s/config.yaml` during `make up` before K3s is installed. It disables bundled Traefik and ServiceLB so Helm-managed Traefik and MetalLB can own ingress and LoadBalancer IPs.
