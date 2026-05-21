# Homelab Backup Strategy Notes

## Purpose of Backups

Backups protect against data loss from failure modes you can't predict or prevent. For a K3s homelab, the main risks:

- Disk or node hardware failure exceeding replica count
- Accidental deletion (`kubectl delete pvc`, dropped database table, broken automation)
- Software corruption (Longhorn bug, SQLite corruption from hard shutdown, bad migration)
- Configuration drift (changed something, can't remember the working state)
- Security incidents (compromised credentials, ransomware)
- Storage backend migration or cluster rebuild

UPS protection covers power events. Backups cover everything else.

## Two Layers of Backup

For stateful workloads, you want both layers because they protect against different things.

### Layer 1: Block-level snapshots (Longhorn)

Longhorn snapshots are crash-consistent block copies of the entire PVC. The volume gets frozen, blocks are captured, and shipped to remote storage.

What it's good for:

- Fast restore of a whole volume after disk/node loss
- Accidental PVC deletion recovery
- Whole-cluster disaster recovery
- Easy automation via CRDs

Limitations:

- Crash-consistent, not application-consistent. Captures whatever's on disk at that moment.
- Longhorn-specific format. Can't easily restore to a different storage backend.
- All-or-nothing. Can't restore a single table or a single HA entity.
- If Longhorn itself has a bug, the snapshot may also be affected.

Shipping to remote storage protects you against the cluster itself dying. Snapshots stored locally on the same Longhorn volumes they're backing up are worthless if the underlying disks or the whole cluster fail, so the offsite copy is what makes the snapshot actually recoverable in a disaster scenario.

### Layer 2: Application-level backups

Logical exports through the application: `pg_dump` for Postgres, HA's built-in backup for Home Assistant.

What it's good for:

- Application-consistent backups (Postgres holds a snapshot isolation transaction during dump)
- Portable, restorable anywhere Postgres or HA runs
- Granular restore (single table, single config)
- Validates data integrity at backup time (corrupt rows show up as dump errors)
- Point-in-time recovery (with WAL archiving)

Limitations:

- Slower for very large datasets
- Doesn't capture non-application state (file uploads stored on PVC, etc.)
- Requires application-specific tooling and knowledge to restore

## What to Snapshot vs Not

| Workload                      | Longhorn Snapshot | App-Level Backup             | Notes                                                               |
| ----------------------------- | ----------------- | ---------------------------- | ------------------------------------------------------------------- |
| Postgres                      | Yes               | Yes (pg_dump daily)          | Both layers. Consider WAL archiving if data really matters.         |
| Home Assistant                | Yes               | Yes (built-in backup)        | SQLite is fragile, the logical backup is the trustworthy layer.     |
| Authentik                     | Yes               | Covered by Postgres backup   | Data lives in Postgres.                                             |
| Registry                      | Yes               | No                           | Images can be rebuilt and repushed. Snapshot is sufficient.         |
| Prometheus                    | Optional          | No                           | Metrics are time-series. Losing recent data is rarely catastrophic. |
| Loki                          | Optional          | No                           | Same as Prometheus.                                                 |
| Pi-hole                       | Yes               | Optional (Teleporter export) | Config is small, snapshot fine. Teleporter is bonus.                |
| Cache layers, queues          | No                | No                           | Ephemeral by design.                                                |
| Workload examples / test apps | No                | No                           | Rebuildable from helm chart.                                        |

Rule of thumb: if losing it means re-entering data you can't reproduce, back it up at both layers. If it's derived or rebuildable, snapshot only or skip entirely.

## Backup Cadence

For an actively-developed homelab:

- Daily for anything with accumulating user data (Postgres, HA recorder)
- Weekly is a reasonable minimum for slowly-changing config
- Continuous (WAL archiving) for Postgres if point-in-time recovery matters
- Retention: 7 daily + 4 weekly + 12 monthly is a common pattern

Daily is the right cadence for HA specifically because sensor history accumulates continuously.

## Automation

Two independent pieces handle the two backup layers: Longhorn owns block-level backups end-to-end, and a separate app-level script handles Postgres and Home Assistant.

### Longhorn RecurringJob

Longhorn manages everything in its own job: triggering the snapshot, creating the backup, and exporting it to a configured remote storage backend using credentials from a Kubernetes Secret. The remote target is set once in Longhorn's settings (`backupTarget` + `backupTargetCredentialSecret`) and applies to all backups. Nothing external needs to read or ship Longhorn data; by the time a RecurringJob completes, the data is already in remote storage.

Built-in CRD for scheduled snapshots and backups. Define once, applies to volumes via label selector.

```yaml
apiVersion: longhorn.io/v1beta2
kind: RecurringJob
metadata:
  name: daily-snapshot
  namespace: longhorn-system
spec:
  cron: "0 2 * * *"
  task: "snapshot"
  retain: 7
  concurrency: 2
  groups:
    - default
---
apiVersion: longhorn.io/v1beta2
kind: RecurringJob
metadata:
  name: weekly-backup
  namespace: longhorn-system
spec:
  cron: "0 3 * * 0"
  task: "backup"
  retain: 4
  concurrency: 2
  groups:
    - default
```

Volumes opt in via label: `recurring-job-group.longhorn.io/default: "enabled"`.

### App-level backup script

A separate script (Go binary, shell script, or Kubernetes CronJob) handles application-consistent backups for the only workloads with persistent state we actually care about: Postgres and Home Assistant. Everything else is either covered by Postgres (Authentik) or rebuildable (registry, monitoring, Pi-hole config).

Responsibilities:

- Run `pg_dump` for each database, stream directly to remote storage
- Trigger Home Assistant's backup API, download the resulting tarball, stream to remote storage
- Write a manifest with timestamps, sizes, and checksums alongside the backups
- Report success/failure via notification (Slack, ntfy, email)

The script uses the same remote storage backend as Longhorn (same bucket, different prefix), with credentials from a SOPS-encrypted Kubernetes Secret. For continuous Postgres WAL archiving, WAL-G or pgBackRest run as a sidecar or in the Postgres image, independently of this script.

- Capturing pg dump means you'll have up to 23 hr 59 minute gaps until the next pg dump backup.
- WAL archiving means you also ship all of the database changes that happened in that in-between period. But this requires extra configuration than you get out of the box with Postgres.
- Probably won't ever implement this, but it's good to know about.

This split keeps the responsibilities clean: Longhorn handles block-level disaster recovery, the script handles application-consistent point-in-time backups for the workloads that matter.

## Where to Store Backups

The 3-2-1 rule: 3 copies, 2 different media, 1 offsite. Even at homelab scale.

Critically: backups must live somewhere other than the cluster they're backing up. If the whole cluster dies, you can't restore from PVCs that live on the dead cluster.

Options:

| Destination                     | Pros                                       | Cons                                        |
| ------------------------------- | ------------------------------------------ | ------------------------------------------- |
| Backblaze B2                    | Cheapest ($0.005/GB), generous free egress | One more vendor                             |
| Cloudflare R2                   | Zero egress fees, simple                   | Slightly more expensive on storage          |
| AWS S3                          | Maximum compatibility, mature              | Expensive, egress fees sting on restore     |
| Self-hosted MinIO (off-cluster) | Full control, no recurring cost            | Requires separate hardware, you maintain it |
| External USB drive              | Cheap, simple                              | Manual, single point of failure, no offsite |

Recommendation for homelab: B2 or R2 for offsite, optionally a local MinIO or NAS as a second copy for fast restores.

## Restore Procedures

### Longhorn snapshot restore

1. In Longhorn UI, navigate to the volume's snapshot history.
2. Pick a snapshot, click "Revert" to roll the volume back in place, or "Create Volume" to clone it to a new PVC.
3. For backups (offsite copy), use "Restore Latest Backup" from the Backup page. This creates a new volume from the remote backup.
4. Update the PVC binding if you restored to a new volume name.

Time to restore: minutes for snapshots, longer for backups (network-bound).

### Longhorn full cluster recovery

If the cluster is gone:

1. Stand up new K3s cluster, install Longhorn.
2. Configure Longhorn with the same S3 backup target.
3. Longhorn auto-discovers existing backups in the bucket.
4. Restore volumes one at a time from the Backup page.
5. Recreate PVCs pointing to restored volumes, redeploy workloads.

### Postgres restore from pg_dump

```bash
# Pull dump from S3
aws s3 cp s3://my-backups/postgres/20260520.dump ./backup.dump

# Drop and recreate target DB (careful!)
psql -h postgres -U admin -c "DROP DATABASE mydb;"
psql -h postgres -U admin -c "CREATE DATABASE mydb;"

# Restore
pg_restore -h postgres -U admin -d mydb --no-owner --no-acl ./backup.dump
```

For point-in-time recovery with WAL archiving, the procedure is more involved: restore base backup, then replay WAL up to a target time.

### Home Assistant restore

1. Fresh HA deployment via Helm chart.
2. Copy backup tarball into HA's `/backup` directory (or restore via UI upload).
3. From HA UI: Settings > System > Backups > select backup > Restore.
4. HA restarts and replays configuration + recorder DB.

## Testing Restores

The most important and most skipped step. A backup you've never restored isn't a backup, it's a guess.

Suggested cadence:

- Quarterly: Do a test restore of Postgres to a scratch namespace. Verify row counts and a few sample queries.
- Quarterly: Spin up HA from backup in a test environment. Verify config loads and recorder data is intact.
- Annually: Full disaster recovery drill. Stand up a fresh cluster from scratch using only your backups and Helm charts. Time it.

The drills surface gaps: missing credentials, undocumented manual steps, drift between what's actually deployed and what's in git, restore procedures that no longer work.

## Common Gotchas

- Forgetting to back up secrets. SOPS-encrypted secrets in git are recoverable; in-cluster Secrets that aren't in git are not.
- Backup credentials stored in the cluster being backed up. If the cluster dies, you can't access the backups. Keep credentials in a password manager or external vault.
- Backups succeeding silently while producing corrupt or incomplete data. Always check exit codes and validate dump file sizes against expected ranges.
- Storage costs creeping up due to retention misconfiguration. Set lifecycle rules on the bucket to auto-expire old backups.
- Restoring to a Postgres version older than the backup. Always restore to equal-or-newer Postgres.
