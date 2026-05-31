package models

import (
	"time"

	"github.com/google/uuid"
)

type Cluster struct {
	ID        string    `json:"id" yaml:"id"`
	Name      string    `json:"name" yaml:"name"`
	Endpoints []string  `json:"endpoints" yaml:"endpoints"`
	Username  string    `json:"username,omitempty" yaml:"username,omitempty"`
	Password  string    `json:"password,omitempty" yaml:"password,omitempty"`
	TLS       bool      `json:"tls" yaml:"tls"`
	CertFile  string    `json:"certFile,omitempty" yaml:"certFile,omitempty"`
	KeyFile   string    `json:"keyFile,omitempty" yaml:"keyFile,omitempty"`
	CAFile    string    `json:"caFile,omitempty" yaml:"caFile,omitempty"`
	Region    string    `json:"region,omitempty" yaml:"region,omitempty"`
	CreatedAt time.Time `json:"createdAt" yaml:"createdAt"`
	UpdatedAt time.Time `json:"updatedAt" yaml:"updatedAt"`
}

func NewCluster() *Cluster {
	return &Cluster{
		ID:        uuid.New().String(),
		CreatedAt: time.Now(),
		UpdatedAt: time.Now(),
	}
}

type Backup struct {
	ID            string       `json:"id"`
	ClusterID     string       `json:"clusterId"`
	ClusterName   string       `json:"clusterName"`
	Type          string       `json:"type"`
	Status        string       `json:"status"`
	Path          string       `json:"path"`
	MetaPath      string       `json:"metaPath"`
	Size          int64        `json:"size"`
	Encrypted     bool         `json:"encrypted"`
	KMSKeyID      string       `json:"kmsKeyId,omitempty"`
	Checksum      string       `json:"checksum"`
	Revision      int64        `json:"revision"`
	KeysCount     int64        `json:"keysCount"`
	ParentID      string       `json:"parentId,omitempty"`
	DiffSize      int64        `json:"diffSize,omitempty"`
	RetentionDays int          `json:"retentionDays"`
	Message       string       `json:"message,omitempty"`
	CreatedAt     time.Time    `json:"createdAt"`
	CompletedAt   time.Time    `json:"completedAt,omitempty"`
	Duration      int64        `json:"duration,omitempty"`
	SnapshotMeta  SnapshotMeta `json:"snapshotMeta"`
	Replicated    bool         `json:"replicated"`
	ReplicaSites  []string     `json:"replicaSites,omitempty"`
}

type SnapshotMeta struct {
	Version       string    `json:"version"`
	FormatVersion string    `json:"formatVersion"`
	StartTime     time.Time `json:"startTime"`
	EndTime       time.Time `json:"endTime"`
	WALStartIndex int64     `json:"walStartIndex"`
	WALEndIndex   int64     `json:"walEndIndex"`
	Revision      int64     `json:"revision"`
	KeysCount     int64     `json:"keysCount"`
	Checksum      string    `json:"checksum"`
	SourceCluster string    `json:"sourceCluster"`
	EtcdVersion   string    `json:"etcdVersion"`
}

func NewBackup(clusterID, clusterName string, backupType string) *Backup {
	return &Backup{
		ID:          uuid.New().String(),
		ClusterID:   clusterID,
		ClusterName: clusterName,
		Type:        backupType,
		Status:      "pending",
		CreatedAt:   time.Now(),
		SnapshotMeta: SnapshotMeta{
			Version:       "2.0.0",
			FormatVersion: "v2wal",
			StartTime:     time.Now(),
		},
	}
}

type RestoreJob struct {
	ID            string    `json:"id"`
	BackupID      string    `json:"backupId"`
	ClusterID     string    `json:"clusterId"`
	TargetCluster string   `json:"targetCluster"`
	Status        string   `json:"status"`
	Type          string   `json:"type"`
	Message       string   `json:"message,omitempty"`
	PointInTime   time.Time `json:"pointInTime,omitempty"`
	WALIndex      int64    `json:"walIndex,omitempty"`
	CreatedAt     time.Time `json:"createdAt"`
	CompletedAt   time.Time `json:"completedAt,omitempty"`
	Duration      int64    `json:"duration,omitempty"`
}

func NewRestoreJob(backupID, clusterID string, restoreType string) *RestoreJob {
	return &RestoreJob{
		ID:        uuid.New().String(),
		BackupID:  backupID,
		ClusterID: clusterID,
		Type:      restoreType,
		Status:    "pending",
		CreatedAt: time.Now(),
	}
}

