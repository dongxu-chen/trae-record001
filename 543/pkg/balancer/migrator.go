package balancer

import (
	"context"
	"fmt"
	"sort"
	"strings"
	"sync"
	"time"

	"rabbitmq-lb/pkg/config"
	"rabbitmq-lb/pkg/monitor"
	"rabbitmq-lb/pkg/predictor"
	"rabbitmq-lb/pkg/rabbitmq"
)

type MigrationPlan struct {
	QueueName     string
	Vhost         string
	SourceNode    string
	TargetNode    string
	Priority      int
	Reason        string
	Messages      int64
	Memory        int64
	EstimatedTime time.Duration
	TrafficRate   float64
	Urgent        bool
}

type Migrator struct {
	client           *rabbitmq.Client
	config           *config.BalancerConfig
	mu               sync.Mutex
	lastMigrations   map[string]time.Time
	inProgress       map[string]bool
	migrationHistory []MigrationRecord
	pausedConsumers  map[string]bool
	rebalanceChan    chan struct{}
	ctx              context.Context
	cancel           context.CancelFunc
}

type MigrationRecord struct {
	Timestamp  time.Time
	QueueName  string
	Vhost      string
	SourceNode string
	TargetNode string
	Success    bool
	Duration   time.Duration
	Error      string
}

func NewMigrator(client *rabbitmq.Client, cfg *config.BalancerConfig) *Migrator {
	ctx, cancel := context.WithCancel(context.Background())
	return &Migrator{
		client:          client,
		config:          cfg,
		lastMigrations:  make(map[string]time.Time),
		inProgress:      make(map[string]bool),
		migrationHistory: make([]MigrationRecord, 0),
		pausedConsumers: make(map[string]bool),
		rebalanceChan:   make(chan struct{}, 10),
		ctx:             ctx,
		cancel:          cancel,
	}
}

func (m *Migrator) TriggerRebalance() {
	select {
	case m.rebalanceChan <- struct{}{}:
	default:
	}
}

func (m *Migrator) GetRebalanceChannel() <-chan struct{} {
	return m.rebalanceChan
}

func (m *Migrator) Stop() {
	m.cancel()
}

func (m *Migrator) GenerateMigrationPlans(
	state *monitor.ClusterState,
	predictions map[string]*predictor.PredictionResult,
	burstQueues map[string]bool,
) []MigrationPlan {
	m.mu.Lock()
	defer m.mu.Unlock()

	if len(state.Nodes) < 2 {
		return nil
	}

	runningNodes := make([]*monitor.NodeState, 0)
	for _, node := range state.Nodes {
		if node.Running {
			runningNodes = append(runningNodes, node)
		}
	}

	if len(runningNodes) < 2 {
		return nil
	}

	avgLoad := calculateAverageLoad(runningNodes)

	overloadedNodes := make([]*monitor.NodeState, 0)
	underloadedNodes := make([]*monitor.NodeState, 0)

	for _, node := range runningNodes {
		loadRatio := node.LoadScore / avgLoad
		if loadRatio > (1 + m.config.RebalanceThreshold) {
			overloadedNodes = append(overloadedNodes, node)
		} else if loadRatio < (1 - m.config.RebalanceThreshold) {
			underloadedNodes = append(underloadedNodes, node)
		}
	}

	if len(overloadedNodes) == 0 || len(underloadedNodes) == 0 {
		return nil
	}

	var plans []MigrationPlan

	for _, overNode := range overloadedNodes {
		queuesOnNode := m.getQueuesOnNode(state, overNode.Name)

		sort.Slice(queuesOnNode, func(i, j int) bool {
			return queuesOnNode[i].Messages > queuesOnNode[j].Messages
		})

		for _, queue := range queuesOnNode {
			if m.shouldExcludeQueue(queue) {
				continue
			}

			if m.isInCooldown(queue.Name, queue.Vhost) {
				continue
			}

			queueKey := queue.Vhost + ":" + queue.Name
			if burstQueues != nil && burstQueues[queueKey] {
				continue
			}

			if !m.isWithinMigrationWindow() {
				continue
			}

			if !m.isLowTraffic(queue) {
				continue
			}

			targetNode := m.selectTargetNode(underloadedNodes, queue)
			if targetNode == nil {
				continue
			}

			plan := MigrationPlan{
				QueueName:     queue.Name,
				Vhost:         queue.Vhost,
				SourceNode:    overNode.Name,
				TargetNode:    targetNode.Name,
				Priority:      m.calculatePriority(queue, predictions),
				Reason:        fmt.Sprintf("Overloaded node %s (load: %.2f)", overNode.Name, overNode.LoadScore),
				Messages:      queue.Messages,
				Memory:        queue.Memory,
				EstimatedTime: m.estimateMigrationTime(queue),
				TrafficRate:   queue.MessageStats.PublishDetails.Rate,
				Urgent:        false,
			}

			plans = append(plans, plan)

			if len(plans) >= m.config.MaxMigrationsPerCycle {
				return plans
			}
		}
	}

	sort.Slice(plans, func(i, j int) bool {
		return plans[i].Priority > plans[j].Priority
	})

	return plans
}

