# used to spin a cluster up for the first time
.PHONY: up

up:
	@echo "Starting up the application..."
	@if ! command -v docker >/dev/null 2>&1; then \
		echo "error: docker is required for app image builds during make up"; \
		exit 1; \
	fi
	@echo "Restoring default workstation DNS during cluster bootstrap..."
	@bash ./scripts/setup-local-pihole-dns.sh disable
	@echo "Configuring local registry host access..."
	@bash ./scripts/setup-registry-home.sh
	@echo "Configuring local ingress host access..."
	@bash ./scripts/setup-ingress-home.sh
	@echo "Creating k3s config directory..."
	@sudo mkdir -p /etc/rancher/k3s
	@echo "disable:" | sudo tee /etc/rancher/k3s/config.yaml
	@echo "  - traefik" | sudo tee -a /etc/rancher/k3s/config.yaml
	@echo "  - servicelb" | sudo tee -a /etc/rancher/k3s/config.yaml
	@echo "Installing k3s..."
	@curl -sfL https://get.k3s.io | sh -
	@sleep 10
	@mkdir -p ~/.kube
	@sudo cp /etc/rancher/k3s/k3s.yaml ~/.kube/config
	@sudo chown $(shell echo $$USER):$(shell echo $$USER) ~/.kube/config
	@./scripts/setup.sh
	@echo "Waiting for Pi-hole deployment to become available..."
	@kubectl -n pihole wait --for=condition=available deployment/pihole --timeout=180s
	@echo "Enabling workstation Pi-hole DNS..."
	@bash ./scripts/setup-local-pihole-dns.sh enable
	@bash ./scripts/setup-local-pihole-dns.sh status

# used to sync any helmfile changes to an existing cluster
.PHONY: sync
sync:
	@echo "Syncing Helmfile..."
	@helmfile sync

# used to run the fast local checks that are reasonable on every commit
.PHONY: validate-fast
validate-fast:
	@echo "Running fast validation..."
	@if command -v shellcheck >/dev/null 2>&1; then \
		shellcheck scripts/*.sh; \
	else \
		echo "Skipping shellcheck: not installed"; \
	fi
	@if command -v terraform >/dev/null 2>&1; then \
		terraform -chdir=terraform fmt -check -diff; \
	else \
		echo "Skipping terraform fmt: terraform not installed"; \
	fi

# used to run the same validation flow locally that CI uses
.PHONY: validate
validate: validate-fast
	@echo "Running full validation..."
	@helmfile repos
	@helmfile lint
	@helmfile template > /tmp/homelab-manifests.yaml
	@if command -v kubeconform >/dev/null 2>&1; then \
		kubeconform -strict -summary -ignore-missing-schemas -kubernetes-version 1.31.0 /tmp/homelab-manifests.yaml; \
	else \
		echo "Skipping kubeconform: not installed"; \
	fi
	@if command -v kube-linter >/dev/null 2>&1; then \
		kube-linter lint --config .kube-linter.yaml /tmp/homelab-manifests.yaml; \
	else \
		echo "Skipping kube-linter: not installed"; \
	fi
	@if command -v helm >/dev/null 2>&1 && helm plugin list 2>/dev/null | grep -q unittest; then \
		helm unittest charts/* services/*/chart; \
	else \
		echo "Skipping helm unittest: helm-unittest plugin not installed"; \
	fi
	@if command -v kubeconform >/dev/null 2>&1 && command -v kube-linter >/dev/null 2>&1; then \
		bash scripts/validate-manifests.sh; \
	else \
		echo "Skipping standalone manifest validation: kubeconform and/or kube-linter not installed"; \
	fi

# used to tear down the cluster
.PHONY: down
down:
	@echo "Stopping the Cluster..."
	@echo "Restoring default workstation DNS before cluster teardown..."
	@bash ./scripts/setup-local-pihole-dns.sh disable
	@sudo /usr/local/bin/k3s-uninstall.sh

# check for helm chart updates; prompts y/n before writing helmfile.yaml
.PHONY: update-charts
update-charts:
	@bash scripts/update-charts.sh

# build or push an app-owned image from apps/<name>/Dockerfile
.PHONY: image-build
image-build:
	@if [ -z "$(SERVICE)" ]; then \
		echo "Usage: make image-build SERVICE=<app> [TAG=dev] [REGISTRY=registry.home:5000] [IMAGE_NAMESPACE=homelab]"; \
		exit 1; \
	fi
	@bash scripts/service-image.sh build "$(SERVICE)" "$(or $(TAG),dev)" "$(or $(REGISTRY),registry.home:5000)" "$(or $(IMAGE_NAMESPACE),homelab)"

.PHONY: image-push
image-push:
	@if [ -z "$(SERVICE)" ]; then \
		echo "Usage: make image-push SERVICE=<app> [TAG=dev] [REGISTRY=registry.home:5000] [IMAGE_NAMESPACE=homelab]"; \
		exit 1; \
	fi
	@bash scripts/service-image.sh push "$(SERVICE)" "$(or $(TAG),dev)" "$(or $(REGISTRY),registry.home:5000)" "$(or $(IMAGE_NAMESPACE),homelab)"

.PHONY: image-build-push
image-build-push:
	@if [ -z "$(SERVICE)" ]; then \
		echo "Usage: make image-build-push SERVICE=<app> [TAG=dev] [REGISTRY=registry.home:5000] [IMAGE_NAMESPACE=homelab]"; \
		exit 1; \
	fi
	@bash scripts/service-image.sh build-push "$(SERVICE)" "$(or $(TAG),dev)" "$(or $(REGISTRY),registry.home:5000)" "$(or $(IMAGE_NAMESPACE),homelab)"

.PHONY: image-ref
image-ref:
	@if [ -z "$(SERVICE)" ]; then \
		echo "Usage: make image-ref SERVICE=<app> [TAG=dev] [REGISTRY=registry.home:5000] [IMAGE_NAMESPACE=homelab]"; \
		exit 1; \
	fi
	@bash scripts/service-image.sh image-ref "$(SERVICE)" "$(or $(TAG),dev)" "$(or $(REGISTRY),registry.home:5000)" "$(or $(IMAGE_NAMESPACE),homelab)"

.PHONY: pihole-dns-enable
pihole-dns-enable:
	@bash ./scripts/setup-local-pihole-dns.sh enable

.PHONY: pihole-dns-disable
pihole-dns-disable:
	@bash ./scripts/setup-local-pihole-dns.sh disable

.PHONY: pihole-dns-status
pihole-dns-status:
	@bash ./scripts/setup-local-pihole-dns.sh status
