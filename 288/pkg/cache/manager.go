package cache

import (
	"archive/tar"
	"compress/gzip"
	"context"
	"encoding/json"
	"fmt"
	"io"
	"os"
	"path/filepath"
	"time"

	"cicache/pkg/storage"
)

type CacheEntry struct {
	Key         string    `json:"key"`
	Fingerprint string    `json:"fingerprint"`
	Path        string    `json:"path"`
	Size        int64     `json:"size"`
	CreatedAt   time.Time `json:"created_at"`
	AccessedAt  time.Time `json:"accessed_at"`
}

type CacheIndex struct {
	Entries []CacheEntry `json:"entries"`
}

type Manager struct {
	storage      storage.Storage
	lru          *LRUCache
	tieredLRU    *TieredLRUCache
	cacheDir     string
	indexPath    string
	maxCacheSize int64
	useTiered    bool
	analytics    *Analytics
	projectID    string
	projectType  string
}

type ManagerOption func(*Manager)

func WithMaxCacheSize(size int64) ManagerOption {
	return func(m *Manager) {
		m.maxCacheSize = size
	}
}

func WithCacheDir(dir string) ManagerOption {
	return func(m *Manager) {
		m.cacheDir = dir
	}
}

func WithTieredCache(enabled bool) ManagerOption {
	return func(m *Manager) {
		m.useTiered = enabled
	}
}

func WithProjectInfo(projectID, projectType string) ManagerOption {
	return func(m *Manager) {
		m.projectID = projectID
		m.projectType = projectType
	}
}

func NewManager(store storage.Storage, opts ...ManagerOption) (*Manager, error) {
	home, err := os.UserHomeDir()
	if err != nil {
		return nil, err
	}

	m := &Manager{
		storage:      store,
		cacheDir:     filepath.Join(home, ".cicache", "local"),
		maxCacheSize: 10 * 1024 * 1024 * 1024,
		useTiered:    false,
	}

	for _, opt := range opts {
		opt(m)
	}

	m.indexPath = filepath.Join(m.cacheDir, "index.json")

	if err := os.MkdirAll(m.cacheDir, 0755); err != nil {
		return nil, err
	}

	m.analytics = NewAnalytics(m.cacheDir)

	if m.useTiered {
		m.tieredLRU = NewTieredLRUCache(m.maxCacheSize,
			WithOnTieredEvict(func(key string, size int64, tier CacheTier) {
				m.onEvict(key)
			}),
		)
	} else {
		m.lru = NewLRUCache(m.maxCacheSize, func(key string, size int64) {
			m.onEvict(key)
		})
	}

	if err := m.loadIndex(); err != nil {
		return nil, err
	}

	return m, nil
}

func (m *Manager) onEvict(key string) {
	cachePath := filepath.Join(m.cacheDir, key+".tar.gz")
	os.Remove(cachePath)
}

func (m *Manager) loadIndex() error {
	data, err := os.ReadFile(m.indexPath)
	if err != nil {
		if os.IsNotExist(err) {
			return nil
		}
		return err
	}

	var index CacheIndex
	if err := json.Unmarshal(data, &index); err != nil {
		return err
	}

	if m.useTiered {
		for _, entry := range index.Entries {
			m.tieredLRU.Put(entry.Key, entry.Size)
		}
	} else {
		for _, entry := range index.Entries {
			m.lru.Put(entry.Key, entry.Size)
		}
	}

	return nil
}

func (m *Manager) saveIndex() error {
	var entries []CacheEntry

	if m.useTiered {
		items := m.tieredLRU.GetItems()
		entries = make([]CacheEntry, 0, len(items))
		for _, item := range items {
			entries = append(entries, CacheEntry{
				Key:        item.Key,
				Size:       item.Size,
				CreatedAt:  item.CreatedAt,
				AccessedAt: item.AccessedAt,
			})
		}
	} else {
		items := m.lru.GetItems()
		entries = make([]CacheEntry, 0, len(items))
		for _, item := range items {
			entries = append(entries, CacheEntry{
				Key:        item.Key,
				Size:       item.Size,
				CreatedAt:  item.CreatedAt,
				AccessedAt: item.AccessedAt,
			})
		}
	}

	index := CacheIndex{Entries: entries}
	data, err := json.MarshalIndent(index, "", "  ")
	if err != nil {
		return err
	}

	return os.WriteFile(m.indexPath, data, 0644)
}

