package backup

import (
	"context"
	"crypto/sha256"
	"encoding/hex"
	"encoding/json"
	"fmt"
	"os"
	"path/filepath"
	"sort"
	"sync"
	"time"

	clientv3 "go.etcd.io/etcd/client/v3"
	"etcd-backup-manager/internal/cluster"
	"etcd-backup-manager/internal/encryption"
	"etcd-backup-manager/internal/storage"
	"etcd-backup-manager/pkg/models"
)

type Encryptor interface {
	Encrypt(data []byte) ([]byte, error)
	Decrypt(data []byte) ([]byte, error)
	IsEnabled() bool
}

type Manager struct {
	clusterMgr  *cluster.Manager
	storage     storage.Storage
	encryptor   Encryptor
	backups     map[string]*models.Backup
	restoreJobs map[string]*models.RestoreJob
	mu          sync.RWMutex
	tempDir     string
	walDir      string
}

type BackupSnapshot struct {
	Meta     models.SnapshotMeta `json:"meta"`
	Kvs      map[string][]byte   `json:"kvs"`
	Checksum string              `json:"checksum"`
}

type WALIncrementalBackup struct {
	Meta         models.SnapshotMeta `json:"meta"`
	ParentID     string              `json:"parentId"`
	Records      []*WALRecord        `json:"records"`
	CompactedKvs map[string][]byte   `json:"compactedKvs"`
	Checksum     string              `json:"checksum"`
}

func NewManager(clusterMgr *cluster.Manager, storage storage.Storage, encryptor Encryptor, tempDir string) (*Manager, error) {
	if err := os.MkdirAll(tempDir, 0755); err != nil {
		return nil, fmt.Errorf("failed to create temp directory: %w", err)
	}

	return &Manager{
		clusterMgr:  clusterMgr,
		storage:     storage,
		encryptor:   encryptor,
		backups:     make(map[string]*models.Backup),
		restoreJobs: make(map[string]*models.RestoreJob),
		tempDir:     tempDir,
		walDir:      filepath.Join(tempDir, "wal"),
	}, nil
}

func (m *Manager) CreateFullBackup(ctx context.Context, clusterID string) (*models.Backup, error) {
	cluster, err := m.clusterMgr.GetCluster(clusterID)
	if err != nil {
		return nil, err
	}

	client, err := m.clusterMgr.GetClient(clusterID)
	if err != nil {
		return nil, err
	}

	backup := models.NewBackup(clusterID, cluster.Name, "full")
	backup.Status = "running"
	backup.SnapshotMeta.SourceCluster = cluster.Name
	m.addBackup(backup)

	go m.executeFullBackup(ctx, backup, client, clusterID)
	return backup, nil
}

func (m *Manager) executeFullBackup(ctx context.Context, backup *models.Backup, client *clientv3.Client, clusterID string) {
	defer func() {
		backup.CompletedAt = time.Now()
		backup.SnapshotMeta.EndTime = time.Now()
		m.updateBackup(backup)
	}()

	snapshot, err := m.takeSnapshot(ctx, client)
	if err != nil {
		backup.Status = "failed"
		backup.Message = fmt.Sprintf("Failed to take snapshot: %v", err)
		return
	}

	backup.Revision = snapshot.Meta.Revision
	backup.KeysCount = snapshot.Meta.KeysCount
	backup.Checksum = snapshot.Checksum
	backup.SnapshotMeta = snapshot.Meta

	data, err := json.Marshal(snapshot)
	if err != nil {
		backup.Status = "failed"
		backup.Message = fmt.Sprintf("Failed to marshal snapshot: %v", err)
		return
	}

	if m.encryptor.IsEnabled() {
		encrypted, err := m.encryptor.Encrypt(data)
		if err != nil {
			backup.Status = "failed"
			backup.Message = fmt.Sprintf("Failed to encrypt: %v", err)
			return
		}
		data = encrypted
		backup.Encrypted = true

		if kmsEnc, ok := m.encryptor.(*encryption.KMSEncryptor); ok {
			backup.KMSKeyID = kmsEnc.GetCurrentKeyID()
		}
	}

	storageKey := fmt.Sprintf("backups/%s/%s/full/%s.db", backup.ClusterName, backup.ClusterID, backup.ID)
	if err := m.storage.Save(ctx, storageKey, data); err != nil {
		backup.Status = "failed"
		backup.Message = fmt.Sprintf("Failed to save to storage: %v", err)
		return
	}

	size, err := m.storage.GetSize(ctx, storageKey)
	if err == nil {
		backup.Size = size
	}

	backup.Path = storageKey
	backup.Status = "completed"

	metaData, _ := json.Marshal(backup.SnapshotMeta)
	metaKey := fmt.Sprintf("backups/%s/%s/full/%s.meta", backup.ClusterName, backup.ClusterID, backup.ID)
	m.storage.Save(ctx, metaKey, metaData)
	backup.MetaPath = metaKey
}

