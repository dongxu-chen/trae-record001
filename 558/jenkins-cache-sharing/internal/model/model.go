package model

import "time"

type CacheType string

const (
	CacheTypeMaven  CacheType = "maven"
	CacheTypeNPM    CacheType = "npm"
	CacheTypeGradle CacheType = "gradle"
)

type CacheStatus string

const (
	CacheStatusActive   CacheStatus = "active"
	CacheStatusArchived CacheStatus = "archived"
	CacheStatusExpired  CacheStatus = "expired"
	CacheStatusDeleting CacheStatus = "deleting"
)

type DependencyFileHash struct {
	Path string `json:"path"`
	Hash string `json:"hash"`
}

type CacheEntry struct {
	ID                string                 `json:"id"`
	Name              string                 `json:"name"`
	Type              CacheType              `json:"type"`
	Version           string                 `json:"version"`
	BuildNumber       int                    `json:"build_number"`
	JobName           string                 `json:"job_name"`
	Status            CacheStatus            `json:"status"`
	Size              int64                  `json:"size"`
	ObjectKey         string                 `json:"object_key"`
	Checksum          string                 `json:"checksum"`
	DependencyHash    string                 `json:"dependency_hash"`
	DependencyFiles   []DependencyFileHash   `json:"dependency_files,omitempty"`
	Tags              []string               `json:"tags"`
	CreatedAt         time.Time              `json:"created_at"`
	UpdatedAt         time.Time              `json:"updated_at"`
	ExpiresAt         *time.Time             `json:"expires_at"`
	AccessCount       int                    `json:"access_count"`
	LastAccess        *time.Time             `json:"last_access"`
}

type CacheVersion struct {
	ID          string    `json:"id"`
	CacheType   CacheType `json:"cache_type"`
	Version     string    `json:"version"`
	ParentID    string    `json:"parent_id,omitempty"`
	Entries     []string  `json:"entries"`
	IsLatest    bool      `json:"is_latest"`
	Description string    `json:"description"`
	CreatedAt   time.Time `json:"created_at"`
}

type CleanupStrategy string

const (
	CleanupStrategyLRU       CleanupStrategy = "lru"
	CleanupStrategySize      CleanupStrategy = "size"
	CleanupStrategyAge       CleanupStrategy = "age"
	CleanupStrategyHybrid    CleanupStrategy = "hybrid"
	CleanupStrategyLRUSize   CleanupStrategy = "lru_size"
)

type CleanupPolicy struct {
	ID              string           `json:"id"`
	Name            string           `json:"name"`
	CacheTypes      []CacheType      `json:"cache_types"`
	MaxAge          time.Duration    `json:"max_age"`
	MaxSize         int64            `json:"max_size"`
	MaxVersions     int              `json:"max_versions"`
	KeepLatest      int              `json:"keep_latest"`
	Strategy        CleanupStrategy  `json:"strategy"`
	LRUWeight       float64          `json:"lru_weight"`
	SizeWeight      float64          `json:"size_weight"`
	Enabled         bool             `json:"enabled"`
	CronExpression  string           `json:"cron_expression"`
	LastRunAt       *time.Time       `json:"last_run_at"`
	CreatedAt       time.Time        `json:"created_at"`
}

type CleanupResult struct {
	PolicyID   string    `json:"policy_id"`
	RemovedIDs []string  `json:"removed_ids"`
	FreedBytes int64     `json:"freed_bytes"`
	Errors     []string  `json:"errors,omitempty"`
	StartedAt  time.Time `json:"started_at"`
	FinishedAt time.Time `json:"finished_at"`
}

type WarmupTrigger string

const (
	WarmupTriggerManual       WarmupTrigger = "manual"
	WarmupTriggerDependency   WarmupTrigger = "dependency_change"
	WarmupTriggerScheduled    WarmupTrigger = "scheduled"
	WarmupTriggerBuildComplete WarmupTrigger = "build_complete"
)

