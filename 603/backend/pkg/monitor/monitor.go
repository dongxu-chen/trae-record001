package monitor

import (
	"context"
	"sync"
	"time"

	"pulsar-backlog-manager/pkg/audit"
	"pulsar-backlog-manager/pkg/config"
	"pulsar-backlog-manager/pkg/pulsar"
)

type BacklogHandler func(TopicBacklog)

type TopicBacklog struct {
	Topic         string
	Subscription  string
	BacklogSize   int64
	AvgMsgSize    float64
	StorageSize   int64
	EffectiveBacklog int64
	MsgRateIn     float64
	MsgRateOut    float64
	Timestamp     time.Time
	ConsumerCount int
}

type Monitor struct {
	config     config.MonitorConfig
	pulsar     *pulsar.Client
	audit      *audit.AuditLogger
	handlers   []BacklogHandler
	backlogs   map[string]TopicBacklog
	history    map[string][]TopicBacklog
	mu         sync.RWMutex
	topics     []string
}

func NewMonitor(cfg config.MonitorConfig, pulsarClient *pulsar.Client, auditLog *audit.AuditLogger) *Monitor {
	return &Monitor{
		config:   cfg,
		pulsar:   pulsarClient,
		audit:    auditLog,
		handlers: make([]BacklogHandler, 0),
		backlogs: make(map[string]TopicBacklog),
		history:  make(map[string][]TopicBacklog),
		topics:   cfg.Topics,
	}
}

func (m *Monitor) RegisterHandler(handler BacklogHandler) {
	m.handlers = append(m.handlers, handler)
}

func (m *Monitor) Start(ctx context.Context) {
	ticker := time.NewTicker(time.Duration(m.config.IntervalSeconds) * time.Second)
	defer ticker.Stop()

	for {
		select {
		case <-ctx.Done():
			return
		case <-ticker.C:
			m.collectMetrics()
		}
	}
}

func (m *Monitor) collectMetrics() {
	m.mu.Lock()
	defer m.mu.Unlock()

	for _, topic := range m.topics {
		stats, err := m.pulsar.GetTopicStats(topic)
		if err != nil {
			continue
		}

		backlog := TopicBacklog{
			Topic:         topic,
			Subscription:  "default",
			BacklogSize:   stats.MsgBacklog,
			AvgMsgSize:    stats.AvgMsgSize,
			StorageSize:   stats.StorageSize,
			MsgRateIn:     stats.MsgRateIn,
			MsgRateOut:    stats.MsgRateOut,
			Timestamp:     time.Now(),
			ConsumerCount: stats.SubscriptionCount,
		}

		if backlog.AvgMsgSize > 0 {
			backlog.EffectiveBacklog = int64(float64(backlog.BacklogSize) * (backlog.AvgMsgSize / 1024.0))
		} else if backlog.StorageSize > 0 && backlog.BacklogSize > 0 {
			backlog.AvgMsgSize = float64(backlog.StorageSize) / float64(backlog.BacklogSize)
			backlog.EffectiveBacklog = int64(float64(backlog.BacklogSize) * (backlog.AvgMsgSize / 1024.0))
		} else {
			backlog.EffectiveBacklog = backlog.BacklogSize
		}

		key := topic + "-default"
		m.backlogs[key] = backlog

		if _, exists := m.history[key]; !exists {
			m.history[key] = make([]TopicBacklog, 0, 1000)
		}
		m.history[key] = append(m.history[key], backlog)
		if len(m.history[key]) > 1000 {
			m.history[key] = m.history[key][1:]
		}

		for _, handler := range m.handlers {
			go handler(backlog)
		}
	}
}

func (m *Monitor) GetCurrentBacklogs() map[string]TopicBacklog {
	m.mu.RLock()
	defer m.mu.RUnlock()
	result := make(map[string]TopicBacklog)
	for k, v := range m.backlogs {
		result[k] = v
	}
	return result
}

func (m *Monitor) GetBacklogHistory(topic, subscription string) []TopicBacklog {
	m.mu.RLock()
	defer m.mu.RUnlock()
	key := topic + "-" + subscription
	if history, exists := m.history[key]; exists {
		result := make([]TopicBacklog, len(history))
		copy(result, history)
		return result
	}
	return []TopicBacklog{}
}

func (m *Monitor) AddTopic(topic string) {
	m.mu.Lock()
	defer m.mu.Unlock()
	for _, t := range m.topics {
		if t == topic {
			return
		}
	}
	m.topics = append(m.topics, topic)
	m.audit.Log(audit.ActionAddTopic, topic, "Added topic to monitoring")
}

func (m *Monitor) RemoveTopic(topic string) {
	m.mu.Lock()
	defer m.mu.Unlock()
	for i, t := range m.topics {
		if t == topic {
			m.topics = append(m.topics[:i], m.topics[i+1:]...)
			break
		}
	}
	m.audit.Log(audit.ActionRemoveTopic, topic, "Removed topic from monitoring")
}

func (m *Monitor) GetTopics() []string {
	m.mu.RLock()
	defer m.mu.RUnlock()
	result := make([]string, len(m.topics))
	copy(result, m.topics)
	return result
}
