# Argo CD and Future Homelab GitOps

## Purpose

Document whether Argo CD should eventually replace the current Helmfile deployment workflow when the homelab moves from ephemeral desktop K3s to a permanent Talos-based cluster.

## Current Context

The current project runs K3s locally on a personal desktop for development. `make up` installs K3s, `scripts/setup.sh` bootstraps infrastructure and applications, and `helmfile.yaml` defines the Helm repositories, releases, values, secrets, dependencies, and hooks.

The future physical homelab is expected to use three mini-PCs with approximately 96 GB of total memory. Talos is a good candidate for those nodes because it is an immutable, Kubernetes-focused operating system with configuration managed through `talosctl` and machine configuration files.

The current and future environments do not need to use the same cluster bootstrap mechanism:

```text
Current desktop:  K3s + Helmfile + Tilt + SOPS
Future homelab:   Talos + Kubernetes + Helmfile or Argo CD + SOPS
```

The Talos design is a future infrastructure plan rather than the current implementation. The reference notes currently describe generated Talos configuration under `~/talos`, while the repository itself contains the K3s bootstrap path.

## What Argo CD Is

Argo CD is a Kubernetes controller and deployment system for GitOps. It watches a Git repository, renders the desired Kubernetes resources, compares them with the live cluster, and optionally synchronizes the cluster automatically.

Argo CD is not an operating system, Kubernetes installer, image builder, secret manager, or Terraform replacement. It starts working after a Kubernetes API is available and Argo CD itself has been bootstrapped.

The basic flow is:

```text
Git commit
    |
    v
Argo CD fetches and renders the desired state
    |
    v
Argo CD compares Git state with live Kubernetes state
    |
    v
Argo CD applies changes and reports health/sync status
```

Argo CD normally refreshes Git repositories periodically. The default reconciliation interval is approximately two to three minutes, and Git webhooks can trigger an earlier refresh when the Argo CD API is reachable by the Git provider.

## Argo CD and Helm Are Complementary

This is not an Argo CD versus Helm decision.

Helm answers:

> How should this application be packaged and templated?

Argo CD answers:

> What should be running in the cluster, and does the live cluster match Git?

A future stack could therefore be:

```text
Talos
  └── Kubernetes
        ├── Helm charts       -> package and render applications
        ├── Argo CD           -> reconcile rendered resources from Git
        ├── SOPS/External Secrets -> provide secrets
        └── Terraform         -> manage external APIs such as Authentik
```

Argo CD can use Helm charts directly. Helm is primarily used to render the chart, while Argo CD manages synchronization and drift rather than relying on Helm's local release lifecycle.

The more relevant choice is whether to keep Helmfile as the deployment orchestrator or eventually express the releases as native Argo CD `Application` resources.

## What Argo CD Would Provide

### Automatic synchronization

After a commit is merged to the tracked branch, Argo CD can render and deploy the change without requiring a manual `helmfile sync` from the desktop.

### Drift correction

With automated self-healing enabled, Argo CD can detect manual changes made with `kubectl` and restore the Git-defined state. This makes the cluster a reconciled runtime rather than a system that depends on remembering to run deployment commands.

### Resource pruning

With automated pruning enabled, Argo CD can remove Kubernetes resources that were intentionally removed from Git. This is useful for maintaining a clean cluster, but it should be enabled only after the migration is understood because a bad commit can delete resources.

### Deployment visibility

Argo CD provides application-level sync status, health, history, rendered manifests, events, and failure details. This would make it easier to answer whether a Git commit was actually deployed and which resource prevented an application from becoming healthy.

### Less dependence on the desktop

The desktop would no longer need to have the cluster's administrative kubeconfig just to deploy ordinary changes. Argo CD would pull the repository and apply changes from inside the cluster.

### Better multi-cluster support

If the homelab eventually grows beyond one cluster, Argo CD can manage multiple Kubernetes destinations from a common Git structure. This is not necessary for the first physical cluster, but it is a useful future capability.

## What Argo CD Would Replace

If the project eventually moves to native Argo CD applications, the mapping would look like this:

