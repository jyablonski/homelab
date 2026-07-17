# Homelab Tools

Standalone Go application for reusable homelab utilities. The first package is a destination-agnostic backup toolkit; future operational tools can add packages under `pkg/` and commands under `cmd/`. The application can later run as a Kubernetes jobs-only release.

## Backup toolkit

The `pkg/backup` package provides:

- atomic filesystem artifact writes
- SHA-256 and size metadata
- JSON manifests
- injectable command execution for testing
- PostgreSQL logical backups using `pg_dump` and `pg_dumpall`
- generic file-artifact backups for application-generated archives

The filesystem store is intentionally the only store implemented initially. A remote object-store implementation can be added once the destination is chosen, without changing the PostgreSQL or file backup producers.

The CLI emits JSON-structured lifecycle logs to stderr using Go's `log/slog`. Logs include the backup kind, run ID, database names, artifact keys, sizes, and failure stages; database credentials are not logged.

Run the current PostgreSQL command locally:

```bash
cd apps/tools
PGHOST=localhost PGUSER=postgres PGPASSWORD='...' go run ./cmd/homelab-backup postgres
```

Copy an application-generated archive, such as a Home Assistant backup, into the same artifact and manifest format:

```bash
cd apps/tools
go run ./cmd/homelab-backup file \
  --kind home-assistant \
  --source /config/backups/backup.tar \
  --output-dir ./backups
```

Longhorn volume backups remain a separate infrastructure concern and should use Longhorn `RecurringJob` resources rather than this module.

## Development

```bash
cd apps/tools
go tool gotestsum --format=short-verbose -- ./...
go vet ./...
go build ./cmd/...
```

The module pins `gotestsum`, `deadcode`, and `golint` as Go tools in `go.mod`. Go formatting, tests, dead-code analysis, and lint checks run through pre-commit and the Go Quality workflow. The workflow requires at least 90% statement coverage for the module's tested packages.

The PostgreSQL integration test uses Testcontainers and runs automatically when Docker is available. It skips locally when Docker is unavailable, but should run in CI where the hosted runner provides Docker.

The application is not currently wired into Helmfile or a Kubernetes CronJob. The placeholder `values.yaml` keeps a future release jobs-only; add scheduled entries after the remote storage target, Secret shape, PVC mounts, retention, and scheduling policy are chosen.
