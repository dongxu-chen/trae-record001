package rollback

import (
	"context"
	"encoding/json"
	"fmt"
	"os"
	"path/filepath"
	"sync"
	"time"
)

type RollbackPhase string

const (
	PhasePreMigration    RollbackPhase = "pre_migration"
	PhaseSnapshotTaken   RollbackPhase = "snapshot_taken"
	PhaseResourceCreated RollbackPhase = "resource_created"
	PhaseDataMigrated    RollbackPhase = "data_migrated"
	PhaseTrafficSwitched RollbackPhase = "traffic_switched"
	PhaseCompleted       RollbackPhase = "completed"
	PhaseRollingBack     RollbackPhase = "rolling_back"
	PhaseRolledBack      RollbackPhase = "rolled_back"
	PhaseFailed          RollbackPhase = "failed"
)

type RollbackTrigger string

const (
	TriggerManual        RollbackTrigger = "manual"
	TriggerHealthCheck   RollbackTrigger = "health_check"
	TriggerErrorThreshold RollbackTrigger = "error_threshold"
	TriggerTimeout       RollbackTrigger = "timeout"
	TriggerUserRequest   RollbackTrigger = "user_request"
)

type ResourceAction struct {
	ResourceID   string            `json:"resource_id"`
	ResourceType string            `json:"resource_type"`
	Action       string            `json:"action"`
	Status       string            `json:"status"`
	SourceState  map[string]string `json:"source_state"`
	TargetState  map[string]string `json:"target_state"`
	Timestamp    int64             `json:"timestamp"`
	RollbackFunc string            `json:"rollback_func"`
}

type HealthCheck struct {
	ID          string            `json:"id"`
	Name        string            `json:"name"`
	Type        string            `json:"type"`
	Endpoint    string            `json:"endpoint"`
	Interval    int               `json:"interval"`
	Timeout     int               `json:"timeout"`
	MaxRetries  int               `json:"max_retries"`
	Status      string            `json:"status"`
	LastCheck   int64             `json:"last_check"`
	FailedCount int               `json:"failed_count"`
	Labels      map[string]string `json:"labels"`
}

type RollbackPlan struct {
	ID              string            `json:"id"`
	MigrationTaskID string            `json:"migration_task_id"`
	Name            string            `json:"name"`
	CreatedAt       int64             `json:"created_at"`
	CurrentPhase    RollbackPhase     `json:"current_phase"`
	Actions         []*ResourceAction `json:"actions"`
	HealthChecks    []*HealthCheck    `json:"health_checks"`
	Trigger         RollbackTrigger   `json:"trigger"`
	TriggeredAt     int64             `json:"triggered_at"`
	CompletedAt     int64             `json:"completed_at"`
	ErrorThreshold  int               `json:"error_threshold"`
	CurrentErrors   int               `json:"current_errors"`
	TimeoutSeconds  int               `json:"timeout_seconds"`
	AutoRollback    bool              `json:"auto_rollback"`
	RollbackOrder   []string          `json:"rollback_order"`
	Notes           string            `json:"notes"`
	mu              sync.RWMutex
}

type RollbackManager struct {
	plans    map[string]*RollbackPlan
	storeDir string
	mu       sync.RWMutex
}

type RollbackResult struct {
	Success        bool   `json:"success"`
	PlanID         string `json:"plan_id"`
	Trigger        RollbackTrigger `json:"trigger"`
	CompletedPhase RollbackPhase `json:"completed_phase"`
	ActionsCount   int    `json:"actions_count"`
	FailedActions  int    `json:"failed_actions"`
	Duration       int64  `json:"duration"`
	ErrorMessage   string `json:"error_message"`
}

func NewRollbackManager(storeDir string) (*RollbackManager, error) {
	if err := os.MkdirAll(storeDir, 0755); err != nil {
		return nil, fmt.Errorf("failed to create rollback store directory: %w", err)
	}

	rm := &RollbackManager{
		plans:    make(map[string]*RollbackPlan),
		storeDir: storeDir,
	}

	if err := rm.loadPlans(); err != nil {
		return nil, err
	}

	return rm, nil
}

func (rm *RollbackManager) CreatePlan(migrationTaskID, name string, autoRollback bool) *RollbackPlan {
	rm.mu.Lock()
	defer rm.mu.Unlock()

	planID := fmt.Sprintf("rollback-%d", time.Now().UnixNano())
	plan := &RollbackPlan{
		ID:              planID,
		MigrationTaskID: migrationTaskID,
		Name:            name,
		CreatedAt:       time.Now().Unix(),
		CurrentPhase:    PhasePreMigration,
		Actions:         make([]*ResourceAction, 0),
		HealthChecks:    make([]*HealthCheck, 0),
		AutoRollback:    autoRollback,
		ErrorThreshold:  5,
		TimeoutSeconds:  3600,
		RollbackOrder:   make([]string, 0),
	}

	rm.plans[planID] = plan
	rm.savePlan(plan)

	return plan
}

