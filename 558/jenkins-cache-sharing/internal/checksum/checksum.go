package checksum

import (
	"crypto/sha256"
	"encoding/hex"
	"encoding/json"
	"fmt"
	"io"
	"os"
	"path/filepath"
	"sort"
	"strings"

	"github.com/jenkins-cache-sharing/internal/model"
)

type DependencyFile struct {
	Path    string `json:"path"`
	Content string `json:"content"`
	Hash    string `json:"hash"`
}

type DependencyHash struct {
	CacheType   model.CacheType  `json:"cache_type"`
	Files       []DependencyFile `json:"files"`
	Combined    string           `json:"combined"`
	GeneratedAt int64            `json:"generated_at"`
}

var mavenPatterns = []string{"pom.xml", "pom.properties"}
var npmPatterns = []string{"package.json", "package-lock.json", "npm-shrinkwrap.json", "yarn.lock", "pnpm-lock.yaml"}
var gradlePatterns = []string{"build.gradle", "build.gradle.kts", "settings.gradle", "settings.gradle.kts", "gradle.properties", "gradle-wrapper.properties"}

func ComputeDependencyHash(cacheType model.CacheType, projectDir string) (*DependencyHash, error) {
	patterns := getPatterns(cacheType)
	files, err := collectDependencyFiles(projectDir, patterns)
	if err != nil {
		return nil, fmt.Errorf("failed to collect dependency files: %w", err)
	}

	if len(files) == 0 {
		return &DependencyHash{
			CacheType:   cacheType,
			Files:       []DependencyFile{},
			Combined:    "",
			GeneratedAt: 0,
		}, nil
	}

	sort.Slice(files, func(i, j int) bool {
		return files[i].Path < files[j].Path
	})

	for i := range files {
		hash, err := computeContentHash(files[i].Content)
		if err != nil {
			return nil, fmt.Errorf("failed to compute hash for %s: %w", files[i].Path, err)
		}
		files[i].Hash = hash
	}

	combinedHash := computeCombinedHash(files)

	return &DependencyHash{
		CacheType:   cacheType,
		Files:       files,
		Combined:    combinedHash,
		GeneratedAt: 0,
	}, nil
}

func ComputeDependencyHashFromReader(cacheType model.CacheType, readers map[string]io.Reader) (*DependencyHash, error) {
	var files []DependencyFile

	for path, reader := range readers {
		content, err := io.ReadAll(reader)
		if err != nil {
			return nil, fmt.Errorf("failed to read %s: %w", path, err)
		}

		normalized := normalizeContent(string(content))
		hash, err := computeContentHash(normalized)
		if err != nil {
			return nil, fmt.Errorf("failed to compute hash for %s: %w", path, err)
		}

		files = append(files, DependencyFile{
			Path:    path,
			Content: normalized,
			Hash:    hash,
		})
	}

	sort.Slice(files, func(i, j int) bool {
		return files[i].Path < files[j].Path
	})

	combinedHash := computeCombinedHash(files)

	return &DependencyHash{
		CacheType:   cacheType,
		Files:       files,
		Combined:    combinedHash,
		GeneratedAt: 0,
	}, nil
}

func ComputeHashFromContents(cacheType model.CacheType, fileContents map[string]string) (*DependencyHash, error) {
	readers := make(map[string]io.Reader)
	for path, content := range fileContents {
		readers[path] = strings.NewReader(content)
	}
	return ComputeDependencyHashFromReader(cacheType, readers)
}

func getPatterns(cacheType model.CacheType) []string {
	switch cacheType {
	case model.CacheTypeMaven:
		return mavenPatterns
	case model.CacheTypeNPM:
		return npmPatterns
	case model.CacheTypeGradle:
		return gradlePatterns
	default:
		return []string{}
	}
}

func collectDependencyFiles(projectDir string, patterns []string) ([]DependencyFile, error) {
	var files []DependencyFile

	err := filepath.Walk(projectDir, func(path string, info os.FileInfo, err error) error {
		if err != nil {
			return err
		}

		if info.IsDir() {
			rel, err := filepath.Rel(projectDir, path)
			if err == nil && shouldSkipDir(rel) {
				return filepath.SkipDir
			}
			return nil
		}

		name := filepath.Base(path)
		for _, pattern := range patterns {
			if name == pattern {
				content, err := os.ReadFile(path)
				if err != nil {
					return fmt.Errorf("failed to read %s: %w", path, err)
				}

				normalized := normalizeContent(string(content))
				files = append(files, DependencyFile{
					Path:    path,
					Content: normalized,
				})
				break
			}
		}

		return nil
	})

	if err != nil {
		return nil, err
	}

	return files, nil
}

func shouldSkipDir(relPath string) bool {
	skipDirs := []string{
		"node_modules", ".git", ".svn", ".hg",
		"target", "build", "dist", ".next", ".cache",
		".idea", ".vscode", ".m2", ".gradle",
		"vendor", "__pycache__",
	}

	for _, skip := range skipDirs {
		if relPath == skip || strings.HasPrefix(relPath, skip+string(filepath.Separator)) {
			return true
		}
	}
	return false
}

func normalizeContent(content string) string {
	lines := strings.Split(content, "\n")
	var normalized []string

	for _, line := range lines {
		trimmed := strings.TrimSpace(line)
		if trimmed == "" {
			continue
		}
		if strings.HasPrefix(trimmed, "//") || strings.HasPrefix(trimmed, "#") {
			continue
		}
		if strings.HasPrefix(trimmed, "<!--") {
			continue
		}
		normalized = append(normalized, trimmed)
	}

	return strings.Join(normalized, "\n")
}

func computeContentHash(content string) (string, error) {
	normalized := strings.ReplaceAll(content, "\r\n", "\n")
	normalized = strings.ReplaceAll(normalized, "\t", " ")
	normalized = strings.TrimSpace(normalized)

	h := sha256.New()
	h.Write([]byte(normalized))
	return hex.EncodeToString(h.Sum(nil)), nil
}

func computeCombinedHash(files []DependencyFile) string {
	h := sha256.New()

	for _, f := range files {
		h.Write([]byte(f.Path + ":" + f.Hash + ";"))
	}

	return hex.EncodeToString(h.Sum(nil))
}

func HasDependencyChanged(currentHash, previousHash string) bool {
	if previousHash == "" {
		return true
	}
	return currentHash != previousHash
}

func (dh *DependencyHash) ToJSON() (string, error) {
	data, err := json.Marshal(dh)
	if err != nil {
		return "", err
	}
	return string(data), nil
}

func (dh *DependencyHash) ShortHash() string {
	if len(dh.Combined) >= 12 {
		return dh.Combined[:12]
	}
	return dh.Combined
}

func GetDependencyFilePatterns(cacheType model.CacheType) []string {
	patterns := getPatterns(cacheType)
	result := make([]string, len(patterns))
	copy(result, patterns)
	return result
}
