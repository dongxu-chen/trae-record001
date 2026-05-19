package backup

import (
	"context"
	"database/sql"
	"fmt"
	"os"
	"os/exec"
	"path/filepath"
	"strconv"
	"sync"
	"time"

	"backup-tool/pkg/config"
	"backup-tool/pkg/logger"

	_ "github.com/go-sql-driver/mysql"
)

type MySQLBackup struct {
	cfg        *config.MySQLConfig
	backupDir  string
	lastBinlog string
	lastPos    int64
	mu         sync.RWMutex
}

func NewMySQLBackup(cfg *config.MySQLConfig, backupDir string) *MySQLBackup {
	return &MySQLBackup{
		cfg:       cfg,
		backupDir: backupDir,
	}
}

func (m *MySQLBackup) BackupDatabase(ctx context.Context, dbName string) (*BackupResult, error) {
	startTime := time.Now()
	logger.Infof("Starting MySQL backup for database: %s", dbName)

	timestamp := time.Now().Format("20060102_150405")
	filename := fmt.Sprintf("mysql_%s_%s.sql", dbName, timestamp)
	filePath := filepath.Join(m.backupDir, filename)

	args := []string{
		"--host", m.cfg.Host,
		"--port", strconv.Itoa(m.cfg.Port),
		"--user", m.cfg.User,
		"--password=" + m.cfg.Password,
		"--single-transaction",
		"--quick",
		"--lock-tables=false",
		"--set-gtid-purged=OFF",
		dbName,
	}

	cmd := exec.CommandContext(ctx, m.cfg.MysqldumpPath, args...)
	cmd.Env = append(os.Environ(), "MYSQL_PWD="+m.cfg.Password)

	output, err := os.Create(filePath)
	if err != nil {
		return nil, fmt.Errorf("failed to create output file: %w", err)
	}
	defer output.Close()

	cmd.Stdout = output

	if err := cmd.Run(); err != nil {
		os.Remove(filePath)
		return nil, fmt.Errorf("mysqldump failed: %w", err)
	}

	fileInfo, err := os.Stat(filePath)
	if err != nil {
		return nil, fmt.Errorf("failed to get file info: %w", err)
	}

	gtidSet, binlogFile, binlogPos, err := m.getGTIDInfo(ctx)
	if err != nil {
		logger.Warnf("Failed to get GTID info: %v", err)
	}

	result := &BackupResult{
		Database:      dbName,
		Type:          BackupTypeMySQL,
		FilePath:      filePath,
		FileName:      filename,
		Size:          fileInfo.Size(),
		Duration:      time.Since(startTime),
		Success:       true,
		IsIncremental: false,
		GTIDSet:       gtidSet,
		BinlogFile:    binlogFile,
		BinlogPos:     binlogPos,
		Timestamp:     startTime,
	}

	logger.Infof("MySQL backup completed for %s: %s, size: %d bytes, duration: %v",
		dbName, filePath, fileInfo.Size(), time.Since(startTime))

	return result, nil
}

func (m *MySQLBackup) getGTIDInfo(ctx context.Context) (string, string, int64, error) {
	dsn := fmt.Sprintf("%s:%s@tcp(%s:%d)/",
		m.cfg.User, m.cfg.Password, m.cfg.Host, m.cfg.Port)

	db, err := sql.Open("mysql", dsn)
	if err != nil {
		return "", "", 0, err
	}
	defer db.Close()

	var gtidExecuted, binlogFile, binlogPos := "", "", int64(0)

	rows, err := db.QueryContext(ctx, "SHOW MASTER STATUS")
	if err == nil {
		defer rows.Close()
		if rows.Next() {
			var dummy interface{}
			rows.Scan(&binlogFile, &binlogPos, &dummy, &dummy, &gtidExecuted)
		}
	}

	return gtidExecuted, binlogFile, binlogPos, nil
}

