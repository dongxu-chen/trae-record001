package audit

import (
	"fmt"
	"sync"
	"time"
)

const (
	ActionAddTopic         = "add_topic"
	ActionRemoveTopic      = "remove_topic"
	ActionScaleUp          = "scale_up"
	ActionScaleDown        = "scale_down"
	ActionManualScale      = "manual_scale"
	ActionPartitionUp      = "partition_up"
	ActionPartitionDown    = "partition_down"
	ActionManualPartition  = "manual_partition"
	ActionRateLimit        = "rate_limit_adjust"
	ActionManualRateLimit  = "manual_rate_limit"
	ActionUpdateStrategy   = "update_strategy"
	ActionDeleteStrategy   = "delete_strategy"
	ActionPredictionAlert  = "prediction_alert"
	ActionDLQConfig        = "dlq_config"
	ActionDLQSend          = "dlq_send"
	ActionDLQRetry         = "dlq_retry"
	ActionReplay           = "replay"
	ActionReplayCancel     = "replay_cancel"
	ActionDelayConfig      = "delay_config"
	ActionDelayPause       = "delay_pause"
	ActionDelayResume      = "delay_resume"
)

type AuditLog struct {
	ID        int64     `json:"id"`
	Timestamp time.Time `json:"timestamp"`
	Action    string    `json:"action"`
	Topic     string    `json:"topic"`
	Message   string    `json:"message"`
}

type AuditLogger struct {
	logs  []AuditLog
	mu    sync.RWMutex
	count int64
}

func NewAuditLogger() *AuditLogger {
	return &AuditLogger{
		logs: make([]AuditLog, 0, 1000),
	}
}

func (a *AuditLogger) Log(action, topic, format string, args ...interface{}) {
	a.mu.Lock()
	defer a.mu.Unlock()

	a.count++
	log := AuditLog{
		ID:        a.count,
		Timestamp: time.Now(),
		Action:    action,
		Topic:     topic,
		Message:   fmt.Sprintf(format, args...),
	}

	a.logs = append(a.logs, log)
	if len(a.logs) > 10000 {
		a.logs = a.logs[1000:]
	}
}

func (a *AuditLogger) GetLogs(limit, offset int) []AuditLog {
	a.mu.RLock()
	defer a.mu.RUnlock()

	if offset >= len(a.logs) {
		return []AuditLog{}
	}

	end := offset + limit
	if end > len(a.logs) {
		end = len(a.logs)
	}

	result := make([]AuditLog, end-offset)
	for i := offset; i < end; i++ {
		result[i-offset] = a.logs[len(a.logs)-1-i]
	}
	return result
}

func (a *AuditLogger) GetLogsByTopic(topic string, limit int) []AuditLog {
	a.mu.RLock()
	defer a.mu.RUnlock()

	result := make([]AuditLog, 0, limit)
	for i := len(a.logs) - 1; i >= 0 && len(result) < limit; i-- {
		if a.logs[i].Topic == topic {
			result = append(result, a.logs[i])
		}
	}
	return result
}

func (a *AuditLogger) GetLogsByAction(action string, limit int) []AuditLog {
	a.mu.RLock()
	defer a.mu.RUnlock()

	result := make([]AuditLog, 0, limit)
	for i := len(a.logs) - 1; i >= 0 && len(result) < limit; i-- {
		if a.logs[i].Action == action {
			result = append(result, a.logs[i])
		}
	}
	return result
}

func (a *AuditLogger) GetAllLogs() []AuditLog {
	a.mu.RLock()
	defer a.mu.RUnlock()

	result := make([]AuditLog, len(a.logs))
	copy(result, a.logs)
	return result
}
