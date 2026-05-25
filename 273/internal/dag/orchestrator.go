package dag

import (
	"context"
	"fmt"
	"log"
	"scheduler/internal/models"
	"scheduler/internal/store"
	"sync"
	"time"

	"github.com/google/uuid"
	"github.com/robfig/cron/v3"
)

type Orchestrator struct {
	store       *store.PostgresStore
	dagExecs    map[string]*DAGExecutionState
	mu          sync.RWMutex
	taskHandler func(taskID string) error
}

type DAGExecutionState struct {
	ExecutionID    int64
	DagID          string
	CompletedTasks map[string]bool
	FailedTasks    map[string]bool
	TaskStatus     map[string]string
	StartTime      time.Time
	Status         string
}

func NewOrchestrator(store *store.PostgresStore) *Orchestrator {
	return &Orchestrator{
		store:    store,
		dagExecs: make(map[string]*DAGExecutionState),
	}
}

func (o *Orchestrator) SetTaskHandler(handler func(taskID string) error) {
	o.taskHandler = handler
}

func (o *Orchestrator) CreateDAG(ctx context.Context, req *models.CreateDAGRequest) (*models.DAG, error) {
	var nextRunTime time.Time
	if req.CronExpr != "" {
		schedule, err := cron.ParseStandard(req.CronExpr)
		if err != nil {
			return nil, fmt.Errorf("invalid cron expression: %w", err)
		}
		nextRunTime = schedule.Next(time.Now())
	}

	dag := &models.DAG{
		ID:          uuid.New().String(),
		Name:        req.Name,
		Description: req.Description,
		Status:      models.DagStatusPending,
		CronExpr:    req.CronExpr,
		TaskIDs:     req.TaskIDs,
		NextRunTime: nextRunTime,
	}

	if err := o.store.CreateDAG(ctx, dag); err != nil {
		return nil, err
	}

	return dag, nil
}

func (o *Orchestrator) AddDependency(ctx context.Context, req *models.AddDependencyRequest) error {
	dep := &models.DAGDependency{
		DagID:           req.DagID,
		TaskID:          req.TaskID,
		DependsOnTaskID: req.DependsOnTaskID,
		DependencyType:  req.DependencyType,
	}
	if dep.DependencyType == "" {
		dep.DependencyType = "success"
	}
	return o.store.AddDependency(ctx, dep)
}

func (o *Orchestrator) TriggerDAG(ctx context.Context, dagID, triggeredBy string) error {
	dag, err := o.store.GetDAG(ctx, dagID)
	if err != nil {
		return err
	}

	log.Printf("Triggering DAG: %s, triggered by: %s", dagID, triggeredBy)

	exec := &models.DAGExecution{
		DagID:          dagID,
		StartTime:      time.Now(),
		Status:         models.DagStatusRunning,
		TriggeredBy:    triggeredBy,
		CompletedTasks: []string{},
		FailedTasks:    []string{},
	}
	if err := o.store.CreateDAGExecution(ctx, exec); err != nil {
		return err
	}

	state := &DAGExecutionState{
		ExecutionID:    exec.ID,
		DagID:          dagID,
		CompletedTasks: make(map[string]bool),
		FailedTasks:    make(map[string]bool),
		TaskStatus:     make(map[string]string),
		StartTime:      time.Now(),
		Status:         models.DagStatusRunning,
	}

	o.mu.Lock()
	o.dagExecs[dagID] = state
	o.mu.Unlock()

	allDeps, err := o.store.GetDAGDependencies(ctx, dagID)
	if err != nil {
		log.Printf("Failed to get DAG dependencies: %v", err)
	}

	depMap := make(map[string][]string)
	for _, dep := range allDeps {
		depMap[dep.TaskID] = append(depMap[dep.TaskID], dep.DependsOnTaskID)
	}

	readyTasks := o.findReadyTasks(dag.TaskIDs, depMap, state)
	log.Printf("Found %d ready tasks to start for DAG %s", len(readyTasks), dagID)

	for _, taskID := range readyTasks {
		state.TaskStatus[taskID] = "queued"
		if o.taskHandler != nil {
			go func(tid string) {
				if err := o.taskHandler(tid); err != nil {
					log.Printf("Failed to trigger task %s: %v", tid, err)
				}
			}(taskID)
		}
	}

	return nil
}

func (o *Orchestrator) findReadyTasks(taskIDs []string, depMap map[string][]string, state *DAGExecutionState) []string {
	var ready []string

	for _, taskID := range taskIDs {
		if state.CompletedTasks[taskID] || state.FailedTasks[taskID] {
			continue
		}
		if _, ok := state.TaskStatus[taskID]; ok && state.TaskStatus[taskID] != "" {
			continue
		}

		deps := depMap[taskID]
		allDepsCompleted := true

		for _, depID := range deps {
			if !state.CompletedTasks[depID] {
				allDepsCompleted = false
				break
			}
		}

		if allDepsCompleted {
			ready = append(ready, taskID)
		}
	}

	return ready
}

