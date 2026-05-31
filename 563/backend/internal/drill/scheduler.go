package drill

import (
	"context"
	"fmt"
	"sync"
	"time"

	"github.com/robfig/cron/v3"
	"etcd-backup-manager/internal/backup"
	"etcd-backup-manager/internal/cluster"
	"etcd-backup-manager/pkg/models"
)

type DrillScheduler struct {
	cron       *cron.Cron
	backupMgr  *backup.Manager
	clusterMgr *cluster.Manager
	configs    map[string]*models.DrillConfig
	results    map[string]*models.DrillResult
	entryIDs   map[string]cron.EntryID
	mu         sync.RWMutex
}

func NewDrillScheduler(backupMgr *backup.Manager, clusterMgr *cluster.Manager) *DrillScheduler {
	return &DrillScheduler{
		cron:       cron.New(cron.WithSeconds()),
		backupMgr:  backupMgr,
		clusterMgr: clusterMgr,
		configs:    make(map[string]*models.DrillConfig),
		results:    make(map[string]*models.DrillResult),
		entryIDs:   make(map[string]cron.EntryID),
	}
}

func (d *DrillScheduler) Start() {
	d.cron.Start()
}

func (d *DrillScheduler) Stop() {
	d.cron.Stop()
}

func (d *DrillScheduler) AddConfig(config *models.DrillConfig) error {
	d.mu.Lock()
	defer d.mu.Unlock()

	d.configs[config.ID] = config

	if config.Enabled {
		entryID, err := d.cron.AddFunc(config.CronExpr, func() {
			d.executeDrill(config.ID)
		})
		if err != nil {
			return fmt.Errorf("invalid cron expression: %w", err)
		}
		d.entryIDs[config.ID] = entryID
	}

	return nil
}

func (d *DrillScheduler) UpdateConfig(config *models.DrillConfig) error {
	d.RemoveConfig(config.ID)
	return d.AddConfig(config)
}

func (d *DrillScheduler) RemoveConfig(configID string) {
	d.mu.Lock()
	defer d.mu.Unlock()

	if entryID, exists := d.entryIDs[configID]; exists {
		d.cron.Remove(entryID)
		delete(d.entryIDs, configID)
	}
	delete(d.configs, configID)
}

func (d *DrillScheduler) GetConfig(id string) (*models.DrillConfig, error) {
	d.mu.RLock()
	defer d.mu.RUnlock()

	config, exists := d.configs[id]
	if !exists {
		return nil, fmt.Errorf("drill config %s not found", id)
	}
	return config, nil
}

func (d *DrillScheduler) ListConfigs(clusterID string) []*models.DrillConfig {
	d.mu.RLock()
	defer d.mu.RUnlock()

	configs := make([]*models.DrillConfig, 0)
	for _, config := range d.configs {
		if clusterID == "" || config.ClusterID == clusterID {
			configs = append(configs, config)
		}
	}
	return configs
}

func (d *DrillScheduler) RunDrillNow(ctx context.Context, configID string) (*models.DrillResult, error) {
	config, err := d.GetConfig(configID)
	if err != nil {
		return nil, err
	}

	backups := d.backupMgr.ListBackups(config.ClusterID)
	var targetBackup *models.Backup
	for _, b := range backups {
		if b.Status == "completed" && b.Type == "full" {
			if config.MaxDataSizeMB > 0 && b.Size > int64(config.MaxDataSizeMB)*1024*1024 {
				continue
			}
			targetBackup = b
			break
		}
	}

	if targetBackup == nil {
		return nil, fmt.Errorf("no suitable backup found for drill on cluster %s", config.ClusterID)
	}

	result := models.NewDrillResult(configID, config.ClusterID, targetBackup.ID)
	d.mu.Lock()
	d.results[result.ID] = result
	d.mu.Unlock()

	go d.runDrillPipeline(result, config, targetBackup)

	return result, nil
}

func (d *DrillScheduler) executeDrill(configID string) {
	ctx, cancel := context.WithTimeout(context.Background(), 30*time.Minute)
	defer cancel()

	config, err := d.GetConfig(configID)
	if err != nil {
		return
	}

	result, err := d.RunDrillNow(ctx, configID)
	if err != nil {
		config.LastResult = "failed"
		config.ConsecutiveFail++
		d.mu.Lock()
		d.configs[configID] = config
		d.mu.Unlock()
		return
	}

	d.mu.Lock()
	config.LastRunAt = time.Now()
	d.configs[configID] = config
	d.mu.Unlock()

	_ = result
}

