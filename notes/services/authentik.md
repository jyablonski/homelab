# Authentik Notes

## What It Is

Authentik is a self-hosted identity provider. In this homelab, it is meant to become the single login layer for services that otherwise have separate, weak, or awkward authentication.

Instead of every service handling auth differently, Authentik can sit in front of them as the source of truth for:

- users
- groups
- SSO sessions
- OAuth2 / OIDC providers
- access policies
- login and logout flows

Think of it as the local version of "Log in with Google," except owned by the homelab.

## Why Use It

The current cluster exposes several useful admin surfaces:

- Grafana
- Longhorn
- Pi-hole
- Prometheus
- Home Assistant

Some have their own auth. Some are intentionally simple. Some should not be exposed casually. Authentik gives one place to decide who can reach what.

The main value is consistency. You can create one user, one session, and one set of access rules instead of separately managing service-specific accounts and tokens.

## Problems It Solves

Authentik helps with:

- replacing shared default credentials
- avoiding long-lived dashboard tokens where possible
- putting SSO in front of tools that do not have great built-in auth
- centralizing access when the lab grows beyond one person or one workstation
- making admin UIs feel like one secured environment

It does not solve everything by itself. You still need stable DNS, ingress, secrets, and persistence. It also adds another moving part, so it should not become a hard dependency before the cluster is stable enough to justify it.

## Current Repo State

The Helmfile release exists in `helmfile.yaml` and deploys Authentik into the `authentik` namespace.

Current values live in:

- `services/authentik/values.yaml`
- `services/authentik/secrets.sops.yaml`

The current setup uses:

- external Postgres at `postgres.postgres.svc.cluster.local`
- bundled Redis
- Traefik ingress at `authentik.home`

This is enough for a first real integration while still keeping Authentik optional during first boot.

## First Setup

Authentik cannot fully bootstrap itself from Terraform on a brand-new cluster because Terraform needs an Authentik API token first. The first run is intentionally a two-step process.

1. Start the cluster:

   ```bash
   make up
   ```

   If `TF_VAR_authentik_token` is not set, `make up` deploys Authentik and skips Terraform with a message explaining the next step.

2. Open Authentik:

   ```text
   http://authentik.home/if/flow/initial-setup/
   ```

3. Create the initial admin user and log in.

4. Create an API token in Authentik.

   The token is used by Terraform to create Authentik providers, applications, and Kubernetes Secrets. If the copy button does not work over `http://authentik.home`, use a local port-forward because browser clipboard APIs are restricted on plain HTTP hostnames:

   ```bash
   kubectl -n authentik port-forward svc/authentik-server 9000:80
   ```

   Then open `http://localhost:9000` and create/copy the token there.

5. Add a password for the Terraform-managed homelab admin user in SOPS:

   ```bash
   sops services/authentik/secrets.sops.yaml
   ```

   Under `authentik`, set `homelab_admin_password` (plaintext in the editor; SOPS encrypts on save). Defaults for the user itself are in `terraform/variables.tf` (`jyablonski`, `jacob`, `jyablonski9@gmail.com`).

6. Export the token and apply the Terraform-managed Authentik config:

   ```bash
   export TF_VAR_authentik_token='<token>'
   make authentik-apply
   ```

   `make authentik-apply` reads the bootstrap API token from the cluster, loads `homelab_admin_password` from SOPS, and applies Terraform. That creates the `jyablonski` internal admin (member of `homelab-admins`), OAuth/OIDC apps, Kubernetes Secrets, and restarts consuming workloads.

   Keep `akadmin` for bootstrap/API automation; use `jyablonski` for day-to-day Authentik admin login. Password changes in the UI are not reconciled by Terraform (`lifecycle.ignore_changes` on `password`).

`make down` removes local Terraform state because the cluster, Authentik database, and Kubernetes Secrets are also destroyed. The provider lock file is intentionally kept.

## Terraform Involvement

The files under `terraform/` define Authentik resources such as:

- OAuth2 providers
- Authentik applications
- generated client secrets
- Kubernetes Secrets containing OAuth client credentials

Terraform currently writes:

- `grafana-oauth-secret` in the `monitoring` namespace
- `django-oauth-secret` and `runner-oauth-secret` in the `apps` namespace

The Authentik API token is only for Terraform to administer Authentik. The generated OAuth client IDs and secrets are what integrated apps use to authenticate themselves to Authentik during login.

## Current Integrations

Grafana works as the first native OIDC integration.

Terraform creates the Grafana OAuth provider/application in Authentik and writes `grafana-oauth-secret`. The Grafana chart then reads that Secret through environment variables:

```text
GF_AUTH_GENERIC_OAUTH_CLIENT_ID
GF_AUTH_GENERIC_OAUTH_CLIENT_SECRET
```

Browser-facing OAuth URLs use `http://authentik.home` (Pi-hole / workstation DNS). Pods use the in-cluster Authentik service for token and userinfo calls (`authentik-server.authentik.svc.cluster.local`), matching Grafana and the Terraform-managed `OIDC_*_URL` keys in app OAuth secrets. Do not use per-pod `hostAliases` to pin Traefik IPs for SSO.

Django and Runner use native OIDC with the `groups` scope; `homelab-admins` maps to Django staff/superuser and Authentik admin via Terraform.

## Other SSO Candidates

Good native OIDC candidates:

- Runner, because it has a browser-facing UI for running approved jobs. Authentik could provide login, and Runner could authorize actions based on groups such as `runner-users` or `homelab-admins`.
- Django, because it has a browser-facing admin interface and Django has mature OIDC/social-auth libraries. Authentik groups could map to Django staff, superuser, or app-specific permissions.
- Grafana role mapping, using Authentik groups to assign Grafana Admin, Editor, or Viewer. Grafana already supports Authentik login; role mapping would make authorization less manual.
- Home Assistant only after checking its auth model carefully; it has its own user/session system and may not be worth forcing early.

The `api` service is not a good first SSO target because it does not currently expose a frontend login surface. It may still need auth later for API clients or service-to-service calls, but Runner and Django are better next steps for user-facing SSO.

Good ingress-gated candidates:

- Prometheus, because it has little useful built-in auth in this setup.
- Longhorn UI, because it is an admin surface that should not be casually exposed.
- Pi-hole admin, if you want Authentik to gate access before Pi-hole's own login.

The ingress-gated pattern protects access before traffic reaches the app. It does not necessarily make the app aware of the Authentik user. Native OIDC is better when the app needs user identity, roles, or per-user audit behavior.
