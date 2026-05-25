package storage

import (
	"context"
	"database/sql"
	"db-bench/internal/config"
	"db-bench/internal/metrics"
	"encoding/json"
	"fmt"
	"os"
	"path/filepath"
	"time"

	_ "modernc.org/sqlite"
)

type BenchmarkRun struct {
	ID               int64     `db:"id"`
	RunID            string    `db:"run_id"`
	Name             string    `db:"name"`
	DatabaseType     string    `db:"database_type"`
	DatabaseHost     string    `db:"database_host"`
	DatabasePort     int       `db:"database_port"`
	DatabaseName     string    `db:"database_name"`
	StartTime        time.Time `db:"start_time"`
	EndTime          time.Time `db:"end_time"`
	DurationSeconds  float64   `db:"duration_seconds"`
	TargetConcurrency int      `db:"target_concurrency"`
	ReadRatio        float64   `db:"read_ratio"`
	WriteRatio       float64   `db:"write_ratio"`
	HotspotPct       float64   `db:"hotspot_pct"`
	HotspotSkew      float64   `db:"hotspot_skew"`
	TotalRecords     int       `db:"total_records"`
	Status           string    `db:"status"`
	FinalQPS         float64   `db:"final_qps"`
	FinalTPS         float64   `db:"final_tps"`
	FinalErrorRate   float64   `db:"final_error_rate"`
	FinalP50         float64   `db:"final_p50"`
	FinalP99         float64   `db:"final_p99"`
	FinalP999        float64   `db:"final_p999"`
	TotalOps         uint64    `db:"total_ops"`
	SuccessOps       uint64    `db:"success_ops"`
	FailedOps        uint64    `db:"failed_ops"`
}

type TimeSeriesPoint struct {
	Timestamp    time.Time `db:"timestamp"`
	ElapsedSec   float64   `db:"elapsed_sec"`
	Concurrency  int       `db:"concurrency"`
	QPS          float64   `db:"qps"`
	TPS          float64   `db:"tps"`
	ErrorRate    float64   `db:"error_rate"`
	P50          float64   `db:"p50"`
	P99          float64   `db:"p99"`
	P999         float64   `db:"p999"`
	TotalOps     uint64    `db:"total_ops"`
	InstantQPS   float64   `db:"instant_qps"`
}

type Snapshot struct {
	ID               int64     `db:"id"`
	RunID            string    `db:"run_id"`
	Timestamp        time.Time `db:"timestamp"`
	ElapsedSec       float64   `db:"elapsed_sec"`
	Concurrency      int       `db:"concurrency"`
	ActiveWorkers    int       `db:"active_workers"`
	ConfigJSON       string    `db:"config_json"`
	MetricsJSON      string    `db:"metrics_json"`
	CheckpointNum    int       `db:"checkpoint_num"`
}

type Storage struct {
	db *sql.DB
}

func NewStorage(dataDir string) (*Storage, error) {
	if dataDir == "" {
		dataDir = "./data"
	}
	if err := os.MkdirAll(dataDir, 0755); err != nil {
		return nil, fmt.Errorf("failed to create data directory: %w", err)
	}

	dbPath := filepath.Join(dataDir, "db_bench.db")
	db, err := sql.Open("sqlite", dbPath)
	if err != nil {
		return nil, fmt.Errorf("failed to open sqlite database: %w", err)
	}

	if _, err := db.Exec("PRAGMA journal_mode=WAL; PRAGMA synchronous=NORMAL;"); err != nil {
		return nil, fmt.Errorf("failed to set sqlite pragmas: %w", err)
	}

	s := &Storage{db: db}
	if err := s.initSchema(); err != nil {
		return nil, err
	}

	return s, nil
}

