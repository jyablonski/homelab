package backup

import (
	"bytes"
	"context"
	"fmt"
	"io"
	"os"
	"path/filepath"
	"strings"
	"testing"
	"time"

	"github.com/moby/moby/api/pkg/stdcopy"
	"github.com/testcontainers/testcontainers-go"
	tcexec "github.com/testcontainers/testcontainers-go/exec"
	"github.com/testcontainers/testcontainers-go/modules/postgres"
)

func TestPostgresBackupWithTestcontainers(t *testing.T) {
	testcontainers.SkipIfProviderIsNotHealthy(t)

	ctx, cancel := context.WithTimeout(context.Background(), 3*time.Minute)
	defer cancel()

	container, err := postgres.Run(
		ctx,
		"postgres:17-alpine",
		postgres.WithDatabase("testdb"),
		postgres.WithUsername("postgres"),
		postgres.WithPassword("test"),
		postgres.BasicWaitStrategies(),
	)
	if err != nil {
		t.Fatalf("start PostgreSQL container: %v", err)
	}
	testcontainers.CleanupContainer(t, container)

	containerRunner := &postgresContainerCommandRunner{container: container}
	execSQL(t, containerRunner, "CREATE DATABASE authentik")
	execSQL(t, containerRunner, "CREATE DATABASE dagster")
	execSQL(t, containerRunner, `
		CREATE TABLE backup_fixture (id integer PRIMARY KEY, value text NOT NULL);
		INSERT INTO backup_fixture (id, value) VALUES (1, 'backup-test');
	`)

	store, err := NewFilesystemStore(t.TempDir())
	if err != nil {
		t.Fatal(err)
	}
	manifest, err := (PostgresBackup{
		Store:  store,
		Runner: containerRunner,
		Stderr: &bytes.Buffer{},
	}).Run(ctx, PostgresConfig{
		Databases:      []string{"testdb", "authentik", "dagster"},
		IncludeGlobals: true,
		Environment:    []string{"PGUSER=postgres", "PGPASSWORD=test"},
	})
	if err != nil {
		t.Fatalf("run PostgreSQL backup: %v", err)
	}
	if len(manifest.Artifacts) != 4 {
		t.Fatalf("expected globals plus three database dumps, got %d artifacts", len(manifest.Artifacts))
	}

	dumpKey := manifest.Artifacts[0].Key
	for _, artifact := range manifest.Artifacts {
		if strings.HasSuffix(artifact.Key, "/testdb.dump") {
			dumpKey = artifact.Key
			break
		}
	}
	dump, err := os.ReadFile(filepath.Join(store.Root, dumpKey))
	if err != nil {
		t.Fatalf("read generated dump: %v", err)
	}
	if len(dump) == 0 {
		t.Fatal("generated PostgreSQL dump is empty")
	}

	execSQL(t, containerRunner, "CREATE DATABASE restored")
	if err := container.CopyToContainer(ctx, dump, "/tmp/testdb.dump", 0o600); err != nil {
		t.Fatalf("copy dump into PostgreSQL container: %v", err)
	}
	execContainer(t, containerRunner, "pg_restore", "-U", "postgres", "-d", "restored", "/tmp/testdb.dump")
	output := execContainer(t, containerRunner, "psql", "-U", "postgres", "-d", "restored", "-tAc", "SELECT value FROM backup_fixture")
	if strings.TrimSpace(output) != "backup-test" {
		t.Fatalf("restored data did not match fixture: %q", output)
	}
}

type postgresContainerCommandRunner struct {
	container testcontainers.Container
}

func (r *postgresContainerCommandRunner) Run(ctx context.Context, name string, args []string, env []string, stdout, stderr io.Writer) error {
	status, output, err := r.container.Exec(ctx, append([]string{name}, args...), tcexec.WithEnv(env))
	if err != nil {
		return err
	}
	if _, err := stdcopy.StdCopy(stdout, stderr, output); err != nil {
		return err
	}
	if status != 0 {
		return fmt.Errorf("command %q exited with status %d", name, status)
	}
	return nil
}

func execSQL(t *testing.T, runner CommandRunner, sql string) string {
	t.Helper()
	return execContainer(t, runner, "psql", "-U", "postgres", "-d", "testdb", "-v", "ON_ERROR_STOP=1", "-c", sql)
}

func execContainer(t *testing.T, runner CommandRunner, name string, args ...string) string {
	t.Helper()
	var stdout, stderr bytes.Buffer
	err := runner.Run(
		context.Background(),
		name,
		args,
		[]string{"PGUSER=postgres", "PGPASSWORD=test"},
		&stdout,
		&stderr,
	)
	if err != nil {
		t.Fatalf("execute command %q %q: %v\nstderr: %s", name, args, err, stderr.String())
	}
	return stdout.String()
}
