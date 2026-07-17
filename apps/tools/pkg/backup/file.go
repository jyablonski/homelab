package backup

import (
	"context"
	"fmt"
	"io"
	"log/slog"
	"os"
	"path/filepath"
	"time"
)

// FileBackup copies an archive into a Store.
type FileBackup struct {
	Store  Store
	Now    func() time.Time
	Logger *slog.Logger
}

// Run copies sourcePath into the store and writes a manifest.
func (b FileBackup) Run(ctx context.Context, kind, sourcePath, key string) (Manifest, error) {
	if b.Store == nil {
		return Manifest{}, fmt.Errorf("file backup store is required")
	}
	if sourcePath == "" {
		return Manifest{}, fmt.Errorf("file backup source path is required")
	}
	if key == "" {
		key = filepath.Base(sourcePath)
	}
	if b.Now == nil {
		b.Now = time.Now
	}

	startedAt := b.Now().UTC()
	manifest := Manifest{
		Version:   1,
		Kind:      kind,
		RunID:     startedAt.Format("20060102T150405Z"),
		StartedAt: startedAt,
	}
	logger := backupLogger(b.Logger)
	logger.InfoContext(ctx, "file backup started", "kind", kind, "run_id", manifest.RunID, "artifact_key", key)

	source, err := os.Open(sourcePath)
	if err != nil {
		logger.ErrorContext(ctx, "file backup failed", "kind", kind, "run_id", manifest.RunID, "stage", "open_source", "error", err)
		return Manifest{}, fmt.Errorf("open backup source %q: %w", sourcePath, err)
	}
	defer source.Close()

	artifact, err := b.Store.Write(ctx, fmt.Sprintf("%s/%s/%s", kind, manifest.RunID, key), func(writer io.Writer) error {
		_, err := io.Copy(writer, source)
		return err
	})
	if err != nil {
		logger.ErrorContext(ctx, "file backup failed", "kind", kind, "run_id", manifest.RunID, "stage", "write_artifact", "error", err)
		return Manifest{}, fmt.Errorf("copy backup source %q: %w", sourcePath, err)
	}
	manifest.Artifacts = append(manifest.Artifacts, artifact)
	logger.InfoContext(ctx, "file backup artifact completed", "kind", kind, "run_id", manifest.RunID, "artifact_key", artifact.Key, "size_bytes", artifact.Size)
	manifest.CompletedAt = b.Now().UTC()

	if _, err := manifest.Write(ctx, b.Store); err != nil {
		logger.ErrorContext(ctx, "file backup failed", "kind", kind, "run_id", manifest.RunID, "stage", "write_manifest", "error", err)
		return Manifest{}, fmt.Errorf("write file backup manifest: %w", err)
	}
	logger.InfoContext(ctx, "file backup completed", "kind", kind, "run_id", manifest.RunID, "artifact_count", len(manifest.Artifacts))

	return manifest, nil
}
