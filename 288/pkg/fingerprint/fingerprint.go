package fingerprint

import (
	"crypto/sha256"
	"encoding/hex"
	"fmt"
	"hash"
	"io"
	"os"
	"path/filepath"
	"sort"
	"strings"
)

type Fingerprint struct {
	Hash      string
	Algorithm string
	Files     []string
}

type Calculator struct {
	algorithm    string
	includePaths []string
	excludePaths []string
}

type Option func(*Calculator)

func WithAlgorithm(algorithm string) Option {
	return func(c *Calculator) {
		c.algorithm = algorithm
	}
}

func WithIncludePaths(paths []string) Option {
	return func(c *Calculator) {
		c.includePaths = append(c.includePaths, paths...)
	}
}

func WithExcludePaths(paths []string) Option {
	return func(c *Calculator) {
		c.excludePaths = append(c.excludePaths, paths...)
	}
}

func NewCalculator(opts ...Option) *Calculator {
	c := &Calculator{
		algorithm: "sha256",
	}
	for _, opt := range opts {
		opt(c)
	}
	return c
}

func (c *Calculator) Calculate(files []string) (*Fingerprint, error) {
	var h hash.Hash
	switch strings.ToLower(c.algorithm) {
	case "sha256":
		h = sha256.New()
	default:
		return nil, fmt.Errorf("unsupported algorithm: %s", c.algorithm)
	}

	validFiles := make([]string, 0)
	for _, file := range files {
		if !c.shouldExclude(file) {
			validFiles = append(validFiles, file)
		}
	}

	sort.Strings(validFiles)

	for _, file := range validFiles {
		fileHash, err := c.calculateFileHash(file)
		if err != nil {
			return nil, fmt.Errorf("failed to hash %s: %w", file, err)
		}
		h.Write([]byte(fileHash))
	}

	finalHash := hex.EncodeToString(h.Sum(nil))

	return &Fingerprint{
		Hash:      finalHash,
		Algorithm: c.algorithm,
		Files:     validFiles,
	}, nil
}

func (c *Calculator) calculateFileHash(filePath string) (string, error) {
	info, err := os.Stat(filePath)
	if err != nil {
		return "", err
	}

	if info.IsDir() {
		return c.calculateDirHash(filePath)
	}

	return c.calculateSingleFileHash(filePath)
}

func (c *Calculator) calculateSingleFileHash(filePath string) (string, error) {
	file, err := os.Open(filePath)
	if err != nil {
		return "", err
	}
	defer file.Close()

	h := sha256.New()
	if _, err := io.Copy(h, file); err != nil {
		return "", err
	}

	return hex.EncodeToString(h.Sum(nil)), nil
}

func (c *Calculator) calculateDirHash(dirPath string) (string, error) {
	h := sha256.New()

	err := filepath.Walk(dirPath, func(path string, info os.FileInfo, err error) error {
		if err != nil {
			return err
		}

		if c.shouldExclude(path) {
			if info.IsDir() {
				return filepath.SkipDir
			}
			return nil
		}

		relPath, err := filepath.Rel(dirPath, path)
		if err != nil {
			return err
		}

		h.Write([]byte(relPath))
		h.Write([]byte(info.Mode().String()))

		if !info.IsDir() {
			fileHash, err := c.calculateSingleFileHash(path)
			if err != nil {
				return err
			}
			h.Write([]byte(fileHash))
		}

		return nil
	})

	if err != nil {
		return "", err
	}

	return hex.EncodeToString(h.Sum(nil)), nil
}

func (c *Calculator) shouldExclude(path string) bool {
	for _, exclude := range c.excludePaths {
		matched, err := filepath.Match(exclude, filepath.Base(path))
		if err == nil && matched {
			return true
		}
		if strings.Contains(path, exclude) {
			return true
		}
	}
	return false
}

func (f *Fingerprint) String() string {
	return fmt.Sprintf("%s:%s", f.Algorithm, f.Hash)
}

func (f *Fingerprint) Short() string {
	if len(f.Hash) > 12 {
		return f.Hash[:12]
	}
	return f.Hash
}

func (f *Fingerprint) CacheKey(prefix string) string {
	if prefix == "" {
		return f.Hash
	}
	return fmt.Sprintf("%s-%s", prefix, f.Short())
}
