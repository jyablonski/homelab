package main

import (
	"context"
	"flag"
	"fmt"
	"io"
	"log/slog"
	"os"
	"strings"

	"github.com/jyablonski/homelab/tools/pkg/backup"
)

func main() {
	slog.SetDefault(slog.New(slog.NewJSONHandler(os.Stderr, &slog.HandlerOptions{Level: slog.LevelInfo})))
	os.Exit(run(os.Args[1:], os.Stdout, os.Stderr))
}

func run(args []string, stdout, stderr io.Writer) int {
	if len(args) == 0 {
		usage(stderr)
		return 2
	}

	var err error
	switch args[0] {
	case "postgres":
		err = runPostgres(args[1:])
	case "file":
		err = runFile(args[1:])
	case "help", "-h", "--help":
		usage(stdout)
		return 0
	default:
		usage(stderr)
		return 2
	}

	if err != nil {
		fmt.Fprintf(stderr, "backup failed: %v\n", err)
		return 1
	}
	return 0
}

func runPostgres(args []string) error {
	flags := flag.NewFlagSet("postgres", flag.ContinueOnError)
	flags.SetOutput(os.Stderr)
	outputDir := flags.String("output-dir", "./backups", "directory where backup artifacts are written")
	databases := flags.String("databases", "postgres,authentik,dagster", "comma-separated PostgreSQL database names")
	includeGlobals := flags.Bool("include-globals", true, "include PostgreSQL roles and other global objects")
	if err := flags.Parse(args); err != nil {
		return err
	}

	store, err := backup.NewFilesystemStore(*outputDir)
	if err != nil {
		return err
	}
	manifest, err := (backup.PostgresBackup{
		Store:  store,
		Runner: backup.ExecCommandRunner{},
		Stderr: os.Stderr,
		Logger: slog.Default(),
	}).Run(context.Background(), backup.PostgresConfig{
		Databases:      splitList(*databases),
		IncludeGlobals: *includeGlobals,
		Environment:    postgresEnvironment(),
	})
	if err != nil {
		return err
	}

	fmt.Printf("PostgreSQL backup completed: %s/%s\n", manifest.Kind, manifest.RunID)
	return nil
}

func runFile(args []string) error {
	flags := flag.NewFlagSet("file", flag.ContinueOnError)
	flags.SetOutput(os.Stderr)
	kind := flags.String("kind", "file", "backup kind used in the artifact path")
	sourcePath := flags.String("source", "", "path to the backup file")
	key := flags.String("key", "", "artifact filename; defaults to the source filename")
	outputDir := flags.String("output-dir", "./backups", "directory where backup artifacts are written")
	if err := flags.Parse(args); err != nil {
		return err
	}

	store, err := backup.NewFilesystemStore(*outputDir)
	if err != nil {
		return err
	}
	manifest, err := (backup.FileBackup{Store: store, Logger: slog.Default()}).Run(context.Background(), *kind, *sourcePath, *key)
	if err != nil {
		return err
	}

	fmt.Printf("File backup completed: %s/%s\n", manifest.Kind, manifest.RunID)
	return nil
}

func postgresEnvironment() []string {
	var environment []string
	for _, key := range []string{"PGHOST", "PGPORT", "PGUSER", "PGPASSWORD", "PGDATABASE", "PGSSLMODE"} {
		if value, ok := os.LookupEnv(key); ok {
			environment = append(environment, key+"="+value)
		}
	}
	return environment
}

func splitList(value string) []string {
	parts := strings.Split(value, ",")
	result := make([]string, 0, len(parts))
	for _, part := range parts {
		if trimmed := strings.TrimSpace(part); trimmed != "" {
			result = append(result, trimmed)
		}
	}
	return result
}

func usage(writer io.Writer) {
	fmt.Fprintln(writer, "Usage: homelab-backup <postgres|file> [options]")
	fmt.Fprintln(writer)
	fmt.Fprintln(writer, "The current implementation writes an atomic filesystem artifact set.")
	fmt.Fprintln(writer, "Add an object-store implementation before scheduling it in-cluster.")
}