func (m *Migrator) GenerateFailureRecoveryPlans(
	state *monitor.ClusterState,
	failedNodes []string,
	burstQueues map[string]bool,
) []MigrationPlan {
	m.mu.Lock()
	defer m.mu.Unlock()

	if len(failedNodes) == 0 {
		return nil
	}

	runningNodes := make([]*monitor.NodeState, 0)
	for _, node := range state.Nodes {
		if node.Running {
			runningNodes = append(runningNodes, node)
		}
	}

	if len(runningNodes) == 0 {
		return nil
	}

	var plans []MigrationPlan

	for _, failedNode := range failedNodes {
		queuesOnFailedNode := m.getQueuesOnNode(state, failedNode)

		for _, queue := range queuesOnFailedNode {
			if m.shouldExcludeQueue(queue) {
				continue
			}

			queueKey := queue.Vhost + ":" + queue.Name
			if burstQueues != nil && burstQueues[queueKey] {
				continue
			}

			targetNode := m.selectTargetNode(runningNodes, queue)
			if targetNode == nil {
				continue
			}

			plan := MigrationPlan{
				QueueName:     queue.Name,
				Vhost:         queue.Vhost,
				SourceNode:    failedNode,
				TargetNode:    targetNode.Name,
				Priority:      100,
				Reason:        fmt.Sprintf("Node failure recovery: %s", failedNode),
				Messages:      queue.Messages,
				Memory:        queue.Memory,
				EstimatedTime: m.estimateMigrationTime(queue),
				TrafficRate:   queue.MessageStats.PublishDetails.Rate,
				Urgent:        true,
			}

			plans = append(plans, plan)
		}
	}

	return plans
}

func (m *Migrator) ExecuteMigration(plan MigrationPlan) error {
	m.mu.Lock()
	key := plan.Vhost + ":" + plan.QueueName
	if m.inProgress[key] {
		m.mu.Unlock()
		return fmt.Errorf("migration already in progress for queue %s", plan.QueueName)
	}
	m.inProgress[key] = true
	m.mu.Unlock()

	defer func() {
		m.mu.Lock()
		delete(m.inProgress, key)
		m.mu.Unlock()
	}()

	startTime := time.Now()

	var migrationErr error
	if !m.config.DryRun {
		migrationErr = m.performSafeMigration(plan)
	}

	duration := time.Since(startTime)

	record := MigrationRecord{
		Timestamp:  time.Now(),
		QueueName:  plan.QueueName,
		Vhost:      plan.Vhost,
		SourceNode: plan.SourceNode,
		TargetNode: plan.TargetNode,
		Success:    migrationErr == nil,
		Duration:   duration,
	}

	if migrationErr != nil {
		record.Error = migrationErr.Error()
	} else {
		m.mu.Lock()
		m.lastMigrations[key] = time.Now()
		m.mu.Unlock()
	}

	m.mu.Lock()
	m.migrationHistory = append(m.migrationHistory, record)
	if len(m.migrationHistory) > 1000 {
		m.migrationHistory = m.migrationHistory[1:]
	}
	m.mu.Unlock()

	return migrationErr
}

