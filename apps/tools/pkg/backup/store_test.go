package backup

import (
	"context"
	"errors"
	"io"
	"os"
	"path/filepath"
	"strings"
	"testing"
)

func TestNewFilesystemStoreValidatesRoot(t *testing.T) {
	t.Run("empty root", func(t *testing.T) {
		if _, err := NewFilesystemStore("   "); err == nil {
			t.Fatal("expected empty root to be rejected")
		}
	})

	t.Run("root is a file", func(t *testing.T) {
		root := filepath.Join(t.TempDir(), "not-a-directory")
		if err := os.WriteFile(root, []byte("file"), 0o600); err != nil {
			t.Fatal(err)
		}
		if _, err := NewFilesystemStore(filepath.Join(root, "child")); err == nil {
			t.Fatal("expected a file-backed root to be rejected")
		}
	})
}

func TestFilesystemStoreWritesAtomicArtifactAndDigest(t *testing.T) {
	store, err := NewFilesystemStore(t.TempDir())
	if err != nil {
		t.Fatal(err)
	}

	artifact, err := store.Write(context.Background(), "postgres/run/dump.sql", func(writer io.Writer) error {
		_, err := writer.Write([]byte("select 1;\n"))
		return err
	})
	if err != nil {
		t.Fatal(err)
	}

	if artifact.Key != "postgres/run/dump.sql" || artifact.Size != 10 || artifact.SHA256 == "" {
		t.Fatalf("unexpected artifact metadata: %+v", artifact)
	}
	if _, err := os.Stat(filepath.Join(store.Root, artifact.Key)); err != nil {
		t.Fatal(err)
	}
}

func TestFilesystemStoreRejectsPathTraversal(t *testing.T) {
	store, err := NewFilesystemStore(t.TempDir())
	if err != nil {
		t.Fatal(err)
	}

	for _, key := range []string{"../outside", "/outside", ".."} {
		t.Run(key, func(t *testing.T) {
			if _, err := store.Write(context.Background(), key, func(io.Writer) error { return nil }); err == nil {
				t.Errorf("expected key %q to be rejected", key)
			}
		})
	}
}

func TestFilesystemStoreDoesNotLeavePartialArtifactOnWriterFailure(t *testing.T) {
	store, err := NewFilesystemStore(t.TempDir())
	if err != nil {
		t.Fatal(err)
	}

	_, err = store.Write(context.Background(), "postgres/run/dump.sql", func(writer io.Writer) error {
		_, _ = writer.Write([]byte("partial"))
		return os.ErrPermission
	})
	if err == nil {
		t.Fatal("expected writer error")
	}

	entries, err := os.ReadDir(filepath.Join(store.Root, "postgres", "run"))
	if err != nil {
		t.Fatal(err)
	}
	for _, entry := range entries {
		if strings.Contains(entry.Name(), ".backup-") {
			t.Errorf("temporary artifact was not removed: %s", entry.Name())
		}
	}
}

func TestFilesystemStoreRejectsCanceledContext(t *testing.T) {
	store, err := NewFilesystemStore(t.TempDir())
	if err != nil {
		t.Fatal(err)
	}
	ctx, cancel := context.WithCancel(context.Background())
	cancel()

	if _, err := store.Write(ctx, "postgres/run/dump.sql", func(io.Writer) error { return nil }); !errors.Is(err, context.Canceled) {
		t.Fatalf("expected canceled context, got %v", err)
	}
}

func TestFilesystemStoreRejectsContextCanceledDuringWrite(t *testing.T) {
	store, err := NewFilesystemStore(t.TempDir())
	if err != nil {
		t.Fatal(err)
	}
	ctx, cancel := context.WithCancel(context.Background())

	_, err = store.Write(ctx, "postgres/run/dump.sql", func(writer io.Writer) error {
		if _, err := writer.Write([]byte("content")); err != nil {
			return err
		}
		cancel()
		return nil
	})
	if !errors.Is(err, context.Canceled) {
		t.Fatalf("expected canceled context, got %v", err)
	}
}

func TestFilesystemStoreReportsArtifactDirectoryFailure(t *testing.T) {
	root := filepath.Join(t.TempDir(), "root")
	if err := os.WriteFile(root, []byte("file"), 0o600); err != nil {
		t.Fatal(err)
	}

	store := &FilesystemStore{Root: root}
	if _, err := store.Write(context.Background(), "nested/artifact", func(io.Writer) error { return nil }); err == nil {
		t.Fatal("expected artifact directory error")
	}
}
