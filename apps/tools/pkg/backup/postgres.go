package backup

import (
	"context"
	"fmt"
	"io"
	"log/slog"
	"time"
)

// PostgresConfig configures PostgreSQL backup commands and databases.
type PostgresConfig struct {
	DumpCommand    string
	DumpAllCommand string
	Databases      []string
	Environment    []string
	IncludeGlobals bool
}

// PostgresBackup creates logical PostgreSQL backups in a Store.
type PostgresBackup struct {
	Store  Store
	Runner CommandRunner
	Now    func() time.Time
	Stderr io.Writer
	Logger *slog.Logger
}

// Run writes optional PostgreSQL globals and a dump for each database.
func (b PostgresBackup) Run(ctx context.Context, config PostgresConfig) (Manifest, error) {
	if b.Store == nil {
		return Manifest{}, fmt.Errorf("postgres backup store is required")
	}
	if b.Runner == nil {
		return Manifest{}, fmt.Errorf("postgres backup command runner is required")
	}
	if config.DumpCommand == "" {
		config.DumpCommand = "pg_dump"
	}
	if config.DumpAllCommand == "" {
		config.DumpAllCommand = "pg_dumpall"
	}
	if len(config.Databases) == 0 {
		return Manifest{}, fmt.Errorf("at least one PostgreSQL database is required")
	}
	if b.Now == nil {
		b.Now = time.Now
	}
	if b.Stderr == nil {
		b.Stderr = io.Discard
	}

	startedAt := b.Now().UTC()
	runID := startedAt.Format("20060102T150405Z")
	manifest := Manifest{
		Version:   1,
		Kind:      "postgres",
		RunID:     runID,
		StartedAt: startedAt,
	}
	logger := backupLogger(b.Logger)
	logger.InfoContext(ctx, "postgres backup started", "run_id", manifest.RunID, "database_count", len(config.Databases), "include_globals", config.IncludeGlobals)
	prefix := fmt.Sprintf("postgres/%s", runID)

	if config.IncludeGlobals {
		logger.InfoContext(ctx, "postgres globals backup started", "run_id", manifest.RunID)
		artifact, err := b.Store.Write(ctx, prefix+"/globals.sql", func(writer io.Writer) error {
			return b.Runner.Run(ctx, config.DumpAllCommand, []string{"--globals-only"}, config.Environment, writer, b.Stderr)
		})
		if err != nil {
			logger.ErrorContext(ctx, "postgres backup failed", "run_id", manifest.RunID, "stage", "globals", "error", err)
			return Manifest{}, fmt.Errorf("backup PostgreSQL globals: %w", err)
		}
		manifest.Artifacts = append(manifest.Artifacts, artifact)
		logger.InfoContext(ctx, "postgres globals backup completed", "run_id", manifest.RunID, "artifact_key", artifact.Key, "size_bytes", artifact.Size)
	}

	for _, database := range config.Databases {
		if database == "" {
			logger.ErrorContext(ctx, "postgres backup failed", "run_id", manifest.RunID, "stage", "validate_database", "error", "database name cannot be empty")
			return Manifest{}, fmt.Errorf("database name cannot be empty")
		}

		logger.InfoContext(ctx, "postgres database backup started", "run_id", manifest.RunID, "database", database)
		artifact, err := b.Store.Write(ctx, fmt.Sprintf("%s/%s.dump", prefix, database), func(writer io.Writer) error {
			args := []string{"--format=custom", "--dbname", database}
			return b.Runner.Run(ctx, config.DumpCommand, args, config.Environment, writer, b.Stderr)
		})
		if err != nil {
			logger.ErrorContext(ctx, "postgres backup failed", "run_id", manifest.RunID, "database", database, "stage", "database", "error", err)
			return Manifest{}, fmt.Errorf("backup PostgreSQL database %q: %w", database, err)
		}
		manifest.Artifacts = append(manifest.Artifacts, artifact)
		logger.InfoContext(ctx, "postgres database backup completed", "run_id", manifest.RunID, "database", database, "artifact_key", artifact.Key, "size_bytes", artifact.Size)
	}

	manifest.CompletedAt = b.Now().UTC()
	if _, err := manifest.Write(ctx, b.Store); err != nil {
		logger.ErrorContext(ctx, "postgres backup failed", "run_id", manifest.RunID, "stage", "write_manifest", "error", err)
		return Manifest{}, fmt.Errorf("write PostgreSQL backup manifest: %w", err)
	}
	logger.InfoContext(ctx, "postgres backup completed", "run_id", manifest.RunID, "artifact_count", len(manifest.Artifacts))

	return manifest, nil
}
