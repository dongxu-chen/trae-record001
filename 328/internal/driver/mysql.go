package driver

import (
	"context"
	"database/sql"
	"db-bench/internal/config"
	"fmt"
	"time"

	_ "github.com/go-sql-driver/mysql"
)

type MySQLDriver struct {
	BaseDriver
	db *sql.DB
}

func NewMySQLDriver(cfg config.DatabaseConfig) *MySQLDriver {
	return &MySQLDriver{
		BaseDriver: BaseDriver{cfg: cfg},
	}
}

func (d *MySQLDriver) Connect(ctx context.Context) error {
	dsn := fmt.Sprintf("%s:%s@tcp(%s:%d)/%s?charset=utf8mb4&parseTime=True&loc=Local",
		d.cfg.User, d.cfg.Password, d.cfg.Host, d.cfg.Port, d.cfg.Database)

	db, err := sql.Open("mysql", dsn)
	if err != nil {
		return fmt.Errorf("failed to open mysql connection: %w", err)
	}

	db.SetMaxOpenConns(d.cfg.MaxConnections)
	db.SetMaxIdleConns(d.cfg.MaxConnections)
	db.SetConnMaxLifetime(time.Hour)

	if err := db.PingContext(ctx); err != nil {
		return fmt.Errorf("failed to ping mysql: %w", err)
	}

	d.db = db
	return nil
}

func (d *MySQLDriver) Close(ctx context.Context) error {
	if d.db != nil {
		return d.db.Close()
	}
	return nil
}

func (d *MySQLDriver) InitSchema(ctx context.Context, totalRecords int) error {
	createTable := `
		CREATE TABLE IF NOT EXISTS benchmark (
			id INT PRIMARY KEY,
			value VARCHAR(255) NOT NULL,
			created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
			updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
			INDEX idx_value (value(50))
		) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
	`
	if _, err := d.db.ExecContext(ctx, createTable); err != nil {
		return fmt.Errorf("failed to create table: %w", err)
	}

	if _, err := d.db.ExecContext(ctx, "TRUNCATE TABLE benchmark"); err != nil {
		return fmt.Errorf("failed to truncate table: %w", err)
	}

	tx, err := d.db.BeginTx(ctx, nil)
	if err != nil {
		return fmt.Errorf("failed to begin transaction: %w", err)
	}

	stmt, err := tx.PrepareContext(ctx, "INSERT INTO benchmark (id, value) VALUES (?, ?)")
	if err != nil {
		tx.Rollback()
		return fmt.Errorf("failed to prepare statement: %w", err)
	}
	defer stmt.Close()

	for i := 0; i < totalRecords; i++ {
		value := d.GenerateValue()
		if _, err := stmt.ExecContext(ctx, i, value); err != nil {
			tx.Rollback()
			return fmt.Errorf("failed to insert record %d: %w", i, err)
		}
		if i > 0 && i%1000 == 0 {
			if err := tx.Commit(); err != nil {
				return fmt.Errorf("failed to commit batch: %w", err)
			}
			tx, err = d.db.BeginTx(ctx, nil)
			if err != nil {
				return fmt.Errorf("failed to begin new transaction: %w", err)
			}
			stmt, err = tx.PrepareContext(ctx, "INSERT INTO benchmark (id, value) VALUES (?, ?)")
			if err != nil {
				tx.Rollback()
				return fmt.Errorf("failed to prepare new statement: %w", err)
			}
		}
	}

	return tx.Commit()
}

func (d *MySQLDriver) Read(ctx context.Context, key int) Result {
	start := time.Now()
	var value string
	query := "SELECT value FROM benchmark WHERE id = ?"
	err := d.db.QueryRowContext(ctx, query, key).Scan(&value)
	duration := float64(time.Since(start).Microseconds()) / 1000.0

	return Result{
		DurationMs: duration,
		Success:    err == nil,
		Error:      err,
		OpType:     OpRead,
	}
}

func (d *MySQLDriver) Write(ctx context.Context, key int, value string) Result {
	start := time.Now()
	query := "INSERT INTO benchmark (id, value) VALUES (?, ?) ON DUPLICATE KEY UPDATE value = VALUES(value), updated_at = CURRENT_TIMESTAMP"
	_, err := d.db.ExecContext(ctx, query, key, value)
	duration := float64(time.Since(start).Microseconds()) / 1000.0

	return Result{
		DurationMs: duration,
		Success:    err == nil,
		Error:      err,
		OpType:     OpWrite,
	}
}

func (d *MySQLDriver) HealthCheck(ctx context.Context) error {
	if d.db == nil {
		return fmt.Errorf("not connected")
	}
	return d.db.PingContext(ctx)
}