func (m *MySQLBackup) BackupIncremental(ctx context.Context) ([]*BackupResult, error) {
	logger.Info("Starting MySQL incremental backup (binlog)")

	dsn := fmt.Sprintf("%s:%s@tcp(%s:%d)/",
		m.cfg.User, m.cfg.Password, m.cfg.Host, m.cfg.Port)

	db, err := sql.Open("mysql", dsn)
	if err != nil {
		return nil, err
	}
	defer db.Close()

	rows, err := db.QueryContext(ctx, "SHOW BINARY LOGS")
	if err != nil {
		return nil, err
	}
	defer rows.Close()

	var results []*BackupResult
	m.mu.RLock()
	lastBinlog := m.lastBinlog
	m.mu.RUnlock()

	for rows.Next() {
		var logName string
		var fileSize int64
		if err := rows.Scan(&logName, &fileSize); err != nil {
			continue
		}

		if lastBinlog != "" && logName <= lastBinlog {
			continue
		}

		result, err := m.backupBinlog(ctx, logName)
		if err != nil {
			logger.Errorf("Failed to backup binlog %s: %v", logName, err)
			continue
		} else {
			results = append(results, result)
		}
	}

	if len(results) > 0 {
		lastResult := results[len(results)-1]
		m.mu.Lock()
		m.lastBinlog = lastResult.BinlogFile
		m.mu.Unlock()
	}

	return results, nil
}

func (m *MySQLBackup) backupBinlog(ctx context.Context, binlogName string) (*BackupResult, error) {
	startTime := time.Now()

	timestamp := time.Now().Format("20060102_150405")
	filename := fmt.Sprintf("mysql_binlog_%s_%s.sql", binlogName, timestamp)
	filePath := filepath.Join(m.backupDir, "incremental", filename)

	if err := os.MkdirAll(filepath.Dir(filePath), 0755); err != nil {
		return nil, err
	}

	args := []string{
		"--host", m.cfg.Host,
		"--port", strconv.Itoa(m.cfg.Port),
		"--user", m.cfg.User,
		binlogName,
	}

	cmd := exec.CommandContext(ctx, m.cfg.MysqlbinlogPath, args...)
	cmd.Env = append(os.Environ(), "MYSQL_PWD="+m.cfg.Password)

	output, err := os.Create(filePath)
	if err != nil {
		return nil, err
	}
	defer output.Close()

	cmd.Stdout = output

	if err := cmd.Run(); err != nil {
		os.Remove(filePath)
		return nil, err
	}

	fileInfo, err := os.Stat(filePath)
	if err != nil {
		return nil, err
	}

	return &BackupResult{
		Database:      "binlog",
		Type:          BackupTypeMySQL,
		FilePath:      filePath,
		FileName:      filename,
		Size:          fileInfo.Size(),
		Duration:      time.Since(startTime),
		Success:       true,
		IsIncremental: true,
		BinlogFile:    binlogName,
		Timestamp:     startTime,
	}, nil
}

func (m *MySQLBackup) BackupAll(ctx context.Context) ([]*BackupResult, error) {
	var results []*BackupResult
	var wg sync.WaitGroup
	var mu sync.Mutex

	sem := make(chan struct{}, 4)

	for _, dbName := range m.cfg.Databases {
		wg.Add(1)
		sem <- struct{}{}

		go func(db string) {
			defer wg.Done()
			defer func() { <-sem }()

			result, err := m.BackupDatabase(ctx, db)
			mu.Lock()
			defer mu.Unlock()

			if err != nil {
				logger.Errorf("Backup failed for %s: %v", db, err)
				results = append(results, &BackupResult{
					Database: db,
					Type:     BackupTypeMySQL,
					Success:  false,
					Error:    err,
					Timestamp: time.Now(),
				})
			} else {
				results = append(results, result)
			}
		}(dbName)
	}

	wg.Wait()
	return results, nil
}
