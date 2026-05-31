package autoscaler

import (
	"context"
	"fmt"
	"sync"
	"time"

	"pulsar-backlog-manager/pkg/audit"
	"pulsar-backlog-manager/pkg/config"
	"pulsar-backlog-manager/pkg/monitor"
	"pulsar-backlog-manager/pkg/pulsar"
	"pulsar-backlog-manager/pkg/strategy"
)

type scaleDirection int

const (
	scaleNone scaleDirection = iota
	scaleUp
	scaleDown
)

type scaleState struct {
	currentCount int
	targetCount  int
	direction    scaleDirection
	lastAction   time.Time
}

type AutoScaler struct {
	config      config.AutoScalerConfig
	pulsar      *pulsar.Client
	strategy    *strategy.Manager
	audit       *audit.AuditLogger
	states      map[string]*scaleState
	mu          sync.Mutex
	coolDown    time.Duration
	stepInterval time.Duration
}

func NewAutoScaler(cfg config.AutoScalerConfig, pulsarClient *pulsar.Client, strategyMgr *strategy.Manager, auditLog *audit.AuditLogger) *AutoScaler {
	return &AutoScaler{
		config:       cfg,
		pulsar:       pulsarClient,
		strategy:     strategyMgr,
		audit:        auditLog,
		states:       make(map[string]*scaleState),
		coolDown:     10 * time.Second,
		stepInterval: 15 * time.Second,
	}
}

func (a *AutoScaler) HandleBacklog(backlog monitor.TopicBacklog) {
	if !a.config.Enabled {
		return
	}

	key := backlog.Topic + "-" + backlog.Subscription
	strategyCfg := a.strategy.GetStrategy(backlog.Topic)

	if strategyCfg != nil && !strategyCfg.AutoScale.Enabled {
		return
	}

	scaleUpThreshold := a.config.ScaleUpThreshold
	scaleDownThreshold := a.config.ScaleDownThreshold
	minConsumers := a.config.MinConsumers
	maxConsumers := a.config.MaxConsumers

	if strategyCfg != nil {
		scaleUpThreshold = int64(strategyCfg.AutoScale.ScaleUpThreshold)
		scaleDownThreshold = int64(strategyCfg.AutoScale.ScaleDownThreshold)
		minConsumers = strategyCfg.AutoScale.MinConsumers
		maxConsumers = strategyCfg.AutoScale.MaxConsumers
	}

	a.mu.Lock()
	defer a.mu.Unlock()

	state, exists := a.states[key]
	if !exists {
		state = &scaleState{
			currentCount: minConsumers,
			targetCount:  minConsumers,
			direction:    scaleNone,
			lastAction:   time.Now(),
		}
		a.states[key] = state
	}

	a.computeTarget(state, backlog.BacklogSize, scaleUpThreshold, scaleDownThreshold, minConsumers, maxConsumers)

	a.executeSmoothStep(key, backlog.Topic, backlog.Subscription, state)
}

func (a *AutoScaler) computeTarget(state *scaleState, backlogSize, scaleUpThreshold, scaleDownThreshold int64, minConsumers, maxConsumers int) {
	if backlogSize > scaleUpThreshold {
		pressureRatio := float64(backlogSize) / float64(scaleUpThreshold)
		increment := 1
		if pressureRatio > 4.0 {
			increment = 4
		} else if pressureRatio > 2.0 {
			increment = 2
		}
		newTarget := state.currentCount + increment
		if newTarget > maxConsumers {
			newTarget = maxConsumers
		}
		state.targetCount = newTarget
		state.direction = scaleUp
	} else if backlogSize < scaleDownThreshold && state.currentCount > minConsumers {
		newTarget := state.currentCount - 1
		if newTarget < minConsumers {
			newTarget = minConsumers
		}
		state.targetCount = newTarget
		state.direction = scaleDown
	} else {
		state.targetCount = state.currentCount
		state.direction = scaleNone
	}
}

