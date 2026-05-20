package backup

import (
	"context"
	"fmt"
	"os"
	"os/exec"
	"path/filepath"
	"strconv"
	"sync"
	"time"

	"backup-tool/pkg/config"
	"backup-tool/pkg/logger"
)

type PostgreSQLBackup struct {
	cfg       *config.PostgreSQLConfig
	backupDir string
}

func NewPostgreSQLBackup(cfg *config.PostgreSQLConfig, backupDir string) *PostgreSQLBackup {
	return &PostgreSQLBackup{
		cfg:       cfg,
		backupDir: backupDir,
	}
}

func (p *PostgreSQLBackup) BackupDatabase(ctx context.Context, dbName string) (*BackupResult, error) {
	startTime := time.Now()
	logger.Infof("Starting PostgreSQL backup for database: %s", dbName)

	timestamp := time.Now().Format("20060102_150405")
	filename := fmt.Sprintf("postgresql_%s_%s.sql", dbName, timestamp)
	filePath := filepath.Join(p.backupDir, filename)

	args := []string{
		"--host", p.cfg.Host,
		"--port", strconv.Itoa(p.cfg.Port),
		"--username", p.cfg.User,
		"--no-password",
		"--no-owner",
		"--no-privileges",
		dbName,
	}

	cmd := exec.CommandContext(ctx, p.cfg.PgDumpPath, args...)
	cmd.Env = append(os.Environ(), fmt.Sprintf("PGPASSWORD=%s", p.cfg.Password))

	output, err := os.Create(filePath)
	if err != nil {
		return nil, fmt.Errorf("failed to create output file: %w", err)
	}
	defer output.Close()

	cmd.Stdout = output

	if err := cmd.Run(); err != nil {
		os.Remove(filePath)
		return nil, fmt.Errorf("pg_dump failed: %w", err)
	}

	fileInfo, err := os.Stat(filePath)
	if err != nil {
		return nil, fmt.Errorf("failed to get file info: %w", err)
	}

	result := &BackupResult{
		Database:      dbName,
		Type:          BackupTypePostgreSQL,
		FilePath:      filePath,
		FileName:      filename,
		Size:          fileInfo.Size(),
		Duration:      time.Since(startTime),
		Success:       true,
		IsIncremental: false,
		Timestamp:     startTime,
	}

	logger.Infof("PostgreSQL backup completed for %s: %s, size: %d bytes, duration: %v",
		dbName, filePath, fileInfo.Size(), time.Since(startTime))

	return result, nil
}

func (p *PostgreSQLBackup) BackupAll(ctx context.Context) ([]*BackupResult, error) {
	var results []*BackupResult
	var wg sync.WaitGroup
	var mu sync.Mutex

	sem := make(chan struct{}, 4)

	for _, dbName := range p.cfg.Databases {
		wg.Add(1)
		sem <- struct{}{}

		go func(db string) {
			defer wg.Done()
			defer func() { <-sem }()

			result, err := p.BackupDatabase(ctx, db)
			mu.Lock()
			defer mu.Unlock()

			if err != nil {
				logger.Errorf("Backup failed for %s: %v", db, err)
				results = append(results, &BackupResult{
					Database: db,
					Type:     BackupTypePostgreSQL,
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
