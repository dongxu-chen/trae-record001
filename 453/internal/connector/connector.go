package connector

import (
	"context"
	"database/sql"
	"encoding/json"
	"fmt"
	"strings"
	"time"

	_ "github.com/go-sql-driver/mysql"
	_ "github.com/lib/pq"
)

type DBType string

const (
	MySQL DBType = "mysql"
	PG    DBType = "postgres"
)

type DBConfig struct {
	Type     DBType
	Host     string
	Port     int
	User     string
	Password string
	Database string
	MaxConns int
}

type QueryResult struct {
	Columns []string
	Rows    []map[string]interface{}
	Count   int
}

type QueryLogEntry struct {
	Query     string
	StartTime time.Time
	Duration  time.Duration
	RowsSent  int
	Schema    string
}

type Connector interface {
	Connect(ctx context.Context) error
	Close() error
	ExecuteQuery(ctx context.Context, query string, args ...interface{}) (*QueryResult, error)
	FetchSlowQueryLog(ctx context.Context, since time.Time, limit int) ([]QueryLogEntry, error)
	FetchQueryStats(ctx context.Context) ([]QueryLogEntry, error)
	Ping(ctx context.Context) error
	GetType() DBType
}

type baseConnector struct {
	db   *sql.DB
	conf DBConfig
}

type MySQLConnector struct {
	baseConnector
}

type PGConnector struct {
	baseConnector
}

func NewConnector(conf DBConfig) Connector {
	switch conf.Type {
	case MySQL:
		return &MySQLConnector{baseConnector{conf: conf}}
	case PG:
		return &PGConnector{baseConnector{conf: conf}}
	default:
		return nil
	}
}

func (bc *baseConnector) buildDSN() string {
	switch bc.conf.Type {
	case MySQL:
		return fmt.Sprintf("%s:%s@tcp(%s:%d)/%s?parseTime=true&charset=utf8mb4",
			bc.conf.User, bc.conf.Password, bc.conf.Host, bc.conf.Port, bc.conf.Database)
	case PG:
		return fmt.Sprintf("host=%s port=%d user=%s password=%s dbname=%s sslmode=disable",
			bc.conf.Host, bc.conf.Port, bc.conf.User, bc.conf.Password, bc.conf.Database)
	default:
		return ""
	}
}

func (bc *baseConnector) driverName() string {
	switch bc.conf.Type {
	case MySQL:
		return "mysql"
	case PG:
		return "postgres"
	default:
		return ""
	}
}

func (bc *baseConnector) Connect(ctx context.Context) error {
	dsn := bc.buildDSN()
	db, err := sql.Open(bc.driverName(), dsn)
	if err != nil {
		return fmt.Errorf("failed to open db: %w", err)
	}

	maxConns := bc.conf.MaxConns
	if maxConns <= 0 {
		maxConns = 10
	}
	db.SetMaxOpenConns(maxConns)
	db.SetMaxIdleConns(maxConns / 2)
	db.SetConnMaxLifetime(30 * time.Minute)

	if err := db.PingContext(ctx); err != nil {
		db.Close()
		return fmt.Errorf("failed to ping db: %w", err)
	}

	bc.db = db
	return nil
}

func (bc *baseConnector) Close() error {
	if bc.db != nil {
		return bc.db.Close()
	}
	return nil
}

func (bc *baseConnector) Ping(ctx context.Context) error {
	if bc.db == nil {
		return fmt.Errorf("not connected")
	}
	return bc.db.PingContext(ctx)
}

func (bc *baseConnector) GetType() DBType {
	return bc.conf.Type
}

func (bc *baseConnector) ExecuteQuery(ctx context.Context, query string, args ...interface{}) (*QueryResult, error) {
	if bc.db == nil {
		return nil, fmt.Errorf("not connected")
	}

	rows, err := bc.db.QueryContext(ctx, query, args...)
	if err != nil {
		return nil, fmt.Errorf("query failed: %w", err)
	}
	defer rows.Close()

	cols, err := rows.Columns()
	if err != nil {
		return nil, fmt.Errorf("failed to get columns: %w", err)
	}

	colTypes, err := rows.ColumnTypes()
	if err != nil {
		return nil, fmt.Errorf("failed to get column types: %w", err)
	}

	result := &QueryResult{
		Columns: cols,
		Rows:    make([]map[string]interface{}, 0),
	}

	for rows.Next() {
		values := make([]interface{}, len(cols))
		valuePtrs := make([]interface{}, len(cols))
		for i := range cols {
			switch colTypes[i].DatabaseTypeName() {
			case "BIGINT", "INT", "SMALLINT", "TINYINT", "INTEGER":
				var v sql.NullInt64
				valuePtrs[i] = &v
				values[i] = &v
			case "FLOAT", "DOUBLE", "DECIMAL", "NUMERIC", "REAL":
				var v sql.NullFloat64
				valuePtrs[i] = &v
				values[i] = &v
			case "TEXT", "VARCHAR", "CHAR", "BPCHAR", "BYTEA":
				var v sql.NullString
				valuePtrs[i] = &v
				values[i] = &v
			case "TIMESTAMP", "DATETIME", "DATE", "TIME":
				var v sql.NullTime
				valuePtrs[i] = &v
				values[i] = &v
			default:
				valuePtrs[i] = &values[i]
				values[i] = new(interface{})
			}
		}

		if err := rows.Scan(valuePtrs...); err != nil {
			return nil, fmt.Errorf("failed to scan row: %w", err)
		}

		row := make(map[string]interface{})
		for i, col := range cols {
			switch v := valuePtrs[i].(type) {
			case *sql.NullInt64:
				if v.Valid {
					row[col] = v.Int64
				} else {
					row[col] = nil
				}
			case *sql.NullFloat64:
				if v.Valid {
					row[col] = v.Float64
				} else {
					row[col] = nil
				}
			case *sql.NullString:
				if v.Valid {
					row[col] = v.String
				} else {
					row[col] = nil
				}
			case *sql.NullTime:
				if v.Valid {
					row[col] = v.Time
				} else {
					row[col] = nil
				}
			default:
				row[col] = values[i]
			}
		}
		result.Rows = append(result.Rows, row)
	}

	result.Count = len(result.Rows)
	return result, nil
}

