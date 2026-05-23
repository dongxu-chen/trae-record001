package scheduler

import (
	"context"
	"fmt"
	"log"
	"strings"
	"sync"
	"time"

	"scheduler/internal/models"
	"scheduler/internal/store"
	"scheduler/pkg/dag"
	"scheduler/pkg/lock"

	"github.com/google/uuid"
	"github.com/robfig/cron/v3"
)

type Scheduler struct {
	store        *store.MySQLStore
	locker       *lock.RedisLock
	schedulerID  string
	cron         *cron.Cron
	ticker       *time.Ticker
	stopChan     chan struct{}
	dagGraph     *dag.TaskDependencyGraph
	dagMutex     sync.RWMutex
	dagUpdatedAt time.Time
}

func NewScheduler(store *store.MySQLStore, locker *lock.RedisLock, schedulerID string) *Scheduler {
	return &Scheduler{
		store:        store,
		locker:       locker,
		schedulerID:  schedulerID,
		cron:         cron.New(cron.WithSeconds()),
		ticker:       time.NewTicker(1 * time.Second),
		stopChan:     make(chan struct{}),
		dagGraph:     dag.NewTaskDependencyGraph(),
		dagUpdatedAt: time.Time{},
	}
}

func (s *Scheduler) Start(ctx context.Context) error {
	log.Printf("Scheduler %s starting...", s.schedulerID)
	s.cron.Start()
	go s.run(ctx)
	return nil
}

func (s *Scheduler) Stop() {
	s.cron.Stop()
	s.ticker.Stop()
	close(s.stopChan)
	log.Printf("Scheduler %s stopped", s.schedulerID)
}

func (s *Scheduler) run(ctx context.Context) {
	for {
		select {
		case <-ctx.Done():
			return
		case <-s.stopChan:
			return
		case <-s.ticker.C:
			s.checkAndDispatchTasks(ctx)
		}
	}
}

func (s *Scheduler) checkAndDispatchTasks(ctx context.Context) {
	leaderKey := "scheduler:leader"
	lock, acquired, err := s.locker.Acquire(ctx, leaderKey, 5*time.Second)
	if err != nil {
		log.Printf("Failed to acquire leader lock: %v", err)
		return
	}
	if !acquired {
		return
	}
	defer lock.Release(ctx)

	tasks, err := s.store.GetPendingTasks(ctx)
	if err != nil {
		log.Printf("Failed to get pending tasks: %v", err)
		return
	}

	for _, task := range tasks {
		if err := s.dispatchTask(ctx, &task); err != nil {
			log.Printf("Failed to dispatch task %s: %v", task.ID, err)
		}
	}
}

func (s *Scheduler) dispatchTask(ctx context.Context, task *models.Task) error {
	taskLockKey := fmt.Sprintf("task:%s", task.ID)
	lock, acquired, err := s.locker.Acquire(ctx, taskLockKey, 30*time.Second)
	if err != nil {
		return err
	}
	if !acquired {
		return nil
	}
	defer lock.Release(ctx)

	executionID := uuid.New().String()
	execution := &models.TaskExecution{
		ID:         executionID,
		TaskID:     task.ID,
		Status:     models.ExecutionStatusPending,
		RetryCount: 0,
		WorkerID:   s.schedulerID,
		CreatedAt:  time.Now(),
		UpdatedAt:  time.Now(),
	}

	if err := s.store.CreateExecution(ctx, execution); err != nil {
		return err
	}

	task.Status = models.TaskStatusRunning
	now := time.Now()
	task.LastRunAt = &now
	if err := s.store.UpdateTask(ctx, task); err != nil {
		return err
	}

	if err := s.enqueueTask(ctx, task, executionID); err != nil {
		return err
	}

	return nil
}

func (s *Scheduler) enqueueTask(ctx context.Context, task *models.Task, executionID string) error {
	queueKey := "scheduler:task:queue"
	taskData := fmt.Sprintf("%s:%s", task.ID, executionID)
	return s.locker.GetClient().LPush(ctx, queueKey, taskData).Err()
}

func CalculateNextRunTime(task *models.Task) (*time.Time, error) {
	now := time.Now()

	switch task.TriggerType {
	case models.TriggerTypeCron:
		if task.CronExpr == "" {
			return nil, fmt.Errorf("cron expression is empty")
		}
		schedule, err := cron.ParseStandard(task.CronExpr)
		if err != nil {
			return nil, fmt.Errorf("invalid cron expression: %w", err)
		}
		next := schedule.Next(now)
		return &next, nil

	case models.TriggerTypeInterval:
		if task.IntervalSec <= 0 {
			return nil, fmt.Errorf("invalid interval")
		}
		next := now.Add(time.Duration(task.IntervalSec) * time.Second)
		return &next, nil

	case models.TriggerTypeManual:
		return nil, nil

	default:
		return nil, fmt.Errorf("unknown trigger type: %s", task.TriggerType)
	}
}

func (s *Scheduler) CheckDependencies(ctx context.Context, task *models.Task) (bool, error) {
	if task.Dependencies == "" {
		return true, nil
	}

	depTaskIDs := strings.Split(task.Dependencies, ",")
	for _, depTaskID := range depTaskIDs {
		depTaskID = strings.TrimSpace(depTaskID)
		if depTaskID == "" {
			continue
		}

		executions, _, err := s.store.ListExecutions(ctx, depTaskID, 0, 1)
		if err != nil {
			return false, err
		}

		if len(executions) == 0 || executions[0].Status != models.ExecutionStatusSuccess {
			return false, nil
		}
	}

	return true, nil
}

