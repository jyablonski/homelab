# Local Development with Tilt

## Purpose

Describe how the desktop should remain a fast, isolated development environment after the permanent Talos-based homelab cluster exists.

The permanent cluster should run the stable version of the homelab. The desktop should provide a disposable local Kubernetes environment where application changes can be developed and tested before they are committed, reviewed, and deployed to the permanent cluster.

## Recommended Split

Use different tools and clusters for different jobs:

```text
Desktop development:
  K3s + Helmfile + Tilt + local registry

Permanent homelab:
  Talos + Kubernetes + Helmfile initially
  Argo CD optionally later
```

Tilt is a development loop, not the production deployment controller. It watches source files, rebuilds or live-updates application containers, applies local Kubernetes resources, and provides fast feedback while code is changing.

The permanent cluster should use the normal deployment workflow. That can initially be helmfile sync and could later become Argo CD reconciliation if the operational benefits justify the additional system.

## What the Current Tiltfile Already Does

The current Tiltfile targets app-owned workloads rather than the entire infrastructure stack.

It currently:

- Restricts Tilt to an allowed Kubernetes context.
- Renders app releases with helmfile -e dev -l bootstrap=app template.
- Watches Helmfile, the reusable workload chart, application values, and encrypted secret files.
- Builds application images for the local registry.home:5000 registry.
- Live-syncs Python, Node, and other source files into running pods.
- Uses development process commands such as Uvicorn reload and Next.js development mode.
- Rebuilds images when Dockerfiles, dependency lockfiles, or other image inputs change.
- Compiles the Go example locally and syncs the resulting binary into the pod.
- Applies the runner RBAC manifest directly because Helmfile presync hooks do not execute during helmfile template.
- Exposes useful application and health links in the Tilt UI.

The existing values-dev.yaml.gotmpl files also provide a useful environment boundary. They enable development-only commands and single-replica behavior while rendering to empty values outside the dev environment.

## What Tilt Is Good At

### Fast source feedback

Editing application source should usually update the running pod without rebuilding the entire image. The current Python applications sync source into /app, Uvicorn or Django reloads the process, and the Node application runs its development server.

### Application-focused iteration

Tilt can manage the application layer while shared infrastructure such as Postgres, Prometheus, Traefik, and the local registry remains installed in the desktop K3s cluster.

### Local Kubernetes fidelity

Running the applications in Kubernetes catches issues that a host-only development server would miss, including service discovery, environment injection, probes, ingress behavior, mounted secrets, resource settings, and inter-service communication.

### Development visibility

The Tilt UI provides resource logs, build status, live-update status, deployment failures, and links to the running services.

## What Tilt Should Not Do

Tilt should not be pointed at the permanent cluster. It should not:

- Live-sync source into production pods.
- Rebuild or overwrite production image tags.
- Apply development values to production workloads.
- Use production database credentials.
- Push development images to the production registry.
- Manage production infrastructure or persistent data.
- Become the production source of truth.

The production cluster should receive reviewed configuration through the production deployment workflow, not through an active developer process on the desktop.

## Desktop Development Cluster

The desktop should run its own local K3s cluster. It can be created using the existing make up workflow or a future development-specific wrapper around that workflow.

The local cluster should have enough shared infrastructure for the applications to behave realistically:

- Traefik or another ingress controller.
- A local Postgres instance.
- A local container registry.
- Longhorn or another local storage option if the applications require persistent volumes.
- Any infrastructure service required by the application being developed.

The local cluster does not necessarily need every production service. A smaller development profile could omit monitoring, logging, Home Assistant, Pi-hole, Authentik, or other services unless the change under test depends on them.

The current Tiltfile expects infrastructure to already exist because it renders only app releases. A fresh desktop development cluster therefore needs an infrastructure bootstrap before make dev can work.

The intended layering is:

```text
Local K3s bootstrap
  └── shared development infrastructure
        └── Tilt-managed application workloads
```

## Suggested Daily Workflow

