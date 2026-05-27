package main

import (
	"context"
	"fmt"
	"os"
	"os/signal"
	"syscall"

	"github.com/spf13/pflag"
	"registry-sync/pkg/audit"
	"registry-sync/pkg/config"
	"registry-sync/pkg/filter"
	"registry-sync/pkg/progress"
	"registry-sync/pkg/registry"
	"registry-sync/pkg/sync"
)

var (
	configPath    string
	encryptionKey string
	jobName       string
	dryRun        bool
	verbose       bool
	encryptConfig bool
	cleanupOnly   bool
	operator      string
	showAuditLogs bool
)

func init() {
	pflag.StringVarP(&configPath, "config", "c", "config.json", "Path to configuration file")
	pflag.StringVarP(&encryptionKey, "key", "k", "", "Encryption key for sensitive data")
	pflag.StringVarP(&jobName, "job", "j", "", "Specific sync job to run")
	pflag.BoolVarP(&dryRun, "dry-run", "n", false, "Show what would be synced without actually syncing")
	pflag.BoolVarP(&verbose, "verbose", "v", false, "Enable verbose output")
	pflag.BoolVar(&encryptConfig, "encrypt", false, "Encrypt and save the configuration file")
	pflag.BoolVar(&cleanupOnly, "cleanup-only", false, "Only run cleanup (delete target images not in source)")
	pflag.StringVar(&operator, "operator", "system", "Operator name for audit logs")
	pflag.BoolVar(&showAuditLogs, "show-audit-logs", false, "Show recent audit logs and exit")
}

func main() {
	pflag.Parse()

	if showAuditLogs {
		if err := showAuditLogsHistory(); err != nil {
			fmt.Printf("Failed to show audit logs: %v\n", err)
			os.Exit(1)
		}
		return
	}

	if encryptConfig {
		if err := encryptConfiguration(); err != nil {
			fmt.Printf("Failed to encrypt config: %v\n", err)
			os.Exit(1)
		}
		fmt.Println("Configuration encrypted successfully")
		return
	}

	if err := runSync(); err != nil {
		fmt.Printf("Sync failed: %v\n", err)
		os.Exit(1)
	}
}

func showAuditLogsHistory() error {
	cfg, err := config.LoadConfig(configPath, encryptionKey)
	if err != nil {
		return fmt.Errorf("failed to load config: %w", err)
	}

	for _, job := range cfg.SyncJobs {
		if job.Audit.Enabled {
			auditLogger, err := audit.NewAuditLogger(audit.AuditLogConfig{
				LogPath:   job.Audit.LogPath,
				Operator:  operator,
				BatchSize: job.Audit.BatchSize,
			})
			if err != nil {
				fmt.Printf("Failed to open audit log for job %s->%s: %v\n", 
					job.SourceRegistry, job.TargetRegistry, err)
				continue
			}
			defer auditLogger.Close()

			logs, err := auditLogger.ReadLogs(100)
			if err != nil {
				fmt.Printf("Failed to read audit logs: %v\n", err)
				continue
			}

			fmt.Printf("\n=== Audit Logs for job: %s -> %s ===\n", 
				job.SourceRegistry, job.TargetRegistry)
			for _, log := range logs {
				fmt.Printf("[%s] %s | %s | %s | %s:%s\n",
					log.Timestamp.Format("2006-01-02 15:04:05"),
					log.Operator,
					log.Action,
					log.Status,
					log.SourceRepo,
					log.SourceTag)
			}

			summary := auditLogger.GetSummary()
			fmt.Printf("\nSummary: %v\n", summary)
		}
	}

	return nil
}

func encryptConfiguration() error {
	if encryptionKey == "" {
		return fmt.Errorf("encryption key is required")
	}

	cfg, err := config.LoadConfig(configPath, "")
	if err != nil {
		return fmt.Errorf("failed to load config: %w", err)
	}

	return config.SaveConfig(configPath, cfg, encryptionKey)
}

