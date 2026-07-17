package backup

import (
	"context"
	"errors"
	"os"
	"path/filepath"
	"strings"
	"testing"
	"time"
)

func TestFileBackupValidatesRequiredInputs(t *testing.T) {
	store, err := NewFilesystemStore(t.TempDir())
	if err != nil {
		t.Fatal(err)
	}

	tests := []struct {
		name   string
		backup FileBackup
		kind   string
		source string
		want   string
	}{
		{name: "missing store", source: "source", want: "file backup store is required"},
		{name: "missing source", backup: FileBackup{Store: store}, want: "file backup source path is required"},
		{name: "missing file", backup: FileBackup{Store: store}, source: filepath.Join(t.TempDir(), "missing"), want: "open backup source"},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			_, err := tt.backup.Run(context.Background(), tt.kind, tt.source, "")
			if err == nil || !containsError(err, tt.want) {
				t.Fatalf("expected error containing %q, got %v", tt.want, err)
			}
		})
	}
}

func TestFileBackupCopiesArtifactAndWritesManifest(t *testing.T) {
	sourceDir := t.TempDir()
	sourcePath := filepath.Join(sourceDir, "home-assistant.tar")
	if err := os.WriteFile(sourcePath, []byte("backup contents"), 0o600); err != nil {
		t.Fatal(err)
	}
	store, err := NewFilesystemStore(t.TempDir())
	if err != nil {
		t.Fatal(err)
	}
	now := time.Date(2026, 7, 17, 12, 0, 0, 0, time.UTC)

	manifest, err := (FileBackup{
		Store: store,
		Now:   func() time.Time { return now },
	}).Run(context.Background(), "home-assistant", sourcePath, "config.tar")
	if err != nil {
		t.Fatal(err)
	}

	if len(manifest.Artifacts) != 1 || manifest.Artifacts[0].Key != "home-assistant/20260717T120000Z/config.tar" {
		t.Fatalf("unexpected manifest: %+v", manifest)
	}
	content, err := os.ReadFile(filepath.Join(store.Root, manifest.Artifacts[0].Key))
	if err != nil {
		t.Fatal(err)
	}
	if string(content) != "backup contents" {
		t.Fatalf("unexpected backup content: %q", content)
	}
}

func TestFileBackupUsesSourceNameAndCurrentTimeByDefault(t *testing.T) {
	sourceDir := t.TempDir()
	sourcePath := filepath.Join(sourceDir, "config.tar")
	if err := os.WriteFile(sourcePath, []byte("backup contents"), 0o600); err != nil {
		t.Fatal(err)
	}
	store, err := NewFilesystemStore(t.TempDir())
	if err != nil {
		t.Fatal(err)
	}

	manifest, err := (FileBackup{Store: store}).Run(context.Background(), "home-assistant", sourcePath, "")
	if err != nil {
		t.Fatal(err)
	}
	if len(manifest.Artifacts) != 1 || filepath.Base(manifest.Artifacts[0].Key) != "config.tar" {
		t.Fatalf("expected source filename in artifact key, got %+v", manifest.Artifacts)
	}
}

func TestFileBackupReportsSourceCopyFailure(t *testing.T) {
	sourceDir := t.TempDir()
	store, err := NewFilesystemStore(t.TempDir())
	if err != nil {
		t.Fatal(err)
	}

	_, err = (FileBackup{Store: store}).Run(context.Background(), "file", sourceDir, "directory.tar")
	if err == nil || !containsError(err, "copy backup source") {
		t.Fatalf("expected source copy error, got %v", err)
	}
}

func containsError(err error, want string) bool {
	return err != nil && (errors.Is(err, os.ErrNotExist) || strings.Contains(err.Error(), want))
}
