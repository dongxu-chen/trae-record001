package delay

import (
	"fmt"
	"sync"
	"time"

	"pulsar-backlog-manager/pkg/audit"
	"pulsar-backlog-manager/pkg/monitor"
	"pulsar-backlog-manager/pkg/strategy"
)

type SubscriptionPriority int

const (
	PriorityCore     SubscriptionPriority = iota + 1
	PriorityNormal
	PriorityNonCore
)

type subState struct {
	subscription string
	priority     SubscriptionPriority
	paused       bool
	pausedAt     time.Time
	resumedAt    time.Time
}

type DelayStats struct {
	Topic           string              `json:"topic"`
	PausedSubs      []string            `json:"paused_subscriptions"`
	ActiveSubs      []string            `json:"active_subscriptions"`
	TotalPauses     int64               `json:"total_pauses"`
	TotalResumes    int64               `json:"total_resumes"`
	Threshold       int64               `json:"threshold"`
	RecoveryThreshold int64             `json:"recovery_threshold"`
	CurrentBacklog  int64               `json:"current_backlog"`
	IsDegraded      bool                `json:"is_degraded"`
}

type DelayProcessor struct {
	strategy *strategy.Manager
	audit    *audit.AuditLogger
	topics   map[string]*topicDelayState
	mu       sync.Mutex
}

type topicDelayState struct {
	subscriptions   map[string]*subState
	isDegraded      bool
	totalPauses     int64
	totalResumes    int64
	threshold       int64
	recoveryThreshold int64
	lastChanged     time.Time
}

func NewDelayProcessor(strategyMgr *strategy.Manager, auditLog *audit.AuditLogger) *DelayProcessor {
	return &DelayProcessor{
		strategy: strategyMgr,
		audit:    auditLog,
		topics:   make(map[string]*topicDelayState),
	}
}

func (d *DelayProcessor) HandleBacklog(backlog monitor.TopicBacklog) {
	strategyCfg := d.strategy.GetStrategy(backlog.Topic)
	if strategyCfg == nil || !strategyCfg.DelayProcess.Enabled {
		return
	}

	d.mu.Lock()
	defer d.mu.Unlock()

	key := backlog.Topic
	state, exists := d.topics[key]
	if !exists {
		threshold := int64(strategyCfg.DelayProcess.BacklogThreshold)
		recovery := int64(strategyCfg.DelayProcess.RecoveryThreshold)
		if recovery == 0 {
			recovery = threshold / 2
		}
		state = &topicDelayState{
			subscriptions:     make(map[string]*subState),
			threshold:         threshold,
			recoveryThreshold: recovery,
		}

		for _, sub := range strategyCfg.DelayProcess.NonCoreSubscriptions {
			state.subscriptions[sub] = &subState{
				subscription: sub,
				priority:     PriorityNonCore,
				paused:       false,
			}
		}
		for _, sub := range strategyCfg.DelayProcess.CoreSubscriptions {
			state.subscriptions[sub] = &subState{
				subscription: sub,
				priority:     PriorityCore,
				paused:       false,
			}
		}

		if _, subExists := state.subscriptions[backlog.Subscription]; !subExists {
			state.subscriptions[backlog.Subscription] = &subState{
				subscription: backlog.Subscription,
				priority:     PriorityNormal,
				paused:       false,
			}
		}

		d.topics[key] = state
	}

	if time.Since(state.lastChanged) < 30*time.Second {
		return
	}

	if backlog.BacklogSize > state.threshold && !state.isDegraded {
		d.degradeNonCore(backlog.Topic, state)
	} else if backlog.BacklogSize < state.recoveryThreshold && state.isDegraded {
		d.resumeNonCore(backlog.Topic, state)
	}
}

func (d *DelayProcessor) degradeNonCore(topic string, state *topicDelayState) {
	state.isDegraded = true
	state.lastChanged = time.Now()

	for _, sub := range state.subscriptions {
		if sub.priority == PriorityNonCore && !sub.paused {
			sub.paused = true
			sub.pausedAt = time.Now()
			state.totalPauses++
			d.audit.Log(audit.ActionDelayPause, topic,
				"Paused non-core subscription [%s] due to backlog degradation (backlog > threshold)",
				sub.subscription)
		}
	}
}

func (d *DelayProcessor) resumeNonCore(topic string, state *topicDelayState) {
	state.isDegraded = false
	state.lastChanged = time.Now()

	for _, sub := range state.subscriptions {
		if sub.priority == PriorityNonCore && sub.paused {
			sub.paused = false
			sub.resumedAt = time.Now()
			state.totalResumes++
			d.audit.Log(audit.ActionDelayResume, topic,
				"Resumed non-core subscription [%s] - backlog recovered",
				sub.subscription)
		}
	}
}