func (a *AutoScaler) executeSmoothStep(key, topic, subscription string, state *scaleState) {
	if state.currentCount == state.targetCount {
		return
	}

	interval := a.stepInterval
	if state.direction == scaleDown {
		interval = a.coolDown
	}

	if time.Since(state.lastAction) < interval {
		return
	}

	if state.direction == scaleUp && state.currentCount < state.targetCount {
		consumerName := fmt.Sprintf("auto-consumer-%d", state.currentCount+1)
		_, err := a.pulsar.CreateConsumer(topic, subscription, consumerName)
		if err != nil {
			a.audit.Log(audit.ActionScaleUp, topic, "Failed to add consumer %s: %v", consumerName, err)
			return
		}
		state.currentCount++
		state.lastAction = time.Now()
		a.audit.Log(audit.ActionScaleUp, topic,
			"Smooth scale up: added consumer %s (now %d, target %d)",
			consumerName, state.currentCount, state.targetCount)

		if state.currentCount < state.targetCount {
			go a.scheduleNextStep(key, topic, subscription)
		}
	} else if state.direction == scaleDown && state.currentCount > state.targetCount {
		consumerName := fmt.Sprintf("auto-consumer-%d", state.currentCount)
		a.pulsar.RemoveConsumer(topic, subscription, consumerName)
		state.currentCount--
		state.lastAction = time.Now()
		a.audit.Log(audit.ActionScaleDown, topic,
			"Smooth scale down: removed consumer %s (now %d, target %d)",
			consumerName, state.currentCount, state.targetCount)
	}
}

func (a *AutoScaler) scheduleNextStep(key, topic, subscription string) {
	time.Sleep(a.stepInterval)

	a.mu.Lock()
	defer a.mu.Unlock()

	state, exists := a.states[key]
	if !exists || state.direction != scaleUp || state.currentCount >= state.targetCount {
		return
	}

	consumerName := fmt.Sprintf("auto-consumer-%d", state.currentCount+1)
	_, err := a.pulsar.CreateConsumer(topic, subscription, consumerName)
	if err != nil {
		a.audit.Log(audit.ActionScaleUp, topic, "Failed to add consumer %s: %v", consumerName, err)
		return
	}
	state.currentCount++
	state.lastAction = time.Now()
	a.audit.Log(audit.ActionScaleUp, topic,
		"Smooth scale up: added consumer %s (now %d, target %d)",
		consumerName, state.currentCount, state.targetCount)

	if state.currentCount < state.targetCount {
		go a.scheduleNextStep(key, topic, subscription)
	}
}

func (a *AutoScaler) StartSmoothScaler(ctx context.Context) {
	ticker := time.NewTicker(30 * time.Second)
	defer ticker.Stop()

	for {
		select {
		case <-ctx.Done():
			return
		case <-ticker.C:
			a.cleanupStaleTargets()
		}
	}
}

func (a *AutoScaler) cleanupStaleTargets() {
	a.mu.Lock()
	defer a.mu.Unlock()

	now := time.Now()
	for key, state := range a.states {
		if state.direction == scaleUp && now.Sub(state.lastAction) > 5*time.Minute {
			state.targetCount = state.currentCount
			state.direction = scaleNone
		}
		if state.direction == scaleDown && now.Sub(state.lastAction) > 3*time.Minute {
			state.targetCount = state.currentCount
			state.direction = scaleNone
		}
		_ = key
	}
}

func (a *AutoScaler) SetConsumerCount(topic, subscription string, count int) error {
	key := topic + "-" + subscription
	a.mu.Lock()
	defer a.mu.Unlock()

	state, exists := a.states[key]
	if !exists {
		state = &scaleState{
			currentCount: 0,
			targetCount:  0,
			direction:    scaleNone,
			lastAction:   time.Now(),
		}
		a.states[key] = state
	}

	currentCount := state.currentCount

	if count > currentCount {
		for i := currentCount; i < count; i++ {
			consumerName := fmt.Sprintf("manual-consumer-%d", i+1)
			_, err := a.pulsar.CreateConsumer(topic, subscription, consumerName)
			if err != nil {
				return err
			}
		}
	} else if count < currentCount {
		for i := currentCount; i > count; i-- {
			consumerName := fmt.Sprintf("manual-consumer-%d", i)
			a.pulsar.RemoveConsumer(topic, subscription, consumerName)
		}
	}

	state.currentCount = count
	state.targetCount = count
	state.direction = scaleNone
	state.lastAction = time.Now()
	a.audit.Log(audit.ActionManualScale, topic, "Manually set consumer count to %d", count)
	return nil
}

func (a *AutoScaler) GetConsumerCount(topic, subscription string) int {
	a.mu.Lock()
	defer a.mu.Unlock()
	key := topic + "-" + subscription
	if state, exists := a.states[key]; exists {
		return state.currentCount
	}
	return 0
}

func (a *AutoScaler) GetScaleState(topic, subscription string) (current int, target int, direction scaleDirection) {
	a.mu.Lock()
	defer a.mu.Unlock()
	key := topic + "-" + subscription
	if state, exists := a.states[key]; exists {
		return state.currentCount, state.targetCount, state.direction
	}
	return 0, 0, scaleNone
}
