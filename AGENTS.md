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
- `notes/services/<service>.md`: service-level architecture, operational runbooks, bootstrap flows, integrations, and troubleshooting; keep these documents under `notes/services/` rather than inside each service configuration directory.
- `apps/`: app source, Dockerfiles, chart values, and standalone manifests.
- `scripts/`: bootstrap, DNS, image, chart update, and validation helpers.
- `talos/`: future three-node Talos cluster inventory, Image Factory schematic, and machine configuration patches; generated configs remain ignored.
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
- `services/*/values.yaml`: chart-specific service configuration, including prepared-but-not-deployed services.
- `services/*/secrets.sops.yaml`: encrypted secrets merged by Helmfile.
- `services/metallb/ip-pool.yaml`: standalone MetalLB address pool.
- `apps/workload-chart-example/`: reference app-owned workload.
- `apps/tools/`: standalone Go tools app, including the backup command and future jobs-only workload.
- `talos/cluster.yaml`: tracked Talos versions and hardware inventory; node-specific values remain empty until verified on physical hardware.
- `talos/schematic.yaml`: Image Factory extensions required by the future Talos nodes.
- `talos/patches/`: hardware-independent Talos machine configuration patches.

## Common Tools

Prefer `make` targets over long hand-written commands. Useful tools include:

- `kubectl`, `helm`, `helmfile`
- `helm-secrets`, `sops`, `age`
- `docker`
- `shellcheck`
- `terraform`
- `talosctl`
- `kubeconform`, `kube-linter`
- `helm unittest`
- `pre-commit`
- `yq`, `jq`

## Main Commands

```bash
make up                 # install K3s, bootstrap infra, build/push apps, sync apps
make sync               # helmfile sync against an existing cluster
make dev                # tilt up: live code reload + helm re-render for apps/*
make dev-down           # tilt down: remove Tilt-managed app resources
make down               # restore DNS and uninstall local K3s
make validate-fast      # shellcheck and terraform fmt when tools exist
make validate           # full local validation path mirroring CI
make update-charts      # check chart versions and optionally update helmfile.yaml
make image-ref SERVICE=api          # example: print the API's default dev image reference
make image-build-push SERVICE=api   # example: build and push the API's default dev image
make pihole-dns-enable
make pihole-dns-disable
make pihole-dns-status
make talos-secrets       # create the SOPS-encrypted Talos cluster identity once
make talos-config        # render ignored machine configs after inventory is complete
make talos-validate      # strictly validate rendered configs for bare metal
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

Most browser-facing services resolve through Pi-hole and route through Traefik. The local registry uses a direct MetalLB LoadBalancer IP and bypasses Traefik. For app-owned workloads, prefer `ClusterIP` plus Traefik ingress. Every app and service gets its own `<name>.home` host (Pi-hole wildcards `*.home` to Traefik); `apps.home` is the gethomepage dashboard. The workload chart's strip-prefix middleware remains available for path-based routing if ever needed.

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
- `homepage`: dashboard for browser-facing apps and services.
- `home-assistant`: home automation.
- `frigate`: NVR/object detection; not deployed by default per README.
- `mosquitto`: MQTT broker for home-automation integrations.
- `zigbee2mqtt`: Zigbee coordinator bridge; configured but disabled until hardware is available.
- `openthread-border-router`: Thread border router; configured but disabled until hardware is available.
- `authentik`: SSO/OIDC; Terraform-managed OAuth apps on `make up`.

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

The app directory name becomes the Helm release name and the image name. Image helpers target `registry.home:5000/homelab/<app>:dev`. Chart defaults exist because this is a single personal homelab (no environment matrix): image repo/tag, pull policy, replica count, component label, and ServiceMonitor scrape settings are inferred unless overridden. See `charts/workload/README.md`.

Use `apps/workload-chart-example/` as the reference. It has Go source, a Dockerfile, a minimal `apps/workload-chart-example/values.yaml`, probes, Prometheus metrics, and Traefik shared-host ingress.

When adding an app:

1. Create `apps/<app>/Dockerfile`, `apps/<app>/values.yaml`, and source files.
2. Add a Helmfile release with `chart: ./charts/workload` and `name: <app>` matching the directory.
3. In `apps/<app>/values.yaml`, set `service.port`, probes, env, and ingress only; omit `image` and `podLabels` unless overriding chart defaults.
4. Set `labels.bootstrap: app`.
5. Add `needs:` for required infra such as Prometheus or registry.
6. Add or update the app section in `Tiltfile` so the local dev loop builds, renders, and live-syncs the new app.
7. Build and push with the `image-build-push` Make target, setting `SERVICE` to the app directory name; for example, `make image-build-push SERVICE=api`.
8. Validate Helmfile rendering; add chart tests if chart behavior changed.

## Workload Chart

`charts/workload` is intentionally narrow: one simple stateless deployment plus optional app-owned CronJobs.

In scope:

- `Deployment`, single container, optional `Service`, optional `Ingress`.
- Jobs-only releases by setting `deployment.enabled: false`; deployment-owned resources are suppressed and autoscaling must remain disabled.
- Optional Traefik strip-prefix middleware.
- Optional `HorizontalPodAutoscaler`.
- Optional `ServiceMonitor`.
- Env vars, secret/configmap-backed env vars, and `envFrom`.
- Existing Secret/ConfigMap mounts via `extraVolumes` and `extraVolumeMounts`.
- Service account, probes, resources, labels, annotations, scheduling controls.
- Explicit `hostPort` for node-local access.

Out of scope:

- StatefulSets and PVC ownership.
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
- `talos/secrets.sops.yaml` is the future cluster identity; generate it once with `make talos-secrets`, never replace it for an existing cluster, and keep an off-cluster backup with the required age keys.

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

- `ty` runs at local pre-commit for each touched app under `apps/api`, `apps/django`, or `apps/runner`; CI uses the Python Quality workflow (`SKIP: ty` in the validate pre-commit job).
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

### CI checkout and triggers

- Use `actions/checkout@v7` with `sparse-checkout` for every focused CI job. Include its working directory and every transitive runtime input such as shared schemas, scripts, Helm charts, fixtures, and config files; use `sparse-checkout-cone-mode: false` when selecting individual files or glob patterns.
- Add `push` and `pull_request` `paths:` filters to focused workflows so unrelated changes do not start them, and keep those filters aligned with the job's actual inputs. The Validation Pipeline is intentionally limited to infrastructure, deployment configuration, scripts, Terraform, and GitHub configuration changes; app source uses its dedicated CI.
- Do not path-filter a job that runs `pre-commit --all-files` unless its repository-wide checks are moved or split first; otherwise changes can evade formatting and hygiene validation.

## Editing Conventions

- Prefer small, focused changes.
- Keep service documentation in `notes/services/<service>.md`; keep service deployment configuration under `services/<service>/`.
- Do not add module docstrings or other top-of-file comment blocks to Python (or other source) files; start with imports or code.
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
