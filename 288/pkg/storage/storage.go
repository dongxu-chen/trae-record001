package storage

import (
	"context"
	"fmt"
	"io"
	"time"
)

type ObjectInfo struct {
	Key          string
	Size         int64
	LastModified time.Time
	ETag         string
	Metadata     map[string]string
}

type Storage interface {
	Upload(ctx context.Context, key string, reader io.Reader, size int64) error
	Download(ctx context.Context, key string) (io.ReadCloser, error)
	Exists(ctx context.Context, key string) (bool, error)
	Delete(ctx context.Context, key string) error
	List(ctx context.Context, prefix string) ([]ObjectInfo, error)
	GetInfo(ctx context.Context, key string) (*ObjectInfo, error)
	Close() error
}

type Config struct {
	Type     string
	Endpoint string
	Bucket   string
	Region   string
	AccessKey string
	SecretKey string
	UseSSL   bool
	BasePath string
}

type Factory func(config Config) (Storage, error)

var factories = make(map[string]Factory)

func Register(name string, factory Factory) {
	factories[name] = factory
}

func NewStorage(config Config) (Storage, error) {
	factory, ok := factories[config.Type]
	if !ok {
		return nil, fmt.Errorf("unknown storage type: %s", config.Type)
	}
	return factory(config)
}

func init() {
	Register("local", NewLocalStorage)
}