The eventual workflow should look like this:

```text
1. Start or select the isolated desktop K3s context.
2. Ensure the local development infrastructure is running.
3. Start Tilt.
4. Edit application source and use live updates.
5. Run tests, migrations, and application checks locally.
6. Commit the change on a feature branch.
7. Open a pull request and let CI validate it.
8. Merge the change.
9. Deploy the reviewed change to the permanent cluster through Helmfile or Argo CD.
```

With the current commands, the rough flow is:

```bash
# One-time or after rebuilding the local cluster
make up

# Start the local application development loop
make dev

# Apply new Django migrations manually when needed
make migrate

# Stop Tilt-managed application resources
make dev-down

# Remove the disposable local cluster when desired
make down
```

These commands are intentionally different from the future production workflow. make dev should remain a local-development command, while production deployment should be a separate explicit action.

## Cluster Context Safety

The most important safety property is making it difficult for Tilt to target the permanent cluster accidentally.

The current Tiltfile uses an allowed context named default. That is useful today, but the context name should become an explicit development-only name before the permanent cluster is introduced. For example:

```text
homelab-dev
homelab-prod
```

The Tiltfile should allow only homelab-dev. Production should use a different context and should be rejected by Tilt before any resources are applied.

The Makefile and helper scripts should eventually make the distinction equally obvious. A future make dev wrapper could verify the active context, while production deployment could require an explicit production context or a separate command.

The goal is defense in depth:

```text
Tilt allowlist
  + explicit kubeconfig context names
  + separate registry and image names
  + separate DNS/ingress names
  + separate secrets
  = low chance of accidental production changes
```

## Registry and Image Isolation

The current development workflow targets:

```text
registry.home:5000/homelab/<app>:dev
```

That is appropriate for a local development registry, but it becomes dangerous if the desktop and permanent cluster use the same registry and mutable dev tags at the same time. A local Tilt build could overwrite an image that production is using.

The safer future design is:

```text
Development:
  registry.dev.home:5000/homelab/<app>:dev

Production:
  production registry or registry.home:5000/homelab/<app>:release-<version>
```

At minimum, development and production should have separate registries or separate image namespaces. Immutable production tags or image digests should be used for the permanent cluster.

The desktop build process should remain fast and disposable. The production build process should produce a traceable image from a reviewed commit and publish a version that the production deployment explicitly references.

## DNS and Ingress Isolation

The current applications use .home hostnames such as api.home, agenda.home, and grafana.home. That works when the desktop is the only cluster using the local DNS configuration, but it becomes ambiguous if the desktop development cluster and permanent cluster run at the same time.

Before both clusters are used concurrently, introduce a clear naming scheme, for example:

```text
Development:
  api.dev.home
  agenda.dev.home
  registry.dev.home

Permanent cluster:
  api.home
  agenda.home
  registry.home
```

The exact suffix is less important than ensuring that a browser request or Docker push cannot silently resolve to the wrong cluster.

The development DNS layer could use a local resolver, /etc/hosts, a dedicated Pi-hole configuration, or another split-DNS arrangement. The permanent cluster should not depend on the desktop's Pi-hole being active.

This likely requires values changes because the current development overlays mainly change process arguments and replica behavior; they do not yet provide a separate ingress-host convention.

## Secrets and Development Data

The local cluster should never use production credentials or production data unless there is a deliberate, documented reason.

The current Tiltfile watches application secrets.sops.yaml files, and Helmfile decrypts them during development rendering. Once a permanent cluster exists, this should be reviewed carefully because the same encrypted files may currently be used for both local and future production environments.

Prefer separate encrypted development secrets where necessary:

```text
services/postgres/secrets-dev.sops.yaml
services/postgres/secrets.sops.yaml
apps/api/secrets-dev.sops.yaml
apps/api/secrets.sops.yaml
```

Development secrets should use disposable credentials, local OAuth redirect URLs, local API keys, and non-production tokens. Development databases should be initialized with safe test data or empty schemas rather than copies of private production data.