type WarmupTask struct {
	ID             string        `json:"id"`
	CacheType      CacheType     `json:"cache_type"`
	SourceJob      string        `json:"source_job"`
	SourceBuild    int           `json:"source_build"`
	TargetJobs     []string      `json:"target_jobs"`
	Status         string        `json:"status"`
	Progress       float64       `json:"progress"`
	Error          string        `json:"error,omitempty"`
	Trigger        WarmupTrigger `json:"trigger"`
	PreviousHash   string        `json:"previous_hash,omitempty"`
	CurrentHash    string        `json:"current_hash,omitempty"`
	CreatedAt      time.Time     `json:"created_at"`
	FinishedAt     *time.Time    `json:"finished_at,omitempty"`
}

type DependencyChangeEvent struct {
	ID           string      `json:"id"`
	CacheType    CacheType   `json:"cache_type"`
	JobName      string      `json:"job_name"`
	BuildNumber  int         `json:"build_number"`
	PreviousHash string      `json:"previous_hash"`
	CurrentHash  string      `json:"current_hash"`
	ChangedFiles []string    `json:"changed_files"`
	AutoWarmed   bool        `json:"auto_warmed"`
	WarmupTaskID string      `json:"warmup_task_id,omitempty"`
	CreatedAt    time.Time   `json:"created_at"`
}

type JenkinsBuild struct {
	JobName    string            `json:"job_name"`
	BuildNumber int             `json:"build_number"`
	Result     string            `json:"result"`
	Parameters map[string]string `json:"parameters"`
	Artifacts  []JenkinsArtifact `json:"artifacts"`
	Timestamp  int64             `json:"timestamp"`
	Duration   int64             `json:"duration"`
}

type JenkinsArtifact struct {
	FileName string `json:"file_name"`
	RelativePath string `json:"relative_path"`
	Size     int64  `json:"size"`
}

type APIMessage struct {
	Success bool        `json:"success"`
	Message string      `json:"message"`
	Data    interface{} `json:"data,omitempty"`
}

type PaginatedResult struct {
	Items      interface{} `json:"items"`
	Total      int64       `json:"total"`
	Page       int         `json:"page"`
	PageSize   int         `json:"page_size"`
	TotalPages int         `json:"total_pages"`
}

type CacheStats struct {
	TotalCaches   int64            `json:"total_caches"`
	TotalSize     int64            `json:"total_size"`
	ByType        map[CacheType]int64 `json:"by_type"`
	ByTypeSize    map[CacheType]int64 `json:"by_type_size"`
	ActiveCount   int64            `json:"active_count"`
	ArchivedCount int64            `json:"archived_count"`
	ExpiredCount  int64            `json:"expired_count"`
}

type ProjectGroup struct {
	ID          string      `json:"id"`
	Name        string      `json:"name"`
	Description string      `json:"description"`
	Jobs        []string    `json:"jobs"`
	CacheTypes  []CacheType `json:"cache_types"`
	SharingEnabled bool     `json:"sharing_enabled"`
	MinSimilarity float64   `json:"min_similarity"`
	CreatedAt   time.Time   `json:"created_at"`
	UpdatedAt   time.Time   `json:"updated_at"`
}

type SimilarityMatch struct {
	SourceJob    string  `json:"source_job"`
	TargetJob    string  `json:"target_job"`
	CacheType    CacheType `json:"cache_type"`
	Similarity   float64 `json:"similarity"`
	MatchedHash  string  `json:"matched_hash"`
	CacheEntryID string  `json:"cache_entry_id"`
	CacheSize    int64   `json:"cache_size"`
}

type BuildStage string

const (
	BuildStageResolve  BuildStage = "resolve"
	BuildStageCompile  BuildStage = "compile"
	BuildStageTest     BuildStage = "test"
	BuildStagePackage  BuildStage = "package"
	BuildStageDeploy   BuildStage = "deploy"
)

