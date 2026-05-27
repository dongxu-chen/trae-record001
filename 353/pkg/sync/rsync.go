package sync

import (
	"context"
	"fmt"
	"io"
	"os"
	"os/exec"
	"strings"
	"sync"
	"time"

	"github.com/cloud-migration-tool/config"
)

type RsyncResult struct {
	Success      bool
	FilesTransferred int
	TotalSize    int64
	Error        error
	ElapsedTime  time.Duration
	StartTime    time.Time
	EndTime      time.Time
}

type RsyncManager struct {
	config     config.RsyncConfig
	results    []RsyncResult
	mu         sync.Mutex
	isRunning  bool
	stopChan   chan struct{}
}

func NewRsyncManager(cfg config.RsyncConfig) *RsyncManager {
	return &RsyncManager{
		config:   cfg,
		results:  make([]RsyncResult, 0),
		stopChan: make(chan struct{}),
	}
}

func (rm *RsyncManager) buildRsyncArgs() []string {
	args := []string{
		"-avz",
		"--delete",
		"--progress",
	}

	if rm.config.BandwidthLimit != "" {
		args = append(args, fmt.Sprintf("--bwlimit=%s", rm.config.BandwidthLimit))
	}

	for _, pattern := range rm.config.ExcludePatterns {
		args = append(args, fmt.Sprintf("--exclude=%s", pattern))
	}

	if rm.config.SSHKeyPath != "" {
		args = append(args, fmt.Sprintf("-e ssh -i %s -p %d", rm.config.SSHKeyPath, rm.config.SSHPort))
	} else {
		args = append(args, fmt.Sprintf("-e ssh -p %d", rm.config.SSHPort))
	}

	args = append(args, rm.config.SourcePath)

	if rm.config.SSHUser != "" && rm.config.SSHHost != "" {
		args = append(args, fmt.Sprintf("%s@%s:%s", rm.config.SSHUser, rm.config.SSHHost, rm.config.DestPath))
	} else {
		args = append(args, rm.config.DestPath)
	}

	return args
}

func (rm *RsyncManager) SyncOnce(ctx context.Context) (*RsyncResult, error) {
	startTime := time.Now()
	result := &RsyncResult{
		StartTime: startTime,
		Success:   false,
	}

	args := rm.buildRsyncArgs()
	cmd := exec.CommandContext(ctx, "rsync", args...)

	var outputBuf strings.Builder
	cmd.Stdout = &outputBuf
	cmd.Stderr = &outputBuf

	err := cmd.Run()
	result.EndTime = time.Now()
	result.ElapsedTime = result.EndTime.Sub(result.StartTime)

	if err != nil {
		result.Error = fmt.Errorf("rsync failed: %w - %s", err, outputBuf.String())
		rm.addResult(*result)
		return result, result.Error
	}

	result.Success = true
	result.FilesTransferred = parseFilesTransferred(outputBuf.String())
	result.TotalSize = parseTotalSize(outputBuf.String())

	rm.addResult(*result)
	return result, nil
}

func (rm *RsyncManager) StartContinuousSync(ctx context.Context) error {
	rm.mu.Lock()
	if rm.isRunning {
		rm.mu.Unlock()
		return fmt.Errorf("continuous sync already running")
	}
	rm.isRunning = true
	rm.stopChan = make(chan struct{})
	rm.mu.Unlock()

	defer func() {
		rm.mu.Lock()
		rm.isRunning = false
		rm.mu.Unlock()
	}()

	syncInterval := rm.config.SyncInterval
	if syncInterval <= 0 {
		syncInterval = 300
	}

	ticker := time.NewTicker(time.Duration(syncInterval) * time.Second)
	defer ticker.Stop()

	for {
		select {
		case <-ctx.Done():
			return ctx.Err()
		case <-rm.stopChan:
			return nil
		case <-ticker.C:
			_, _ = rm.SyncOnce(ctx)
		}
	}
}

