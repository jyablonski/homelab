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
- Headlamp
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

5. Export the token and apply the Terraform-managed Authentik config:

   ```bash
   export TF_VAR_authentik_token='<token>'
   make authentik-apply
   ```

   This runs Terraform, creates the OAuth/OIDC resources, writes client credentials into Kubernetes Secrets, and restarts the workloads that consume those Secrets.

`make down` removes local Terraform state because the cluster, Authentik database, and Kubernetes Secrets are also destroyed. The provider lock file is intentionally kept.

## Terraform Involvement

The files under `terraform/` define Authentik resources such as:

- OAuth2 providers
- Authentik applications
- generated client secrets
- Kubernetes Secrets containing OAuth client credentials

Terraform currently writes:

- `grafana-oauth-secret` in the `monitoring` namespace
- `headlamp-oauth-secret` in the `kube-system` namespace

The Authentik API token is only for Terraform to administer Authentik. The generated OAuth client IDs and secrets are what integrated apps use to authenticate themselves to Authentik during login.

## Current Integrations

Grafana works as the first native OIDC integration.

Terraform creates the Grafana OAuth provider/application in Authentik and writes `grafana-oauth-secret`. The Grafana chart then reads that Secret through environment variables:

```text
GF_AUTH_GENERIC_OAUTH_CLIENT_ID
GF_AUTH_GENERIC_OAUTH_CLIENT_SECRET
```

The browser-facing authorization URL uses `http://authentik.home`, while Grafana's server-side token and userinfo URLs use the in-cluster Authentik service DNS name. This is necessary because the browser can resolve `.home` names through Pi-hole, but pods should use Kubernetes DNS for service-to-service calls.

Headlamp was explored but is not considered working as a simple Authentik SSO integration.

Unlike Grafana, Headlamp's OIDC mode is tied to Kubernetes API authentication. Authentik can complete the login flow, but the Kubernetes API server must also trust Authentik as an OIDC issuer and RBAC must be configured for Authentik users or groups. Without that deeper Kubernetes OIDC setup, Headlamp returns to its login screen. For now, keep Headlamp's existing token/in-cluster access model or protect it later with an ingress-level auth gate instead of native OIDC.

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
- Headlamp, if you want SSO as an access gate without making Authentik a Kubernetes API identity provider.

The ingress-gated pattern protects access before traffic reaches the app. It does not necessarily make the app aware of the Authentik user. Native OIDC is better when the app needs user identity, roles, or per-user audit behavior.
