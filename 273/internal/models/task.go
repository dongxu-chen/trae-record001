package models

import (
	"encoding/json"
	"time"
)

const (
	TaskStatusPending   = "pending"
	TaskStatusRunning   = "running"
	TaskStatusPaused    = "paused"
	TaskStatusCompleted = "completed"
	TaskStatusFailed    = "failed"
	TaskStatusDeleted   = "deleted"
	TaskStatusWaiting   = "waiting"
)

const (
	ExecutionStatusRunning = "running"
	ExecutionStatusSuccess = "success"
	ExecutionStatusFailed  = "failed"
)

const (
	NodeStatusOnline  = "online"
	NodeStatusOffline = "offline"
)

const (
	ResourcePoolDefault = "default"
	ResourcePoolCPU     = "cpu"
	ResourcePoolIO      = "io"
	ResourcePoolMemory  = "memory"
)

const (
	DagStatusPending   = "pending"
	DagStatusRunning   = "running"
	DagStatusCompleted = "completed"
	DagStatusFailed    = "failed"
	DagStatusPaused    = "paused"
)

type Task struct {
	ID             string          `json:"id"`
	Name           string          `json:"name"`
	CronExpr       string          `json:"cron_expr"`
	TaskType       string          `json:"task_type"`
	Payload        json.RawMessage `json:"payload"`
	Status         string          `json:"status"`
	ShardKey       string          `json:"shard_key,omitempty"`
	ShardTotal     int             `json:"shard_total"`
	ShardIndex     int             `json:"shard_index"`
	NodeID         string          `json:"node_id,omitempty"`
	ResourcePool   string          `json:"resource_pool"`
	DagID          string          `json:"dag_id,omitempty"`
	NextRunTime    time.Time       `json:"next_run_time"`
	LastRunTime    time.Time       `json:"last_run_time"`
	LastRunStatus  string          `json:"last_run_status"`
	LastError      string          `json:"last_error"`
	RunCount       int             `json:"run_count"`
	Priority       int             `json:"priority"`
	MaxRetries     int             `json:"max_retries"`
	RetryCount     int             `json:"retry_count"`
	AvgDurationMs  int64           `json:"avg_duration_ms"`
	IsDeleted      bool            `json:"is_deleted"`
	CreatedAt      time.Time       `json:"created_at"`
	UpdatedAt      time.Time       `json:"updated_at"`
}

type TaskExecution struct {
	ID         int64     `json:"id"`
	TaskID     string    `json:"task_id"`
	NodeID     string    `json:"node_id"`
	StartTime  time.Time `json:"start_time"`
	EndTime    time.Time `json:"end_time"`
	Status     string    `json:"status"`
	Error      string    `json:"error"`
	DurationMs int64     `json:"duration_ms"`
	ShardIndex int       `json:"shard_index"`
	CreatedAt  time.Time `json:"created_at"`
}

type Node struct {
	ID           string    `json:"id"`
	Host         string    `json:"host"`
	Port         int       `json:"port"`
	Status       string    `json:"status"`
	TaskCount    int       `json:"task_count"`
	LastHeartbeat time.Time `json:"last_heartbeat"`
	RegisteredAt time.Time `json:"registered_at"`
	UpdatedAt    time.Time `json:"updated_at"`
}

type CreateTaskRequest struct {
	Name       string          `json:"name" binding:"required"`
	CronExpr   string          `json:"cron_expr" binding:"required"`
	TaskType   string          `json:"task_type" binding:"required"`
	Payload    json.RawMessage `json:"payload"`
	ShardKey   string          `json:"shard_key,omitempty"`
	ShardTotal int             `json:"shard_total"`
	Priority   int             `json:"priority"`
	MaxRetries int             `json:"max_retries"`
}

type UpdateTaskRequest struct {
	Name         string          `json:"name"`
	CronExpr     string          `json:"cron_expr"`
	TaskType     string          `json:"task_type"`
	Payload      json.RawMessage `json:"payload"`
	Priority     *int            `json:"priority"`
	MaxRetries   *int            `json:"max_retries"`
	ResourcePool string          `json:"resource_pool"`
}

type DAG struct {
	ID          string    `json:"id"`
	Name        string    `json:"name"`
	Description string    `json:"description"`
	Status      string    `json:"status"`
	CronExpr    string    `json:"cron_expr"`
	TaskIDs     []string  `json:"task_ids"`
	NextRunTime time.Time `json:"next_run_time"`
	LastRunTime time.Time `json:"last_run_time"`
	IsDeleted   bool      `json:"is_deleted"`
	CreatedAt   time.Time `json:"created_at"`
	UpdatedAt   time.Time `json:"updated_at"`
}

type DAGDependency struct {
	ID              int64  `json:"id"`
	DagID           string `json:"dag_id"`
	TaskID          string `json:"task_id"`
	DependsOnTaskID string `json:"depends_on_task_id"`
	DependencyType  string `json:"dependency_type"`
}

type DAGExecution struct {
	ID           int64     `json:"id"`
	DagID        string    `json:"dag_id"`
	StartTime    time.Time `json:"start_time"`
	EndTime      time.Time `json:"end_time"`
	Status       string    `json:"status"`
	TriggeredBy  string    `json:"triggered_by"`
	CompletedTasks []string `json:"completed_tasks"`
	FailedTasks  []string  `json:"failed_tasks"`
	CreatedAt    time.Time `json:"created_at"`
}

type ResourcePool struct {
	Name            string `json:"name"`
	WorkerCount     int    `json:"worker_count"`
	MaxWorkerCount  int    `json:"max_worker_count"`
	RunningTasks    int    `json:"running_tasks"`
	QueuedTasks     int    `json:"queued_tasks"`
	CPUQuota        int    `json:"cpu_quota"`
	MemoryQuotaMB   int    `json:"memory_quota_mb"`
	Description     string `json:"description"`
}

type LoadPrediction struct {
	TimePoint   time.Time `json:"time_point"`
	PredictedLoad float64 `json:"predicted_load"`
	Confidence  float64   `json:"confidence"`
	Trend       string    `json:"trend"`
}

type ResourcePoolConfig struct {
	Name           string `json:"name" binding:"required"`
	WorkerCount    int    `json:"worker_count"`
	MaxWorkerCount int    `json:"max_worker_count"`
	CPUQuota       int    `json:"cpu_quota"`
	MemoryQuotaMB  int    `json:"memory_quota_mb"`
	Description    string `json:"description"`
}

type CreateDAGRequest struct {
	Name        string   `json:"name" binding:"required"`
	Description string   `json:"description"`
	CronExpr    string   `json:"cron_expr"`
	TaskIDs     []string `json:"task_ids"`
}

type AddDependencyRequest struct {
	DagID           string `json:"dag_id" binding:"required"`
	TaskID          string `json:"task_id" binding:"required"`
	DependsOnTaskID string `json:"depends_on_task_id" binding:"required"`
	DependencyType  string `json:"dependency_type"`
}