func (m *Manager) Upload(ctx context.Context, key string, sourcePath string) error {
	sourcePath, err := filepath.Abs(sourcePath)
	if err != nil {
		return err
	}

	archivePath := filepath.Join(m.cacheDir, key+".tar.gz")
	
	if err := createArchive(sourcePath, archivePath); err != nil {
		return err
	}

	stat, err := os.Stat(archivePath)
	if err != nil {
		return err
	}

	file, err := os.Open(archivePath)
	if err != nil {
		return err
	}
	defer file.Close()

	if err := m.storage.Upload(ctx, key, file, stat.Size()); err != nil {
		return err
	}

	if m.useTiered {
		m.tieredLRU.Put(key, stat.Size(), TierWarm)
	} else {
		m.lru.Put(key, stat.Size())
	}
	m.saveIndex()

	return nil
}

func (m *Manager) Download(ctx context.Context, key string, targetPath string) (bool, error) {
	targetPath, err := filepath.Abs(targetPath)
	if err != nil {
		return false, err
	}

	startTime := time.Now()
	archivePath := filepath.Join(m.cacheDir, key+".tar.gz")

	if _, err := os.Stat(archivePath); err == nil {
		cacheHit := false
		var size int64
		if m.useTiered {
			var item *TieredCacheItem
			item, cacheHit = m.tieredLRU.Get(key)
			if item != nil {
				size = item.Size
			}
		} else {
			var item *CacheItem
			item, cacheHit = m.lru.Get(key)
			if item != nil {
				size = item.Size
			}
		}
		if cacheHit {
			if err := extractArchive(archivePath, targetPath); err != nil {
				return false, err
			}
			m.saveIndex()
			duration := time.Since(startTime).Nanoseconds()
			m.analytics.RecordHit(key, size, duration, m.projectID, m.projectType)
			return true, nil
		}
	}

	exists, err := m.storage.Exists(ctx, key)
	if err != nil {
		return false, err
	}

	if !exists {
		m.analytics.RecordMiss(key, m.projectID, m.projectType)
		return false, nil
	}

	reader, err := m.storage.Download(ctx, key)
	if err != nil {
		return false, err
	}
	defer reader.Close()

	if err := os.MkdirAll(filepath.Dir(archivePath), 0755); err != nil {
		return false, err
	}

	file, err := os.Create(archivePath)
	if err != nil {
		return false, err
	}
	defer file.Close()

	written, err := io.Copy(file, reader)
	if err != nil {
		return false, err
	}

	if m.useTiered {
		m.tieredLRU.Put(key, written, TierHot)
	} else {
		m.lru.Put(key, written)
	}
	m.saveIndex()

	if err := extractArchive(archivePath, targetPath); err != nil {
		return false, err
	}

	duration := time.Since(startTime).Nanoseconds()
	m.analytics.RecordHit(key, written, duration, m.projectID, m.projectType)
	return true, nil
}

func (m *Manager) Exists(ctx context.Context, key string) (bool, error) {
	if m.useTiered {
		if m.tieredLRU.Contains(key) {
			return true, nil
		}
	} else {
		if m.lru.Contains(key) {
			return true, nil
		}
	}

	return m.storage.Exists(ctx, key)
}

func (m *Manager) Delete(ctx context.Context, key string) error {
	if m.useTiered {
		m.tieredLRU.Remove(key)
	} else {
		m.lru.Remove(key)
	}
	
	if err := m.storage.Delete(ctx, key); err != nil {
		return err
	}

	cachePath := filepath.Join(m.cacheDir, key+".tar.gz")
	os.Remove(cachePath)

	return m.saveIndex()
}

func (m *Manager) List(ctx context.Context, prefix string) ([]string, error) {
	var keys []string

	var items []interface{}
	if m.useTiered {
		for _, item := range m.tieredLRU.GetItems() {
			if prefix == "" || len(item.Key) >= len(prefix) && item.Key[:len(prefix)] == prefix {
				keys = append(keys, item.Key)
			}
		}
	} else {
		for _, item := range m.lru.GetItems() {
			if prefix == "" || len(item.Key) >= len(prefix) && item.Key[:len(prefix)] == prefix {
				keys = append(keys, item.Key)
			}
		}
	}

	remoteItems, err := m.storage.List(ctx, prefix)
	if err != nil {
		return keys, nil
	}

	localKeys := make(map[string]bool)
	for _, k := range keys {
		localKeys[k] = true
	}

	for _, item := range remoteItems {
		if !localKeys[item.Key] {
			keys = append(keys, item.Key)
		}
	}

	return keys, nil
}