func (s *Storage) initSchema() error {
	schema := `
	CREATE TABLE IF NOT EXISTS benchmark_runs (
		id INTEGER PRIMARY KEY AUTOINCREMENT,
		run_id TEXT UNIQUE NOT NULL,
		name TEXT NOT NULL,
		database_type TEXT NOT NULL,
		database_host TEXT NOT NULL,
		database_port INTEGER NOT NULL,
		database_name TEXT NOT NULL,
		start_time TIMESTAMP NOT NULL,
		end_time TIMESTAMP,
		duration_seconds REAL,
		target_concurrency INTEGER NOT NULL,
		read_ratio REAL NOT NULL,
		write_ratio REAL NOT NULL,
		hotspot_pct REAL NOT NULL,
		hotspot_skew REAL NOT NULL,
		total_records INTEGER NOT NULL,
		status TEXT NOT NULL,
		final_qps REAL,
		final_tps REAL,
		final_error_rate REAL,
		final_p50 REAL,
		final_p99 REAL,
		final_p999 REAL,
		total_ops INTEGER,
		success_ops INTEGER,
		failed_ops INTEGER,
		created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
	);

	CREATE TABLE IF NOT EXISTS timeseries (
		id INTEGER PRIMARY KEY AUTOINCREMENT,
		run_id TEXT NOT NULL,
		timestamp TIMESTAMP NOT NULL,
		elapsed_sec REAL NOT NULL,
		concurrency INTEGER NOT NULL,
		qps REAL NOT NULL,
		tps REAL NOT NULL,
		error_rate REAL NOT NULL,
		p50 REAL NOT NULL,
		p99 REAL NOT NULL,
		p999 REAL NOT NULL,
		total_ops INTEGER NOT NULL,
		instant_qps REAL NOT NULL,
		FOREIGN KEY (run_id) REFERENCES benchmark_runs(run_id) ON DELETE CASCADE
	);

	CREATE INDEX IF NOT EXISTS idx_timeseries_run_id ON timeseries(run_id);
	CREATE INDEX IF NOT EXISTS idx_timeseries_timestamp ON timeseries(timestamp);

	CREATE TABLE IF NOT EXISTS snapshots (
		id INTEGER PRIMARY KEY AUTOINCREMENT,
		run_id TEXT NOT NULL,
		timestamp TIMESTAMP NOT NULL,
		elapsed_sec REAL NOT NULL,
		concurrency INTEGER NOT NULL,
		active_workers INTEGER NOT NULL,
		config_json TEXT NOT NULL,
		metrics_json TEXT NOT NULL,
		checkpoint_num INTEGER NOT NULL,
		FOREIGN KEY (run_id) REFERENCES benchmark_runs(run_id) ON DELETE CASCADE
	);

	CREATE INDEX IF NOT EXISTS idx_snapshots_run_id ON snapshots(run_id);
	CREATE INDEX IF NOT EXISTS idx_snapshots_timestamp ON snapshots(timestamp);
	`

	_, err := s.db.Exec(schema)
	return err
}

func (s *Storage) Close() error {
	return s.db.Close()
}

func (s *Storage) CreateRun(ctx context.Context, run *BenchmarkRun) error {
	query := `
		INSERT INTO benchmark_runs (
			run_id, name, database_type, database_host, database_port, database_name,
			start_time, target_concurrency, read_ratio, write_ratio,
			hotspot_pct, hotspot_skew, total_records, status
		) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
	`
	_, err := s.db.ExecContext(ctx, query,
		run.RunID, run.Name, run.DatabaseType, run.DatabaseHost, run.DatabasePort, run.DatabaseName,
		run.StartTime, run.TargetConcurrency, run.ReadRatio, run.WriteRatio,
		run.HotspotPct, run.HotspotSkew, run.TotalRecords, run.Status,
	)
	return err
}

func (s *Storage) UpdateRunStatus(ctx context.Context, runID string, status string) error {
	query := `UPDATE benchmark_runs SET status = ? WHERE run_id = ?`
	_, err := s.db.ExecContext(ctx, query, status, runID)
	return err
}

func (s *Storage) CompleteRun(ctx context.Context, runID string, snap metrics.Snapshot) error {
	query := `
		UPDATE benchmark_runs SET
			status = 'completed',
			end_time = ?,
			duration_seconds = ?,
			final_qps = ?,
			final_tps = ?,
			final_error_rate = ?,
			final_p50 = ?,
			final_p99 = ?,
			final_p999 = ?,
			total_ops = ?,
			success_ops = ?,
			failed_ops = ?
		WHERE run_id = ?
	`
	_, err := s.db.ExecContext(ctx, query,
		time.Now(), snap.Duration.Seconds(),
		snap.QPS, snap.TPS, snap.ErrorRate,
		snap.P50, snap.P99, snap.P999,
		snap.TotalOps, snap.SuccessOps, snap.FailedOps,
		runID,
	)
	return err
}