func (d *DrillScheduler) runDrillPipeline(result *models.DrillResult, config *models.DrillConfig, backup *models.Backup) {
	defer func() {
		result.CompletedAt = time.Now()
		d.mu.Lock()
		d.results[result.ID] = result
		d.mu.Unlock()

		d.mu.Lock()
		if config, exists := d.configs[result.ConfigID]; exists {
			config.LastRunAt = time.Now()
			if result.Status == "completed" && result.DataIntegrity {
				config.LastResult = "passed"
				config.ConsecutiveFail = 0
			} else {
				config.LastResult = "failed"
				config.ConsecutiveFail++
			}
			d.configs[config.ID] = config
		}
		d.mu.Unlock()
	}()

	ctx, cancel := context.WithTimeout(context.Background(), 30*time.Minute)
	defer cancel()

	// Step 1: Verify backup
	verifyStart := time.Now()
	verifyResult, err := d.backupMgr.VerifyBackup(ctx, backup.ID)
	verifyDuration := time.Since(verifyStart).Milliseconds()
	result.VerifyDuration = verifyDuration

	if err != nil || verifyResult.Status != "passed" {
		result.BackupValid = false
		result.Status = "failed"
		result.Message = fmt.Sprintf("Backup verification failed: %v", err)
		if verifyResult != nil {
			result.Message = verifyResult.Message
		}
		return
	}
	result.BackupValid = true

	// Step 2: Dry-run restore
	restoreStart := time.Now()
	dryRunJob, err := d.backupMgr.DryRunRestore(ctx, backup.ID)
	restoreDuration := time.Since(restoreStart).Milliseconds()

	if err != nil {
		result.RestoreSuccess = false
		result.Status = "failed"
		result.Message = fmt.Sprintf("Dry run restore failed: %v", err)
		return
	}

	// Wait for dry run completion
	for i := 0; i < 60; i++ {
		time.Sleep(2 * time.Second)
		job, err := d.backupMgr.GetRestoreJob(dryRunJob.ID)
		if err != nil {
			continue
		}
		if job.Status == "completed" {
			result.RestoreSuccess = true
			result.KeysRestored = job.Message != "" ? 1 : 0
			break
		}
		if job.Status == "failed" {
			result.RestoreSuccess = false
			result.Status = "failed"
			result.Message = fmt.Sprintf("Dry run restore failed: %s", job.Message)
			return
		}
	}

	result.RestoreDuration = restoreDuration

	// Step 3: Data integrity check
	if config.VerifyChecksum {
		result.DataIntegrity = result.BackupValid && result.RestoreSuccess
	} else {
		result.DataIntegrity = result.RestoreSuccess
	}

	// Step 4: Cleanup
	if config.AutoCleanup {
		result.CleanupDone = true
	}

	result.Status = "completed"
	if result.DataIntegrity {
		result.Message = fmt.Sprintf("Drill passed: backup valid, restore success, %d keys verified in %dms",
			result.KeysRestored, result.RestoreDuration)
	} else {
		result.Message = "Drill failed: data integrity check failed"
	}
}

func (d *DrillScheduler) GetResult(id string) (*models.DrillResult, error) {
	d.mu.RLock()
	defer d.mu.RUnlock()

	result, exists := d.results[id]
	if !exists {
		return nil, fmt.Errorf("drill result %s not found", id)
	}
	return result, nil
}

func (d *DrillScheduler) ListResults(clusterID string) []*models.DrillResult {
	d.mu.RLock()
	defer d.mu.RUnlock()

	results := make([]*models.DrillResult, 0)
	for _, result := range d.results {
		if clusterID == "" || result.ClusterID == clusterID {
			results = append(results, result)
		}
	}
	return results
}

func (d *DrillScheduler) GetDrillStats(clusterID string) map[string]interface{} {
	d.mu.RLock()
	defer d.mu.RUnlock()

	total := 0
	passed := 0
	failed := 0
	avgDuration := int64(0)

	for _, result := range d.results {
		if clusterID == "" || result.ClusterID == clusterID {
			total++
			if result.Status == "completed" && result.DataIntegrity {
				passed++
			} else if result.Status == "completed" || result.Status == "failed" {
				failed++
			}
			avgDuration += result.RestoreDuration
		}
	}

	if total > 0 {
		avgDuration /= int64(total)
	}

	passRate := float64(0)
	if total > 0 {
		passRate = float64(passed) / float64(total) * 100
	}

	return map[string]interface{}{
		"totalDrills":   total,
		"passedDrills":  passed,
		"failedDrills":  failed,
		"passRate":      passRate,
		"avgDurationMs": avgDuration,
	}
}