func (m *Manager) CreateIncrementalBackup(ctx context.Context, clusterID string, parentBackupID string) (*models.Backup, error) {
	cluster, err := m.clusterMgr.GetCluster(clusterID)
	if err != nil {
		return nil, err
	}

	client, err := m.clusterMgr.GetClient(clusterID)
	if err != nil {
		return nil, err
	}

	var parentBackup *models.Backup
	if parentBackupID != "" {
		parentBackup, err = m.GetBackup(parentBackupID)
		if err != nil {
			return nil, fmt.Errorf("parent backup not found: %w", err)
		}
	} else {
		parentBackup = m.getLatestBackup(clusterID, "full")
		if parentBackup == nil {
			return m.CreateFullBackup(ctx, clusterID)
		}
	}

	backup := models.NewBackup(clusterID, cluster.Name, "incremental")
	backup.ParentID = parentBackup.ID
	backup.SnapshotMeta.SourceCluster = cluster.Name
	backup.SnapshotMeta.WALStartIndex = parentBackup.SnapshotMeta.WALEndIndex
	backup.Status = "running"
	m.addBackup(backup)

	go m.executeWALIncrementalBackup(ctx, backup, parentBackup, client, clusterID)
	return backup, nil
}

func (m *Manager) executeWALIncrementalBackup(ctx context.Context, backup, parentBackup *models.Backup, client *clientv3.Client, clusterID string) {
	defer func() {
		backup.CompletedAt = time.Now()
		backup.SnapshotMeta.EndTime = time.Now()
		m.updateBackup(backup)
	}()

	walRecords, err := m.collectWALRecords(ctx, client, parentBackup.SnapshotMeta.WALEndIndex)
	if err != nil {
		backup.Status = "failed"
		backup.Message = fmt.Sprintf("Failed to collect WAL records: %v", err)
		return
	}

	var walEndIndex int64
	if len(walRecords) > 0 {
		walEndIndex = walRecords[len(walRecords)-1].Index
	} else {
		walEndIndex = parentBackup.SnapshotMeta.WALEndIndex
	}

	currentStatus, err := m.clusterMgr.GetClusterStatus(ctx, clusterID)
	etcdVersion := ""
	if err == nil {
		etcdVersion = currentStatus.Version
	}

	currentResp, err := client.Get(ctx, "", clientv3.WithPrefix(), clientv3.WithCountOnly())
	if err != nil {
		backup.Status = "failed"
		backup.Message = fmt.Sprintf("Failed to get current revision: %v", err)
		return
	}

	compactedKvs, err := m.buildCompactedKvs(ctx, client, walRecords)
	if err != nil {
		backup.Status = "failed"
		backup.Message = fmt.Sprintf("Failed to build compacted kvs: %v", err)
		return
	}

	backup.SnapshotMeta.WALEndIndex = walEndIndex
	backup.SnapshotMeta.Revision = currentResp.Header.Revision
	backup.SnapshotMeta.EtcdVersion = etcdVersion

	incrBackup := &WALIncrementalBackup{
		Meta:         backup.SnapshotMeta,
		ParentID:     parentBackup.ID,
		Records:      walRecords,
		CompactedKvs: compactedKvs,
	}

	hasher := sha256.New()
	for _, rec := range walRecords {
		hasher.Write([]byte{rec.Type})
		hasher.Write(rec.Data)
	}
	incrBackup.Checksum = hex.EncodeToString(hasher.Sum(nil))

	backup.KeysCount = int64(len(compactedKvs))
	backup.DiffSize = int64(len(walRecords))
	backup.Checksum = incrBackup.Checksum

	data, err := json.Marshal(incrBackup)
	if err != nil {
		backup.Status = "failed"
		backup.Message = fmt.Sprintf("Failed to marshal WAL incremental backup: %v", err)
		return
	}

	if m.encryptor.IsEnabled() {
		encrypted, err := m.encryptor.Encrypt(data)
		if err != nil {
			backup.Status = "failed"
			backup.Message = fmt.Sprintf("Failed to encrypt: %v", err)
			return
		}
		data = encrypted
		backup.Encrypted = true

		if kmsEnc, ok := m.encryptor.(*encryption.KMSEncryptor); ok {
			backup.KMSKeyID = kmsEnc.GetCurrentKeyID()
		}
	}

	storageKey := fmt.Sprintf("backups/%s/%s/inc/%s.wal", backup.ClusterName, backup.ClusterID, backup.ID)
	if err := m.storage.Save(ctx, storageKey, data); err != nil {
		backup.Status = "failed"
		backup.Message = fmt.Sprintf("Failed to save to storage: %v", err)
		return
	}

	size, err := m.storage.GetSize(ctx, storageKey)
	if err == nil {
		backup.Size = size
	}

	backup.Path = storageKey
	backup.Status = "completed"

	metaData, _ := json.Marshal(backup.SnapshotMeta)
	metaKey := fmt.Sprintf("backups/%s/%s/inc/%s.meta", backup.ClusterName, backup.ClusterID, backup.ID)
	m.storage.Save(ctx, metaKey, metaData)
	backup.MetaPath = metaKey
}