func (m *MySQLConnector) FetchSlowQueryLog(ctx context.Context, since time.Time, limit int) ([]QueryLogEntry, error) {
	if m.db == nil {
		return nil, fmt.Errorf("not connected")
	}

	query := `
		SELECT sql_text, start_time, query_time, rows_sent
		FROM mysql.slow_log
		WHERE start_time >= ?
		ORDER BY start_time DESC
		LIMIT ?
	`

	rows, err := m.db.QueryContext(ctx, query, since, limit)
	if err != nil {
		return nil, fmt.Errorf("failed to fetch slow query log: %w", err)
	}
	defer rows.Close()

	var entries []QueryLogEntry
	for rows.Next() {
		var entry QueryLogEntry
		var queryTimeStr string
		var startTime time.Time
		var rowsSent int
		var sqlText string

		if err := rows.Scan(&sqlText, &startTime, &queryTimeStr, &rowsSent); err != nil {
			continue
		}

		entry.Query = sqlText
		entry.StartTime = startTime
		entry.RowsSent = rowsSent

		parts := strings.Split(queryTimeStr, ":")
		if len(parts) == 3 {
			var h, m, s int
			fmt.Sscanf(parts[0], "%d", &h)
			fmt.Sscanf(parts[1], "%d", &m)
			fmt.Sscanf(parts[2], "%f", &s)
			entry.Duration = time.Duration(h)*time.Hour + time.Duration(m)*time.Minute + time.Duration(s)*time.Second
		}

		entries = append(entries, entry)
	}

	return entries, nil
}

func (m *MySQLConnector) FetchQueryStats(ctx context.Context) ([]QueryLogEntry, error) {
	if m.db == nil {
		return nil, fmt.Errorf("not connected")
	}

	query := `
		SELECT DIGEST_TEXT, COUNT_STAR, AVG_TIMER_WAIT/1000000000 as avg_ms,
		       SUM_ROWS_SENT, FIRST_SEEN, LAST_SEEN
		FROM performance_schema.events_statements_summary_by_digest
		WHERE DIGEST_TEXT IS NOT NULL
		ORDER BY COUNT_STAR DESC
		LIMIT 100
	`

	rows, err := m.db.QueryContext(ctx, query)
	if err != nil {
		return nil, fmt.Errorf("failed to fetch query stats: %w", err)
	}
	defer rows.Close()

	var entries []QueryLogEntry
	for rows.Next() {
		var entry QueryLogEntry
		var digestText string
		var countStar int64
		var avgMs float64
		var rowsSent int64
		var firstSeen, lastSeen time.Time

		if err := rows.Scan(&digestText, &countStar, &avgMs, &rowsSent, &firstSeen, &lastSeen); err != nil {
			continue
		}

		entry.Query = digestText
		entry.Duration = time.Duration(avgMs) * time.Millisecond
		entry.StartTime = lastSeen
		entry.RowsSent = int(rowsSent)
		entries = append(entries, entry)
	}

	return entries, nil
}

func (p *PGConnector) FetchSlowQueryLog(ctx context.Context, since time.Time, limit int) ([]QueryLogEntry, error) {
	if p.db == nil {
		return nil, fmt.Errorf("not connected")
	}

	query := `
		SELECT query, calls, total_exec_time, mean_exec_time, rows,
		       min_exec_time, max_exec_time
		FROM pg_stat_statements
		WHERE query NOT LIKE '%pg_stat%'
		ORDER BY total_exec_time DESC
		LIMIT $1
	`

	rows, err := p.db.QueryContext(ctx, query, limit)
	if err != nil {
		return nil, fmt.Errorf("failed to fetch pg stat statements: %w", err)
	}
	defer rows.Close()

	var entries []QueryLogEntry
	for rows.Next() {
		var entry QueryLogEntry
		var queryText string
		var calls int64
		var totalExecTime, meanExecTime, rowsAffected float64
		var minExec, maxExec float64

		if err := rows.Scan(&queryText, &calls, &totalExecTime, &meanExecTime, &rowsAffected, &minExec, &maxExec); err != nil {
			continue
		}

		entry.Query = queryText
		entry.Duration = time.Duration(meanExecTime) * time.Millisecond
		entry.StartTime = time.Now()
		entry.RowsSent = int(rowsAffected)
		entries = append(entries, entry)
	}

	return entries, nil
}

func (p *PGConnector) FetchQueryStats(ctx context.Context) ([]QueryLogEntry, error) {
	return p.FetchSlowQueryLog(ctx, time.Time{}, 100)
}

func QueryResultToJSON(result *QueryResult) (string, error) {
	data, err := json.Marshal(result.Rows)
	if err != nil {
		return "", fmt.Errorf("failed to marshal result: %w", err)
	}
	return string(data), nil
}