If the same secret file is intentionally shared, that should be an explicit decision rather than an accidental consequence of Helmfile values merging.

## Shared Configuration Versus Environment Differences

The local and permanent clusters should share as much application behavior as possible:

- Application source code.
- Dockerfiles.
- The reusable workload chart.
- Base Helm values.
- Service names and internal API contracts.
- Health checks and metrics configuration.
- SOPS file structure and secret key names.
- CI validation and test commands.

They should differ where the environment genuinely differs:

- Kubernetes context.
- Image registry and image tag policy.
- Ingress hostnames.
- Replica counts and autoscaling.
- Development reload commands.
- Resource requests and limits.
- Persistent storage settings.
- External OAuth redirect URLs.
- Development versus production credentials.
- Monitoring and logging scope.

The existing values-dev.yaml.gotmpl pattern is a reasonable starting point for process and replica differences. It should not become a place to hide broad infrastructure divergence indefinitely; larger differences should eventually be represented as clearly named environment values or separate profiles.

## Database Migrations

Database migrations should remain an explicit development action. The current entrypoint only migrates an uninitialized database, and the repository already provides make migrate.

The local workflow should therefore be:

```text
Edit model/schema
  -> generate migration
  -> review migration
  -> run make migrate against local Postgres
  -> test application behavior
```

The production migration path should remain separate and deliberate. A local Tilt reload should not automatically run migrations against any database other than the isolated local development database.

## Relationship to Production Helmfile or Argo CD

Tilt should not need to know whether production eventually uses Helmfile or Argo CD. Its job is to render and apply the local development application layer.

The desired repository flow is:

```text
Feature branch
  └── local K3s + Tilt
        └── fast source feedback and integration testing
              └── pull request and CI validation
                    └── merge to main
                          └── production Helmfile sync or Argo CD reconciliation
```

The same Helm chart and application values can support both environments, while Tilt selects the local development values and image workflow.

If Argo CD is adopted later, it should manage only the permanent cluster. The desktop should continue using Tilt because continuous Git reconciliation is not a substitute for live source syncing and reload-based development.

## Possible Future Commands

The current commands are sufficient for now, but the long-term operator experience could become more explicit:

```bash
make dev-up       # start or bootstrap the isolated desktop K3s cluster
make dev          # start Tilt against the development context
make dev-migrate  # apply local database migrations
make dev-down     # stop Tilt-managed resources
make dev-reset    # intentionally destroy and recreate local state
make sync         # manually deploy the permanent cluster if Helmfile remains
```

These are proposed commands rather than current Makefile targets. The important design decision is the separation between local development lifecycle commands and permanent-cluster deployment commands.

## Recommendation

Keep using the current K3s plus Tilt workflow on the desktop. It is already aligned with the desired local development experience and is appropriate for an ephemeral environment.

When the mini-PCs arrive, set up Talos and the permanent Kubernetes cluster independently. Initially continue using Helmfile for production deployment so the operating-system migration and deployment-controller migration do not happen at the same time.

Keep the desktop development cluster separate and disposable. Start it with the shared infrastructure required by the applications, then run Tilt only against the development context and development registry.

Before the two environments run concurrently, add explicit isolation for Kubernetes contexts, registry endpoints, image tags, DNS names, ingress hosts, and secrets. This is more important than whether the permanent cluster eventually uses Helmfile or Argo CD.

Explore Argo CD later if the permanent cluster would benefit from continuous reconciliation, drift correction, deployment history, or eliminating manual production sync commands. Argo CD should manage the permanent cluster; Tilt should remain the fast local development loop.

## References

- [Tiltfile](../../Tiltfile)
- [Makefile](../../Makefile)
- [helmfile.yaml](../../helmfile.yaml)
- [Tilt documentation](https://docs.tilt.dev/)
- [Tilt live update](https://docs.tilt.dev/live_update_reference.html)
