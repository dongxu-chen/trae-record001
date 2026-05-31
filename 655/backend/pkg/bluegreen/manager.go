package bluegreen

import (
	"context"
	"fmt"
	"sync"
	"time"

	"github.com/google/uuid"

	"servicemesh-gateway/pkg/istio"
	"servicemesh-gateway/pkg/models"
	redisclient "servicemesh-gateway/pkg/redis"
)

type BlueGreenManager struct {
	istioClient  *istio.Client
	trafficStore *redisclient.TrafficStore
	deployments  map[string]*models.BlueGreenDeployment
	mu           sync.RWMutex
	stopCh       chan struct{}
}

func NewBlueGreenManager(istioClient *istio.Client, trafficStore *redisclient.TrafficStore) *BlueGreenManager {
	bgm := &BlueGreenManager{
		istioClient:  istioClient,
		trafficStore: trafficStore,
		deployments:  make(map[string]*models.BlueGreenDeployment),
		stopCh:       make(chan struct{}),
	}

	go bgm.deploymentLoop()

	return bgm
}

func (bgm *BlueGreenManager) CreateDeployment(req *models.BlueGreenDeployment) (*models.BlueGreenDeployment, error) {
	req.ID = uuid.New().String()
	req.Status = "pending"
	req.Phase = "preparing"
	req.CreatedAt = time.Now()
	req.UpdatedAt = time.Now()

	if req.StepSize == 0 {
		req.StepSize = 10
	}
	if req.StepIntervalSeconds == 0 {
		req.StepIntervalSeconds = 60
	}
	if req.RollbackThreshold == 0 {
		req.RollbackThreshold = 5.0
	}

	bgm.mu.Lock()
	bgm.deployments[req.ID] = req
	bgm.mu.Unlock()

	bgm.trafficStore.HSet("bluegreen:deployments", req.ID, req)

	return req, nil
}

func (bgm *BlueGreenManager) StartDeployment(id string) error {
	bgm.mu.Lock()
	deployment, exists := bgm.deployments[id]
	bgm.mu.Unlock()

	if !exists {
		return fmt.Errorf("deployment %s not found", id)
	}

	if deployment.Status != "pending" && deployment.Status != "paused" {
		return fmt.Errorf("invalid deployment status: %s", deployment.Status)
	}

	deployment.Status = "running"
	deployment.Phase = "in-progress"
	deployment.UpdatedAt = time.Now()

	bgm.mu.Lock()
	bgm.deployments[id] = deployment
	bgm.mu.Unlock()

	bgm.trafficStore.HSet("bluegreen:deployments", id, deployment)

	return nil
}

func (bgm *BlueGreenManager) PauseDeployment(id string) error {
	bgm.mu.Lock()
	deployment, exists := bgm.deployments[id]
	bgm.mu.Unlock()

	if !exists {
		return fmt.Errorf("deployment %s not found", id)
	}

	if deployment.Status != "running" {
		return fmt.Errorf("can only pause running deployments")
	}

	deployment.Status = "paused"
	deployment.UpdatedAt = time.Now()

	bgm.mu.Lock()
	bgm.deployments[id] = deployment
	bgm.mu.Unlock()

	bgm.trafficStore.HSet("bluegreen:deployments", id, deployment)

	return nil
}

func (bgm *BlueGreenManager) RollbackDeployment(id string) error {
	bgm.mu.Lock()
	deployment, exists := bgm.deployments[id]
	bgm.mu.Unlock()

	if !exists {
		return fmt.Errorf("deployment %s not found", id)
	}

	return bgm.executeRollback(deployment, "manual rollback triggered")
}

