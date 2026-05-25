package driver

import (
	"context"
	"db-bench/internal/config"
	"fmt"
	"time"

	"github.com/jackc/pgx/v5"
	"github.com/jackc/pgx/v5/pgxpool"
)

type PostgreSQLDriver struct {
	BaseDriver
	pool *pgxpool.Pool
}

func NewPostgreSQLDriver(cfg config.DatabaseConfig) *PostgreSQLDriver {
	return &PostgreSQLDriver{
		BaseDriver: BaseDriver{cfg: cfg},
	}
}

func (d *PostgreSQLDriver) Connect(ctx context.Context) error {
	connStr := fmt.Sprintf("postgres://%s:%s@%s:%d/%s?sslmode=disable",
		d.cfg.User, d.cfg.Password, d.cfg.Host, d.cfg.Port, d.cfg.Database)

	poolConfig, err := pgxpool.ParseConfig(connStr)
	if err != nil {
		return fmt.Errorf("failed to parse pgx config: %w", err)
	}

	poolConfig.MaxConns = int32(d.cfg.MaxConnections)
	poolConfig.ConnConfig.ConnectTimeout = d.cfg.Timeout

	pool, err := pgxpool.NewWithConfig(ctx, poolConfig)
	if err != nil {
		return fmt.Errorf("failed to create pgx pool: %w", err)
	}

	if err := pool.Ping(ctx); err != nil {
		pool.Close()
		return fmt.Errorf("failed to ping postgres: %w", err)
	}

	d.pool = pool
	return nil
}

func (d *PostgreSQLDriver) Close(ctx context.Context) error {
	if d.pool != nil {
		d.pool.Close()
	}
	return nil
}

func (d *PostgreSQLDriver) InitSchema(ctx context.Context, totalRecords int) error {
	createTable := `
		CREATE TABLE IF NOT EXISTS benchmark (
			id INTEGER PRIMARY KEY,
			value VARCHAR(255) NOT NULL,
			created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
			updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
		)
	`
	if _, err := d.pool.Exec(ctx, createTable); err != nil {
		return fmt.Errorf("failed to create table: %w", err)
	}

	createIndex := "CREATE INDEX IF NOT EXISTS idx_benchmark_value ON benchmark(value)"
	if _, err := d.pool.Exec(ctx, createIndex); err != nil {
		return fmt.Errorf("failed to create index: %w", err)
	}

	if _, err := d.pool.Exec(ctx, "TRUNCATE TABLE benchmark"); err != nil {
		return fmt.Errorf("failed to truncate table: %w", err)
	}

	batch := &pgx.Batch{}
	for i := 0; i < totalRecords; i++ {
		value := d.GenerateValue()
		batch.Queue("INSERT INTO benchmark (id, value) VALUES ($1, $2)", i, value)
		if i > 0 && i%1000 == 0 {
			br := d.pool.SendBatch(ctx, batch)
			if err := br.Close(); err != nil {
				return fmt.Errorf("failed to execute batch at %d: %w", i, err)
			}
			batch = &pgx.Batch{}
		}
	}

	if batch.Len() > 0 {
		br := d.pool.SendBatch(ctx, batch)
		if err := br.Close(); err != nil {
			return fmt.Errorf("failed to execute final batch: %w", err)
		}
	}

	return nil
}

func (d *PostgreSQLDriver) Read(ctx context.Context, key int) Result {
	start := time.Now()
	var value string
	query := "SELECT value FROM benchmark WHERE id = $1"
	err := d.pool.QueryRow(ctx, query, key).Scan(&value)
	duration := float64(time.Since(start).Microseconds()) / 1000.0

	return Result{
		DurationMs: duration,
		Success:    err == nil,
		Error:      err,
		OpType:     OpRead,
	}
}

func (d *PostgreSQLDriver) Write(ctx context.Context, key int, value string) Result {
	start := time.Now()
	query := `
		INSERT INTO benchmark (id, value, updated_at) VALUES ($1, $2, CURRENT_TIMESTAMP)
		ON CONFLICT (id) DO UPDATE SET value = EXCLUDED.value, updated_at = CURRENT_TIMESTAMP
	`
	_, err := d.pool.Exec(ctx, query, key, value)
	duration := float64(time.Since(start).Microseconds()) / 1000.0

	return Result{
		DurationMs: duration,
		Success:    err == nil,
		Error:      err,
		OpType:     OpWrite,
	}
}

func (d *PostgreSQLDriver) HealthCheck(ctx context.Context) error {
	if d.pool == nil {
		return fmt.Errorf("not connected")
	}
	return d.pool.Ping(ctx)
}
