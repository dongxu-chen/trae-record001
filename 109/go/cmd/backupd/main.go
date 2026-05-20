package main

import (
	"context"
	"flag"
	"fmt"
	"os"
	"os/signal"
	"path/filepath"
	"syscall"
	"time"

	"backup-tool/pkg/backup"
	"backup-tool/pkg/config"
	"backup-tool/pkg/logger"
	"backup-tool/pkg/metrics"
	"backup-tool/pkg/storage"
)

var (
	configFile = flag.String("config", "config.yaml", "Path to configuration file")
	version    = flag.Bool("version", false, "Show version information")
	once       = flag.Bool("once", false, "Run backup once and exit")
)

const (
	Version = "1.0.0"
)

func main() {
	flag.Parse()

	if *version {
		fmt.Printf("Backup Tool v%s\n", Version)
		return
	}

	cfg, err := config.Load(*configFile)
	if err != nil {
		fmt.Printf("Failed to load configuration: %v\n", err)
		os.Exit(1)
	}

	if err := logger.Init(&cfg.Logging); err != nil {
		fmt.Printf("Failed to initialize logger: %v\n", err)
		os.Exit(1)
	}

	logger.Infof("Backup Tool v%s starting...", Version)

	backupDir := cfg.Backup.LocalDir
	if err := os.MkdirAll(backupDir, 0755); err != nil {
		logger.Fatalf("Failed to create backup directory: %v", err)
	}

	if err := os.MkdirAll(filepath.Join(backupDir, "incremental"), 0755); err != nil {
		logger.Fatalf("Failed to create incremental directory: %v", err)
	}

	metrics := metrics.NewBackupMetrics()
	metrics.Register()
	metrics.StartServer(&cfg.Server)

	var storageInstance storage.Storage
	if cfg.Storage.Type != "" {
		storageInstance, err = storage.NewStorage(&cfg.Storage)
		if err != nil {
			logger.Fatalf("Failed to initialize storage: %v", err)
		}
	}

	pipeline := backup.NewPipeline(&cfg.Backup)

	ctx, cancel := context.WithCancel(context.Background())
	defer cancel()

	sigChan := make(chan os.Signal, 1)
	signal.Notify(sigChan, syscall.SIGINT, syscall.SIGTERM)

	go func() {
		sig := <-sigChan
		logger.Infof("Received signal %v, shutting down...", sig)
		cancel()
	}()

	if *once {
		runBackup(ctx, cfg, pipeline, storageInstance, metrics)
		logger.Info("Backup completed, exiting...")
		return
	}

	logger.Info("Starting backup pipeline...")
	pipeline.Start(ctx, storageInstance)

	ticker := time.NewTicker(1 * time.Hour)
	defer ticker.Stop()

	for {
		select {
		case <-ctx.Done():
			logger.Info("Context cancelled, stopping backup scheduler")
			return
		case <-ticker.C:
			runBackup(ctx, cfg, pipeline, storageInstance, metrics)
		}
	}
}

func runBackup(ctx context.Context, cfg *config.Config, pipeline *backup.Pipeline, storageInstance storage.Storage, metrics *metrics.BackupMetrics) {
	logger.Info("Starting backup process...")
	startTime := time.Now()

	mysqlBackup := backup.NewMySQLBackup(&cfg.Database.MySQL, cfg.Backup.LocalDir)
	mysqlResults, err := mysqlBackup.BackupAll(ctx)
	if err != nil {
		logger.Errorf("MySQL backup failed: %v", err)
	}

	if cfg.Backup.EnableIncremental {
		incrResults, err := mysqlBackup.BackupIncremental(ctx)
		if err != nil {
			logger.Errorf("MySQL incremental backup failed: %v", err)
		}
		mysqlResults = append(mysqlResults, incrResults...)
	}

	pgBackup := backup.NewPostgreSQLBackup(&cfg.Database.PostgreSQL, cfg.Backup.LocalDir)
	pgResults, err := pgBackup.BackupAll(ctx)
	if err != nil {
		logger.Errorf("PostgreSQL backup failed: %v", err)
	}

	allResults := append(mysqlResults, pgResults...)

	for _, result := range allResults {
		if result == nil {
			continue
		}

		if !result.Success {
			logger.Warnf("Backup failed for %s: %v", result.Database, result.Error)
			continue
		}

		logger.Infof("Backup completed for %s: %s, size: %d bytes, duration: %v",
			result.Database, result.FilePath, result.Size, result.Duration)

		job := &backup.PipelineJob{
			Database:   result.Database,
			Type:       result.Type,
			FilePath:   result.FilePath,
			BackupResult: result,
		}
		pipeline.Submit(job)
	}

	stats := pipeline.GetStats()
	logger.Infof("Backup process completed in %v: total=%d, success=%d, failed=%d",
		time.Since(startTime), stats.TotalJobs, stats.SuccessJobs, stats.FailedJobs)
}
