package models

import (
	"time"
)

type KeyEvent struct {
	ID             string        `json:"id"`
	DB             int           `json:"db"`
	Key            string        `json:"key"`
	EventType      string        `json:"event_type"`
	Timestamp      time.Time     `json:"timestamp"`
	Processed      bool          `json:"processed"`
	ProcessedAt    time.Time     `json:"processed_at,omitempty"`
	LatencyMs      int64         `json:"latency_ms,omitempty"`
	RetryCount     int           `json:"retry_count"`
	Error          string        `json:"error,omitempty"`
	Sampled        bool          `json:"sampled,omitempty"`
}

type EventStats struct {
	TotalEvents     int64 `json:"total_events"`
	ProcessedEvents int64 `json:"processed_events"`
	FailedEvents    int64 `json:"failed_events"`
	ExpiredEvents   int64 `json:"expired_events"`
	DeletedEvents   int64 `json:"deleted_events"`
	SetEvents       int64 `json:"set_events"`
	SampledEvents   int64 `json:"sampled_events"`
}

type LatencyStats struct {
	AvgMs   float64 `json:"avg_ms"`
	P50Ms   float64 `json:"p50_ms"`
	P95Ms   float64 `json:"p95_ms"`
	P99Ms   float64 `json:"p99_ms"`
	MaxMs   float64 `json:"max_ms"`
	MinMs   float64 `json:"min_ms"`
	Count   int64   `json:"count"`
}

type KeyEventCount struct {
	Key       string `json:"key"`
	Count     int64  `json:"count"`
	EventType string `json:"event_type"`
	DB        int    `json:"db"`
}

type CallbackRequest struct {
	EventType string `json:"event_type"`
	Key       string `json:"key"`
	DB        int    `json:"db"`
	Timestamp int64  `json:"timestamp"`
}
