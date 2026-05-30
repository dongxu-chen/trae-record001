package canary

import (
	"context"
	"fmt"
	"sync"
	"time"

	"mesh-security-platform/internal/models"
)

type CanaryStrategy string

const (
	StrategyLinear     CanaryStrategy = "linear"
	StrategyCanary     CanaryStrategy = "canary"
	StrategyBlueGreen  CanaryStrategy = "bluegreen"
)

type DeploymentStatus string

const (
	StatusPending     DeploymentStatus = "pending"
	StatusProgressing DeploymentStatus = "progressing"
	StatusPaused      DeploymentStatus = "paused"
	StatusPromoted    DeploymentStatus = "promoted"
	StatusRolledBack  DeploymentStatus = "rolled_back"
	StatusFailed      DeploymentStatus = "failed"
)

type CanaryDeployment struct {
	ID             string
	PolicyID       string
	Policy         *models.Policy
	Strategy       CanaryStrategy
	TrafficPercent int
	Status         DeploymentStatus
	StartTime      time.Time
	UpdateTime     time.Time
	Duration       string
	Metrics        *models.CanaryMetrics
	Stages         []CanaryStage
	CurrentStage   int
	CancelFunc     context.CancelFunc
	mu             sync.RWMutex
}

type CanaryStage struct {
	TrafficPercent int
	Duration       time.Duration
	Status         DeploymentStatus
	StartTime      time.Time
}

type Manager struct {
	deployments map[string]*CanaryDeployment
	mu          sync.RWMutex
	metricsChan chan *models.CanaryMetrics
}

func NewManager() *Manager {
	return &Manager{
		deployments: make(map[string]*CanaryDeployment),
		metricsChan: make(chan *models.CanaryMetrics, 100),
	}
}

func (m *Manager) StartCanaryDeployment(policy *models.Policy, strategy CanaryStrategy, duration string) (*models.CanaryDeployment, error) {
	m.mu.Lock()
	defer m.mu.Unlock()

	if _, exists := m.deployments[policy.ID]; exists {
		return nil, fmt.Errorf("canary deployment already exists for policy %s", policy.ID)
	}

	stages := m.generateStages(strategy, duration)

	ctx, cancel := context.WithCancel(context.Background())

	deployment := &CanaryDeployment{
		ID:             generateDeploymentID(policy.ID),
		PolicyID:       policy.ID,
		Policy:         policy,
		Strategy:       strategy,
		TrafficPercent: 0,
		Status:         StatusPending,
		StartTime:      time.Now(),
		UpdateTime:     time.Now(),
		Duration:       duration,
		Stages:         stages,
		CurrentStage:   0,
		CancelFunc:     cancel,
	}

	m.deployments[policy.ID] = deployment

	go m.runCanaryDeployment(ctx, deployment)

	return m.toAPIModel(deployment), nil
}

func (m *Manager) generateStages(strategy CanaryStrategy, duration string) []CanaryStage {
	totalDuration, _ := time.ParseDuration(duration)
	if totalDuration == 0 {
		totalDuration = 30 * time.Minute
	}

	var stages []CanaryStage

	switch strategy {
	case StrategyLinear:
		steps := 10
		stageDuration := totalDuration / time.Duration(steps)
		for i := 1; i <= steps; i++ {
			stages = append(stages, CanaryStage{
				TrafficPercent: i * 10,
				Duration:       stageDuration,
				Status:         StatusPending,
			})
		}

	case StrategyCanary:
		stages = []CanaryStage{
			{TrafficPercent: 5, Duration: totalDuration * 2 / 10, Status: StatusPending},
			{TrafficPercent: 25, Duration: totalDuration * 2 / 10, Status: StatusPending},
			{TrafficPercent: 50, Duration: totalDuration * 2 / 10, Status: StatusPending},
			{TrafficPercent: 75, Duration: totalDuration * 2 / 10, Status: StatusPending},
			{TrafficPercent: 100, Duration: totalDuration * 2 / 10, Status: StatusPending},
		}

	case StrategyBlueGreen:
		stages = []CanaryStage{
			{TrafficPercent: 0, Duration: totalDuration / 2, Status: StatusPending},
			{TrafficPercent: 100, Duration: totalDuration / 2, Status: StatusPending},
		}

	default:
		stages = []CanaryStage{
			{TrafficPercent: 100, Duration: totalDuration, Status: StatusPending},
		}
	}

	return stages
}

func (m *Manager) runCanaryDeployment(ctx context.Context, deployment *CanaryDeployment) {
	deployment.mu.Lock()
	deployment.Status = StatusProgressing
	deployment.mu.Unlock()

	for i := range deployment.Stages {
		select {
		case <-ctx.Done():
			deployment.mu.Lock()
			deployment.Status = StatusRolledBack
			deployment.mu.Unlock()
			return
		default:
		}

		deployment.mu.Lock()
		deployment.CurrentStage = i
		deployment.TrafficPercent = deployment.Stages[i].TrafficPercent
		deployment.Stages[i].Status = StatusProgressing
		deployment.Stages[i].StartTime = time.Now()
		deployment.UpdateTime = time.Now()
		deployment.mu.Unlock()

		stageTimer := time.NewTimer(deployment.Stages[i].Duration)
		metricsTicker := time.NewTicker(10 * time.Second)

	stageLoop:
		for {
			select {
			case <-ctx.Done():
				stageTimer.Stop()
				metricsTicker.Stop()
				return
			case <-stageTimer.C:
				stageTimer.Stop()
				metricsTicker.Stop()
				break stageLoop
			case <-metricsTicker.C:
				metrics := m.collectMetrics(deployment)
				deployment.mu.Lock()
				deployment.Metrics = metrics
				deployment.mu.Unlock()

				if !m.checkHealth(metrics) {
					deployment.mu.Lock()
					deployment.Status = StatusFailed
					deployment.mu.Unlock()
					m.rollback(deployment)
					stageTimer.Stop()
					metricsTicker.Stop()
					return
				}
			}
		}

		deployment.mu.Lock()
		deployment.Stages[i].Status = StatusPromoted
		deployment.mu.Unlock()
	}

	deployment.mu.Lock()
	deployment.Status = StatusPromoted
	deployment.TrafficPercent = 100
	deployment.UpdateTime = time.Now()
	deployment.mu.Unlock()
}

