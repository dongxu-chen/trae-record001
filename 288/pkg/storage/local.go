package storage

import (
	"context"
	"crypto/md5"
	"encoding/hex"
	"io"
	"os"
	"path/filepath"
	"strings"
	"time"
)

type LocalStorage struct {
	basePath string
}

func NewLocalStorage(config Config) (Storage, error) {
	basePath := config.BasePath
	if basePath == "" {
		home, err := os.UserHomeDir()
		if err != nil {
			return nil, err
		}
		basePath = filepath.Join(home, ".cicache", "storage")
	}

	if err := os.MkdirAll(basePath, 0755); err != nil {
		return nil, err
	}

	return &LocalStorage{basePath: basePath}, nil
}

func (s *LocalStorage) getFullPath(key string) string {
	return filepath.Join(s.basePath, filepath.FromSlash(key))
}

func (s *LocalStorage) Upload(ctx context.Context, key string, reader io.Reader, size int64) error {
	fullPath := s.getFullPath(key)
	
	if err := os.MkdirAll(filepath.Dir(fullPath), 0755); err != nil {
		return err
	}

	file, err := os.Create(fullPath)
	if err != nil {
		return err
	}
	defer file.Close()

	_, err = io.Copy(file, reader)
	return err
}

func (s *LocalStorage) Download(ctx context.Context, key string) (io.ReadCloser, error) {
	fullPath := s.getFullPath(key)
	return os.Open(fullPath)
}

func (s *LocalStorage) Exists(ctx context.Context, key string) (bool, error) {
	fullPath := s.getFullPath(key)
	_, err := os.Stat(fullPath)
	if err == nil {
		return true, nil
	}
	if os.IsNotExist(err) {
		return false, nil
	}
	return false, err
}

func (s *LocalStorage) Delete(ctx context.Context, key string) error {
	fullPath := s.getFullPath(key)
	return os.Remove(fullPath)
}

func (s *LocalStorage) List(ctx context.Context, prefix string) ([]ObjectInfo, error) {
	var objects []ObjectInfo

	prefixPath := s.getFullPath(prefix)
	
	err := filepath.Walk(s.basePath, func(path string, info os.FileInfo, err error) error {
		if err != nil {
			return err
		}

		if info.IsDir() {
			return nil
		}

		relPath, err := filepath.Rel(s.basePath, path)
		if err != nil {
			return err
		}

		key := filepath.ToSlash(relPath)

		if prefix != "" && !strings.HasPrefix(key, prefix) {
			return nil
		}

		etag, _ := calculateETag(path)

		objects = append(objects, ObjectInfo{
			Key:          key,
			Size:         info.Size(),
			LastModified: info.ModTime(),
			ETag:         etag,
		})

		return nil
	})

	if err != nil {
		return nil, err
	}

	return objects, nil
}

func (s *LocalStorage) GetInfo(ctx context.Context, key string) (*ObjectInfo, error) {
	fullPath := s.getFullPath(key)
	info, err := os.Stat(fullPath)
	if err != nil {
		return nil, err
	}

	etag, _ := calculateETag(fullPath)

	return &ObjectInfo{
		Key:          key,
		Size:         info.Size(),
		LastModified: info.ModTime(),
		ETag:         etag,
	}, nil
}

func (s *LocalStorage) Close() error {
	return nil
}

func calculateETag(path string) (string, error) {
	file, err := os.Open(path)
	if err != nil {
		return "", err
	}
	defer file.Close()

	hash := md5.New()
	if _, err := io.Copy(hash, file); err != nil {
		return "", err
	}

	return hex.EncodeToString(hash.Sum(nil)), nil
}
