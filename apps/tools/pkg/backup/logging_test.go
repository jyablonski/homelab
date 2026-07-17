package backup

import (
	"bytes"
	"context"
	"os"
	"path/filepath"
	"strings"
	"testing"
	"time"

	"log/slog"
)

func TestFileBackupLogsLifecycle(t *testing.T) {
	sourcePath := filepath.Join(t.TempDir(), "config.tar")
	if err := os.WriteFile(sourcePath, []byte("backup contents"), 0o600); err != nil {
		t.Fatal(err)
	}
	store, err := NewFilesystemStore(t.TempDir())
	if err != nil {
		t.Fatal(err)
	}
	var logs bytes.Buffer
	now := time.Date(2026, 7, 17, 12, 0, 0, 0, time.UTC)

	_, err = (FileBackup{
		Store:  store,
		Now:    func() time.Time { return now },
		Logger: slog.New(slog.NewTextHandler(&logs, nil)),
	}).Run(context.Background(), "home-assistant", sourcePath, "config.tar")
	if err != nil {
		t.Fatal(err)
	}

	assertLogMessages(t, logs.String(),
		"file backup started",
		"file backup artifact completed",
		"file backup completed",
	)
}

func TestPostgresBackupLogsLifecycleWithoutSecrets(t *testing.T) {
	store, err := NewFilesystemStore(t.TempDir())
	if err != nil {
		t.Fatal(err)
	}
	var logs bytes.Buffer

	_, err = (PostgresBackup{
		Store:  store,
		Runner: &fakeCommandRunner{},
		Logger: slog.New(slog.NewTextHandler(&logs, nil)),
	}).Run(context.Background(), PostgresConfig{
		Databases:   []string{"postgres"},
		Environment: []string{"PGPASSWORD=secret-value"},
	})
	if err != nil {
		t.Fatal(err)
	}

	assertLogMessages(t, logs.String(),
		"postgres backup started",
		"postgres database backup started",
		"postgres database backup completed",
		"postgres backup completed",
	)
	if strings.Contains(logs.String(), "secret-value") {
		t.Fatal("backup logs contained a database password")
	}
}

func assertLogMessages(t *testing.T, logs string, messages ...string) {
	t.Helper()
	for _, message := range messages {
		if !strings.Contains(logs, `msg="`+message+`"`) {
			t.Errorf("logs did not contain message %q: %s", message, logs)
		}
	}
}
