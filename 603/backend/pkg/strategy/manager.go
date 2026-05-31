package strategy

import (
	"sync"

	"pulsar-backlog-manager/pkg/audit"
	"pulsar-backlog-manager/pkg/config"
)

type AutoScaleStrategy struct {
	Enabled            bool
	MinConsumers       int
	MaxConsumers       int
	ScaleUpThreshold   int
	ScaleDownThreshold int
}

type PartitionStrategy struct {
	Enabled            bool
	MinPartitions      int
	MaxPartitions      int
	ScaleUpThreshold   int
	ScaleDownThreshold int
}

type RateLimitStrategy struct {
	Enabled              bool
	MaxRate              int
	BacklogThreshold     int
	RecoveryThreshold    int
	TopicBacklogThreshold int
}

type PredictionStrategy struct {
	Enabled        bool
	AlertThreshold int
}

type DeadLetterStrategy struct {
	Enabled         bool
	MaxRedeliveries int
	DLQTopic        string
	RetryTopic      string
}

type ReplayStrategy struct {
	Enabled      bool
	MaxMessages  int
	TargetTopic  string
}

type DelayProcessStrategy struct {
	Enabled              bool
	BacklogThreshold     int
	RecoveryThreshold    int
	CoreSubscriptions    []string
	NonCoreSubscriptions []string
}

type Strategy struct {
	TopicName   string
	AutoScale   AutoScaleStrategy
	Partition   PartitionStrategy
	RateLimit   RateLimitStrategy
	Prediction  PredictionStrategy
	DeadLetter  DeadLetterStrategy
	Replay      ReplayStrategy
	DelayProcess DelayProcessStrategy
	Priority    int
}

type Manager struct {
	config   *config.Config
	audit    *audit.AuditLogger
	strategies map[string]*Strategy
	mu       sync.RWMutex
}

func NewManager(cfg *config.Config, auditLog *audit.AuditLogger) *Manager {
	mgr := &Manager{
		config:     cfg,
		audit:      auditLog,
		strategies: make(map[string]*Strategy),
	}

	mgr.strategies["default"] = &Strategy{
		TopicName: "default",
		AutoScale: AutoScaleStrategy{
			Enabled:            cfg.AutoScaler.Enabled,
			MinConsumers:       cfg.AutoScaler.MinConsumers,
			MaxConsumers:       cfg.AutoScaler.MaxConsumers,
			ScaleUpThreshold:   int(cfg.AutoScaler.ScaleUpThreshold),
			ScaleDownThreshold: int(cfg.AutoScaler.ScaleDownThreshold),
		},
		Partition: PartitionStrategy{
			Enabled:            true,
			MinPartitions:      1,
			MaxPartitions:      32,
			ScaleUpThreshold:   50000,
			ScaleDownThreshold: 5000,
		},
		RateLimit: RateLimitStrategy{
			Enabled:               cfg.RateLimiter.Enabled,
			MaxRate:               int(cfg.RateLimiter.MaxRate),
			BacklogThreshold:      100000,
			RecoveryThreshold:     10000,
			TopicBacklogThreshold: 50000,
		},
		Prediction: PredictionStrategy{
			Enabled:        cfg.Prediction.Enabled,
			AlertThreshold: 100000,
		},
		DeadLetter: DeadLetterStrategy{
			Enabled:         true,
			MaxRedeliveries: 3,
			DLQTopic:        "",
			RetryTopic:      "",
		},
		Replay: ReplayStrategy{
			Enabled:     true,
			MaxMessages: 1000,
			TargetTopic: "",
		},
		DelayProcess: DelayProcessStrategy{
			Enabled:              true,
			BacklogThreshold:     50000,
			RecoveryThreshold:    25000,
			CoreSubscriptions:    []string{},
			NonCoreSubscriptions: []string{},
		},
		Priority: 0,
	}

	return mgr
}

func (m *Manager) GetStrategy(topic string) *Strategy {
	m.mu.RLock()
	defer m.mu.RUnlock()

	if strategy, exists := m.strategies[topic]; exists {
		return strategy
	}
	return m.strategies["default"]
}

func (m *Manager) SetStrategy(strategy *Strategy) {
	m.mu.Lock()
	defer m.mu.Unlock()

	m.strategies[strategy.TopicName] = strategy
	m.audit.Log(audit.ActionUpdateStrategy, strategy.TopicName, "Updated strategy configuration")
}

func (m *Manager) DeleteStrategy(topic string) {
	m.mu.Lock()
	defer m.mu.Unlock()

	if topic == "default" {
		return
	}
	delete(m.strategies, topic)
	m.audit.Log(audit.ActionDeleteStrategy, topic, "Deleted strategy configuration")
}

func (m *Manager) GetAllStrategies() map[string]*Strategy {
	m.mu.RLock()
	defer m.mu.RUnlock()

	result := make(map[string]*Strategy)
	for k, v := range m.strategies {
		result[k] = v
	}
	return result
}