func (m *Migrator) performSafeMigration(plan MigrationPlan) error {
	hasConsumers := plan.Messages > 0 || plan.TrafficRate > 0

	if hasConsumers {
		if err := m.client.PauseQueueConsumers(plan.Vhost, plan.QueueName); err != nil {
			return fmt.Errorf("pause consumers failed: %w", err)
		}

		m.mu.Lock()
		m.pausedConsumers[plan.Vhost+":"+plan.QueueName] = true
		m.mu.Unlock()

		time.Sleep(1 * time.Second)
	}

	if err := m.client.SetQueueMasterLocation(plan.Vhost, plan.QueueName, plan.TargetNode); err != nil {
		if hasConsumers {
			m.client.ResumeQueueConsumers(plan.Vhost, plan.QueueName)
			m.mu.Lock()
			delete(m.pausedConsumers, plan.Vhost+":"+plan.QueueName)
			m.mu.Unlock()
		}
		return fmt.Errorf("set master location failed: %w", err)
	}

	migrationTimeout := m.estimateMigrationTime(plan) * 3
	if migrationTimeout < 30*time.Second {
		migrationTimeout = 30 * time.Second
	}
	if migrationTimeout > 10*time.Minute {
		migrationTimeout = 10 * time.Minute
	}

	syncCtx, cancel := context.WithTimeout(m.ctx, migrationTimeout)
	defer cancel()

	if err := m.waitForQueueMigration(syncCtx, plan); err != nil {
		if hasConsumers {
			m.client.ResumeQueueConsumers(plan.Vhost, plan.QueueName)
			m.mu.Lock()
			delete(m.pausedConsumers, plan.Vhost+":"+plan.QueueName)
			m.mu.Unlock()
		}
		return fmt.Errorf("queue migration timeout: %w", err)
	}

	if hasConsumers {
		if err := m.client.ResumeQueueConsumers(plan.Vhost, plan.QueueName); err != nil {
			return fmt.Errorf("resume consumers failed: %w", err)
		}

		m.mu.Lock()
		delete(m.pausedConsumers, plan.Vhost+":"+plan.QueueName)
		m.mu.Unlock()
	}

	if err := m.client.RemoveQueueMasterLocationPolicy(plan.Vhost, plan.QueueName); err != nil {
	}

	return nil
}

func (m *Migrator) waitForQueueMigration(ctx context.Context, plan MigrationPlan) error {
	ticker := time.NewTicker(500 * time.Millisecond)
	defer ticker.Stop()

	for {
		select {
		case <-ctx.Done():
			return ctx.Err()
		case <-ticker.C:
			onNode, err := m.client.IsQueueOnNode(plan.Vhost, plan.QueueName, plan.TargetNode)
			if err != nil {
				continue
			}
			if onNode {
				return nil
			}
		}
	}
}

func (m *Migrator) getQueuesOnNode(state *monitor.ClusterState, nodeName string) []rabbitmq.Queue {
	var queues []rabbitmq.Queue
	for _, queue := range state.Queues {
		if queue.Node == nodeName {
			queues = append(queues, queue)
		}
	}
	return queues
}

func (m *Migrator) shouldExcludeQueue(queue rabbitmq.Queue) bool {
	if queue.Messages > m.config.MaxQueueSize {
		return true
	}

	if queue.Messages < m.config.MinMessagesPerQueue {
		return true
	}

	for _, excludeQueue := range m.config.ExcludeQueues {
		if matched, _ := matchPattern(excludeQueue, queue.Name); matched {
			return true
		}
	}

	for _, excludeVhost := range m.config.ExcludeVhosts {
		if matched, _ := matchPattern(excludeVhost, queue.Vhost); matched {
			return true
		}
	}

	return false
}

