package main

import (
	"encoding/json"
	"time"
)

const MaxPayloadSize = 1024 * 1024

type TaskStatus string

const (
	TaskStatusPending   TaskStatus = "pending"
	TaskStatusRunning   TaskStatus = "running"
	TaskStatusCompleted TaskStatus = "completed"
	TaskStatusFailed    TaskStatus = "failed"
	TaskStatusDeadLetter TaskStatus = "dead_letter"
)

type Task struct {
	ID          string          `json:"id"`
	Type        string          `json:"type"`
	Payload     json.RawMessage `json:"payload"`
	Status      TaskStatus      `json:"status"`
	Result      interface{}     `json:"result,omitempty"`
	Error       string          `json:"error,omitempty"`
	LastError   string          `json:"last_error,omitempty"`
	CreatedAt   time.Time       `json:"created_at"`
	StartedAt   *time.Time      `json:"started_at,omitempty"`
	EndedAt     *time.Time      `json:"ended_at,omitempty"`
	RetryCount  int             `json:"retry_count"`
	StreamID    string          `json:"stream_id,omitempty"`
	IsDeadLetter bool           `json:"is_dead_letter,omitempty"`
}

type TaskRequest struct {
	Type    string          `json:"type" binding:"required"`
	Payload json.RawMessage `json:"payload"`
}

type TaskResponse struct {
	Task *Task `json:"task"`
}