func (m *Manager) Clear() error {
	if m.useTiered {
		m.tieredLRU.Clear()
	} else {
		m.lru.Clear()
	}

	entries, _ := os.ReadDir(m.cacheDir)
	for _, entry := range entries {
		if !entry.IsDir() && filepath.Ext(entry.Name()) == ".gz" {
			os.Remove(filepath.Join(m.cacheDir, entry.Name()))
		}
	}

	return m.saveIndex()
}

func (m *Manager) GetStats() (count int, size int64) {
	if m.useTiered {
		return m.tieredLRU.Count(), m.tieredLRU.Size()
	}
	return m.lru.Count(), m.lru.Size()
}

func (m *Manager) GetTierStats() map[CacheTier]map[string]int64 {
	if m.useTiered {
		return m.tieredLRU.GetTierStats()
	}
	return nil
}

func (m *Manager) PromoteToCore(key string) bool {
	if m.useTiered {
		return m.tieredLRU.PromoteToCore(key)
	}
	return false
}

func (m *Manager) GetAnalytics() *Analytics {
	return m.analytics
}

func (m *Manager) SaveAnalytics() error {
	return m.analytics.Save()
}

func (m *Manager) Close() error {
	m.saveIndex()
	return m.storage.Close()
}

func createArchive(sourcePath string, targetPath string) error {
	if err := os.MkdirAll(filepath.Dir(targetPath), 0755); err != nil {
		return err
	}

	file, err := os.Create(targetPath)
	if err != nil {
		return err
	}
	defer file.Close()

	gzipWriter := gzip.NewWriter(file)
	defer gzipWriter.Close()

	tarWriter := tar.NewWriter(gzipWriter)
	defer tarWriter.Close()

	sourceInfo, err := os.Stat(sourcePath)
	if err != nil {
		return err
	}

	if sourceInfo.IsDir() {
		return addDirToTar(tarWriter, sourcePath, "")
	}

	return addFileToTar(tarWriter, sourcePath, filepath.Base(sourcePath))
}

func addDirToTar(tw *tar.Writer, dirPath string, basePath string) error {
	entries, err := os.ReadDir(dirPath)
	if err != nil {
		return err
	}

	for _, entry := range entries {
		fullPath := filepath.Join(dirPath, entry.Name())
		relPath := filepath.Join(basePath, entry.Name())

		if entry.IsDir() {
			if err := addDirToTar(tw, fullPath, relPath); err != nil {
				return err
			}
		} else {
			if err := addFileToTar(tw, fullPath, relPath); err != nil {
				return err
			}
		}
	}

	return nil
}

func addFileToTar(tw *tar.Writer, filePath string, arcName string) error {
	fileInfo, err := os.Stat(filePath)
	if err != nil {
		return err
	}

	header, err := tar.FileInfoHeader(fileInfo, "")
	if err != nil {
		return err
	}
	header.Name = filepath.ToSlash(arcName)

	if err := tw.WriteHeader(header); err != nil {
		return err
	}

	if !fileInfo.Mode().IsRegular() {
		return nil
	}

	file, err := os.Open(filePath)
	if err != nil {
		return err
	}
	defer file.Close()

	_, err = io.Copy(tw, file)
	return err
}

func extractArchive(archivePath string, targetPath string) error {
	if err := os.MkdirAll(targetPath, 0755); err != nil {
		return err
	}

	file, err := os.Open(archivePath)
	if err != nil {
		return err
	}
	defer file.Close()

	gzipReader, err := gzip.NewReader(file)
	if err != nil {
		return err
	}
	defer gzipReader.Close()

	tarReader := tar.NewReader(gzipReader)

	for {
		header, err := tarReader.Next()
		if err == io.EOF {
			break
		}
		if err != nil {
			return err
		}

		target := filepath.Join(targetPath, filepath.FromSlash(header.Name))

		switch header.Typeflag {
		case tar.TypeDir:
			if err := os.MkdirAll(target, os.FileMode(header.Mode)); err != nil {
				return err
			}
		case tar.TypeReg:
			if err := os.MkdirAll(filepath.Dir(target), 0755); err != nil {
				return err
			}

			outFile, err := os.Create(target)
			if err != nil {
				return err
			}

			if _, err := io.Copy(outFile, tarReader); err != nil {
				outFile.Close()
				return err
			}

			outFile.Close()
			os.Chmod(target, os.FileMode(header.Mode))
		default:
			return fmt.Errorf("unsupported tar entry type: %v", header.Typeflag)
		}
	}

	return nil
}