func (d *DelayProcessor) RegisterSubscription(topic, subscription string, priority SubscriptionPriority) {
	d.mu.Lock()
	defer d.mu.Unlock()

	state, exists := d.topics[topic]
	if !exists {
		strategyCfg := d.strategy.GetStrategy(topic)
		threshold := int64(50000)
		recovery := int64(25000)
		if strategyCfg != nil && strategyCfg.DelayProcess.Enabled {
			threshold = int64(strategyCfg.DelayProcess.BacklogThreshold)
			recovery = int64(strategyCfg.DelayProcess.RecoveryThreshold)
			if recovery == 0 {
				recovery = threshold / 2
			}
		}
		state = &topicDelayState{
			subscriptions:     make(map[string]*subState),
			threshold:         threshold,
			recoveryThreshold: recovery,
		}
		d.topics[topic] = state
	}

	state.subscriptions[subscription] = &subState{
		subscription: subscription,
		priority:     priority,
		paused:       false,
	}

	priorityLabel := "normal"
	if priority == PriorityCore {
		priorityLabel = "core"
	} else if priority == PriorityNonCore {
		priorityLabel = "non-core"
	}
	d.audit.Log(audit.ActionDelayConfig, topic,
		"Registered subscription [%s] as %s priority", subscription, priorityLabel)
}

func (d *DelayProcessor) PauseSubscription(topic, subscription string) error {
	d.mu.Lock()
	defer d.mu.Unlock()

	state, exists := d.topics[topic]
	if !exists {
		return fmt.Errorf("topic %s not registered", topic)
	}

	sub, exists := state.subscriptions[subscription]
	if !exists {
		return fmt.Errorf("subscription %s not found", subscription)
	}

	if sub.paused {
		return fmt.Errorf("subscription %s already paused", subscription)
	}

	sub.paused = true
	sub.pausedAt = time.Now()
	state.totalPauses++
	d.audit.Log(audit.ActionDelayPause, topic,
		"Manually paused subscription [%s]", subscription)
	return nil
}

func (d *DelayProcessor) ResumeSubscription(topic, subscription string) error {
	d.mu.Lock()
	defer d.mu.Unlock()

	state, exists := d.topics[topic]
	if !exists {
		return fmt.Errorf("topic %s not registered", topic)
	}

	sub, exists := state.subscriptions[subscription]
	if !exists {
		return fmt.Errorf("subscription %s not found", subscription)
	}

	if !sub.paused {
		return fmt.Errorf("subscription %s not paused", subscription)
	}

	sub.paused = false
	sub.resumedAt = time.Now()
	state.totalResumes++
	d.audit.Log(audit.ActionDelayResume, topic,
		"Manually resumed subscription [%s]", subscription)
	return nil
}

func (d *DelayProcessor) IsSubscriptionPaused(topic, subscription string) bool {
	d.mu.Lock()
	defer d.mu.Unlock()

	state, exists := d.topics[topic]
	if !exists {
		return false
	}
	sub, exists := state.subscriptions[subscription]
	if !exists {
		return false
	}
	return sub.paused
}

func (d *DelayProcessor) GetStats(topic string) *DelayStats {
	d.mu.Lock()
	defer d.mu.Unlock()

	state, exists := d.topics[topic]
	if !exists {
		return nil
	}

	paused := make([]string, 0)
	active := make([]string, 0)
	for _, sub := range state.subscriptions {
		if sub.paused {
			paused = append(paused, sub.subscription)
		} else {
			active = append(active, sub.subscription)
		}
	}

	return &DelayStats{
		Topic:             topic,
		PausedSubs:        paused,
		ActiveSubs:        active,
		TotalPauses:       state.totalPauses,
		TotalResumes:      state.totalResumes,
		Threshold:         state.threshold,
		RecoveryThreshold: state.recoveryThreshold,
		IsDegraded:        state.isDegraded,
	}
}

func (d *DelayProcessor) GetAllStats() []*DelayStats {
	d.mu.Lock()
	defer d.mu.Unlock()

	result := make([]*DelayStats, 0, len(d.topics))
	for topic := range d.topics {
		state := d.topics[topic]
		paused := make([]string, 0)
		active := make([]string, 0)
		for _, sub := range state.subscriptions {
			if sub.paused {
				paused = append(paused, sub.subscription)
			} else {
				active = append(active, sub.subscription)
			}
		}
		result = append(result, &DelayStats{
			Topic:             topic,
			PausedSubs:        paused,
			ActiveSubs:        active,
			TotalPauses:       state.totalPauses,
			TotalResumes:      state.totalResumes,
			Threshold:         state.threshold,
			RecoveryThreshold: state.recoveryThreshold,
			IsDegraded:        state.isDegraded,
		})
	}
	return result
}