type Schedule struct {
	ID            string    `json:"id"`
	ClusterID     string    `json:"clusterId"`
	Name          string    `json:"name"`
	CronExpr      string    `json:"cronExpr"`
	BackupType    string    `json:"backupType"`
	RetentionDays int       `json:"retentionDays"`
	Encrypted     bool      `json:"encrypted"`
	KMSKeyID      string    `json:"kmsKeyId,omitempty"`
	Enabled       bool      `json:"enabled"`
	CreatedAt     time.Time `json:"createdAt"`
}

func NewSchedule() *Schedule {
	return &Schedule{
		ID:        uuid.New().String(),
		CreatedAt: time.Now(),
		Enabled:   true,
	}
}

type ReplicationConfig struct {
	ID               string             `json:"id"`
	Name             string             `json:"name"`
	SourceClusterID  string             `json:"sourceClusterId"`
	TargetClusterID  string             `json:"targetClusterId"`
	TargetStorage    StorageConfig      `json:"targetStorage"`
	Mode             string             `json:"mode"`
	CronExpr         string             `json:"cronExpr"`
	BandwidthLimitMB int                `json:"bandwidthLimitMb,omitempty"`
	Compress         bool               `json:"compress"`
	Encrypted        bool               `json:"encrypted"`
	Enabled          bool               `json:"enabled"`
	Status           string             `json:"status"`
	LastSyncAt       time.Time          `json:"lastSyncAt,omitempty"`
	LastSyncSize     int64              `json:"lastSyncSize,omitempty"`
	LagSeconds       int64              `json:"lagSeconds,omitempty"`
	CreatedAt        time.Time          `json:"createdAt"`
	UpdatedAt        time.Time          `json:"updatedAt"`
}

func NewReplicationConfig() *ReplicationConfig {
	return &ReplicationConfig{
		ID:        uuid.New().String(),
		Mode:      "async",
		Compress:  true,
		Encrypted: true,
		Enabled:   true,
		Status:    "idle",
		CreatedAt: time.Now(),
		UpdatedAt: time.Now(),
	}
}

type ReplicationTask struct {
	ID         string    `json:"id"`
	ConfigID   string    `json:"configId"`
	BackupID   string    `json:"backupId"`
	Status     string    `json:"status"`
	SourceSize int64     `json:"sourceSize"`
	TargetSize int64     `json:"targetSize"`
	Duration   int64     `json:"duration"`
	Message    string    `json:"message,omitempty"`
	CreatedAt  time.Time `json:"createdAt"`
	CompletedAt time.Time `json:"completedAt,omitempty"`
}

func NewReplicationTask(configID, backupID string) *ReplicationTask {
	return &ReplicationTask{
		ID:        uuid.New().String(),
		ConfigID:  configID,
		BackupID:  backupID,
		Status:    "pending",
		CreatedAt: time.Now(),
	}
}

type DrillConfig struct {
	ID               string    `json:"id"`
	Name             string    `json:"name"`
	ClusterID        string    `json:"clusterId"`
	CronExpr         string    `json:"cronExpr"`
	TargetClusterID  string    `json:"targetClusterId,omitempty"`
	AutoCleanup      bool      `json:"autoCleanup"`
	CleanupDelayMin  int       `json:"cleanupDelayMin"`
	VerifyChecksum   bool      `json:"verifyChecksum"`
	MaxDataSizeMB    int       `json:"maxDataSizeMb,omitempty"`
	NotifyOnFailure  bool      `json:"notifyOnFailure"`
	Enabled          bool      `json:"enabled"`
	LastRunAt        time.Time `json:"lastRunAt,omitempty"`
	LastResult       string    `json:"lastResult,omitempty"`
	ConsecutiveFail  int       `json:"consecutiveFail"`
	CreatedAt        time.Time `json:"createdAt"`
}

func NewDrillConfig() *DrillConfig {
	return &DrillConfig{
		ID:              uuid.New().String(),
		AutoCleanup:     true,
		CleanupDelayMin: 30,
		VerifyChecksum:  true,
		NotifyOnFailure: true,
		Enabled:         true,
		CreatedAt:       time.Now(),
	}
}

type DrillResult struct {
	ID              string    `json:"id"`
	ConfigID        string    `json:"configId"`
	ClusterID       string    `json:"clusterId"`
	BackupID        string    `json:"backupId"`
	Status          string    `json:"status"`
	BackupValid     bool      `json:"backupValid"`
	RestoreSuccess  bool      `json:"restoreSuccess"`
	DataIntegrity   bool      `json:"dataIntegrity"`
	KeysRestored    int64     `json:"keysRestored"`
	RestoreDuration int64     `json:"restoreDuration"`
	VerifyDuration  int64     `json:"verifyDuration"`
	CleanupDone     bool      `json:"cleanupDone"`
	Message         string    `json:"message,omitempty"`
	CreatedAt       time.Time `json:"createdAt"`
	CompletedAt     time.Time `json:"completedAt,omitempty"`
}

