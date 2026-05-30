package db

import (
	"context"
	"database/sql"
	"fmt"
	"time"

	"slow-query-killer/internal/config"

	_ "github.com/go-sql-driver/mysql"
	_ "github.com/lib/pq"
)

type SlowQuery struct {
	ID            int64
	ConnectionID  int64
	DBName        string
	User          string
	Host          string
	Query         string
	ExecutionTime time.Duration
	LockTime      time.Duration
	RowsExamined  int64
	RowsSent      int64
	State         string
	StartTime     time.Time
}

type Database interface {
	Connect() error
	Close() error
	GetSlowQueries(ctx context.Context, threshold time.Duration) ([]SlowQuery, error)
	KillQuery(ctx context.Context, connectionID int64, mode string) error
	Ping() error
}

type BaseDatabase struct {
	dbName string
	cfg    config.DatabaseConfig
	conn   *sql.DB
}

func NewDatabase(name string, cfg config.DatabaseConfig) (Database, error) {
	switch cfg.Type {
	case config.MySQL:
		return &MySQLDatabase{
			BaseDatabase: BaseDatabase{
				dbName: name,
				cfg:    cfg,
			},
		}, nil
	case config.PostgreSQL:
		return &PostgreSQLDatabase{
			BaseDatabase: BaseDatabase{
				dbName: name,
				cfg:    cfg,
			},
		}, nil
	default:
		return nil, fmt.Errorf("unsupported database type: %s", cfg.Type)
	}
}