| Current workflow                         | Possible Argo CD workflow                                         |
| ---------------------------------------- | ----------------------------------------------------------------- |
| Helmfile release definitions             | Argo CD `Application` or `ApplicationSet` resources               |
| Helmfile chart repositories and versions | Chart source fields on each `Application`                         |
| Helmfile values files                    | Argo CD Helm `valueFiles` or values objects                       |
| `helmfile sync` and `make sync`          | Automated Argo CD synchronization                                 |
| Helmfile `needs` and ordering            | Sync waves plus resource health checks                            |
| `createNamespace: true`                  | Namespace manifests or `CreateNamespace=true`                     |
| Imperative Helmfile hooks                | Normal Kubernetes resources, Jobs, or carefully scoped Argo hooks |
| Much of `scripts/setup.sh`               | Argo CD applications and dependency ordering                      |

Helm itself would not necessarily be removed. The local `charts/workload` chart and third-party Helm charts could continue to be used.

## What Argo CD Would Not Replace

### Talos or K3s bootstrap

Argo CD cannot install Talos, configure BIOS settings, provision mini-PCs, bootstrap the first Kubernetes control plane, or repair a cluster that has no functioning Kubernetes API. A one-time bootstrap process remains necessary.

The future Talos machine configuration should be treated as a separate infrastructure layer managed through `talosctl`, Terraform, or another host-level workflow.

### Image builds

Argo CD deploys image references; it does not build application images. CI or a LAN-accessible build runner would still need to build and push images.

The current workload chart defaults to the local `registry.home:5000` registry and a mutable `dev` tag. For a GitOps deployment, immutable tags or image digests are preferable. If GitHub-hosted CI cannot reach the LAN registry, the choices are a self-hosted LAN runner, a registry reachable by the cluster and CI, or a separate local-development image workflow.

### Terraform and external APIs

The Authentik Terraform configuration manages resources through the Authentik API after Authentik is running. Argo CD does not natively replace that workflow. Terraform can remain a separate Git-driven workflow, or a future Terraform controller/Crossplane setup could reconcile it inside Kubernetes.

### Physical and network infrastructure

Router settings, DHCP reservations, switch configuration, physical disks, BIOS settings, and workstation DNS are outside ordinary Argo CD management unless their vendors expose APIs that another infrastructure tool can manage.

### Persistent data

Git should describe how Postgres, Home Assistant, Longhorn, and other stateful services are deployed and backed up. It should not contain the actual application data. Persistent data requires backups and restore procedures rather than Git reconciliation.

## SOPS and Secrets

SOPS-encrypted files can remain in Git, including a public GitHub repository, as long as the encryption keys and plaintext values are never committed. The fact that a file is encrypted does not protect secrets that were previously committed in plaintext, so secret history and rotation still matter.

The current Helmfile workflow understands entries such as:

```yaml
secrets:
  - services/authentik/secrets.sops.yaml
```

Native Argo CD does not automatically understand Helmfile's `secrets` field or decrypt SOPS files by itself. Moving from Helmfile to native Argo CD would require one of these approaches:

1. Keep Helmfile as an Argo CD Config Management Plugin that runs `helmfile template`, with Helmfile, Helm-secrets, SOPS, age, and the age key installed in the Argo repo-server environment.
2. Use native Argo CD Applications with a SOPS integration such as KSOPS or an equivalent Helm-secrets integration.
3. Use External Secrets Operator, storing only external-secret declarations in Git and keeping actual secret values in a password manager or other secret backend.
4. Use Sealed Secrets or another controller-specific encrypted-secret format.

The first option is a migration bridge, not necessarily the desired final architecture. It preserves Helmfile complexity and means that Helmfile hooks and dependency behavior still need careful treatment.

The second option is more native to Argo CD but requires repository and repo-server configuration. The decryption key must be provisioned into the cluster or Argo repo-server separately from the public Git repository.

## Git Repository Options

The future Argo CD `Application` could track the public repository directly:

```yaml
repoURL: https://github.com/jyablonski/homelab.git
targetRevision: main
```

Argo CD would periodically fetch `main`, notice a new commit, render the desired resources, and synchronize them if automated sync were enabled. A GitHub webhook could reduce the normal polling delay, but a LAN-only cluster would generally use outbound polling because GitHub cannot normally reach the cluster directly.

The source does not have to be GitHub. A local Git server such as Gitea, GitLab, or a bare repository served over SSH or HTTPS would also work. The important requirement is that the Argo repo-server can reach the Git server.

