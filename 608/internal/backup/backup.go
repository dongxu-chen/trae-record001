package backup

import (
	"context"
	"encoding/json"
	"fmt"
	"log"
	"os"
	"path/filepath"
	"sort"
	"strings"
	"sync"
	"time"

	"redis-cluster-scaler/internal/cluster"
	"redis-cluster-scaler/pkg/config"

	"github.com/go-redis/redis/v8"
)

type BackupRecord struct {
	ID        string `json:"id"`
	Timestamp int64  `json:"timestamp"`
	Dir       string `json:"dir"`
	NodeCount int    `json:"node_count"`
	Status    string `json:"status"`
	Error     string `json:"error,omitempty"`
}

type BackupManager struct {
	cfg        config.BackupConfig
	clusterCfg config.ClusterConfig
	clusterMgr *cluster.Manager
	records    []BackupRecord
	recordsMu  sync.RWMutex
	stopCh     chan struct{}
}

func New(cfg config.BackupConfig, clusterCfg config.ClusterConfig, clusterMgr *cluster.Manager) *BackupManager {
	return &BackupManager{
		cfg:        cfg,
		clusterCfg: clusterCfg,
		clusterMgr: clusterMgr,
		records:    make([]BackupRecord, 0),
		stopCh:     make(chan struct{}),
	}
}

func (b *BackupManager) Start(ctx context.Context) {
	if !b.cfg.Enabled {
		log.Println("[Backup] Auto-backup disabled")
		return
	}

	interval := time.Duration(b.cfg.IntervalSec) * time.Second
	ticker := time.NewTicker(interval)
	defer ticker.Stop()

	log.Printf("[Backup] Started with interval: %v", interval)

	for {
		select {
		case <-ctx.Done():
			return
		case <-b.stopCh:
			return
		case <-ticker.C:
			_, err := b.CreateBackup(ctx)
			if err != nil {
				log.Printf("[Backup] Auto-backup failed: %v", err)
			}
		}
	}
}

func (b *BackupManager) Stop() {
	close(b.stopCh)
}

func (b *BackupManager) CreateBackup(ctx context.Context) (*BackupRecord, error) {
	backupID := fmt.Sprintf("backup-%s", time.Now().Format("20060102-150405"))
	backupDir := filepath.Join(b.cfg.Dir, backupID)

	if err := os.MkdirAll(backupDir, 0755); err != nil {
		return nil, fmt.Errorf("create backup dir: %w", err)
	}

	record := &BackupRecord{
		ID:        backupID,
		Timestamp: time.Now().Unix(),
		Dir:       backupDir,
		Status:    "in_progress",
	}

	nodes, err := b.clusterMgr.GetNodes(ctx)
	if err != nil {
		record.Status = "failed"
		record.Error = err.Error()
		b.addRecord(*record)
		return nil, fmt.Errorf("get nodes: %w", err)
	}

	record.NodeCount = len(nodes)

	clusterInfo, err := b.clusterMgr.GetClusterInfo(ctx)
	if err == nil {
		infoPath := filepath.Join(backupDir, "cluster-info.txt")
		var sb strings.Builder
		for k, v := range clusterInfo {
			sb.WriteString(fmt.Sprintf("%s: %s\n", k, v))
		}
		_ = os.WriteFile(infoPath, []byte(sb.String()), 0644)
	}

	nodesJSON, err := json.Marshal(nodes)
	if err == nil {
		nodesPath := filepath.Join(backupDir, "cluster-nodes.json")
		_ = os.WriteFile(nodesPath, nodesJSON, 0644)
	}

	for _, node := range nodes {
		if node.Role != "master" {
			continue
		}

		client := redis.NewClient(&redis.Options{
			Addr:     node.Addr,
			Password: b.clusterCfg.Password,
		})

		safeAddr := strings.ReplaceAll(node.Addr, ":", "_")
		nodeDir := filepath.Join(backupDir, safeAddr)
		_ = os.MkdirAll(nodeDir, 0755)

		infoResult, infoErr := client.Info(ctx).Result()
		if infoErr == nil {
			infoPath := filepath.Join(nodeDir, "info.txt")
			_ = os.WriteFile(infoPath, []byte(infoResult), 0644)
		}

		configResult, configErr := client.ConfigGet(ctx, "*").Result()
		if configErr == nil {
			configPath := filepath.Join(nodeDir, "config.txt")
			var sb strings.Builder
			for i := 0; i < len(configResult)-1; i += 2 {
				sb.WriteString(fmt.Sprintf("%s: %v\n", configResult[i], configResult[i+1]))
			}
			_ = os.WriteFile(configPath, []byte(sb.String()), 0644)
		}

		keysResult, keysErr := client.Info(ctx, "keyspace").Result()
		if keysErr == nil {
			keysPath := filepath.Join(nodeDir, "keyspace.txt")
			_ = os.WriteFile(keysPath, []byte(keysResult), 0644)
		}

		slotInfo := fmt.Sprintf("Slots: %v\n", node.Slots)
		slotPath := filepath.Join(nodeDir, "slots.txt")
		_ = os.WriteFile(slotPath, []byte(slotInfo), 0644)

		client.Close()
	}

	record.Status = "completed"
	b.addRecord(*record)
	b.cleanupOldBackups()

	log.Printf("[Backup] Backup completed: %s", backupID)
	return record, nil
}

func (b *BackupManager) addRecord(record BackupRecord) {
	b.recordsMu.Lock()
	defer b.recordsMu.Unlock()

	b.records = append(b.records, record)
}

func (b *BackupManager) GetRecords() []BackupRecord {
	b.recordsMu.RLock()
	defer b.recordsMu.RUnlock()

	result := make([]BackupRecord, len(b.records))
	copy(result, b.records)
	return result
}

func (b *BackupManager) cleanupOldBackups() {
	entries, err := os.ReadDir(b.cfg.Dir)
	if err != nil {
		return
	}

	var backupDirs []os.DirEntry
	for _, entry := range entries {
		if entry.IsDir() && strings.HasPrefix(entry.Name(), "backup-") {
			backupDirs = append(backupDirs, entry)
		}
	}

	if len(backupDirs) <= b.cfg.RetainCount {
		return
	}

	sort.Slice(backupDirs, func(i, j int) bool {
		return backupDirs[i].Name() < backupDirs[j].Name()
	})

	toDelete := len(backupDirs) - b.cfg.RetainCount
	for i := 0; i < toDelete; i++ {
		dir := filepath.Join(b.cfg.Dir, backupDirs[i].Name())
		_ = os.RemoveAll(dir)
		log.Printf("[Backup] Removed old backup: %s", backupDirs[i].Name())
	}
}
