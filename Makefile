# used to spin a cluster up for the first time
.PHONY: up

up:
	@echo "Starting up the application..."
	@echo "Creating k3s config directory..."
	@sudo mkdir -p /etc/rancher/k3s
	@echo "disable:" | sudo tee /etc/rancher/k3s/config.yaml
	@echo "  - traefik" | sudo tee -a /etc/rancher/k3s/config.yaml
	@echo "Installing k3s..."
	@curl -sfL https://get.k3s.io | sh -
	@sleep 10
	@mkdir -p ~/.kube
	@sudo cp /etc/rancher/k3s/k3s.yaml ~/.kube/config
	@sudo chown $(shell echo $$USER):$(shell echo $$USER) ~/.kube/config
	@./scripts/setup.sh

# used to sync any helmfile changes to an existing cluster
.PHONY: sync
sync:
	@echo "Syncing Helmfile..."
	@helmfile sync

# used to tear down the cluster
.PHONY: down
down:
	@echo "Stopping the Cluster..."
	@sudo /usr/local/bin/k3s-uninstall.sh
