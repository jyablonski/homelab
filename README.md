# Homelab

Repo to store Homelab setup & resources

Run `make up` to spin up a K3s Cluster which downloads & sets up the following services:

1. [Prometheus](http://localhost:9090)
2. [Grafana](http://localhost:3000)
    - Username: `admin`
    - Password: `admin`
3. [Home Assistant](http://localhost:8123/)
4. [Postgres](http://)

When finished, run `make down`