func runSync() error {
	cfg, err := config.LoadConfig(configPath, encryptionKey)
	if err != nil {
		return fmt.Errorf("failed to load config: %w", err)
	}

	jobsToRun := cfg.SyncJobs
	if jobName != "" {
		var found bool
		for _, job := range cfg.SyncJobs {
			if job.SourceRegistry == jobName || job.TargetRegistry == jobName {
				jobsToRun = []config.SyncConfig{job}
				found = true
				break
			}
		}
		if !found {
			return fmt.Errorf("job '%s' not found in configuration", jobName)
		}
	}

	ctx, cancel := context.WithCancel(context.Background())
	defer cancel()

	sigChan := make(chan os.Signal, 1)
	signal.Notify(sigChan, syscall.SIGINT, syscall.SIGTERM)
	go func() {
		<-sigChan
		fmt.Println("\nReceived shutdown signal, stopping...")
		cancel()
	}()

	for i, job := range jobsToRun {
		if dryRun {
			job.DryRun = true
		}

		if operator != "system" {
			job.Audit.Operator = operator
		}

		if cleanupOnly {
			job.Cleanup.Enabled = true
			job.Cleanup.DryRun = dryRun
		}

		fmt.Printf("Running sync job %d: %s -> %s\n", i+1, job.SourceRegistry, job.TargetRegistry)

		if err := runJob(ctx, cfg, job); err != nil {
			fmt.Printf("Job failed: %v\n", err)
			continue
		}
		fmt.Println()
	}

	return nil
}

func runJob(ctx context.Context, cfg *config.Config, job config.SyncConfig) error {
	sourceRegConfig, ok := cfg.GetRegistry(job.SourceRegistry)
	if !ok {
		return fmt.Errorf("source registry '%s' not found", job.SourceRegistry)
	}

	targetRegConfig, ok := cfg.GetRegistry(job.TargetRegistry)
	if !ok {
		return fmt.Errorf("target registry '%s' not found", job.TargetRegistry)
	}

	sourceClient, err := registry.NewClient(sourceRegConfig)
	if err != nil {
		return fmt.Errorf("failed to create source client: %w", err)
	}

	targetClient, err := registry.NewClient(targetRegConfig)
	if err != nil {
		return fmt.Errorf("failed to create target client: %w", err)
	}

	imgFilter, err := filter.NewFilter(job.Filter)
	if err != nil {
		return fmt.Errorf("failed to create filter: %w", err)
	}

	prog := progress.NewSyncProgress()

	syncer, err := sync.NewImageSyncer(sourceClient, targetClient, job, imgFilter, prog)
	if err != nil {
		return fmt.Errorf("failed to create syncer: %w", err)
	}
	defer syncer.Close()

	if verbose {
		go printProgress(ctx, prog)
	}

	if cleanupOnly {
		return runCleanupOnly(ctx, syncer, cfg, job)
	}

	if err := syncer.SyncAll(ctx); err != nil {
		fmt.Printf("Sync error: %v\n", err)
	}

	stats := syncer.GetStatistics()
	fmt.Println(stats.String())

	if job.Audit.Enabled {
		fmt.Printf("Audit log saved to: %s\n", job.Audit.LogPath)
	}

	return nil
}

func runCleanupOnly(ctx context.Context, syncer *sync.ImageSyncer, cfg *config.Config, job config.SyncConfig) error {
	fmt.Println("Running cleanup only mode...")
	
	sourceRepos, err := cfg.GetRegistry(job.SourceRegistry)
	if err != nil {
		return fmt.Errorf("failed to get source registry: %w", err)
	}
	
	_ = sourceRepos
	return nil
}

func printProgress(ctx context.Context, prog *progress.SyncProgress) {
	for {
		select {
		case <-ctx.Done():
			return
		default:
			total, completed, failed, skipped := prog.GetStats()
			_, transferred := prog.GetBytes()
			elapsed := prog.ElapsedTime()
			speed := float64(transferred) / elapsed.Seconds()

			fmt.Printf("\rProgress: %d/%d images | %d failed | %d skipped | %s transferred | %s/s",
				completed+failed+skipped, total, failed, skipped,
				formatBytes(transferred), formatBytes(int64(speed)))
		}
	}
}

func formatBytes(bytes int64) string {
	const unit = 1024
	if bytes < unit {
		return fmt.Sprintf("%d B", bytes)
	}
	div, exp := int64(unit), 0
	for n := bytes / unit; n >= unit; n /= unit {
		div *= unit
		exp++
	}
	return fmt.Sprintf("%.2f %cB", float64(bytes)/float64(div), "KMGTPE"[exp])
}