func (rm *RollbackManager) GetPlan(planID string) (*RollbackPlan, bool) {
	rm.mu.RLock()
	defer rm.mu.RUnlock()
	plan, ok := rm.plans[planID]
	return plan, ok
}

func (rm *RollbackManager) ListPlans() []*RollbackPlan {
	rm.mu.RLock()
	defer rm.mu.RUnlock()
	plans := make([]*RollbackPlan, 0, len(rm.plans))
	for _, plan := range rm.plans {
		plans = append(plans, plan)
	}
	return plans
}

func (p *RollbackPlan) RecordAction(resourceID, resourceType, action string, sourceState, targetState map[string]string, rollbackFunc string) {
	p.mu.Lock()
	defer p.mu.Unlock()

	p.Actions = append(p.Actions, &ResourceAction{
		ResourceID:   resourceID,
		ResourceType: resourceType,
		Action:       action,
		Status:       "completed",
		SourceState:  sourceState,
		TargetState:  targetState,
		Timestamp:    time.Now().Unix(),
		RollbackFunc: rollbackFunc,
	})

	p.RollbackOrder = append([]string{resourceID}, p.RollbackOrder...)
}

func (p *RollbackPlan) AddHealthCheck(check *HealthCheck) {
	p.mu.Lock()
	defer p.mu.Unlock()
	p.HealthChecks = append(p.HealthChecks, check)
}

func (p *RollbackPlan) UpdatePhase(phase RollbackPhase) {
	p.mu.Lock()
	defer p.mu.Unlock()
	p.CurrentPhase = phase
}

func (p *RollbackPlan) RecordError() bool {
	p.mu.Lock()
	defer p.mu.Unlock()
	p.CurrentErrors++
	return p.CurrentErrors >= p.ErrorThreshold
}

func (p *RollbackPlan) ShouldAutoRollback() bool {
	p.mu.RLock()
	defer p.mu.RUnlock()

	if !p.AutoRollback {
		return false
	}

	if p.CurrentErrors >= p.ErrorThreshold {
		return true
	}

	if p.TimeoutSeconds > 0 {
		elapsed := time.Now().Unix() - p.CreatedAt
		if elapsed >= int64(p.TimeoutSeconds) {
			return true
		}
	}

	return false
}

func (rm *RollbackManager) ExecuteRollback(ctx context.Context, planID string, trigger RollbackTrigger) (*RollbackResult, error) {
	rm.mu.Lock()
	plan, ok := rm.plans[planID]
	if !ok {
		rm.mu.Unlock()
		return nil, fmt.Errorf("rollback plan not found: %s", planID)
	}
	rm.mu.Unlock()

	plan.mu.Lock()
	plan.CurrentPhase = PhaseRollingBack
	plan.Trigger = trigger
	plan.TriggeredAt = time.Now().Unix()
	plan.mu.Unlock()

	result := &RollbackResult{
		PlanID:         planID,
		Trigger:        trigger,
		CompletedPhase: plan.CurrentPhase,
	}

	failedCount := 0
	for i := len(plan.Actions) - 1; i >= 0; i-- {
		select {
		case <-ctx.Done():
			return result, ctx.Err()
		default:
		}

		action := plan.Actions[i]
		action.Status = "rolling_back"

		if err := rm.executeRollbackAction(ctx, action); err != nil {
			failedCount++
			action.Status = "failed"
		} else {
			action.Status = "rolled_back"
		}

		result.ActionsCount++
	}

	plan.mu.Lock()
	plan.CurrentPhase = PhaseRolledBack
	plan.CompletedAt = time.Now().Unix()
	plan.mu.Unlock()

	result.Success = failedCount == 0
	result.CompletedPhase = PhaseRolledBack
	result.FailedActions = failedCount
	result.Duration = plan.CompletedAt - plan.TriggeredAt

	if failedCount > 0 {
		result.ErrorMessage = fmt.Sprintf("%d actions failed to rollback", failedCount)
	}

	rm.savePlan(plan)
	return result, nil
}

func (rm *RollbackManager) executeRollbackAction(ctx context.Context, action *ResourceAction) error {
	switch action.RollbackFunc {
	case "delete_resource":
		return rm.rollbackDeleteResource(ctx, action)
	case "restore_snapshot":
		return rm.rollbackRestoreSnapshot(ctx, action)
	case "revert_traffic":
		return rm.rollbackRevertTraffic(ctx, action)
	case "restore_state":
		return rm.rollbackRestoreState(ctx, action)
	default:
		return rm.rollbackGeneric(ctx, action)
	}
}

func (rm *RollbackManager) rollbackDeleteResource(ctx context.Context, action *ResourceAction) error {
	fmt.Printf("Rolling back: Deleting resource %s (%s)\n", action.ResourceID, action.ResourceType)
	select {
	case <-ctx.Done():
		return ctx.Err()
	case <-time.After(500 * time.Millisecond):
	}
	return nil
}

