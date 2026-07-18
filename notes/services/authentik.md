# Authentik

## Purpose

Authentik is the homelab identity provider. It owns user identities, groups, login sessions, and OAuth2/OIDC integrations for services that should not manage their own independent administrator accounts.

Authentik authenticates users, while each integrated application remains responsible for deciding what an authenticated user may do. The shared `homelab-admins` group is the current authorization boundary for administrator access.

## Current architecture

Authentik is deployed as an infrastructure Helmfile release in the `authentik` namespace. The current release uses chart version `2026.2.1`, runs one server replica and one worker replica, exposes a `ClusterIP` service, and is reachable through Traefik at `http://authentik.home`.

Authentik uses the shared PostgreSQL service for its `authentik` database and runs a standalone in-cluster Redis instance. PostgreSQL is the durable state store; Redis is used for transient/cache and task-related state.

```text
Browser
    |
    | http://authentik.home
    v
Pi-hole DNS -> Traefik -> Authentik server
                              |
                              |-- PostgreSQL: authentik database
                              `-- Redis: authentik-redis-master

Grafana / Django / Runner
    |-- browser authorization -> http://authentik.home/application/o/authorize/
    `-- server-side token/userinfo/JWKS calls -> authentik-server.authentik.svc.cluster.local
```

The browser-facing and in-cluster OIDC URLs are intentionally split for Django and Runner. Users must reach the authorization endpoint through the `.home` ingress, while backend token and userinfo calls stay on the Kubernetes network. The internal issuer URL must match the `iss` claim in tokens issued by Authentik.

Relevant implementation files are [Authentik values](../../services/authentik/values.yaml), [Helmfile](../../helmfile.yaml), [encrypted secrets](../../services/authentik/secrets.sops.yaml), [bootstrap script](../../scripts/apply-authentik-terraform.sh), [Terraform resources](../../terraform/authentik.tf), and the [OIDC Terraform module](../../terraform/modules/authentik_oidc_app/).

## Secrets

Authentik secrets are stored only in [authentik/secrets.sops.yaml](../../services/authentik/secrets.sops.yaml). Important values include:

- `authentik.secret_key` — Authentik's application secret key.
- `authentik.postgresql.password` — password for the Authentik PostgreSQL user.
- `authentik.bootstrap_password` — initial chart bootstrap password.
- `authentik.bootstrap_token` — bootstrap API token read by the Terraform setup flow.
- `authentik.bootstrap_email` — bootstrap account email configuration.
- `authentik.homelab_admin_password` — password for the Terraform-managed `jyablonski` user.

Never paste decrypted values into Git, logs, tickets, or documentation. Edit the encrypted file with:

```bash
sops ../../services/authentik/secrets.sops.yaml
```

## Bootstrap flow

The Authentik Helm release is labeled `bootstrap: infra`, depends on PostgreSQL, and is installed during the infrastructure phase of `make up`.

The complete `make up` sequence is:

1. Helmfile installs Authentik, PostgreSQL, Traefik, and the other infrastructure releases.
2. `scripts/apply-authentik-terraform.sh` waits for Traefik, the Authentik server, and the Authentik worker.
3. The script waits for `http://authentik.home` and the Authentik API.
4. It reads `AUTHENTIK_BOOTSTRAP_TOKEN` from the Helm-managed Kubernetes Secret.
5. It decrypts only `homelab_admin_password` from the SOPS file.
6. Terraform creates the shared group, admin user, OAuth providers, applications, and Kubernetes Secrets.
7. Grafana, Django, and Runner are restarted so they read the generated OAuth credentials.
8. The app-owned Helmfile phase deploys or updates Django and Runner.

Run the Terraform/bootstrap step again after changing Authentik-managed resources with:

```bash
make authentik-apply
```

`make authentik-apply` requires a running cluster, a reachable `authentik.home`, the bootstrap token, the SOPS age key, and Terraform provider dependencies.

On a first installation, Authentik may require its initial setup flow at `http://authentik.home/if/flow/initial-setup/`. The normal day-to-day user is `jyablonski`; `akadmin` remains the chart/bootstrap account and should not be used for regular application access.

## Terraform-managed identity model

Terraform manages the durable Authentik objects that other services depend on:

- Group `homelab-admins`, configured as an Authentik superuser group.
- User `jyablonski`, placed in `homelab-admins`.
- The `groups` OAuth scope and its property mapping.
- Grafana OAuth2 provider, application, and Kubernetes Secret.
- Django OAuth2 provider, application, and Kubernetes Secret.
- Runner OAuth2 provider, application, and Kubernetes Secret.

The generated Kubernetes Secrets are:

| Secret                 | Namespace    | Consumers |
| ---------------------- | ------------ | --------- |
| `grafana-oauth-secret` | `monitoring` | Grafana   |
| `django-oauth-secret`  | `apps`       | Django    |
| `runner-oauth-secret`  | `apps`       | Runner    |

Terraform generates OAuth client secrets and writes them directly to Kubernetes Secrets. They should not be copied into application values files.

## Integrations

### Grafana

Grafana uses Authentik as its generic OAuth provider. Its login form is disabled and automatic Authentik login is enabled. Authenticated users can sign in through `grafana.home`; group-to-role mapping gives members of `homelab-admins` the Grafana `Admin` role and other authenticated users the configured lower-privilege role.

The Grafana client ID and secret come from `monitoring/grafana-oauth-secret`. Grafana uses the public authorization URL and in-cluster token/userinfo URLs defined in [services/prometheus/values.yaml](../../services/prometheus/values.yaml).

### Django

Django SSO is enabled for the admin interface. The callback is `http://django.home/sso/callback/`. The `homelab-admins` group is required for both Django staff and superuser access.

Local login remains available at `http://django.home/admin/login/?local=1` as an emergency/application-local path when SSO is disabled or unavailable.

### Runner

Runner uses Authentik for its UI/API login flow at `http://runner.home/auth/callback`. The application requires membership in `homelab-admins` through `RUNNER_SSO_ALLOWED_GROUP`.

Runner receives OIDC credentials and its generated session secret from `apps/runner/values.yaml` and `runner-oauth-secret`.

## Adding administrators

To add an administrator, create or invite the user in Authentik and add the user to `homelab-admins`. Group membership grants access to Authentik administration, Django admin, and Runner's protected functionality.

Avoid editing Terraform-managed users or groups manually in the Authentik UI unless the change is intended to be temporary. Changes managed by Terraform may be overwritten on the next `make authentik-apply`.

## Updating application integrations

When adding an OIDC-integrated application:

1. Add an Authentik provider/application module in `terraform/authentik.tf`.
2. Use a strict callback URL for the application.
3. Create the Kubernetes Secret in the application's namespace.
4. Put non-secret OIDC settings in the application's values file.
5. Put client credentials and generated secrets in the Terraform-created Kubernetes Secret.
6. Use the public Authentik URL for browser authorization and the in-cluster URL for backend calls when the application validates tokens internally.
7. Restart the consuming deployment after the generated Secret changes.

## Operational limitations

- Authentik currently runs one server and one worker replica.
- Authentik depends on PostgreSQL, Traefik, Pi-hole/local DNS, and Redis.
- Cluster loss affects new SSO logins and token validation; existing application sessions may continue only until their local session or token expires.
- The current `.home` URLs are LAN-only and are not suitable for public OAuth callbacks.
- `make down` removes the local Terraform working directory and state files after uninstalling the cluster, so the next cluster bootstrap recreates Terraform-managed Authentik resources from configuration.
- Prometheus, Longhorn, and Pi-hole administration are not currently integrated with Authentik SSO.

## Future candidates

Potential future integrations include:

- Traefik forward-auth for services without native OIDC support.
- Native OIDC for Prometheus.
- Native OIDC or forward-auth protection for Longhorn.
- Authentik protection for the Pi-hole admin interface.
- More granular group-to-role mappings than the current shared administrator group.

## Troubleshooting checklist

If SSO is failing, check the layers in this order:

1. `authentik.home` resolves through Pi-hole and reaches Traefik.
2. Authentik server and worker deployments are ready.
3. PostgreSQL and Redis are reachable from the Authentik namespace.
4. The Authentik API accepts the bootstrap token.
5. The consuming application's OAuth Kubernetes Secret exists and contains the expected keys.
6. The callback URL exactly matches the Terraform provider's allowed redirect URI.
7. Backend token/userinfo/JWKS URLs use the in-cluster Authentik service name.
8. The user belongs to `homelab-admins` when the application requires that group.

Useful status checks:

```bash
kubectl -n authentik get pods,svc
kubectl -n authentik get secret authentik
kubectl -n monitoring get secret grafana-oauth-secret
kubectl -n apps get secret django-oauth-secret runner-oauth-secret
```

Do not print Secret contents while troubleshooting.

## References

- [Authentik Helm values](../../services/authentik/values.yaml)
- [Helmfile Authentik release](../../helmfile.yaml)
- [Encrypted Authentik secrets](../../services/authentik/secrets.sops.yaml)
- [Bootstrap script](../../scripts/apply-authentik-terraform.sh)
- [Terraform Authentik resources](../../terraform/authentik.tf)
- [Terraform-managed admin user](../../terraform/homelab_admin.tf)
- [Reusable OIDC application module](../../terraform/modules/authentik_oidc_app/)