func (bgm *BlueGreenManager) executeRollback(d *models.BlueGreenDeployment, reason string) error {
	d.Status = "rollback"
	d.Phase = "rolling-back"
	d.UpdatedAt = time.Now()

	step := models.DeploymentStep{
		Timestamp:   time.Now(),
		WeightBlue:  100,
		WeightGreen: 0,
		Success:     false,
		Rollback:    true,
		Message:     reason,
	}
	d.DeploymentHistory = append(d.DeploymentHistory, step)

	weightRouting := &models.WeightRouting{
		RoutingRule: models.RoutingRule{
			ID:          uuid.New().String(),
			Name:        fmt.Sprintf("bg-rollback-%s", d.ServiceName),
			Namespace:   d.Namespace,
			Type:        "weight",
			ServiceName: d.ServiceName,
			Status:      "active",
			CreatedAt:   time.Now(),
			UpdatedAt:   time.Now(),
		},
		Subsets: []models.SubsetWeight{
			{SubsetName: d.BlueSubset, Weight: 100, Version: d.BlueVersion},
			{SubsetName: d.GreenSubset, Weight: 0, Version: d.GreenVersion},
		},
	}

	if err := bgm.istioClient.ApplyWeightRouting(weightRouting); err != nil {
		return fmt.Errorf("failed to apply rollback weights: %w", err)
	}

	d.CurrentWeightBlue = 100
	d.Status = "rolled-back"
	d.Phase = "completed"
	d.UpdatedAt = time.Now()

	bgm.mu.Lock()
	bgm.deployments[d.ID] = d
	bgm.mu.Unlock()

	bgm.trafficStore.HSet("bluegreen:deployments", d.ID, d)

	return nil
}

func (bgm *BlueGreenManager) CompleteDeployment(id string) error {
	bgm.mu.Lock()
	deployment, exists := bgm.deployments[id]
	bgm.mu.Unlock()

	if !exists {
		return fmt.Errorf("deployment %s not found", id)
	}

	if deployment.Status != "running" {
		return fmt.Errorf("can only complete running deployments")
	}

	finalStep := models.DeploymentStep{
		Timestamp:   time.Now(),
		WeightBlue:  0,
		WeightGreen: 100,
		Success:     true,
		Rollback:    false,
		Message:     "deployment completed successfully",
	}
	deployment.DeploymentHistory = append(deployment.DeploymentHistory, finalStep)

	weightRouting := &models.WeightRouting{
		RoutingRule: models.RoutingRule{
			ID:          uuid.New().String(),
			Name:        fmt.Sprintf("bg-complete-%s", deployment.ServiceName),
			Namespace:   deployment.Namespace,
			Type:        "weight",
			ServiceName: deployment.ServiceName,
			Status:      "active",
			CreatedAt:   time.Now(),
			UpdatedAt:   time.Now(),
		},
		Subsets: []models.SubsetWeight{
			{SubsetName: deployment.BlueSubset, Weight: 0, Version: deployment.BlueVersion},
			{SubsetName: deployment.GreenSubset, Weight: 100, Version: deployment.GreenVersion},
		},
	}

	if err := bgm.istioClient.ApplyWeightRouting(weightRouting); err != nil {
		return fmt.Errorf("failed to apply final weights: %w", err)
	}

	deployment.CurrentWeightBlue = 0
	deployment.Status = "completed"
	deployment.Phase = "completed"
	deployment.UpdatedAt = time.Now()

	bgm.mu.Lock()
	bgm.deployments[id] = deployment
	bgm.mu.Unlock()

	bgm.trafficStore.HSet("bluegreen:deployments", id, deployment)

	return nil
}

func (bgm *BlueGreenManager) GetDeployment(id string) (*models.BlueGreenDeployment, bool) {
	bgm.mu.RLock()
	defer bgm.mu.RUnlock()

	d, exists := bgm.deployments[id]
	return d, exists
}

func (bgm *BlueGreenManager) ListDeployments(namespace string) []*models.BlueGreenDeployment {
	bgm.mu.RLock()
	defer bgm.mu.RUnlock()

	result := make([]*models.BlueGreenDeployment, 0)
	for _, d := range bgm.deployments {
		if namespace == "" || d.Namespace == namespace {
			result = append(result, d)
		}
	}

	return result
}

func (bgm *BlueGreenManager) deploymentLoop() {
	ticker := time.NewTicker(5 * time.Second)
	defer ticker.Stop()

	for {
		select {
		case <-ticker.C:
			bgm.processDeployments()
		case <-bgm.stopCh:
			return
		}
	}
}

