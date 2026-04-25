# AGENTS.md

Guidance for LLM coding agents working in this repository.

## Purpose

This repo declares a personal K3s homelab in Git. Helmfile is the main source of truth for repositories, chart versions, releases, values, encrypted secrets, release ordering, and bootstrap labels. Third-party service configuration lives under `services/`; app-owned code and Helm values live under `apps/`; shared app deployment behavior lives in `charts/workload`.

## Layout

- `README.md`: human quick start, service table, network flow, roadmap.
- `Makefile`: primary lifecycle, validation, image, DNS, and SOPS commands.
- `helmfile.yaml`: all Helm repos and release definitions.
- `charts/workload/`: local Helm chart for one simple stateless workload.
- `services/`: service values, SOPS secrets, and the local Postgres chart.
- `apps/`: app source, Dockerfiles, chart values, and standalone manifests.
- `scripts/`: bootstrap, DNS, image, chart update, and validation helpers.
- `terraform/`: WIP Authentik/OIDC provider and Kubernetes secret resources.
- `notes/`: operational notes and plans.
- `.github/workflows/validate.yaml`: CI validation pipeline.
- `.pre-commit-config.yaml`: local pre-commit and pre-push hooks.
- `.sops.yaml`: age recipients for `*.sops.yaml`.
- `.kube-linter.yaml`: kube-linter exclusions for local and CI checks.

## High-Value Files

- `helmfile.yaml`: update when adding, removing, or changing releases.
- `charts/workload/values.yaml`: API for the reusable workload chart.
- `charts/workload/templates/`: workload chart Kubernetes resources.
- `charts/workload/tests/workload_test.yaml`: helm-unittest coverage.
- `services/*/values.yaml`: chart-specific service configuration.
- `services/*/secrets.sops.yaml`: encrypted secrets merged by Helmfile.
- `services/metallb/ip-pool.yaml`: standalone MetalLB address pool.
- `apps/workload-chart-example/`: reference app-owned workload.
- `apps/go-cron-test/cronjob.yaml`: standalone manifest used for validation.

## Common Tools

Prefer `make` targets over long hand-written commands. Useful tools include:

- `kubectl`, `helm`, `helmfile`
- `helm-secrets`, `sops`, `age`
- `docker`
- `shellcheck`
- `terraform`
- `kubeconform`, `kube-linter`
- `helm unittest`
- `pre-commit`
- `yq`, `jq`

## Main Commands

```bash
make up                 # install K3s, bootstrap infra, build/push apps, sync apps
make sync               # helmfile sync against an existing cluster
make down               # restore DNS and uninstall local K3s
make validate-fast      # shellcheck and terraform fmt when tools exist
make validate           # full local validation path mirroring CI
make update-charts      # check chart versions and optionally update helmfile.yaml
make image-ref SERVICE=<app> TAG=dev
make image-build-push SERVICE=<app> TAG=dev
make pihole-dns-enable
make pihole-dns-disable
make pihole-dns-status
```

## Bootstrap Model

`make up` restores normal workstation DNS, configures local host entries, installs K3s with bundled Traefik and ServiceLB disabled, writes kubeconfig, runs `scripts/setup.sh`, waits for Pi-hole, then points the workstation at cluster Pi-hole DNS.

`scripts/setup.sh` creates required namespaces, runs `helmfile sync --selector bootstrap=infra`, waits for the local registry, builds and pushes discovered app images from `apps/*`, then runs `helmfile sync --selector bootstrap=app`.

Helmfile labels:

- `bootstrap: infra`: infrastructure and shared services.
- `bootstrap: app`: app-owned workloads that can depend on the registry.

## Network Model

Pinned local endpoints:

- `registry.home` -> `192.168.76.250`
- `apps.home` -> `192.168.76.245`
- Pi-hole DNS service -> `192.168.76.246`

Most browser-facing services resolve through Pi-hole and route through Traefik. The local registry uses a direct MetalLB LoadBalancer IP and bypasses Traefik. For app-owned workloads, prefer `ClusterIP` plus Traefik ingress. Use host-based routes for standalone UIs; use the workload chart's strip-prefix middleware for shared `apps.home` path routes.

## Services

Service configuration lives in `services/`.

- `metallb`: bare-metal LoadBalancer IP assignment.
- `traefik`: ingress controller.
- `longhorn`: default persistent storage.
- `prometheus`: kube-prometheus-stack.
- `grafana`: dashboards and SOPS-managed admin secret.
- `loki`: log aggregation.
- `promtail`: pod log shipping.
- `postgres`: local chart for Postgres 17 and bootstrap SQL.
- `registry`: local OCI registry.
- `pihole`: DNS and `.home` records.
- `headlamp`: Kubernetes dashboard.
- `home-assistant`: home automation.
- `frigate`: NVR/object detection; not deployed by default per README.
- `mosquito`: MQTT broker.
- `authentik`: SSO/OIDC, WIP.
- `keycloak`: values/secrets exist, but no current Helmfile release wires it.

