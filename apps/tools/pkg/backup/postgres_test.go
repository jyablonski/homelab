package backup

import (
	"context"
	"errors"
	"io"
	"strings"
	"testing"
	"time"
)

type fakeCommandRunner struct {
	calls    []fakeCommandCall
	err      error
	failName string
}

type fakeCommandCall struct {
	name string
	args []string
	env  []string
}

func (r *fakeCommandRunner) Run(_ context.Context, name string, args []string, env []string, stdout, _ io.Writer) error {
	r.calls = append(r.calls, fakeCommandCall{name: name, args: args, env: env})
	if r.err != nil || name == r.failName {
		if r.err != nil {
			return r.err
		}
		return errors.New("command failed")
	}
	_, err := io.WriteString(stdout, name+" output")
	return err
}

func TestPostgresBackupValidatesConfiguration(t *testing.T) {
	store, err := NewFilesystemStore(t.TempDir())
	if err != nil {
		t.Fatal(err)
	}

	tests := []struct {
		name   string
		backup PostgresBackup
		config PostgresConfig
		want   string
	}{
		{name: "missing store", backup: PostgresBackup{Runner: &fakeCommandRunner{}}, config: PostgresConfig{Databases: []string{"postgres"}}, want: "postgres backup store is required"},
		{name: "missing runner", backup: PostgresBackup{Store: store}, config: PostgresConfig{Databases: []string{"postgres"}}, want: "postgres backup command runner is required"},
		{name: "missing databases", backup: PostgresBackup{Store: store, Runner: &fakeCommandRunner{}}, want: "at least one PostgreSQL database is required"},
		{name: "empty database", backup: PostgresBackup{Store: store, Runner: &fakeCommandRunner{}}, config: PostgresConfig{Databases: []string{""}}, want: "database name cannot be empty"},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			_, err := tt.backup.Run(context.Background(), tt.config)
			if err == nil || !strings.Contains(err.Error(), tt.want) {
				t.Fatalf("expected error containing %q, got %v", tt.want, err)
			}
		})
	}
}

func TestPostgresBackupCreatesGlobalsDatabasesAndManifest(t *testing.T) {
	store, err := NewFilesystemStore(t.TempDir())
	if err != nil {
		t.Fatal(err)
	}
	runner := &fakeCommandRunner{}
	now := time.Date(2026, 7, 17, 12, 0, 0, 0, time.UTC)

	manifest, err := (PostgresBackup{
		Store:  store,
		Runner: runner,
		Now:    func() time.Time { return now },
	}).Run(context.Background(), PostgresConfig{
		Databases:      []string{"postgres", "authentik"},
		IncludeGlobals: true,
		Environment:    []string{"PGPASSWORD=not-logged"},
	})
	if err != nil {
		t.Fatal(err)
	}

	if len(manifest.Artifacts) != 3 {
		t.Fatalf("expected three artifacts, got %d", len(manifest.Artifacts))
	}
	if len(runner.calls) != 3 {
		t.Fatalf("expected three commands, got %d", len(runner.calls))
	}
	if runner.calls[0].name != "pg_dumpall" || runner.calls[1].name != "pg_dump" {
		t.Fatalf("unexpected commands: %+v", runner.calls)
	}
	if strings.Contains(strings.Join(runner.calls[0].args, " "), "not-logged") {
		t.Fatal("password leaked into command arguments")
	}
}

func TestPostgresBackupStopsOnDumpFailure(t *testing.T) {
	store, err := NewFilesystemStore(t.TempDir())
	if err != nil {
		t.Fatal(err)
	}
	runner := &fakeCommandRunner{err: errors.New("dump failed")}

	_, err = (PostgresBackup{
		Store:  store,
		Runner: runner,
	}).Run(context.Background(), PostgresConfig{Databases: []string{"postgres"}, IncludeGlobals: true})
	if err == nil || !strings.Contains(err.Error(), "backup PostgreSQL globals") {
		t.Fatalf("unexpected error: %v", err)
	}
}

func TestPostgresBackupStopsOnDatabaseDumpFailure(t *testing.T) {
	store, err := NewFilesystemStore(t.TempDir())
	if err != nil {
		t.Fatal(err)
	}
	runner := &fakeCommandRunner{failName: "pg_dump"}

	_, err = (PostgresBackup{
		Store:  store,
		Runner: runner,
	}).Run(context.Background(), PostgresConfig{Databases: []string{"postgres"}, IncludeGlobals: true})
	if err == nil || !strings.Contains(err.Error(), `backup PostgreSQL database "postgres"`) {
		t.Fatalf("unexpected error: %v", err)
	}
}

func TestPostgresBackupWithoutGlobalsUsesConfiguredDumpCommand(t *testing.T) {
	store, err := NewFilesystemStore(t.TempDir())
	if err != nil {
		t.Fatal(err)
	}
	runner := &fakeCommandRunner{}

	manifest, err := (PostgresBackup{Store: store, Runner: runner}).Run(context.Background(), PostgresConfig{
		Databases:   []string{"postgres"},
		DumpCommand: "custom-pg-dump",
	})
	if err != nil {
		t.Fatal(err)
	}
	if len(manifest.Artifacts) != 1 || len(runner.calls) != 1 || runner.calls[0].name != "custom-pg-dump" {
		t.Fatalf("unexpected backup result: manifest=%+v calls=%+v", manifest, runner.calls)
	}
}

func TestPostgresBackupReportsManifestWriteFailure(t *testing.T) {
	filesystem, err := NewFilesystemStore(t.TempDir())
	if err != nil {
		t.Fatal(err)
	}
	store := manifestFailingStore{Store: filesystem}

	_, err = (PostgresBackup{Store: store, Runner: &fakeCommandRunner{}}).Run(context.Background(), PostgresConfig{
		Databases: []string{"postgres"},
	})
	if err == nil || !strings.Contains(err.Error(), "write PostgreSQL backup manifest") {
		t.Fatalf("unexpected error: %v", err)
	}
}

type manifestFailingStore struct {
	Store
}

func (s manifestFailingStore) Write(ctx context.Context, key string, write func(io.Writer) error) (Artifact, error) {
	if strings.HasSuffix(key, "/manifest.json") {
		return Artifact{}, errors.New("manifest store failed")
	}
	return s.Store.Write(ctx, key, write)
}
