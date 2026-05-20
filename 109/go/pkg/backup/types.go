package backup

import (
	"time"
)

type BackupType string

const (
	BackupTypeMySQL      BackupType = "mysql"
	BackupTypePostgreSQL BackupType = "postgresql"
)

type BackupResult struct {
	Database    string        `json:"database"`
	Type        BackupType    `json:"type"`
	FilePath    string        `json:"file_path"`
	FileName    string        `json:"file_name"`
	Size        int64         `json:"size"`
	Duration    time.Duration `json:"duration"`
	Error       error         `json:"error,omitempty"`
	Success     bool          `json:"success"`
	IsIncremental bool        `json:"is_incremental"`
	GTIDSet     string        `json:"gtid_set,omitempty"`
	BinlogFile  string        `json:"binlog_file,omitempty"`
	BinlogPos   int64         `json:"binlog_pos,omitempty"`
	Timestamp   time.Time     `json:"timestamp"`
}

type PipelineStage string

const (
	StageBackup    PipelineStage = "backup"
	StageCompress  PipelineStage = "compress"
	StageEncrypt   PipelineStage = "encrypt"
	StageUpload    PipelineStage = "upload"
)

type PipelineJob struct {
	ID           string
	Database     string
	Type         BackupType
	CurrentStage PipelineStage
	BackupResult *BackupResult
	FilePath     string
	Error        error
	StartTime    time.Time
}

func (j *PipelineJob) SetStage(stage PipelineStage) {
	j.CurrentStage = stage
}

func (j *PipelineJob) SetError(err error) {
	j.Error = err
}

type PipelineStats struct {
	TotalJobs    int64
	BackupJobs   int64
	CompressJobs int64
	EncryptJobs  int64
	UploadJobs   int64
	SuccessJobs  int64
	FailedJobs   int64
}
