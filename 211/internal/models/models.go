package models

import (
	"time"

	"gorm.io/gorm"
)

type TaskStatus string

const (
	TaskStatusPending   TaskStatus = "pending"
	TaskStatusRunning   TaskStatus = "running"
	TaskStatusCompleted TaskStatus = "completed"
	TaskStatusFailed    TaskStatus = "failed"
	TaskStatusPaused    TaskStatus = "paused"
)

type TriggerType string

const (
	TriggerTypeCron     TriggerType = "cron"
	TriggerTypeInterval TriggerType = "interval"
	TriggerTypeManual   TriggerType = "manual"
)

type Task struct {
	ID          string         `gorm:"primaryKey;size:36" json:"id"`
	Name        string         `gorm:"size:100;not null" json:"name"`
	Description string         `gorm:"size:500" json:"description"`
	TaskType    string         `gorm:"size:50;not null" json:"task_type"`
	Payload     string         `gorm:"type:text" json:"payload"`
	TriggerType TriggerType    `gorm:"size:20;not null" json:"trigger_type"`
	CronExpr    string         `gorm:"size:100" json:"cron_expr"`
	IntervalSec int            `json:"interval_sec"`
	Status      TaskStatus     `gorm:"size:20;default:pending" json:"status"`
	MaxRetries  int            `gorm:"default:3" json:"max_retries"`
	RetryDelay  int            `gorm:"default:5" json:"retry_delay"`
	TimeoutSec  int            `gorm:"default:300" json:"timeout_sec"`
	Dependencies string        `gorm:"size:500" json:"dependencies"`
	NextRunAt   *time.Time     `json:"next_run_at"`
	LastRunAt   *time.Time     `json:"last_run_at"`
	CreatedAt   time.Time      `json:"created_at"`
	UpdatedAt   time.Time      `json:"updated_at"`
	DeletedAt   gorm.DeletedAt `gorm:"index" json:"deleted_at,omitempty"`
}

type ExecutionStatus string

const (
	ExecutionStatusPending   ExecutionStatus = "pending"
	ExecutionStatusRunning   ExecutionStatus = "running"
	ExecutionStatusSuccess   ExecutionStatus = "success"
	ExecutionStatusFailed    ExecutionStatus = "failed"
	ExecutionStatusTimeout   ExecutionStatus = "timeout"
)

type TaskExecution struct {
	ID          string          `gorm:"primaryKey;size:36" json:"id"`
	TaskID      string          `gorm:"size:36;index" json:"task_id"`
	Task        Task            `gorm:"foreignKey:TaskID" json:"task,omitempty"`
	Status      ExecutionStatus `gorm:"size:20;default:pending" json:"status"`
	RetryCount  int             `gorm:"default:0" json:"retry_count"`
	WorkerID    string          `gorm:"size:100" json:"worker_id"`
	StartTime   *time.Time      `json:"start_time"`
	EndTime     *time.Time      `json:"end_time"`
	Result      string          `gorm:"type:text" json:"result"`
	Error       string          `gorm:"type:text" json:"error"`
	DurationMs  int64           `json:"duration_ms"`
	CreatedAt   time.Time       `json:"created_at"`
	UpdatedAt   time.Time       `json:"updated_at"`
}

func (Task) TableName() string {
	return "tasks"
}

func (TaskExecution) TableName() string {
	return "task_executions"
}

type AuditEventType string

const (
	AuditEventTaskScheduled  AuditEventType = "task_scheduled"
	AuditEventTaskDispatched AuditEventType = "task_dispatched"
	AuditEventTaskStarted    AuditEventType = "task_started"
	AuditEventTaskCompleted  AuditEventType = "task_completed"
	AuditEventTaskFailed     AuditEventType = "task_failed"
	AuditEventTaskTimeout    AuditEventType = "task_timeout"
	AuditEventTaskRetried    AuditEventType = "task_retried"
	AuditEventNodeJoined     AuditEventType = "node_joined"
	AuditEventNodeLeft       AuditEventType = "node_left"
	AuditEventNodeFailed     AuditEventType = "node_failed"
	AuditEventTaskReassigned AuditEventType = "task_reassigned"
)

type AuditLog struct {
	ID          string         `gorm:"primaryKey;size:36" json:"id"`
	Event       AuditEventType `gorm:"size:30;index" json:"event"`
	TaskID      string         `gorm:"size:36;index" json:"task_id"`
	ExecutionID string         `gorm:"size:36;index" json:"execution_id"`
	WorkerID    string         `gorm:"size:100;index" json:"worker_id"`
	Message     string         `gorm:"size:500" json:"message"`
	Details     string         `gorm:"type:text" json:"details"`
	DurationMs  int64          `json:"duration_ms"`
	RetryCount  int            `json:"retry_count"`
	CreatedAt   time.Time      `gorm:"index" json:"created_at"`
}

func (AuditLog) TableName() string {
	return "audit_logs"
}

type WorkerNode struct {
	ID            string    `gorm:"primaryKey;size:100" json:"id"`
	WorkerCount   int       `json:"worker_count"`
	Status        string    `gorm:"size:20;index" json:"status"`
	LastHeartbeat time.Time `gorm:"index" json:"last_heartbeat"`
	StartedAt     time.Time `json:"started_at"`
	CreatedAt     time.Time `json:"created_at"`
	UpdatedAt     time.Time `json:"updated_at"`
}

func (WorkerNode) TableName() string {
	return "worker_nodes"
}

const (
	WorkerStatusOnline  = "online"
	WorkerStatusOffline = "offline"
	WorkerStatusFailed  = "failed"
)

type TimeoutControl struct {
	Enabled        bool
	DefaultTimeout time.Duration
	MaxTimeout     time.Duration
}
