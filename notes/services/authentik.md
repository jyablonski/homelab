# Authentik Notes

## What It Is

Authentik is the homelab identity provider: users, groups, SSO sessions, and OAuth2/OIDC for integrated apps.

## Bootstrap (automated)

Prerequisites in `services/authentik/secrets.sops.yaml`:

- `homelab_admin_password` — password for the Terraform-managed admin (`jyablonski` by default)
- Helm/bootstrap values for first chart install (`bootstrap_*`)

`make up` flow:

1. Infra Helmfile sync (Authentik, Traefik, Grafana, …)
2. `scripts/apply-authentik-terraform.sh` — reads `AUTHENTIK_BOOTSTRAP_TOKEN` from the `authentik` Secret, loads `homelab_admin_password` from SOPS, applies `terraform/`
3. App Helmfile sync (Django, Runner, …)

Terraform creates:

- Group `homelab-admins` (Authentik superuser)
- User `jyablonski` in that group
- OAuth providers + Kubernetes Secrets: `grafana-oauth-secret`, `django-oauth-secret`, `runner-oauth-secret`
- OIDC `groups` scope on Django and Runner (admin-only SSO)

Optional first visit: `http://authentik.home/if/flow/initial-setup/` if the chart requires it. Day-to-day login: `jyablonski` (not `akadmin`, which remains for API/bootstrap).

Re-apply: `make authentik-apply`. `make down` drops local Terraform state with the cluster.

## Integrations

**Grafana** — generic OAuth; browser URLs via `authentik.home`, token/userinfo in-cluster. Login form disabled; `auto_login` enabled.

**Django** — admin SSO at `/django/sso/*`. Only `homelab-admins` may complete login; same group sets staff/superuser. Local login: `/django/admin/login/?local=1`.

**Runner** — UI/API SSO under `/runner`. Only `homelab-admins` (`RUNNER_SSO_ALLOWED_GROUP`).

Pods use split OIDC URLs in app secrets (public authorize URL, in-cluster issuer/token/userinfo) so token `iss` validation matches Authentik.

## Adding admins

In the Authentik UI, add users to group `homelab-admins`. They can use Django admin, Runner, and Authentik admin (via group `is_superuser`).

## Other candidates

Ingress-gated (forward auth): Prometheus, Longhorn, Pi-hole admin. Native OIDC follow-ups: Grafana role mapping from groups.