func (m *Manager) collectWALRecords(ctx context.Context, client *clientv3.Client, sinceIndex int64) ([]*WALRecord, error) {
	var records []*WALRecord

	watchChan := client.Watch(ctx, "", clientv3.WithPrefix(), clientv3.WithRev(uint64(sinceIndex+1)))

	select {
	case watchResp := <-watchChan:
		for _, event := range watchResp.Events {
			var recType byte
			switch event.Type {
			case clientv3.EventTypePut:
				recType = RecordTypeState
			case clientv3.EventTypeDelete:
				recType = RecordTypeCommit
			}

			record := &WALRecord{
				Type:      recType,
				Index:     event.Kv.ModRevision,
				Term:      event.Kv.ModRevision,
				Data:      event.Kv.Value,
				Timestamp: time.Now(),
			}

			if event.PrevKv != nil {
				keyData := append([]byte(event.Kv.Key), 0x00)
				keyData = append(keyData, event.Kv.Value...)
				record.Data = keyData
			}

			records = append(records, record)
		}
	case <-ctx.Done():
		if len(records) > 0 {
			return records, nil
		}
		return nil, ctx.Err()
	}

	return records, nil
}

func (m *Manager) buildCompactedKvs(ctx context.Context, client *clientv3.Client, records []*WALRecord) (map[string][]byte, error) {
	compacted := make(map[string][]byte)

	for _, rec := range records {
		if rec.Type == RecordTypeState && len(rec.Data) > 0 {
			parts := splitKeyAndValue(rec.Data)
			if len(parts) == 2 {
				compacted[string(parts[0])] = parts[1]
			}
		}
	}

	return compacted, nil
}

func splitKeyAndValue(data []byte) [][]byte {
	for i, b := range data {
		if b == 0x00 {
			return [][]byte{data[:i], data[i+1:]}
		}
	}
	return [][]byte{data}
}

func (m *Manager) takeSnapshot(ctx context.Context, client *clientv3.Client) (*BackupSnapshot, error) {
	resp, err := client.Get(ctx, "", clientv3.WithPrefix())
	if err != nil {
		return nil, err
	}

	kvs := make(map[string][]byte)
	hasher := sha256.New()

	for _, kv := range resp.Kvs {
		kvs[string(kv.Key)] = kv.Value
		hasher.Write(kv.Key)
		hasher.Write(kv.Value)
	}

	statusResp, err := client.Status(ctx, client.Endpoints()[0])
	etcdVersion := ""
	if err == nil {
		etcdVersion = statusResp.Version
	}

	snapshot := &BackupSnapshot{
		Meta: models.SnapshotMeta{
			Version:       "2.0.0",
			FormatVersion: "v2wal",
			StartTime:     time.Now(),
			EndTime:       time.Now(),
			WALStartIndex: 0,
			WALEndIndex:   resp.Header.Revision,
			Revision:      resp.Header.Revision,
			KeysCount:     int64(len(kvs)),
			Checksum:      hex.EncodeToString(hasher.Sum(nil)),
			EtcdVersion:   etcdVersion,
		},
		Kvs:      kvs,
		Checksum: hex.EncodeToString(hasher.Sum(nil)),
	}

	return snapshot, nil
}