func (rm *RsyncManager) StopContinuousSync() {
	rm.mu.Lock()
	defer rm.mu.Unlock()
	if rm.isRunning {
		close(rm.stopChan)
		rm.isRunning = false
	}
}

func (rm *RsyncManager) IsRunning() bool {
	rm.mu.Lock()
	defer rm.mu.Unlock()
	return rm.isRunning
}

func (rm *RsyncManager) addResult(result RsyncResult) {
	rm.mu.Lock()
	defer rm.mu.Unlock()
	rm.results = append(rm.results, result)
}

func (rm *RsyncManager) GetResults() []RsyncResult {
	rm.mu.Lock()
	defer rm.mu.Unlock()
	results := make([]RsyncResult, len(rm.results))
	copy(results, rm.results)
	return results
}

func (rm *RsyncManager) GetLastResult() *RsyncResult {
	rm.mu.Lock()
	defer rm.mu.Unlock()
	if len(rm.results) == 0 {
		return nil
	}
	return &rm.results[len(rm.results)-1]
}

func (rm *RsyncManager) GetStatistics() map[string]interface{} {
	rm.mu.Lock()
	defer rm.mu.Unlock()

	stats := make(map[string]interface{})
	stats["total_runs"] = len(rm.results)

	successCount := 0
	var totalElapsed time.Duration
	var totalFiles int
	var totalBytes int64

	for _, r := range rm.results {
		if r.Success {
			successCount++
			totalElapsed += r.ElapsedTime
			totalFiles += r.FilesTransferred
			totalBytes += r.TotalSize
		}
	}

	stats["success_count"] = successCount
	stats["failure_count"] = len(rm.results) - successCount
	stats["success_rate"] = 0.0
	if len(rm.results) > 0 {
		stats["success_rate"] = float64(successCount) / float64(len(rm.results))
	}
	stats["total_elapsed"] = totalElapsed.String()
	stats["total_files_transferred"] = totalFiles
	stats["total_bytes_transferred"] = totalBytes
	stats["is_running"] = rm.isRunning

	return stats
}

func parseFilesTransferred(output string) int {
	count := 0
	lines := strings.Split(output, "\n")
	for _, line := range lines {
		if strings.Contains(line, "100%") && !strings.Contains(line, "speedup") {
			count++
		}
	}
	return count
}

func parseTotalSize(output string) int64 {
	return 0
}

func CheckRsyncAvailable() bool {
	_, err := exec.LookPath("rsync")
	return err == nil
}

func (rm *RsyncManager) DryRun(ctx context.Context) (string, error) {
	args := rm.buildRsyncArgs()
	args = append(args, "--dry-run")

	cmd := exec.CommandContext(ctx, "rsync", args...)
	output, err := cmd.CombinedOutput()
	return string(output), err
}

func (rm *RsyncManager) SaveLogToFile(filePath string) error {
	rm.mu.Lock()
	defer rm.mu.Unlock()

	f, err := os.Create(filePath)
	if err != nil {
		return err
	}
	defer f.Close()

	for i, result := range rm.results {
		status := "SUCCESS"
		if !result.Success {
			status = "FAILED"
		}
		fmt.Fprintf(f, "=== Sync #%d [%s] ===\n", i+1, status)
		fmt.Fprintf(f, "Start Time: %s\n", result.StartTime.Format(time.RFC3339))
		fmt.Fprintf(f, "End Time: %s\n", result.EndTime.Format(time.RFC3339))
		fmt.Fprintf(f, "Elapsed: %s\n", result.ElapsedTime)
		fmt.Fprintf(f, "Files Transferred: %d\n", result.FilesTransferred)
		fmt.Fprintf(f, "Total Size: %d bytes\n", result.TotalSize)
		if result.Error != nil {
			fmt.Fprintf(f, "Error: %v\n", result.Error)
		}
		fmt.Fprintln(f)
	}

	return nil
}