func (m *Migrator) isInCooldown(queueName, vhost string) bool {
	key := vhost + ":" + queueName
	lastMigrated, exists := m.lastMigrations[key]
	if !exists {
		return false
	}
	return time.Since(lastMigrated) < m.config.MigrationCooldown
}

func (m *Migrator) isWithinMigrationWindow() bool {
	if m.config.MigrationWindowStart == "" || m.config.MigrationWindowEnd == "" {
		return true
	}

	now := time.Now()
	currentTime := now.Hour()*60 + now.Minute()

	startTime := parseTimeToMinutes(m.config.MigrationWindowStart)
	endTime := parseTimeToMinutes(m.config.MigrationWindowEnd)

	if startTime < endTime {
		return currentTime >= startTime && currentTime <= endTime
	}
	return currentTime >= startTime || currentTime <= endTime
}

func (m *Migrator) isLowTraffic(queue rabbitmq.Queue) bool {
	rate := queue.MessageStats.PublishDetails.Rate
	return rate <= m.config.LowTrafficThreshold
}

func (m *Migrator) selectTargetNode(nodes []*monitor.NodeState, queue rabbitmq.Queue) *monitor.NodeState {
	if len(nodes) == 0 {
		return nil
	}

	sort.Slice(nodes, func(i, j int) bool {
		return nodes[i].LoadScore < nodes[j].LoadScore
	})

	return nodes[0]
}

func (m *Migrator) calculatePriority(queue rabbitmq.Queue, predictions map[string]*predictor.PredictionResult) int {
	priority := 50

	key := queue.Vhost + ":" + queue.Name
	if pred, exists := predictions[key]; exists {
		if pred.Trend == "increasing" && pred.Confidence > 0.7 {
			priority += 30
		}
	}

	if queue.Messages > m.config.MinMessagesPerQueue*10 {
		priority += 20
	}

	if queue.Consumers == 0 {
		priority -= 10
	}

	return priority
}

func (m *Migrator) estimateMigrationTime(queue rabbitmq.Queue) time.Duration {
	if queue.Messages == 0 {
		return time.Second * 5
	}

	msgsPerSec := float64(1000)
	estimatedSeconds := float64(queue.Messages) / msgsPerSec
	return time.Duration(estimatedSeconds*1000) * time.Millisecond
}

func (m *Migrator) GetMigrationHistory() []MigrationRecord {
	m.mu.Lock()
	defer m.mu.Unlock()

	history := make([]MigrationRecord, len(m.migrationHistory))
	copy(history, m.migrationHistory)
	return history
}

func (m *Migrator) IsConsumerPaused(vhost, queueName string) bool {
	m.mu.Lock()
	defer m.mu.Unlock()
	return m.pausedConsumers[vhost+":"+queueName]
}

func (m *Migrator) GetPausedConsumersCount() int {
	m.mu.Lock()
	defer m.mu.Unlock()
	return len(m.pausedConsumers)
}

func calculateAverageLoad(nodes []*monitor.NodeState) float64 {
	if len(nodes) == 0 {
		return 0
	}

	var totalLoad float64
	for _, node := range nodes {
		totalLoad += node.LoadScore
	}
	return totalLoad / float64(len(nodes))
}

func matchPattern(pattern, str string) (bool, error) {
	if pattern == str {
		return true, nil
	}

	if strings.Contains(pattern, "*") {
		parts := strings.Split(pattern, "*")
		if len(parts) == 2 {
			if parts[0] == "" {
				return strings.HasSuffix(str, parts[1]), nil
			}
			if parts[1] == "" {
				return strings.HasPrefix(str, parts[0]), nil
			}
			return strings.HasPrefix(str, parts[0]) && strings.HasSuffix(str, parts[1]), nil
		}
	}

	return false, nil
}

func parseTimeToMinutes(timeStr string) int {
	var hour, minute int
	fmt.Sscanf(timeStr, "%d:%d", &hour, &minute)
	return hour*60 + minute
}