func (o *Orchestrator) OnTaskComplete(ctx context.Context, taskID string, success bool) error {
	o.mu.Lock()
	defer o.mu.Unlock()

	var affectedDAGs []string
	for dagID, state := range o.dagExecs {
		if state.Status != models.DagStatusRunning {
			continue
		}

		dag, err := o.store.GetDAG(ctx, dagID)
		if err != nil {
			continue
		}

		isTaskInDAG := false
		for _, t := range dag.TaskIDs {
			if t == taskID {
				isTaskInDAG = true
				break
			}
		}
		if !isTaskInDAG {
			continue
		}

		affectedDAGs = append(affectedDAGs, dagID)

		if success {
			state.CompletedTasks[taskID] = true
			state.TaskStatus[taskID] = "completed"
		} else {
			state.FailedTasks[taskID] = true
			state.TaskStatus[taskID] = "failed"
		}
	}

	for _, dagID := range affectedDAGs {
		state := o.dagExecs[dagID]
		dag, _ := o.store.GetDAG(ctx, dagID)
		allDeps, _ := o.store.GetDAGDependencies(ctx, dagID)

		depMap := make(map[string][]string)
		for _, dep := range allDeps {
			depMap[dep.TaskID] = append(depMap[dep.TaskID], dep.DependsOnTaskID)
		}

		readyTasks := o.findReadyTasks(dag.TaskIDs, depMap, state)
		for _, tid := range readyTasks {
			state.TaskStatus[tid] = "queued"
			if o.taskHandler != nil {
				go func(t string) {
					if err := o.taskHandler(t); err != nil {
						log.Printf("Failed to trigger task %s: %v", t, err)
					}
				}(tid)
			}
		}

		o.checkDAGCompletion(ctx, dagID, state)
	}

	return nil
}

func (o *Orchestrator) checkDAGCompletion(ctx context.Context, dagID string, state *DAGExecutionState) {
	dag, err := o.store.GetDAG(ctx, dagID)
	if err != nil {
		log.Printf("Failed to get DAG %s: %v", dagID, err)
		return
	}

	totalTasks := len(dag.TaskIDs)
	completedCount := len(state.CompletedTasks)
	failedCount := len(state.FailedTasks)

	if completedCount+failedCount >= totalTasks {
		exec := &models.DAGExecution{
			ID:             state.ExecutionID,
			DagID:          dagID,
			EndTime:        time.Now(),
			CompletedTasks: mapKeysToSlice(state.CompletedTasks),
			FailedTasks:    mapKeysToSlice(state.FailedTasks),
		}

		if failedCount > 0 {
			state.Status = models.DagStatusFailed
			exec.Status = models.DagStatusFailed
			log.Printf("DAG %s completed with %d failures", dagID, failedCount)
		} else {
			state.Status = models.DagStatusCompleted
			exec.Status = models.DagStatusCompleted
			log.Printf("DAG %s completed successfully", dagID)
		}

		o.store.UpdateDAGExecution(ctx, exec)
	}
}

func mapKeysToSlice(m map[string]bool) []string {
	keys := make([]string, 0, len(m))
	for k := range m {
		keys = append(keys, k)
	}
	return keys
}

func (o *Orchestrator) GetDAGState(dagID string) *DAGExecutionState {
	o.mu.RLock()
	defer o.mu.RUnlock()
	return o.dagExecs[dagID]
}

func (o *Orchestrator) ScanAndTriggerDAGs(ctx context.Context) error {
	now := time.Now()
	dags, err := o.store.GetDAGsToRun(ctx, now, 100)
	if err != nil {
		return err
	}

	for _, dag := range dags {
		if dag.CronExpr == "" {
			continue
		}

		schedule, err := cron.ParseStandard(dag.CronExpr)
		if err != nil {
			log.Printf("Invalid cron for DAG %s: %v", dag.ID, err)
			continue
		}

		nextTime := schedule.Next(time.Now())
		if err := o.store.UpdateDAGNextRunTime(ctx, dag.ID, nextTime); err != nil {
			log.Printf("Failed to update DAG next run time: %v", err)
		}

		if err := o.TriggerDAG(ctx, dag.ID, "scheduler"); err != nil {
			log.Printf("Failed to trigger DAG %s: %v", dag.ID, err)
		}
	}

	return nil
}

func (o *Orchestrator) GetDAGExecutionStatus(ctx context.Context, dagID string) (map[string]interface{}, error) {
	state := o.GetDAGState(dagID)
	if state == nil {
		return map[string]interface{}{
			"status": "not_running",
		}, nil
	}

	return map[string]interface{}{
		"execution_id":     state.ExecutionID,
		"status":           state.Status,
		"start_time":       state.StartTime,
		"completed_tasks":  mapKeysToSlice(state.CompletedTasks),
		"failed_tasks":     mapKeysToSlice(state.FailedTasks),
		"task_status":      state.TaskStatus,
		"completed_count":  len(state.CompletedTasks),
		"failed_count":     len(state.FailedTasks),
	}, nil
}
