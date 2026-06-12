# used to spin a cluster up for the first time
.PHONY: up

up:
	@echo "Starting up the application..."
	@if ! command -v docker >/dev/null 2>&1; then \
		echo "error: docker is required for app image builds during make up"; \
		exit 1; \
	fi
	@echo "Preparing sudo access..."
	@sudo -v
	@./scripts/run-step.sh "Running DNS bootstrap" -- bash ./scripts/setup-local-pihole-dns.sh disable
	@./scripts/run-step.sh "Configuring registry access" -- bash ./scripts/setup-registry-home.sh
	@./scripts/run-step.sh "Configuring ingress access" -- bash -c 'INGRESS_HOSTS="apps.home authentik.home grafana.home" bash ./scripts/setup-ingress-home.sh'
	@./scripts/run-step.sh "Writing K3s config" -- bash -c 'sudo mkdir -p /etc/rancher/k3s && sudo cp services/k3s/config.yaml /etc/rancher/k3s/config.yaml'
	@./scripts/run-step.sh "Installing K3s" -- bash -c 'curl -sfL https://get.k3s.io | sh -'
	@./scripts/run-step.sh "Waiting for K3s startup" -- sleep 10
	@./scripts/run-step.sh "Configuring kubeconfig" -- bash -c 'mkdir -p ~/.kube && sudo cp /etc/rancher/k3s/k3s.yaml ~/.kube/config && sudo chown "$$(id -un):$$(id -gn)" ~/.kube/config'
	@echo "Starting cluster services..."
	@./scripts/setup.sh
	@./scripts/run-step.sh "Checking Pi-hole readiness" -- kubectl -n pihole wait --for=condition=available deployment/pihole --timeout=180s
	@./scripts/run-step.sh "Enabling workstation DNS" -- bash ./scripts/setup-local-pihole-dns.sh enable
	@./scripts/run-step.sh "Checking workstation DNS" -- bash ./scripts/setup-local-pihole-dns.sh status
	@echo "Cluster startup complete."

# used to sync any helmfile changes to an existing cluster
.PHONY: sync
sync:
	@echo "Syncing Helmfile..."
	@helmfile sync

# Tilt dev loop for apps/* (live code reload, helm re-render, image rebuilds)
.PHONY: dev
dev:
	@tilt up

# stop the dev loop and remove Tilt-managed app resources (make sync restores them)
.PHONY: dev-down
dev-down:
	@tilt down

.PHONY: authentik-apply
authentik-apply:
	@./scripts/apply-authentik-terraform.sh

# Django manage.py via kubectl. Escape hatch: make django-manage ARGS="shell"

_FIRST_GOAL := $(firstword $(MAKECMDGOALS))

MIGRATE_EXTRAS := $(if $(filter migrate,$(_FIRST_GOAL)),$(wordlist 2,$(words $(MAKECMDGOALS)),$(MAKECMDGOALS)),)
MIGRATIONS_EXTRAS := $(if $(filter migrations,$(_FIRST_GOAL)),$(wordlist 2,$(words $(MAKECMDGOALS)),$(MAKECMDGOALS)),)
SHOWMIGRATIONS_EXTRAS := $(if $(filter showmigrations,$(_FIRST_GOAL)),$(wordlist 2,$(words $(MAKECMDGOALS)),$(MAKECMDGOALS)),)

STUBS_RAW := $(strip $(MIGRATE_EXTRAS) $(MIGRATIONS_EXTRAS) $(SHOWMIGRATIONS_EXTRAS))
# Trailing words must be stub targets; exclude real Makefile goals so we never override them.
_RESERVED_FOR_STUB := up sync dev dev-down authentik-apply down validate validate-fast update-charts django-manage image-build image-push image-build-push image-ref pihole-dns-enable pihole-dns-disable pihole-dns-status sops-age-generate migrate migrations showmigrations
STUBS := $(filter-out $(_RESERVED_FOR_STUB),$(STUBS_RAW))

ifneq ($(STUBS),)
.PHONY: $(STUBS)
$(STUBS):
	@:
endif

.PHONY: migrate migrations showmigrations django-manage
migrate:
	@scripts/django-manage.sh migrate $(MIGRATE_EXTRAS)

migrations:
	@scripts/django-manage.sh makemigrations $(MIGRATIONS_EXTRAS)

showmigrations:
	@scripts/django-manage.sh showmigrations $(SHOWMIGRATIONS_EXTRAS)

django-manage:
	@if [ -z "$(ARGS)" ]; then \
		echo 'Usage: make django-manage ARGS="<manage.py arguments>"'; \
		echo 'Example: make django-manage ARGS=shell'; \
		exit 1; \
	fi
	@scripts/django-manage.sh $(ARGS)

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
	@rm -rf terraform/.terraform terraform/terraform.tfstate terraform/terraform.tfstate.*

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

.PHONY: sops-age-generate
sops-age-generate:
	@if [ -z "$(BACKUP_KEY_PATH)" ]; then \
		echo "Usage: make sops-age-generate BACKUP_KEY_PATH=<path>"; \
		exit 1; \
	fi
	@bash ./scripts/setup-sops-age.sh "$(BACKUP_KEY_PATH)"
