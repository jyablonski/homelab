package backup

import (
	"context"
	"io"
	"os"
	"os/exec"
)

// CommandRunner runs commands for backup producers.
type CommandRunner interface {
	Run(context.Context, string, []string, []string, io.Writer, io.Writer) error
}

// ExecCommandRunner executes commands on the local host.
type ExecCommandRunner struct{}

// Run executes a command with the supplied environment and output writers.
func (ExecCommandRunner) Run(ctx context.Context, name string, args []string, env []string, stdout, stderr io.Writer) error {
	command := exec.CommandContext(ctx, name, args...)
	command.Env = append(os.Environ(), env...)
	command.Stdout = stdout
	command.Stderr = stderr
	return command.Run()
}