func (s *Storage) InsertTimeSeries(ctx context.Context, runID string, point TimeSeriesPoint) error {
	query := `
		INSERT INTO timeseries (
			run_id, timestamp, elapsed_sec, concurrency,
			qps, tps, error_rate, p50, p99, p999, total_ops, instant_qps
		) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
	`
	_, err := s.db.ExecContext(ctx, query,
		runID, point.Timestamp, point.ElapsedSec, point.Concurrency,
		point.QPS, point.TPS, point.ErrorRate,
		point.P50, point.P99, point.P999,
		point.TotalOps, point.InstantQPS,
	)
	return err
}

func (s *Storage) SaveSnapshot(ctx context.Context, runID string, elapsedSec float64, concurrency int, activeWorkers int, cfg config.Config, snap metrics.Snapshot, checkpointNum int) error {
	cfgJSON, err := json.Marshal(cfg)
	if err != nil {
		return fmt.Errorf("failed to marshal config: %w", err)
	}

	metricsJSON, err := json.Marshal(snap)
	if err != nil {
		return fmt.Errorf("failed to marshal metrics: %w", err)
	}

	query := `
		INSERT INTO snapshots (
			run_id, timestamp, elapsed_sec, concurrency, active_workers,
			config_json, metrics_json, checkpoint_num
		) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
	`
	_, err = s.db.ExecContext(ctx, query,
		runID, time.Now(), elapsedSec, concurrency, activeWorkers,
		string(cfgJSON), string(metricsJSON), checkpointNum,
	)
	return err
}

func (s *Storage) GetLatestSnapshot(ctx context.Context, runID string) (*Snapshot, error) {
	query := `
		SELECT id, run_id, timestamp, elapsed_sec, concurrency, active_workers,
		       config_json, metrics_json, checkpoint_num
		FROM snapshots
		WHERE run_id = ?
		ORDER BY checkpoint_num DESC
		LIMIT 1
	`

	row := s.db.QueryRowContext(ctx, query, runID)
	var snap Snapshot
	var configJSON, metricsJSON string
	err := row.Scan(&snap.ID, &snap.RunID, &snap.Timestamp, &snap.ElapsedSec, &snap.Concurrency,
		&snap.ActiveWorkers, &configJSON, &metricsJSON, &snap.CheckpointNum)
	if err != nil {
		if err == sql.ErrNoRows {
			return nil, nil
		}
		return nil, err
	}

	snap.ConfigJSON = configJSON
	snap.MetricsJSON = metricsJSON
	return &snap, nil
}

func (s *Storage) ListRuns(ctx context.Context, limit int) ([]BenchmarkRun, error) {
	query := `
		SELECT id, run_id, name, database_type, database_host, database_port, database_name,
		       start_time, end_time, duration_seconds, target_concurrency,
		       read_ratio, write_ratio, hotspot_pct, hotspot_skew, total_records,
		       status, final_qps, final_tps, final_error_rate,
		       final_p50, final_p99, final_p999, total_ops, success_ops, failed_ops
		FROM benchmark_runs
		ORDER BY start_time DESC
		LIMIT ?
	`

	rows, err := s.db.QueryContext(ctx, query, limit)
	if err != nil {
		return nil, err
	}
	defer rows.Close()

	var runs []BenchmarkRun
	for rows.Next() {
		var r BenchmarkRun
		var endTime sql.NullTime
		err := rows.Scan(
			&r.ID, &r.RunID, &r.Name, &r.DatabaseType, &r.DatabaseHost, &r.DatabasePort, &r.DatabaseName,
			&r.StartTime, &endTime, &r.DurationSeconds, &r.TargetConcurrency,
			&r.ReadRatio, &r.WriteRatio, &r.HotspotPct, &r.HotspotSkew, &r.TotalRecords,
			&r.Status, &r.FinalQPS, &r.FinalTPS, &r.FinalErrorRate,
			&r.FinalP50, &r.FinalP99, &r.FinalP999, &r.TotalOps, &r.SuccessOps, &r.FailedOps,
		)
		if err != nil {
			return nil, err
		}
		if endTime.Valid {
			r.EndTime = endTime.Time
		}
		runs = append(runs, r)
	}

	return runs, rows.Err()
}

