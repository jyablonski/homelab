# Self-Hosting Apps on jyablonski.dev via K3s + Cloudflare Tunnel

## Goal

Move apps like `nbadashboard.jyablonski.dev` and `doqs.jyablonski.dev` off AWS CloudFront and GCP VMs into the homelab K3s cluster, exposed publicly via Cloudflare Tunnel. Everything managed as code.

## Architecture Overview

```
User browser
    |
    v
Cloudflare edge (TLS termination, DDoS, caching)
    |
    v
Outbound tunnel (initiated from cluster)
    |
    v
cloudflared pods in K3s
    |
    v
Traefik (host-based routing)
    |
    v
App pods (nbadashboard, doqs, etc.)
```

Traffic flows inbound via an outbound-initiated connection. No ports opened on the home router. DNS for `*.jyablonski.dev` resolves to Cloudflare edge IPs, hiding the home IP entirely.

## What Cloudflare Handles

- DNS for `jyablonski.dev` (nameservers delegated to Cloudflare at the registrar)
- Edge TLS termination with automatic certs
- DDoS protection and basic WAF
- The tunnel endpoint that `cloudflared` connects out to
- Optional: Zero Trust Access policies for SSO-gated internal apps

## What Runs in the Homelab Cluster

- `cloudflared` deployment (2 replicas for HA within the cluster)
- Traefik ingress controller (already running, unchanged)
- `cert-manager` with Cloudflare DNS-01 issuer for internal LAN TLS and wildcard `*.jyablonski.dev` certs
- External Secrets Operator to pull the tunnel token from a secrets backend into a K8s secret
- The apps themselves as standard Deployments + Services + Traefik IngressRoutes

Per-app routing stays in Traefik. The tunnel is a dumb pipe pointing all `*.jyablonski.dev` traffic at `traefik.kube-system.svc.cluster.local:80`, and Traefik dispatches based on the Host header.

## One-Time Setup

Things that must happen manually in the Cloudflare dashboard or registrar:

1. Add `jyablonski.dev` as a zone in Cloudflare
2. Update nameservers at the registrar to point at Cloudflare
3. Generate a scoped API token: `Zone:DNS:Edit`, `Account:Cloudflare Tunnel:Edit`, `Account:Access:Edit`

After this, everything else is Terraform.

## Terraform-Managed Resources

The Cloudflare provider covers the full surface:

- `cloudflare_zero_trust_tunnel_cloudflared` - the tunnel itself
- `cloudflare_zero_trust_tunnel_cloudflared_config` - ingress routing rules (remote config mode)
- `cloudflare_record` - DNS CNAMEs pointing at the tunnel for each subdomain
- `cloudflare_zero_trust_access_application` + `cloudflare_zero_trust_access_policy` - SSO gating for internal apps
- WAF rules, rate limits, page rules if needed

Use `config_src = "cloudflare"` (remote config) so tunnel ingress rules live in Terraform rather than a ConfigMap. One source of truth, and since Traefik handles per-app routing the tunnel config barely changes.

## State Management (S3 Backend)

State lives in an S3 bucket with DynamoDB locking, accessed from GitHub Actions via OIDC so no long-lived AWS credentials exist in GitHub secrets.

### Bucket Configuration

- Versioning enabled (rollback on bad applies)
- Public access blocked
- SSE-S3 encryption at minimum, SSE-KMS if auditable key access matters
- Lifecycle rule expiring noncurrent versions after 90 days

### DynamoDB Lock Table

- On-demand billing
- Single partition key: `LockID` (string)
- Nothing else needed

Alternative: Terraform 1.10+ supports native S3 locking via `use_lockfile = true`, which removes the DynamoDB dependency. DynamoDB is more battle-tested but S3 locking is stable and fine for a homelab.

### GitHub OIDC Role