func (bgm *BlueGreenManager) processDeployments() {
	bgm.mu.Lock()
	deployments := make([]*models.BlueGreenDeployment, 0, len(bgm.deployments))
	for _, d := range bgm.deployments {
		deployments = append(deployments, d)
	}
	bgm.mu.Unlock()

	for _, d := range deployments {
		if d.Status != "running" {
			continue
		}

		if err := bgm.processSingleDeployment(d); err != nil {
			fmt.Printf("Error processing deployment %s: %v\n", d.ID, err)
		}
	}
}

func (bgm *BlueGreenManager) processSingleDeployment(d *models.BlueGreenDeployment) error {
	lastStep := bgm.getLastStep(d)
	now := time.Now()

	if lastStep != nil {
		timeSinceLastStep := now.Sub(lastStep.Timestamp)
		if timeSinceLastStep < time.Duration(d.StepIntervalSeconds)*time.Second {
			return nil
		}
	}

	if d.AutoRollbackEnabled {
		metrics, err := bgm.trafficStore.GetMetrics(
			d.Namespace,
			d.ServiceName,
			now.Add(-2*time.Minute),
			now,
		)
		if err == nil && len(metrics) > 0 {
			latest := metrics[len(metrics)-1]
			errorRate := float64(latest.ErrorCount) / float64(latest.RequestCount) * 100

			if errorRate > d.RollbackThreshold {
				return bgm.executeRollback(d,
					fmt.Sprintf("auto rollback: error rate %.2f%% exceeded threshold %.2f%%",
						errorRate, d.RollbackThreshold))
			}
		}
	}

	nextWeight := d.CurrentWeightBlue - d.StepSize
	if nextWeight < 0 {
		nextWeight = 0
	}

	if nextWeight < d.TargetWeightBlue {
		nextWeight = d.TargetWeightBlue
	}

	if nextWeight == d.CurrentWeightBlue {
		return nil
	}

	weightRouting := &models.WeightRouting{
		RoutingRule: models.RoutingRule{
			ID:          uuid.New().String(),
			Name:        fmt.Sprintf("bg-step-%s-%d", d.ServiceName, nextWeight),
			Namespace:   d.Namespace,
			Type:        "weight",
			ServiceName: d.ServiceName,
			Status:      "active",
			CreatedAt:   time.Now(),
			UpdatedAt:   time.Now(),
		},
		Subsets: []models.SubsetWeight{
			{SubsetName: d.BlueSubset, Weight: nextWeight, Version: d.BlueVersion},
			{SubsetName: d.GreenSubset, Weight: 100 - nextWeight, Version: d.GreenVersion},
		},
	}

	if err := bgm.istioClient.ApplyWeightRouting(weightRouting); err != nil {
		return fmt.Errorf("failed to apply weights: %w", err)
	}

	step := models.DeploymentStep{
		Timestamp:   time.Now(),
		WeightBlue:  nextWeight,
		WeightGreen: 100 - nextWeight,
		Success:     true,
		Rollback:    false,
		Message:     fmt.Sprintf("weight adjusted to %d/%d", nextWeight, 100-nextWeight),
	}

	d.DeploymentHistory = append(d.DeploymentHistory, step)
	d.CurrentWeightBlue = nextWeight

	if nextWeight == d.TargetWeightBlue {
		d.Status = "running"
		d.Phase = "verifying"
	}

	d.UpdatedAt = time.Now()

	bgm.mu.Lock()
	bgm.deployments[d.ID] = d
	bgm.mu.Unlock()

	bgm.trafficStore.HSet("bluegreen:deployments", d.ID, d)

	return nil
}

func (bgm *BlueGreenManager) getLastStep(d *models.BlueGreenDeployment) *models.DeploymentStep {
	if len(d.DeploymentHistory) == 0 {
		return nil
	}
	return &d.DeploymentHistory[len(d.DeploymentHistory)-1]
}

func (bgm *BlueGreenManager) Stop() {
	close(bgm.stopCh)
}