func (m *Manager) loadSnapshot(ctx context.Context, backup *models.Backup) (*BackupSnapshot, error) {
	data, err := m.storage.Get(ctx, backup.Path)
	if err != nil {
		return nil, err
	}

	if backup.Encrypted {
		decrypted, err := m.encryptor.Decrypt(data)
		if err != nil {
			return nil, err
		}
		data = decrypted
	}

	var snapshot BackupSnapshot
	if err := json.Unmarshal(data, &snapshot); err != nil {
		return nil, err
	}

	return &snapshot, nil
}

func (m *Manager) loadWALIncremental(ctx context.Context, backup *models.Backup) (*WALIncrementalBackup, error) {
	data, err := m.storage.Get(ctx, backup.Path)
	if err != nil {
		return nil, err
	}

	if backup.Encrypted {
		decrypted, err := m.encryptor.Decrypt(data)
		if err != nil {
			return nil, err
		}
		data = decrypted
	}

	var incrBackup WALIncrementalBackup
	if err := json.Unmarshal(data, &incrBackup); err != nil {
		return nil, err
	}

	return &incrBackup, nil
}

func (m *Manager) RestoreBackup(ctx context.Context, backupID, targetClusterID string, pointInTime *time.Time) (*models.RestoreJob, error) {
	backup, err := m.GetBackup(backupID)
	if err != nil {
		return nil, err
	}

	if _, err := m.clusterMgr.GetCluster(targetClusterID); err != nil {
		return nil, err
	}

	job := models.NewRestoreJob(backupID, targetClusterID, "restore")
	if pointInTime != nil {
		job.PointInTime = *pointInTime
	}
	m.addRestoreJob(job)

	go m.executeRestore(ctx, job, backup, targetClusterID)
	return job, nil
}

func (m *Manager) RestoreByWALIndex(ctx context.Context, backupID, targetClusterID string, walIndex int64) (*models.RestoreJob, error) {
	backup, err := m.GetBackup(backupID)
	if err != nil {
		return nil, err
	}

	if _, err := m.clusterMgr.GetCluster(targetClusterID); err != nil {
		return nil, err
	}

	job := models.NewRestoreJob(backupID, targetClusterID, "restore")
	job.WALIndex = walIndex
	m.addRestoreJob(job)

	go m.executeRestore(ctx, job, backup, targetClusterID)
	return job, nil
}

func (m *Manager) executeRestore(ctx context.Context, job *models.RestoreJob, backup *models.Backup, targetClusterID string) {
	defer func() {
		job.CompletedAt = time.Now()
		m.updateRestoreJob(job)
	}()

	client, err := m.clusterMgr.GetClient(targetClusterID)
	if err != nil {
		job.Status = "failed"
		job.Message = fmt.Sprintf("Failed to get client: %v", err)
		return
	}

	snapshot, err := m.buildPointInTimeSnapshot(ctx, backup, job.PointInTime, job.WALIndex)
	if err != nil {
		job.Status = "failed"
		job.Message = fmt.Sprintf("Failed to build snapshot: %v", err)
		return
	}

	for key, value := range snapshot.Kvs {
		if _, err := client.Put(ctx, key, string(value)); err != nil {
			job.Status = "failed"
			job.Message = fmt.Sprintf("Failed to restore key %s: %v", key, err)
			return
		}
	}

	job.Status = "completed"
	job.Message = fmt.Sprintf("Successfully restored %d keys", len(snapshot.Kvs))
}

