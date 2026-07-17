package backup

import (
	"context"
	"crypto/sha256"
	"encoding/hex"
	"errors"
	"fmt"
	"hash"
	"io"
	"os"
	"path/filepath"
	"strings"
)

// Artifact describes one stored backup object and its integrity metadata.
type Artifact struct {
	Key    string `json:"key"`
	Size   int64  `json:"size_bytes"`
	SHA256 string `json:"sha256"`
}

// Store receives backup artifacts under relative keys.
type Store interface {
	Write(context.Context, string, func(io.Writer) error) (Artifact, error)
}

// FilesystemStore stores artifacts on a local filesystem.
type FilesystemStore struct {
	Root string
}

// NewFilesystemStore creates a filesystem-backed artifact store rooted at root.
func NewFilesystemStore(root string) (*FilesystemStore, error) {
	if strings.TrimSpace(root) == "" {
		return nil, errors.New("backup output directory is required")
	}

	if err := os.MkdirAll(root, 0o750); err != nil {
		return nil, fmt.Errorf("create backup output directory: %w", err)
	}

	return &FilesystemStore{Root: root}, nil
}

func (s *FilesystemStore) Write(ctx context.Context, key string, write func(io.Writer) error) (Artifact, error) {
	relativeKey, err := cleanKey(key)
	if err != nil {
		return Artifact{}, err
	}
	if err := ctx.Err(); err != nil {
		return Artifact{}, err
	}

	target := filepath.Join(s.Root, filepath.FromSlash(relativeKey))
	if err := os.MkdirAll(filepath.Dir(target), 0o750); err != nil {
		return Artifact{}, fmt.Errorf("create artifact directory: %w", err)
	}

	temporary, err := os.CreateTemp(filepath.Dir(target), ".backup-*")
	if err != nil {
		return Artifact{}, fmt.Errorf("create temporary artifact: %w", err)
	}
	temporaryName := temporary.Name()
	defer os.Remove(temporaryName)

	digest := &digestWriter{writer: temporary, hash: sha256.New()}
	if err := write(digest); err != nil {
		_ = temporary.Close()
		return Artifact{}, err
	}
	if err := ctx.Err(); err != nil {
		_ = temporary.Close()
		return Artifact{}, err
	}
	if err := temporary.Sync(); err != nil {
		_ = temporary.Close()
		return Artifact{}, fmt.Errorf("sync temporary artifact: %w", err)
	}
	if err := temporary.Close(); err != nil {
		return Artifact{}, fmt.Errorf("close temporary artifact: %w", err)
	}
	if err := os.Rename(temporaryName, target); err != nil {
		return Artifact{}, fmt.Errorf("commit artifact %q: %w", relativeKey, err)
	}

	return Artifact{
		Key:    relativeKey,
		Size:   digest.size,
		SHA256: hex.EncodeToString(digest.hash.Sum(nil)),
	}, nil
}

type digestWriter struct {
	writer io.Writer
	hash   hash.Hash
	size   int64
}

func (w *digestWriter) Write(p []byte) (int, error) {
	n, err := w.writer.Write(p)
	if n > 0 {
		w.size += int64(n)
		_, _ = w.hash.Write(p[:n])
	}
	return n, err
}

func cleanKey(key string) (string, error) {
	cleaned := filepath.ToSlash(filepath.Clean(key))
	if cleaned == "." || cleaned == ".." || strings.HasPrefix(cleaned, "../") || strings.HasPrefix(cleaned, "/") {
		return "", fmt.Errorf("invalid artifact key %q", key)
	}

	return cleaned, nil
}
