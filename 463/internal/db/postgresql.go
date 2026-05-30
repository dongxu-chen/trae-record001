package db

import (
	"context"
	"database/sql"
	"fmt"
	"time"
)

type PostgreSQLDatabase struct {
	BaseDatabase
}

func (p *PostgreSQLDatabase) Connect() error {
	dsn := fmt.Sprintf("postgres://%s:%s@%s:%d/postgres?sslmode=disable",
		p.cfg.User, p.cfg.Password, p.cfg.Host, p.cfg.Port)

	conn, err := sql.Open("postgres", dsn)
	if err != nil {
		return fmt.Errorf("failed to open PostgreSQL connection: %w", err)
	}

	conn.SetMaxOpenConns(5)
	conn.SetMaxIdleConns(2)
	conn.SetConnMaxLifetime(30 * time.Minute)

	if err := conn.Ping(); err != nil {
		return fmt.Errorf("failed to ping PostgreSQL: %w", err)
	}

	p.conn = conn
	return nil
}

func (p *PostgreSQLDatabase) Close() error {
	if p.conn != nil {
		return p.conn.Close()
	}
	return nil
}

func (p *PostgreSQLDatabase) Ping() error {
	if p.conn == nil {
		return fmt.Errorf("not connected")
	}
	return p.conn.Ping()
}

func (p *PostgreSQLDatabase) GetSlowQueries(ctx context.Context, threshold time.Duration) ([]SlowQuery, error) {
	query := `
		SELECT 
			pid,
			COALESCE(datname, ''),
			usename,
			client_addr || ':' || COALESCE(client_port::text, ''),
			query,
			EXTRACT(EPOCH FROM (NOW() - query_start)) as duration,
			state,
			query_start
		FROM pg_stat_activity
		WHERE 
			state = 'active'
			AND query IS NOT NULL 
			AND query != ''
			AND query NOT LIKE '%pg_stat_activity%'
			AND usename != $1
			AND (NOW() - query_start) >= $2::interval
		ORDER BY duration DESC
	`

	rows, err := p.conn.QueryContext(ctx, query, p.cfg.User, threshold.String())
	if err != nil {
		return nil, fmt.Errorf("failed to query pg_stat_activity: %w", err)
	}
	defer rows.Close()

	var slowQueries []SlowQuery
	for rows.Next() {
		var (
			pid         int64
			datname     string
			usename     string
			clientAddr  string
			query       string
			durationSec float64
			state       string
			queryStart  time.Time
		)

		if err := rows.Scan(&pid, &datname, &usename, &clientAddr, &query, &durationSec, &state, &queryStart); err != nil {
			continue
		}

		if query == "" {
			continue
		}

		slowQueries = append(slowQueries, SlowQuery{
			ID:            pid,
			ConnectionID:  pid,
			DBName:        datname,
			User:          usename,
			Host:          clientAddr,
			Query:         query,
			ExecutionTime: time.Duration(durationSec) * time.Second,
			State:         state,
			StartTime:     queryStart,
		})
	}

	return slowQueries, nil
}

func (p *PostgreSQLDatabase) KillQuery(ctx context.Context, connectionID int64, mode string) error {
	var killQuery string
	switch mode {
	case "query":
		killQuery = fmt.Sprintf("SELECT pg_cancel_backend(%d)", connectionID)
	case "connection":
		killQuery = fmt.Sprintf("SELECT pg_terminate_backend(%d)", connectionID)
	default:
		killQuery = fmt.Sprintf("SELECT pg_terminate_backend(%d)", connectionID)
	}

	_, err := p.conn.ExecContext(ctx, killQuery)
	if err != nil {
		return fmt.Errorf("failed to kill query %d: %w", connectionID, err)
	}

	return nil
}