func (m *Manager) buildPointInTimeSnapshot(ctx context.Context, baseBackup *models.Backup, pointInTime time.Time, walIndex int64) (*BackupSnapshot, error) {
	snapshot, err := m.loadSnapshot(ctx, baseBackup)
	if err != nil {
		return nil, err
	}

	needReplay := !pointInTime.IsZero() || walIndex > 0

	if !needReplay {
		return snapshot, nil
	}

	chainBackups := m.getBackupChain(baseBackup.ID)

	for _, b := range chainBackups {
		if b.Type != "incremental" {
			continue
		}

		if !pointInTime.IsZero() && b.SnapshotMeta.StartTime.After(pointInTime) {
			break
		}

		if walIndex > 0 && b.SnapshotMeta.WALStartIndex > walIndex {
			break
		}

		incrBackup, err := m.loadWALIncremental(ctx, b)
		if err != nil {
			return nil, fmt.Errorf("failed to load incremental backup %s: %w", b.ID, err)
		}

		for key, value := range incrBackup.CompactedKvs {
			snapshot.Kvs[key] = value
		}

		for _, rec := range incrBackup.Records {
			if rec.Type == RecordTypeCommit {
				parts := splitKeyAndValue(rec.Data)
				if len(parts) > 0 {
					delete(snapshot.Kvs, string(parts[0]))
				}
			}
		}

		if walIndex > 0 {
			snapshot.Meta.WALEndIndex = b.SnapshotMeta.WALEndIndex
		}
	}

	snapshot.Meta.EndTime = time.Now()
	if !pointInTime.IsZero() {
		snapshot.Meta.EndTime = pointInTime
	}

	return snapshot, nil
}

func (m *Manager) VerifyBackup(ctx context.Context, backupID string) (*models.VerifyResult, error) {
	backup, err := m.GetBackup(backupID)
	if err != nil {
		return nil, err
	}

	result := &models.VerifyResult{
		ID:        backupID,
		BackupID:  backupID,
		Status:    "running",
		CreatedAt: time.Now(),
	}

	if backup.Type == "full" {
		snapshot, err := m.loadSnapshot(ctx, backup)
		if err != nil {
			result.Status = "failed"
			result.Message = fmt.Sprintf("Failed to load snapshot: %v", err)
			return result, nil
		}

		hasher := sha256.New()
		for key, value := range snapshot.Kvs {
			hasher.Write([]byte(key))
			hasher.Write(value)
		}
		contentChecksum := hex.EncodeToString(hasher.Sum(nil))

		result.Checksum = contentChecksum
		result.KeysCount = int64(len(snapshot.Kvs))

		if snapshot.Checksum != contentChecksum {
			result.Status = "failed"
			result.Message = "Checksum mismatch: snapshot data integrity check failed"
		} else {
			result.Status = "passed"
			result.Message = fmt.Sprintf("Backup verified successfully (version=%s, walIndex=%d, revision=%d)",
				snapshot.Meta.Version, snapshot.Meta.WALEndIndex, snapshot.Meta.Revision)
		}
	} else {
		incrBackup, err := m.loadWALIncremental(ctx, backup)
		if err != nil {
			result.Status = "failed"
			result.Message = fmt.Sprintf("Failed to load WAL incremental backup: %v", err)
			return result, nil
		}

		hasher := sha256.New()
		for _, rec := range incrBackup.Records {
			hasher.Write([]byte{rec.Type})
			hasher.Write(rec.Data)
		}
		contentChecksum := hex.EncodeToString(hasher.Sum(nil))

		result.Checksum = contentChecksum
		result.KeysCount = int64(len(incrBackup.CompactedKvs))

		if incrBackup.Checksum != contentChecksum {
			result.Status = "failed"
			result.Message = "WAL incremental backup checksum mismatch"
		} else {
			result.Status = "passed"
			result.Message = fmt.Sprintf("WAL incremental backup verified (walRange=%d-%d, records=%d)",
				incrBackup.Meta.WALStartIndex, incrBackup.Meta.WALEndIndex, len(incrBackup.Records))
		}
	}

	return result, nil
}

func (m *Manager) DryRunRestore(ctx context.Context, backupID string) (*models.RestoreJob, error) {
	backup, err := m.GetBackup(backupID)
	if err != nil {
		return nil, err
	}

	job := models.NewRestoreJob(backupID, backup.ClusterID, "dryrun")
	m.addRestoreJob(job)

	go func() {
		defer func() {
			job.CompletedAt = time.Now()
			m.updateRestoreJob(job)
		}()

		if backup.Type == "full" {
			snapshot, err := m.loadSnapshot(ctx, backup)
			if err != nil {
				job.Status = "failed"
				job.Message = fmt.Sprintf("Failed to load snapshot: %v", err)
				return
			}
			job.Status = "completed"
			job.Message = fmt.Sprintf("Dry run successful: %d keys would be restored (revision=%d, walIndex=%d)",
				len(snapshot.Kvs), snapshot.Meta.Revision, snapshot.Meta.WALEndIndex)
		} else {
			incrBackup, err := m.loadWALIncremental(ctx, backup)
			if err != nil {
				job.Status = "failed"
				job.Message = fmt.Sprintf("Failed to load WAL incremental backup: %v", err)
				return
			}
			job.Status = "completed"
			job.Message = fmt.Sprintf("Dry run successful: %d WAL records, %d compacted keys would be applied (walRange=%d-%d)",
				len(incrBackup.Records), len(incrBackup.CompactedKvs),
				incrBackup.Meta.WALStartIndex, incrBackup.Meta.WALEndIndex)
		}
	}()

	return job, nil
}

