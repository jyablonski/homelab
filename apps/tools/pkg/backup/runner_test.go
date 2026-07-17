package backup

import (
	"bytes"
	"context"
	"testing"
)

func TestExecCommandRunner(t *testing.T) {
	tests := []struct {
		name       string
		args       []string
		env        []string
		wantStdout string
		wantStderr string
		wantError  bool
	}{
		{
			name:       "captures output and environment",
			args:       []string{"-c", "printf '%s' \"$BACKUP_TEST_VALUE\"; printf '%s' 'stderr' >&2"},
			env:        []string{"BACKUP_TEST_VALUE=stdout"},
			wantStdout: "stdout",
			wantStderr: "stderr",
		},
		{
			name:      "reports command failure",
			args:      []string{"-c", "exit 3"},
			wantError: true,
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			var stdout, stderr bytes.Buffer
			err := (ExecCommandRunner{}).Run(context.Background(), "sh", tt.args, tt.env, &stdout, &stderr)
			if (err != nil) != tt.wantError {
				t.Fatalf("Run() error = %v, wantError %t", err, tt.wantError)
			}
			if stdout.String() != tt.wantStdout || stderr.String() != tt.wantStderr {
				t.Fatalf("unexpected command output: stdout=%q stderr=%q", stdout.String(), stderr.String())
			}
		})
	}
}