A working copy that exists only on the desktop is not sufficient because Argo CD runs inside the cluster and cannot access the desktop's filesystem. If the Git server itself runs inside the same cluster, it creates a bootstrap dependency: Argo CD cannot retrieve its source while that Git server is unavailable. A public or externally hosted repository avoids that circular dependency.

## Pros and Cons

### Advantages

- Git commits can deploy automatically.
- Manual changes can be detected and corrected.
- The cluster does not depend on the desktop for routine deployments.
- Application health and sync history are visible in one place.
- Removed resources can be pruned automatically.
- The same model can later manage multiple clusters.
- CI does not need broad direct access to the Kubernetes API for deployment.

### Disadvantages

- Argo CD is another system to install, upgrade, secure, monitor, and recover.
- The first bootstrap still requires an external or manual step.
- Native migration from Helmfile requires work.
- SOPS requires an Argo-compatible integration rather than working automatically.
- Automated sync can deploy a bad Git commit quickly.
- Automated pruning can delete resources if the Git change is wrong.
- Argo CD does not solve image builds, Terraform, Talos, hardware, or data backups.
- A cluster with Argo CD but no repository access cannot reconcile new changes.

## When to Reach for Argo CD

Argo CD becomes more valuable after the physical cluster exists and is expected to run continuously.

Good reasons to adopt it would be:

- Manually running `helmfile sync` is becoming tedious.
- The cluster frequently drifts from the repository.
- The desktop should not be required for deployment.
- There are multiple people, environments, or clusters.
- Application health and deployment history need to be visible.
- Automatic recovery after manual changes or partial failures is valuable.
- Image and configuration promotion are being driven through pull requests.

Reasons to defer it would be:

- The cluster is still ephemeral.
- There is only one operator and one cluster.
- `make sync` is simple enough.
- Helmfile already provides the desired dependency and secret behavior.
- The operational cost of adding Argo CD is greater than the value of automatic reconciliation.

## Recommended Path

### Now: keep the local project simple

Continue using the current K3s-based desktop workflow with Helmfile, Tilt, and SOPS. This is a good fit for ephemeral development and avoids introducing Argo CD before there is a persistent cluster that benefits from reconciliation.

### When the mini-PC cluster arrives: start with Talos and Helmfile

Set up the three-node Talos cluster, validate Longhorn and the network model, and reuse the existing Helmfile values and charts where practical. This separates the operating-system migration from the deployment-controller migration.

The cluster bootstrap should be documented and reproducible, but it does not need to be completely driven by Argo CD. Argo CD cannot bootstrap itself before Kubernetes exists.

### Later: explore Argo CD if the need appears

Install Argo CD after the Talos cluster is stable and evaluate it against the actual operational pain. Start with one or two non-critical applications and verify Git synchronization, drift correction, health reporting, and SOPS integration before migrating the whole homelab.

If Argo CD proves useful, migrate Helmfile releases gradually into native Argo CD Applications. Keep Helm charts, values, and encrypted secrets in Git, replace imperative hooks with declarative resources where possible, and retain Helmfile for local development until the native Argo workflow is proven.

The recommended sequence is therefore:

```text
Current desktop:
  K3s + Helmfile + Tilt + SOPS

Future physical cluster:
  Talos + Kubernetes + Helmfile + SOPS

Optional later evolution:
  Talos + Kubernetes + Argo CD + Helm + SOPS integration
```

The goal is Git as the source of truth for desired configuration. Argo CD is one way to automate reconciliation of that truth, not a prerequisite for infrastructure as code.

## References

- [Argo CD Helm integration](https://argo-cd.readthedocs.io/en/stable/user-guide/helm/)
- [Argo CD automated sync](https://argo-cd.readthedocs.io/en/stable/user-guide/auto_sync/)
- [Argo CD webhook configuration](https://argo-cd.readthedocs.io/en/latest/operator-manual/webhook/)
- [Argo CD sync waves](https://argo-cd.readthedocs.io/en/stable/user-guide/sync-waves/)
- [Argo CD Config Management Plugins](https://argo-cd.readthedocs.io/en/stable/operator-manual/config-management-plugins/)
- [Argo CD secret management](https://argo-cd.readthedocs.io/en/stable/operator-manual/secret-management/)
- [Argo CD private repositories](https://argo-cd.readthedocs.io/en/stable/user-guide/private-repositories/)
