package main

import (
	"os"
	"path/filepath"
	"reflect"
	"strings"
	"testing"
)

func TestSplitListTrimsAndDropsEmptyValues(t *testing.T) {
	got := splitList(" postgres, authentik ,, dagster ")
	want := []string{"postgres", "authentik", "dagster"}
	if !reflect.DeepEqual(got, want) {
		t.Fatalf("splitList() = %#v, want %#v", got, want)
	}
}

func TestPostgresEnvironmentIncludesConfiguredVariables(t *testing.T) {
	t.Setenv("PGHOST", "postgres.example")
	t.Setenv("PGPASSWORD", "not-checked-in")
	t.Setenv("UNRELATED", "ignored")

	got := postgresEnvironment()
	if !reflect.DeepEqual(got, []string{"PGHOST=postgres.example", "PGPASSWORD=not-checked-in"}) {
		t.Fatalf("postgresEnvironment() = %#v", got)
	}
}

func TestRunFileCreatesBackup(t *testing.T) {
	sourceDir := t.TempDir()
	sourcePath := filepath.Join(sourceDir, "config.tar")
	if err := os.WriteFile(sourcePath, []byte("backup"), 0o600); err != nil {
		t.Fatal(err)
	}
	outputDir := t.TempDir()

	if err := runFile([]string{"--kind", "home-assistant", "--source", sourcePath, "--output-dir", outputDir}); err != nil {
		t.Fatal(err)
	}

	entries, err := os.ReadDir(filepath.Join(outputDir, "home-assistant"))
	if err != nil {
		t.Fatal(err)
	}
	if len(entries) != 1 {
		t.Fatalf("expected one backup run directory, found %d", len(entries))
	}
}

func TestRunFileReportsBackupErrors(t *testing.T) {
	err := runFile([]string{"--source", filepath.Join(t.TempDir(), "missing")})
	if err == nil || !strings.Contains(err.Error(), "open backup source") {
		t.Fatalf("expected missing source error, got %v", err)
	}
}

func TestRunPostgresCreatesBackupWithCommandOnPath(t *testing.T) {
	binDir := t.TempDir()
	pgDump := filepath.Join(binDir, "pg_dump")
	if err := os.WriteFile(pgDump, []byte("#!/bin/sh\nprintf 'dump'\n"), 0o700); err != nil {
		t.Fatal(err)
	}
	t.Setenv("PATH", binDir+string(os.PathListSeparator)+os.Getenv("PATH"))

	if err := runPostgres([]string{
		"--databases", "postgres",
		"--include-globals=false",
		"--output-dir", t.TempDir(),
	}); err != nil {
		t.Fatal(err)
	}
}

func TestRunPostgresReportsInvalidBackupConfiguration(t *testing.T) {
	err := runPostgres([]string{"--databases", "", "--output-dir", t.TempDir()})
	if err == nil || !strings.Contains(err.Error(), "at least one PostgreSQL database") {
		t.Fatalf("expected missing database error, got %v", err)
	}
}

func TestUsageWritesCommandHelp(t *testing.T) {
	var output strings.Builder
	usage(&output)
	if !strings.Contains(output.String(), "homelab-backup <postgres|file>") {
		t.Fatalf("unexpected usage output: %q", output.String())
	}
}

func TestRunReturnsExpectedExitCodes(t *testing.T) {
	tests := []struct {
		name string
		args []string
		want int
	}{
		{name: "missing command", want: 2},
		{name: "unknown command", args: []string{"unknown"}, want: 2},
		{name: "help", args: []string{"help"}, want: 0},
		{name: "command error", args: []string{"file", "--source", filepath.Join(t.TempDir(), "missing")}, want: 1},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			var stdout, stderr strings.Builder
			if got := run(tt.args, &stdout, &stderr); got != tt.want {
				t.Fatalf("run(%v) = %d, want %d", tt.args, got, tt.want)
			}
		})
	}
}