When adding a service:

1. Add `services/<service>/values.yaml`.
2. Add `services/<service>/secrets.sops.yaml` only if secrets are needed.
3. Add or update the release in `helmfile.yaml`.
4. Add `needs:` dependencies when ordering matters.
5. Use `wait: true` when later bootstrap steps depend on readiness.
6. Run validation before handoff.

## App-Owned Workloads

Expected app layout:

```text
apps/<app>/
├── Dockerfile
├── values.yaml
└── <source files>
```

The app directory name becomes the normal image and release name. Image helpers target `registry.home:5000/homelab/<app>:<tag>`.

Use `apps/workload-chart-example/` as the reference. It has Go source, a Dockerfile, `values.yaml` using `charts/workload`, probes, Prometheus metrics, and Traefik shared-host ingress.

When adding an app:

1. Create `apps/<app>/Dockerfile`, `apps/<app>/values.yaml`, and source files.
2. Add a Helmfile release with `chart: ./charts/workload`.
3. Set `labels.bootstrap: app`.
4. Add `needs:` for required infra such as Prometheus or registry.
5. Build and push with `make image-build-push SERVICE=<app> TAG=dev`.
6. Validate Helmfile rendering; add chart tests if chart behavior changed.

## Workload Chart

`charts/workload` is intentionally narrow: one simple stateless deployment.

In scope:

- `Deployment`, single container, optional `Service`, optional `Ingress`.
- Optional Traefik strip-prefix middleware.
- Optional `HorizontalPodAutoscaler`.
- Optional `ServiceMonitor`.
- Env vars, secret/configmap-backed env vars, and `envFrom`.
- Existing Secret/ConfigMap mounts via `extraVolumes` and `extraVolumeMounts`.
- Service account, probes, resources, labels, annotations, scheduling controls.
- Explicit `hostPort` for node-local access.

Out of scope:

- CronJobs, StatefulSets, PVC ownership.
- Sidecars or init containers.
- Multiple service ports.
- Bundled app-specific infra such as databases or queues.

If a workload needs out-of-scope behavior, prefer a separate chart or standalone manifest instead of stretching `charts/workload`.

## Secrets

Secrets live beside normal values files as encrypted `secrets.sops.yaml` files.

- Never commit plaintext secret values.
- Do not decrypt secrets into committed files.
- Add secret files to the release's `secrets:` list in `helmfile.yaml`.
- Edit with `sops services/<service>/secrets.sops.yaml`.
- Inspect with `sops -d ...` only when needed, and avoid pasting decrypted data.
- `.sops.yaml` defines age recipients for every `*.sops.yaml` path.
- CI requires `SOPS_AGE_KEY` to decrypt Helmfile secrets.

## Validation

Use the narrowest useful check while iterating, then run the broadest feasible validation before handoff.

```bash
make validate-fast
make validate
helm unittest charts/* services/*/chart
terraform -chdir=terraform fmt -check -diff
terraform -chdir=terraform init -backend=false
terraform -chdir=terraform validate
```

The full rendered-manifest path is:

```bash
helmfile repos
helmfile lint
helmfile template > /tmp/homelab-manifests.yaml
kubeconform \
  -strict \
  -summary \
  -ignore-missing-schemas \
  -kubernetes-version 1.31.0 \
  /tmp/homelab-manifests.yaml
kube-linter lint --config .kube-linter.yaml /tmp/homelab-manifests.yaml
bash scripts/validate-manifests.sh
```

Pre-commit behavior:

- `make validate-fast` runs at pre-commit.
- `make validate` runs at pre-push.
- YAML and Markdown use Prettier, excluding Helm template paths.

## CI

`.github/workflows/validate.yaml` runs:

- Helm, Helmfile, helm-secrets, and SOPS setup.
- SOPS decryption smoke test.
- `helmfile repos`, `helmfile lint`, and `helmfile template`.
- `kubeconform`, `kube-linter`, and standalone manifest validation.
- `helm unittest charts/* services/*/chart`.
- `shellcheck scripts/*.sh`.
- `pre-commit run --all-files`.
- Terraform fmt, init, and validate.

Keep local validation aligned with CI when changing validation-sensitive files.

## Editing Conventions

- Prefer small, focused changes.
- Preserve existing YAML style and key ordering where practical.
- Use Helm functions and structured YAML rendering in chart templates.
- Keep chart values backward-compatible unless intentionally changing the API.
- Add or update helm-unittest cases when changing `charts/workload/templates/`.
- Keep shell scripts `bash`, `set -euo pipefail`, and shellcheck-clean.
- Format Terraform with `terraform fmt`.
- Do not edit generated, temporary, or decrypted secret artifacts.
- Do not run destructive cluster or git commands unless explicitly requested.

## Handoff Checklist

Before finishing, report:

- Files changed.
- Validation commands run and results.
- Commands skipped because tools, cluster access, or secrets were unavailable.
- Operational follow-up such as `make sync`, image rebuilds, or SOPS setup.
