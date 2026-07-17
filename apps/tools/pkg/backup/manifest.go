package backup

import (
	"context"
	"encoding/json"
	"fmt"
	"io"
	"time"
)

// Manifest records artifacts from one backup run.
type Manifest struct {
	Version     int        `json:"version"`
	Kind        string     `json:"kind"`
	RunID       string     `json:"run_id"`
	StartedAt   time.Time  `json:"started_at"`
	CompletedAt time.Time  `json:"completed_at"`
	Artifacts   []Artifact `json:"artifacts"`
}

func (m Manifest) Write(ctx context.Context, store Store) (Artifact, error) {
	key := fmt.Sprintf("%s/%s/manifest.json", m.Kind, m.RunID)
	return store.Write(ctx, key, func(writer io.Writer) error {
		encoder := json.NewEncoder(writer)
		encoder.SetIndent("", "  ")
		return encoder.Encode(m)
	})
}