func (s *Storage) GetTimeSeries(ctx context.Context, runID string) ([]TimeSeriesPoint, error) {
	query := `
		SELECT timestamp, elapsed_sec, concurrency, qps, tps, error_rate,
		       p50, p99, p999, total_ops, instant_qps
		FROM timeseries
		WHERE run_id = ?
		ORDER BY timestamp ASC
	`

	rows, err := s.db.QueryContext(ctx, query, runID)
	if err != nil {
		return nil, err
	}
	defer rows.Close()

	var points []TimeSeriesPoint
	for rows.Next() {
		var p TimeSeriesPoint
		err := rows.Scan(
			&p.Timestamp, &p.ElapsedSec, &p.Concurrency, &p.QPS, &p.TPS, &p.ErrorRate,
			&p.P50, &p.P99, &p.P999, &p.TotalOps, &p.InstantQPS,
		)
		if err != nil {
			return nil, err
		}
		points = append(points, p)
	}

	return points, rows.Err()
}

func (s *Storage) GetRun(ctx context.Context, runID string) (*BenchmarkRun, error) {
	query := `
		SELECT id, run_id, name, database_type, database_host, database_port, database_name,
		       start_time, end_time, duration_seconds, target_concurrency,
		       read_ratio, write_ratio, hotspot_pct, hotspot_skew, total_records,
		       status, final_qps, final_tps, final_error_rate,
		       final_p50, final_p99, final_p999, total_ops, success_ops, failed_ops
		FROM benchmark_runs
		WHERE run_id = ?
	`

	row := s.db.QueryRowContext(ctx, query, runID)
	var r BenchmarkRun
	var endTime sql.NullTime
	err := row.Scan(
		&r.ID, &r.RunID, &r.Name, &r.DatabaseType, &r.DatabaseHost, &r.DatabasePort, &r.DatabaseName,
		&r.StartTime, &endTime, &r.DurationSeconds, &r.TargetConcurrency,
		&r.ReadRatio, &r.WriteRatio, &r.HotspotPct, &r.HotspotSkew, &r.TotalRecords,
		&r.Status, &r.FinalQPS, &r.FinalTPS, &r.FinalErrorRate,
		&r.FinalP50, &r.FinalP99, &r.FinalP999, &r.TotalOps, &r.SuccessOps, &r.FailedOps,
	)
	if err != nil {
		return nil, err
	}
	if endTime.Valid {
		r.EndTime = endTime.Time
	}
	return &r, nil
}

func (s *Storage) CompareRuns(ctx context.Context, runIDs []string) (map[string][]TimeSeriesPoint, error) {
	result := make(map[string][]TimeSeriesPoint)
	for _, runID := range runIDs {
		points, err := s.GetTimeSeries(ctx, runID)
		if err != nil {
			return nil, fmt.Errorf("failed to get timeseries for run %s: %w", runID, err)
		}
		result[runID] = points
	}
	return result, nil
}

func (s *Storage) LoadSnapshotConfig(ctx context.Context, runID string) (*config.Config, error) {
	snap, err := s.GetLatestSnapshot(ctx, runID)
	if err != nil {
		return nil, err
	}
	if snap == nil {
		return nil, fmt.Errorf("no snapshot found for run %s", runID)
	}

	var cfg config.Config
	if err := json.Unmarshal([]byte(snap.ConfigJSON), &cfg); err != nil {
		return nil, fmt.Errorf("failed to unmarshal config: %w", err)
	}

	return &cfg, nil
}

func (s *Storage) DeleteRun(ctx context.Context, runID string) error {
	tx, err := s.db.BeginTx(ctx, nil)
	if err != nil {
		return err
	}

	if _, err := tx.ExecContext(ctx, "DELETE FROM timeseries WHERE run_id = ?", runID); err != nil {
		tx.Rollback()
		return err
	}
	if _, err := tx.ExecContext(ctx, "DELETE FROM snapshots WHERE run_id = ?", runID); err != nil {
		tx.Rollback()
		return err
	}
	if _, err := tx.ExecContext(ctx, "DELETE FROM benchmark_runs WHERE run_id = ?", runID); err != nil {
		tx.Rollback()
		return err
	}

	return tx.Commit()
}