- Trust policy scoped to `repo:jyablonski/REPO_NAME:ref:refs/heads/main`
- Permissions: read/write on the state bucket prefix and the lock table
- No Cloudflare permissions needed here; Cloudflare auth is via its own API token stored as a GitHub secret

### Backend Config

```hcl
terraform {
  backend "s3" {
    bucket         = "jyablonski-tf-state"
    key            = "homelab/cloudflare.tfstate"
    region         = "us-west-2"
    dynamodb_table = "tf-state-lock"
    encrypt        = true
  }
}
```

## Secrets Handling

The tunnel token ends up in Terraform state because it's an output of the `cloudflare_zero_trust_tunnel_cloudflared` resource. Two implications:

1. The state bucket must be locked down tightly. Treat it as sensitive.
2. The token should be piped into a proper secrets backend (AWS Secrets Manager, Doppler, Vault) and pulled into the cluster via External Secrets Operator, rather than copy-pasted into a K8s secret manually.

This makes rotation a clean workflow: regenerate the token in Terraform, update the secrets backend, ESO syncs it into the cluster, cloudflared pods restart.

## Repo Layout

```
homelab/
├── infra/
│   ├── bootstrap/         # manual one-time: state bucket, DynamoDB, OIDC role
│   └── cloudflare/        # GitHub Actions-managed: tunnel, DNS, Access
│       ├── backend.tf
│       ├── tunnel.tf
│       ├── dns.tf
│       └── access.tf
└── k8s/
    ├── cloudflared/       # deployment + ExternalSecret for the token
    ├── cert-manager/
    └── apps/
        ├── nbadashboard/
        └── doqs/
```

Bootstrap runs once from the laptop with personal AWS creds. Main config runs in CI on PR merge to main. ArgoCD or Flux reconciles the K8s side independently.

## GitHub Actions Workflow

```yaml
permissions:
  id-token: write
  contents: read

jobs:
  terraform:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: aws-actions/configure-aws-credentials@v4
        with:
          role-to-assume: arn:aws:iam::ACCOUNT_ID:role/github-actions-terraform
          aws-region: us-west-2
      - uses: hashicorp/setup-terraform@v3
      - run: terraform init
      - run: terraform plan
      - run: terraform apply -auto-approve
        if: github.ref == 'refs/heads/main'
        env:
          CLOUDFLARE_API_TOKEN: ${{ secrets.CLOUDFLARE_API_TOKEN }}
```

## Cost Breakdown

| Component                    | Cost                                                          |
| ---------------------------- | ------------------------------------------------------------- |
| Cloudflare Tunnel            | Free (unlimited tunnels, unlimited bandwidth, 1000 hostnames) |
| Cloudflare Zero Trust Access | Free up to 50 users                                           |
| Cloudflare DNS + proxy       | Free                                                          |
| S3 state bucket              | Pennies/month at homelab scale                                |
| DynamoDB lock table          | Free tier covers this indefinitely                            |
| Domain renewal               | ~$10-15/year for `.dev`                                       |

Total ongoing: essentially the domain renewal. AWS CloudFront, NAT Gateway, and GCP VM costs all go to zero.

## Migration Flow Per App

1. Deploy app to K3s with Service + Traefik IngressRoute for the target hostname
2. Add DNS record + tunnel ingress rule in Terraform, apply
3. Test via hosts-file override or a staging subdomain first
4. Cut DNS over in the real record
5. Tear down the AWS CloudFront distribution or GCP VM

## Trade-offs

- Home upload bandwidth is the dynamic response ceiling; fine for dashboards, rough for video
- Cluster downtime = app downtime; no geographic redundancy
- Cloudflare TOS section 2.8 restricts large non-HTML content through the free tunnel; web apps are fine
- Residential ISP terms vary on running servers; tunnels sidestep most issues since nothing is inbound

## Open TODOs

- Decide between remote vs local tunnel config (leaning remote)
- Pick apps to migrate first (doqs is probably simplest as a proof of concept)