type CacheHitRecord struct {
	ID           string     `json:"id"`
	CacheType    CacheType  `json:"cache_type"`
	JobName      string     `json:"job_name"`
	BuildNumber  int        `json:"build_number"`
	Stage        BuildStage `json:"stage"`
	Hit          bool       `json:"hit"`
	RequestedKey string     `json:"requested_key"`
	MatchedEntry string     `json:"matched_entry,omitempty"`
	DependencyHash string   `json:"dependency_hash"`
	Source       string     `json:"source"`
	LatencyMs    int64      `json:"latency_ms"`
	SizeSaved    int64      `json:"size_saved,omitempty"`
	CreatedAt    time.Time  `json:"created_at"`
}

type StageHitRate struct {
	Stage     BuildStage `json:"stage"`
	Total     int64      `json:"total"`
	Hits      int64      `json:"hits"`
	HitRate   float64    `json:"hit_rate"`
	TimeSaved int64      `json:"time_saved_ms"`
	SizeSaved int64      `json:"size_saved"`
}

type HitRateStats struct {
	CacheType      CacheType           `json:"cache_type"`
	JobName        string              `json:"job_name"`
	TimeRange      string              `json:"time_range"`
	TotalRequests  int64               `json:"total_requests"`
	TotalHits      int64               `json:"total_hits"`
	OverallHitRate float64             `json:"overall_hit_rate"`
	ByStage        []StageHitRate      `json:"by_stage"`
	StartTime      time.Time           `json:"start_time"`
	EndTime        time.Time           `json:"end_time"`
}

type StorageBackend struct {
	ID       string `json:"id"`
	Name     string `json:"name"`
	Type     string `json:"type"`
	Endpoint string `json:"endpoint"`
	Bucket   string `json:"bucket"`
	Region   string `json:"region"`
	IsDefault bool  `json:"is_default"`
	IsActive  bool  `json:"is_active"`
}

type MigrationStatus string

const (
	MigrationStatusPending   MigrationStatus = "pending"
	MigrationStatusRunning   MigrationStatus = "running"
	MigrationStatusPaused    MigrationStatus = "paused"
	MigrationStatusCompleted MigrationStatus = "completed"
	MigrationStatusFailed    MigrationStatus = "failed"
)

type MigrationMode string

const (
	MigrationModeFull    MigrationMode = "full"
	MigrationModeIncremental MigrationMode = "incremental"
	MigrationModeSelected MigrationMode = "selected"
)

type MigrationTask struct {
	ID              string          `json:"id"`
	Name            string          `json:"name"`
	SourceBackendID string          `json:"source_backend_id"`
	TargetBackendID string          `json:"target_backend_id"`
	Mode            MigrationMode   `json:"mode"`
	Status          MigrationStatus `json:"status"`
	CacheTypes      []CacheType     `json:"cache_types,omitempty"`
	JobNames        []string        `json:"job_names,omitempty"`
	EntryIDs        []string        `json:"entry_ids,omitempty"`
	DeleteSource    bool            `json:"delete_source"`
	TotalCount      int             `json:"total_count"`
	CompletedCount  int             `json:"completed_count"`
	FailedCount     int             `json:"failed_count"`
	TotalSize       int64           `json:"total_size"`
	CompletedSize   int64           `json:"completed_size"`
	Progress        float64         `json:"progress"`
	Error           string          `json:"error,omitempty"`
	CreatedAt       time.Time       `json:"created_at"`
	StartedAt       *time.Time      `json:"started_at,omitempty"`
	FinishedAt      *time.Time      `json:"finished_at,omitempty"`
}

type MigrationProgress struct {
	TaskID        string `json:"task_id"`
	CurrentEntry  string `json:"current_entry"`
	CurrentJob    string `json:"current_job"`
	CompletedCount int    `json:"completed_count"`
	TotalCount    int    `json:"total_count"`
	CompletedSize int64  `json:"completed_size"`
	TotalSize     int64  `json:"total_size"`
	Progress      float64 `json:"progress"`
}