func (rm *RollbackManager) rollbackRestoreSnapshot(ctx context.Context, action *ResourceAction) error {
	fmt.Printf("Rolling back: Restoring snapshot for %s\n", action.ResourceID)
	select {
	case <-ctx.Done():
		return ctx.Err()
	case <-time.After(500 * time.Millisecond):
	}
	return nil
}

func (rm *RollbackManager) rollbackRevertTraffic(ctx context.Context, action *ResourceAction) error {
	fmt.Printf("Rolling back: Reverting traffic for %s\n", action.ResourceID)
	select {
	case <-ctx.Done():
		return ctx.Err()
	case <-time.After(500 * time.Millisecond):
	}
	return nil
}

func (rm *RollbackManager) rollbackRestoreState(ctx context.Context, action *ResourceAction) error {
	fmt.Printf("Rolling back: Restoring state for %s\n", action.ResourceID)
	select {
	case <-ctx.Done():
		return ctx.Err()
	case <-time.After(500 * time.Millisecond):
	}
	return nil
}

func (rm *RollbackManager) rollbackGeneric(ctx context.Context, action *ResourceAction) error {
	fmt.Printf("Rolling back: Generic rollback for %s\n", action.ResourceID)
	select {
	case <-ctx.Done():
		return ctx.Err()
	case <-time.After(500 * time.Millisecond):
	}
	return nil
}

func (rm *RollbackManager) MonitorHealth(ctx context.Context, planID string) <-chan bool {
	resultChan := make(chan bool, 1)

	plan, ok := rm.GetPlan(planID)
	if !ok {
		resultChan <- false
		close(resultChan)
		return resultChan
	}

	go func() {
		defer close(resultChan)

		ticker := time.NewTicker(30 * time.Second)
		defer ticker.Stop()

		for {
			select {
			case <-ctx.Done():
				return
			case <-ticker.C:
				allHealthy := true
				for _, check := range plan.HealthChecks {
					healthy := rm.performHealthCheck(check)
					if !healthy {
						allHealthy = false
						check.FailedCount++
					}
					check.LastCheck = time.Now().Unix()
				}

				if !allHealthy && plan.ShouldAutoRollback() {
					resultChan <- false
					return
				}

				resultChan <- allHealthy
			}
		}
	}()

	return resultChan
}

func (rm *RollbackManager) performHealthCheck(check *HealthCheck) bool {
	fmt.Printf("Performing health check: %s (%s)\n", check.Name, check.Endpoint)
	return true
}

func (rm *RollbackManager) GenerateRollbackReport(planID string) (string, error) {
	plan, ok := rm.GetPlan(planID)
	if !ok {
		return "", fmt.Errorf("rollback plan not found: %s", planID)
	}

	plan.mu.RLock()
	defer plan.mu.RUnlock()

	report := fmt.Sprintf(`
========================================
回滚预案报告
========================================

基本信息:
- 回滚计划ID: %s
- 迁移任务ID: %s
- 计划名称: %s
- 创建时间: %s
- 当前阶段: %s
- 自动回滚: %v
- 错误阈值: %d
- 当前错误数: %d

`, plan.ID, plan.MigrationTaskID, plan.Name,
		time.Unix(plan.CreatedAt, 0).Format(time.RFC3339),
		plan.CurrentPhase, plan.AutoRollback,
		plan.ErrorThreshold, plan.CurrentErrors)

	if plan.Trigger != "" {
		report += fmt.Sprintf(`
触发信息:
- 触发方式: %s
- 触发时间: %s
`, plan.Trigger, time.Unix(plan.TriggeredAt, 0).Format(time.RFC3339))
	}

	report += `
已记录操作:
`
	for _, action := range plan.Actions {
		report += fmt.Sprintf("  - [%s] %s %s: %s\n",
			time.Unix(action.Timestamp, 0).Format("15:04:05"),
			action.ResourceType, action.ResourceID, action.Action)
	}

	report += `
健康检查配置:
`
	for _, check := range plan.HealthChecks {
		report += fmt.Sprintf("  - %s: %s (interval: %ds, timeout: %ds)\n",
			check.Name, check.Endpoint, check.Interval, check.Timeout)
	}

	return report, nil
}

func (rm *RollbackManager) savePlan(plan *RollbackPlan) error {
	data, err := json.MarshalIndent(plan, "", "  ")
	if err != nil {
		return err
	}

	filename := filepath.Join(rm.storeDir, fmt.Sprintf("%s.json", plan.ID))
	return os.WriteFile(filename, data, 0644)
}

func (rm *RollbackManager) loadPlans() error {
	files, err := filepath.Glob(filepath.Join(rm.storeDir, "rollback-*.json"))
	if err != nil {
		return err
	}

	for _, file := range files {
		data, err := os.ReadFile(file)
		if err != nil {
			continue
		}

		var plan RollbackPlan
		if err := json.Unmarshal(data, &plan); err != nil {
			continue
		}

		rm.plans[plan.ID] = &plan
	}

	return nil
}