func (m *Manager) collectMetrics(deployment *CanaryDeployment) *models.CanaryMetrics {
	return &models.CanaryMetrics{
		SuccessRate: 99.5,
		LatencyP95:   150.0,
		ErrorRate:    0.005,
		Throughput:   1000.0,
	}
}

func (m *Manager) checkHealth(metrics *models.CanaryMetrics) bool {
	if metrics.ErrorRate > 0.05 {
		return false
	}
	if metrics.SuccessRate < 95.0 {
		return false
	}
	return true
}

func (m *Manager) rollback(deployment *CanaryDeployment) {
	deployment.mu.Lock()
	defer deployment.mu.Unlock()
	deployment.TrafficPercent = 0
	deployment.Status = StatusRolledBack
	deployment.UpdateTime = time.Now()
}

func (m *Manager) GetDeployment(policyID string) (*models.CanaryDeployment, bool) {
	m.mu.RLock()
	defer m.mu.RUnlock()

	deployment, exists := m.deployments[policyID]
	if !exists {
		return nil, false
	}
	return m.toAPIModel(deployment), true
}

func (m *Manager) ListDeployments() []*models.CanaryDeployment {
	m.mu.RLock()
	defer m.mu.RUnlock()

	result := make([]*models.CanaryDeployment, 0, len(m.deployments))
	for _, d := range m.deployments {
		result = append(result, m.toAPIModel(d))
	}
	return result
}

func (m *Manager) PauseDeployment(policyID string) error {
	m.mu.Lock()
	defer m.mu.Unlock()

	deployment, exists := m.deployments[policyID]
	if !exists {
		return fmt.Errorf("deployment not found: %s", policyID)
	}

	deployment.mu.Lock()
	defer deployment.mu.Unlock()

	if deployment.Status != StatusProgressing {
		return fmt.Errorf("deployment is not in progressing state")
	}

	if deployment.CancelFunc != nil {
		deployment.CancelFunc()
	}

	deployment.Status = StatusPaused
	deployment.UpdateTime = time.Now()

	return nil
}

func (m *Manager) ResumeDeployment(policyID string) error {
	m.mu.Lock()
	defer m.mu.Unlock()

	deployment, exists := m.deployments[policyID]
	if !exists {
		return fmt.Errorf("deployment not found: %s", policyID)
	}

	deployment.mu.Lock()
	if deployment.Status != StatusPaused {
		deployment.mu.Unlock()
		return fmt.Errorf("deployment is not in paused state")
	}
	deployment.mu.Unlock()

	ctx, cancel := context.WithCancel(context.Background())
	deployment.CancelFunc = cancel

	go m.runCanaryDeployment(ctx, deployment)

	return nil
}

func (m *Manager) RollbackDeployment(policyID string) error {
	m.mu.Lock()
	defer m.mu.Unlock()

	deployment, exists := m.deployments[policyID]
	if !exists {
		return fmt.Errorf("deployment not found: %s", policyID)
	}

	if deployment.CancelFunc != nil {
		deployment.CancelFunc()
	}

	m.rollback(deployment)
	return nil
}

func (m *Manager) PromoteDeployment(policyID string) error {
	m.mu.Lock()
	defer m.mu.Unlock()

	deployment, exists := m.deployments[policyID]
	if !exists {
		return fmt.Errorf("deployment not found: %s", policyID)
	}

	if deployment.CancelFunc != nil {
		deployment.CancelFunc()
	}

	deployment.mu.Lock()
	defer deployment.mu.Unlock()

	deployment.Status = StatusPromoted
	deployment.TrafficPercent = 100
	deployment.UpdateTime = time.Now()

	return nil
}

func (m *Manager) toAPIModel(d *CanaryDeployment) *models.CanaryDeployment {
	d.mu.RLock()
	defer d.mu.RUnlock()

	metrics := &models.CanaryMetrics{}
	if d.Metrics != nil {
		metrics = d.Metrics
	}

	return &models.CanaryDeployment{
		ID:             d.ID,
		PolicyID:       d.PolicyID,
		Strategy:       string(d.Strategy),
		TrafficPercent: d.TrafficPercent,
		Duration:       d.Duration,
		Status:         string(d.Status),
		Metrics:        *metrics,
		CreatedAt:      d.StartTime,
		UpdatedAt:      d.UpdateTime,
	}
}

func generateDeploymentID(policyID string) string {
	return fmt.Sprintf("canary-%s-%d", policyID, time.Now().Unix())
}
