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
- making Grafana, Headlamp, and other admin UIs feel like one secured environment

It does not solve everything by itself. You still need stable DNS, ingress, secrets, and persistence. It also adds another moving part, so it should not become a hard dependency before the cluster is stable enough to justify it.

## Current Repo State

The Helmfile release exists in `helmfile.yaml` and deploys Authentik into the `authentik` namespace.

Current values live in:

- `services/authentik/values.yaml`
- `services/authentik/secrets.sops.yaml`

The current setup uses:

- external Postgres at `postgres.postgres.svc.cluster.local`
- bundled Redis
- a NodePort server on `30080`
- no ingress yet

This is good enough for an experiment, but it is not yet the desired final shape.

## Terraform Involvement

Terraform is intended to configure Authentik after the service exists.

The files under `terraform/` define Authentik resources such as:

- OAuth2 providers
- Authentik applications
- generated client secrets
- Kubernetes Secrets containing OAuth client credentials

In plain terms:

1. Helmfile installs the Authentik service.
2. You create or provide an Authentik API token.
3. Terraform connects to Authentik using that token.
4. Terraform creates SSO integrations for services like Grafana and Headlamp.
5. Terraform writes the generated client credentials back into Kubernetes Secrets.
6. Helm values can later reference those Secrets to enable OIDC login.

This keeps SSO configuration reproducible instead of relying on hand-clicked console setup.

## Current Short-Lived Cluster Reality

Right now the cluster is designed to be turned on briefly and torn down with no meaningful persistence across sessions.

That matters because Authentik stores its state in Postgres. If the database does not persist, then Authentik users, applications, providers, groups, tokens, and flows also disappear.

For the current phase, Authentik should be treated as a learning spike:

- deploy it
- poke around the UI
- wire one low-stakes service
- learn the OIDC flow
- make the setup repeatable

Do not make normal cluster access depend on Authentik yet.

## When To Implement For Real

Wait until the hardware setup is in place before making Authentik the front door.

Good signs that it is time:

- the cluster has stable nodes
- Longhorn or another storage layer persists across restarts
- Postgres data survives cluster cycles
- `.home` DNS records are stable
- Traefik ingress is the normal access path
- SOPS age keys are backed up
- restore procedures are at least lightly tested

At that point Authentik becomes worth the complexity because it can survive long enough to be useful.

## Recommended Implementation Path

1. Keep the current Helmfile release as WIP.
2. Move Authentik from NodePort to Traefik ingress when DNS is stable.
3. Decide which service should be the first OIDC client, probably Grafana.
4. Make Terraform create the Authentik provider and application for that service.
5. Store generated client credentials in Kubernetes Secrets.
6. Update the service Helm values to read those credentials.
7. Repeat for Headlamp only if Headlamp stays in the default install.
