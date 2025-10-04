# Homelab

Personal homelab infrastructure running on K3s with automated deployment via Helmfile.

Run `make up` to spin up a K3s Cluster which downloads & sets up the following services:

1. [Headlamp](http://localhost:8085)
2. [Prometheus](http://localhost:9090)
3. [Grafana](http://localhost:3000)
   - Username: `admin`
   - Password: `admin`
4. [Home Assistant](http://localhost:8123/)
5. [Postgres](http://localhost:5432)
   - Username: `jacob`
   - Password: `password`
6. [Longhorn](http://localhost:30085)

When finished, run `make down`
