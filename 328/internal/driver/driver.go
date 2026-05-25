package driver

import (
	"context"
	"db-bench/internal/config"
	"errors"
	"fmt"
	"math/rand"
)

type OperationType string

const (
	OpRead  OperationType = "read"
	OpWrite OperationType = "write"
)

type Operation struct {
	Type      OperationType
	Key       int
	Value     string
	IsHotspot bool
}

type Result struct {
	DurationMs float64
	Success    bool
	Error      error
	OpType     OperationType
}

type DatabaseDriver interface {
	Connect(ctx context.Context) error
	Close(ctx context.Context) error
	InitSchema(ctx context.Context, totalRecords int) error
	Read(ctx context.Context, key int) Result
	Write(ctx context.Context, key int, value string) Result
	HealthCheck(ctx context.Context) error
}

type BaseDriver struct {
	cfg config.DatabaseConfig
}

func NewDriver(cfg config.DatabaseConfig) (DatabaseDriver, error) {
	switch cfg.Type {
	case config.MySQL:
		return NewMySQLDriver(cfg), nil
	case config.PostgreSQL:
		return NewPostgreSQLDriver(cfg), nil
	case config.MongoDB:
		return NewMongoDBDriver(cfg), nil
	default:
		return nil, errors.New("unsupported database type: " + string(cfg.Type))
	}
}

func (d *BaseDriver) GenerateValue() string {
	return fmt.Sprintf("value_%d_%s", rand.Int63(), randomString(100))
}

func randomString(length int) string {
	const charset = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
	b := make([]byte, length)
	for i := range b {
		b[i] = charset[rand.Intn(len(charset))]
	}
	return string(b)
}