func (m *Manager) ListAvailableTimePoints(ctx context.Context, clusterID string) ([]models.SnapshotMeta, error) {
	backups := m.ListBackups(clusterID)

	var timePoints []models.SnapshotMeta
	for _, b := range backups {
		if b.Status == "completed" {
			timePoints = append(timePoints, b.SnapshotMeta)
		}
	}

	sort.Slice(timePoints, func(i, j int) bool {
		return timePoints[i].EndTime.Before(timePoints[j].EndTime)
	})

	return timePoints, nil
}

func (m *Manager) addBackup(backup *models.Backup) {
	m.mu.Lock()
	defer m.mu.Unlock()
	m.backups[backup.ID] = backup
}

func (m *Manager) updateBackup(backup *models.Backup) {
	m.mu.Lock()
	defer m.mu.Unlock()
	m.backups[backup.ID] = backup
}

func (m *Manager) GetBackup(id string) (*models.Backup, error) {
	m.mu.RLock()
	defer m.mu.RUnlock()
	backup, exists := m.backups[id]
	if !exists {
		return nil, fmt.Errorf("backup %s not found", id)
	}
	return backup, nil
}

func (m *Manager) ListBackups(clusterID string) []*models.Backup {
	m.mu.RLock()
	defer m.mu.RUnlock()

	backups := make([]*models.Backup, 0)
	for _, backup := range m.backups {
		if clusterID == "" || backup.ClusterID == clusterID {
			backups = append(backups, backup)
		}
	}

	sort.Slice(backups, func(i, j int) bool {
		return backups[i].CreatedAt.After(backups[j].CreatedAt)
	})

	return backups
}

func (m *Manager) getLatestBackup(clusterID, backupType string) *models.Backup {
	backups := m.ListBackups(clusterID)
	for _, b := range backups {
		if b.Type == backupType && b.Status == "completed" {
			return b
		}
	}
	return nil
}

func (m *Manager) getBackupChain(backupID string) []*models.Backup {
	backup, err := m.GetBackup(backupID)
	if err != nil {
		return nil
	}

	chain := []*models.Backup{backup}
	current := backup

	for current.ParentID != "" {
		parent, err := m.GetBackup(current.ParentID)
		if err != nil {
			break
		}
		chain = append(chain, parent)
		current = parent
	}

	sort.Slice(chain, func(i, j int) bool {
		return chain[i].CreatedAt.Before(chain[j].CreatedAt)
	})

	return chain
}

func (m *Manager) addRestoreJob(job *models.RestoreJob) {
	m.mu.Lock()
	defer m.mu.Unlock()
	m.restoreJobs[job.ID] = job
}

func (m *Manager) updateRestoreJob(job *models.RestoreJob) {
	m.mu.Lock()
	defer m.mu.Unlock()
	m.restoreJobs[job.ID] = job
}

func (m *Manager) GetRestoreJob(id string) (*models.RestoreJob, error) {
	m.mu.RLock()
	defer m.mu.RUnlock()
	job, exists := m.restoreJobs[id]
	if !exists {
		return nil, fmt.Errorf("restore job %s not found", id)
	}
	return job, nil
}

func (m *Manager) ListRestoreJobs(clusterID string) []*models.RestoreJob {
	m.mu.RLock()
	defer m.mu.RUnlock()

	jobs := make([]*models.RestoreJob, 0)
	for _, job := range m.restoreJobs {
		if clusterID == "" || job.ClusterID == clusterID {
			jobs = append(jobs, job)
		}
	}

	sort.Slice(jobs, func(i, j int) bool {
		return jobs[i].CreatedAt.After(jobs[j].CreatedAt)
	})

	return jobs
}
