package partition

import (
	"sync"
	"time"

	"pulsar-backlog-manager/pkg/audit"
	"pulsar-backlog-manager/pkg/monitor"
	"pulsar-backlog-manager/pkg/pulsar"
	"pulsar-backlog-manager/pkg/strategy"
)

type Manager struct {
	pulsar       *pulsar.Client
	strategy     *strategy.Manager
	audit        *audit.AuditLogger
	partitions   map[string]int
	lastChanged  map[string]time.Time
	mu           sync.Mutex
}

func NewManager(pulsarClient *pulsar.Client, strategyMgr *strategy.Manager, auditLog *audit.AuditLogger) *Manager {
	return &Manager{
		pulsar:      pulsarClient,
		strategy:    strategyMgr,
		audit:       auditLog,
		partitions:  make(map[string]int),
		lastChanged: make(map[string]time.Time),
	}
}

func (m *Manager) HandleBacklog(backlog monitor.TopicBacklog) {
	strategyCfg := m.strategy.GetStrategy(backlog.Topic)
	if strategyCfg == nil || !strategyCfg.Partition.Enabled {
		return
	}

	m.mu.Lock()
	defer m.mu.Unlock()

	if lastChanged, exists := m.lastChanged[backlog.Topic]; exists && time.Since(lastChanged) < 5*time.Minute {
		return
	}

	currentPartitions := m.partitions[backlog.Topic]
	if currentPartitions == 0 {
		currentPartitions = strategyCfg.Partition.MinPartitions
		m.partitions[backlog.Topic] = currentPartitions
	}

	avgBacklogPerPartition := backlog.BacklogSize / int64(currentPartitions)

	if avgBacklogPerPartition > int64(strategyCfg.Partition.ScaleUpThreshold) &&
		currentPartitions < strategyCfg.Partition.MaxPartitions {
		m.scaleUp(backlog.Topic, currentPartitions, strategyCfg.Partition.MaxPartitions)
	} else if avgBacklogPerPartition < int64(strategyCfg.Partition.ScaleDownThreshold) &&
		currentPartitions > strategyCfg.Partition.MinPartitions {
		m.scaleDown(backlog.Topic, currentPartitions, strategyCfg.Partition.MinPartitions)
	}
}

func (m *Manager) scaleUp(topic string, current, max int) {
	target := current * 2
	if target > max {
		target = max
	}

	m.partitions[topic] = target
	m.lastChanged[topic] = time.Now()
	m.audit.Log(audit.ActionPartitionUp, topic, "Increased partitions from %d to %d", current, target)
}

func (m *Manager) scaleDown(topic string, current, min int) {
	target := current / 2
	if target < min {
		target = min
	}

	m.partitions[topic] = target
	m.lastChanged[topic] = time.Now()
	m.audit.Log(audit.ActionPartitionDown, topic, "Decreased partitions from %d to %d", current, target)
}

func (m *Manager) SetPartitionCount(topic string, count int) {
	m.mu.Lock()
	defer m.mu.Unlock()
	m.partitions[topic] = count
	m.lastChanged[topic] = time.Now()
	m.audit.Log(audit.ActionManualPartition, topic, "Manually set partition count to %d", count)
}

func (m *Manager) GetPartitionCount(topic string) int {
	m.mu.Lock()
	defer m.mu.Unlock()
	return m.partitions[topic]
}
