.PHONY: up

up:
	@echo "Starting up the application..."
	@curl -sfL https://get.k3s.io | sh -
	@sleep 10
	@mkdir -p ~/.kube
	@sudo cp /etc/rancher/k3s/k3s.yaml ~/.kube/config
	@sudo chown $(shell echo $$USER):$(shell echo $$USER) ~/.kube/config
	@./scripts/setup.sh


.PHONY: down
down:
	@echo "Stopping the Cluster..."
	@sudo /usr/local/bin/k3s-uninstall.sh
