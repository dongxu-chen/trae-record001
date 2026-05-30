package db

import (
	"context"
	"database/sql"
	"fmt"
	"time"
)

type MySQLDatabase struct {
	BaseDatabase
}

func (m *MySQLDatabase) Connect() error {
	dsn := fmt.Sprintf("%s:%s@tcp(%s:%d)/%s?charset=utf8mb4&parseTime=true",
		m.cfg.User, m.cfg.Password, m.cfg.Host, m.cfg.Port, "information_schema")

	conn, err := sql.Open("mysql", dsn)
	if err != nil {
		return fmt.Errorf("failed to open MySQL connection: %w", err)
	}

	conn.SetMaxOpenConns(5)
	conn.SetMaxIdleConns(2)
	conn.SetConnMaxLifetime(30 * time.Minute)

	if err := conn.Ping(); err != nil {
		return fmt.Errorf("failed to ping MySQL: %w", err)
	}

	m.conn = conn
	return nil
}

func (m *MySQLDatabase) Close() error {
	if m.conn != nil {
		return m.conn.Close()
	}
	return nil
}

func (m *MySQLDatabase) Ping() error {
	if m.conn == nil {
		return fmt.Errorf("not connected")
	}
	return m.conn.Ping()
}

func (m *MySQLDatabase) GetSlowQueries(ctx context.Context, threshold time.Duration) ([]SlowQuery, error) {
	query := `
		SELECT 
			id,
			COALESCE(db, ''),
			USER,
			HOST,
			INFO,
			TIME,
			STATE,
			COMMAND
		FROM information_schema.PROCESSLIST
		WHERE 
			COMMAND != 'Sleep' 
			AND INFO IS NOT NULL 
			AND INFO != ''
			AND TIME >= ?
			AND USER != ?
		ORDER BY TIME DESC
	`

	thresholdSeconds := int64(threshold.Seconds())

	rows, err := m.conn.QueryContext(ctx, query, thresholdSeconds, m.cfg.User)
	if err != nil {
		return nil, fmt.Errorf("failed to query processlist: %w", err)
	}
	defer rows.Close()

	var slowQueries []SlowQuery
	for rows.Next() {
		var (
			id          int64
			dbName      string
			user        string
			host        string
			info        sql.NullString
			timeSeconds int64
			state       sql.NullString
			command     string
		)

		if err := rows.Scan(&id, &dbName, &user, &host, &info, &timeSeconds, &state, &command); err != nil {
			continue
		}

		if !info.Valid || info.String == "" {
			continue
		}

		slowQueries = append(slowQueries, SlowQuery{
			ID:            id,
			ConnectionID:  id,
			DBName:        dbName,
			User:          user,
			Host:          host,
			Query:         info.String,
			ExecutionTime: time.Duration(timeSeconds) * time.Second,
			State:         state.String,
			StartTime:     time.Now().Add(-time.Duration(timeSeconds) * time.Second),
		})
	}

	return slowQueries, nil
}

func (m *MySQLDatabase) KillQuery(ctx context.Context, connectionID int64, mode string) error {
	var killQuery string
	switch mode {
	case "query":
		killQuery = fmt.Sprintf("KILL QUERY %d", connectionID)
	case "connection":
		killQuery = fmt.Sprintf("KILL %d", connectionID)
	default:
		killQuery = fmt.Sprintf("KILL %d", connectionID)
	}

	_, err := m.conn.ExecContext(ctx, killQuery)
	if err != nil {
		return fmt.Errorf("failed to kill query %d: %w", connectionID, err)
	}

	return nil
}