func (s *Scheduler) TriggerDependentTasks(ctx context.Context, completedTaskID string) error {
	tasks, err := s.store.GetTasksByDependency(ctx, completedTaskID)
	if err != nil {
		return err
	}

	for _, task := range tasks {
		ready, err := s.CheckDependencies(ctx, &task)
		if err != nil {
			log.Printf("Failed to check dependencies for task %s: %v", task.ID, err)
			continue
		}
		if ready {
			now := time.Now()
			task.NextRunAt = &now
			if err := s.store.UpdateTask(ctx, &task); err != nil {
				log.Printf("Failed to update task %s: %v", task.ID, err)
			}
		}
	}

	return nil
}

func (s *Scheduler) RegisterTask(ctx context.Context, task *models.Task) error {
	task.ID = uuid.New().String()
	task.Status = models.TaskStatusPending
	task.CreatedAt = time.Now()
	task.UpdatedAt = time.Now()

	nextRunAt, err := CalculateNextRunTime(task)
	if err != nil {
		return err
	}
	task.NextRunAt = nextRunAt

	return s.store.CreateTask(ctx, task)
}

func (s *Scheduler) UpdateTaskNextRun(ctx context.Context, task *models.Task) error {
	nextRunAt, err := CalculateNextRunTime(task)
	if err != nil {
		return err
	}
	task.NextRunAt = nextRunAt
	task.Status = models.TaskStatusPending
	return s.store.UpdateTask(ctx, task)
}

func (s *Scheduler) rebuildDAG(ctx context.Context) error {
	s.dagMutex.Lock()
	defer s.dagMutex.Unlock()

	allTasks, _, err := s.store.ListTasks(ctx, 0, 10000)
	if err != nil {
		return fmt.Errorf("failed to list tasks: %w", err)
	}

	newGraph := dag.NewTaskDependencyGraph()

	for _, task := range allTasks {
		var deps []string
		if task.Dependencies != "" {
			deps = strings.Split(task.Dependencies, ",")
		}
		if err := newGraph.AddTask(task.ID, deps, task); err != nil {
			log.Printf("Warning: failed to add task %s to DAG: %v", task.ID, err)
		}
	}

	if err := newGraph.ValidateNoCycles(); err != nil {
		log.Printf("Warning: DAG has cycle: %v", err)
	}

	s.dagGraph = newGraph
	s.dagUpdatedAt = time.Now()
	log.Printf("DAG rebuilt: %d nodes, %d edges", newGraph.NodeCount(), newGraph.EdgeCount())
	return nil
}

func (s *Scheduler) getOrRebuildDAG(ctx context.Context) *dag.TaskDependencyGraph {
	s.dagMutex.RLock()
	if time.Since(s.dagUpdatedAt) < 5*time.Minute {
		graph := s.dagGraph
		s.dagMutex.RUnlock()
		return graph
	}
	s.dagMutex.RUnlock()

	s.rebuildDAG(ctx)

	s.dagMutex.RLock()
	graph := s.dagGraph
	s.dagMutex.RUnlock()
	return graph
}

func (s *Scheduler) TriggerDependentTasks(ctx context.Context, completedTaskID string) error {
	graph := s.getOrRebuildDAG(ctx)

	dependents := graph.GetDependents(completedTaskID)
	if len(dependents) == 0 {
		return nil
	}

	log.Printf("Task %s completed, checking %d dependent tasks", completedTaskID, len(dependents))

	for _, depTaskID := range dependents {
		ready, err := s.CheckDependenciesWithDAG(ctx, depTaskID, graph)
		if err != nil {
			log.Printf("Failed to check dependencies for task %s: %v", depTaskID, err)
			continue
		}
		if ready {
			task, err := s.store.GetTask(ctx, depTaskID)
			if err != nil {
				log.Printf("Failed to get task %s: %v", depTaskID, err)
				continue
			}
			if task.Status == models.TaskStatusPending || task.Status == models.TaskStatusPaused {
				now := time.Now()
				task.NextRunAt = &now
				task.Status = models.TaskStatusPending
				if err := s.store.UpdateTask(ctx, task); err != nil {
					log.Printf("Failed to update task %s: %v", task.ID, err)
				}
				log.Printf("Dependent task %s is ready and scheduled", depTaskID)
			}
		}
	}

	return nil
}

func (s *Scheduler) CheckDependenciesWithDAG(ctx context.Context, taskID string, graph *dag.TaskDependencyGraph) (bool, error) {
	deps := graph.GetDependencies(taskID)
	if len(deps) == 0 {
		return true, nil
	}

	for _, depTaskID := range deps {
		executions, _, err := s.store.ListExecutions(ctx, depTaskID, 0, 1)
		if err != nil {
			return false, err
		}

		if len(executions) == 0 || executions[0].Status != models.ExecutionStatusSuccess {
			return false, nil
		}
	}

	return true, nil
}

func (s *Scheduler) GetExecutionOrder(ctx context.Context) ([]string, error) {
	graph := s.getOrRebuildDAG(ctx)
	return graph.GetExecutionOrder()
}
