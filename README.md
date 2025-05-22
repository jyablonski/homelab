# Homelab

Repo to store Homelab setup & resources

Run `make up` to spin up a K3s Cluster which downloads & sets up the following services:

1. [Prometheus](http://localhost:30090)
2. [Grafana](http://localhost:30080)
3. [Home Assistant](http://localhost:30108/)

When finished, run `make down`