func NewDrillResult(configID, clusterID, backupID string) *DrillResult {
	return &DrillResult{
		ID:        uuid.New().String(),
		ConfigID:  configID,
		ClusterID: clusterID,
		BackupID:  backupID,
		Status:    "running",
		CreatedAt: time.Now(),
	}
}

type CostAnalysis struct {
	ClusterID           string             `json:"clusterId"`
	Period              string             `json:"period"`
	TotalBackups        int                `json:"totalBackups"`
	TotalSizeBytes      int64              `json:"totalSizeBytes"`
	IncrementalCount    int                `json:"incrementalCount"`
	IncrementalSizeBytes int64             `json:"incrementalSizeBytes"`
	FullCount           int                `json:"fullCount"`
	FullSizeBytes       int64              `json:"fullSizeBytes"`
	StorageCost         float64            `json:"storageCost"`
	NetworkCost         float64            `json:"networkCost"`
	ComputeCost         float64            `json:"computeCost"`
	TotalCost           float64            `json:"totalCost"`
	EstimatedRTO        int64              `json:"estimatedRto"`
	EstimatedRPO        int64              `json:"estimatedRpo"`
	SavingsPercent      float64            `json:"savingsPercent"`
	Recommendations     []CostRecommendation `json:"recommendations"`
	StorageTrend        []StorageTrendPoint `json:"storageTrend"`
}

type CostRecommendation struct {
	Type        string  `json:"type"`
	Current     string  `json:"current"`
	Suggested   string  `json:"suggested"`
	SavingsPct  float64 `json:"savingsPct"`
	Reason      string  `json:"reason"`
	Priority    string  `json:"priority"`
}

type StorageTrendPoint struct {
	Date      string `json:"date"`
	FullSize  int64  `json:"fullSize"`
	IncrSize  int64  `json:"incrSize"`
	TotalSize int64  `json:"totalSize"`
	Cost      float64 `json:"cost"`
}

type StorageConfig struct {
	Type       string `yaml:"type"`
	LocalPath  string `yaml:"localPath,omitempty"`
	S3Endpoint string `yaml:"s3Endpoint,omitempty"`
	S3Bucket   string `yaml:"s3Bucket,omitempty"`
	S3Region   string `yaml:"s3Region,omitempty"`
	AccessKey  string `yaml:"accessKey,omitempty"`
	SecretKey  string `yaml:"secretKey,omitempty"`
	UseSSL     bool   `yaml:"useSSL"`
	PricePerGB float64 `yaml:"pricePerGb,omitempty"`
}

type KMSConfig struct {
	Provider    string `yaml:"provider"`
	Endpoint    string `yaml:"endpoint,omitempty"`
	Region      string `yaml:"region,omitempty"`
	AccessKey   string `yaml:"accessKey,omitempty"`
	SecretKey   string `yaml:"secretKey,omitempty"`
	KeyID       string `yaml:"keyId,omitempty"`
	KeyVault    string `yaml:"keyVault,omitempty"`
	Token       string `yaml:"token,omitempty"`
	Namespace   string `yaml:"namespace,omitempty"`
	CACertPath  string `yaml:"caCertPath,omitempty"`
}

type EncryptionConfig struct {
	Enabled   bool      `yaml:"enabled"`
	Key       string    `yaml:"key,omitempty"`
	KeyPath   string    `yaml:"keyPath,omitempty"`
	Algorithm string    `yaml:"algorithm"`
	KMS       KMSConfig `yaml:"kms,omitempty"`
}

type AppConfig struct {
	Storage    StorageConfig    `yaml:"storage"`
	Encryption EncryptionConfig `yaml:"encryption"`
	Clusters   []Cluster        `yaml:"clusters"`
	Schedules  []Schedule       `yaml:"schedules"`
}

type ClusterStatus struct {
	ID       string   `json:"id"`
	Name     string   `json:"name"`
	Healthy  bool     `json:"healthy"`
	Message  string   `json:"message,omitempty"`
	Members  []Member `json:"members"`
	Revision int64    `json:"revision"`
	DBSize   int64    `json:"dbSize"`
	Leader   string   `json:"leader"`
	Version  string   `json:"version"`
}

type Member struct {
	ID         string   `json:"id"`
	Name       string   `json:"name"`
	Endpoints  []string `json:"endpoints"`
	IsLeader   bool     `json:"isLeader"`
	IsHealthy  bool     `json:"isHealthy"`
}

type VerifyResult struct {
	ID        string    `json:"id"`
	BackupID  string    `json:"backupId"`
	Status    string    `json:"status"`
	Message   string    `json:"message"`
	KeysCount int64     `json:"keysCount"`
	Checksum  string    `json:"checksum"`
	CreatedAt time.Time `json:"createdAt"`
}
