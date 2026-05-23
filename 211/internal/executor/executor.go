package executor

import (
	"context"
	"encoding/json"
	"fmt"
	"log"
	"strings"
	"sync"
	"time"

	"scheduler/internal/models"
	"scheduler/internal/scheduler"
	"scheduler/internal/store"
	"scheduler/pkg/heartbeat"
	"scheduler/pkg/lock"
	"scheduler/pkg/retry"

	"github.com/go-redis/redis/v8"
	"github.com/google/uuid"
)

type TaskHandler func(ctx context.Context, payload string) (string, error)

type Executor struct {
	store            *store.MySQLStore
	locker           *lock.RedisLock
	scheduler        *scheduler.Scheduler
	workerID         string
	handlers         map[string]TaskHandler
	redisClient      *redis.Client
	stopChan         chan struct{}
	wg               sync.WaitGroup
	workerCount      int
	heartbeatManager *heartbeat.HeartbeatManager
	defaultTimeout   time.Duration
	maxTimeout       time.Duration
}

func NewExecutor(store *store.MySQLStore, locker *lock.RedisLock, sched *scheduler.Scheduler, workerID string, workerCount int) *Executor {
	store.SetRedisLocker(locker)
	return &Executor{
		store:          store,
		locker:         locker,
		scheduler:      sched,
		workerID:       workerID,
		handlers:       make(map[string]TaskHandler),
		redisClient:    locker.GetClient(),
		stopChan:       make(chan struct{}),
		workerCount:    workerCount,
		defaultTimeout: 5 * time.Minute,
		maxTimeout:     24 * time.Hour,
	}
}

func (e *Executor) RegisterHandler(taskType string, handler TaskHandler) {
	e.handlers[taskType] = handler
}

func (e *Executor) Start(ctx context.Context) error {
	log.Printf("Executor %s starting with %d workers...", e.workerID, e.workerCount)

	e.heartbeatManager = heartbeat.NewHeartbeatManager(e.store, e.redisClient, e.workerID, e.workerCount)
	if err := e.heartbeatManager.Start(ctx); err != nil {
		return fmt.Errorf("failed to start heartbeat manager: %w", err)
	}

	for i := 0; i < e.workerCount; i++ {
		e.wg.Add(1)
		go e.worker(ctx, i)
	}

	go e.recoverStuckTasks(ctx)

	return nil
}

func (e *Executor) Stop() {
	close(e.stopChan)
	e.wg.Wait()
	if e.heartbeatManager != nil {
		e.heartbeatManager.Stop()
	}
	log.Printf("Executor %s stopped", e.workerID)
}

func (e *Executor) worker(ctx context.Context, workerNum int) {
	defer e.wg.Done()
	log.Printf("Worker %d started", workerNum)

	for {
		select {
		case <-ctx.Done():
			return
		case <-e.stopChan:
			return
		default:
			taskData, err := e.dequeueTask(ctx)
			if err != nil {
				time.Sleep(100 * time.Millisecond)
				continue
			}
			if taskData == "" {
				time.Sleep(100 * time.Millisecond)
				continue
			}

			parts := strings.Split(taskData, ":")
			if len(parts) != 2 {
				log.Printf("Invalid task data: %s", taskData)
				continue
			}
			taskID, executionID := parts[0], parts[1]

			e.executeTask(ctx, taskID, executionID)
		}
	}
}

func (e *Executor) dequeueTask(ctx context.Context) (string, error) {
	queueKey := "scheduler:task:queue"
	result, err := e.redisClient.RPop(ctx, queueKey).Result()
	if err == redis.Nil {
		return "", nil
	}
	return result, err
}

func (e *Executor) executeTask(ctx context.Context, taskID, executionID string) {
	execLockKey := fmt.Sprintf("execution:%s", executionID)
	lock, acquired, err := e.locker.Acquire(ctx, execLockKey, 5*time.Minute)
	if err != nil {
		log.Printf("Failed to acquire execution lock: %v", err)
		return
	}
	if !acquired {
		return
	}
	defer lock.Release(ctx)

	execution, err := e.store.GetExecution(ctx, executionID)
	if err != nil {
		log.Printf("Failed to get execution %s: %v", executionID, err)
		return
	}

	if execution.Status != models.ExecutionStatusPending {
		return
	}

	task, err := e.store.GetTask(ctx, taskID)
	if err != nil {
		log.Printf("Failed to get task %s: %v", taskID, err)
		return
	}

	e.recordAuditLog(ctx, &models.AuditLog{
		ID:          uuid.New().String(),
		Event:       models.AuditEventTaskDispatched,
		TaskID:      taskID,
		ExecutionID: executionID,
		WorkerID:    e.workerID,
		Message:     fmt.Sprintf("Task %s dispatched to worker %s", taskID, e.workerID),
		CreatedAt:   time.Now(),
	})

	handler, exists := e.handlers[task.TaskType]
	if !exists {
		errMsg := fmt.Sprintf("no handler registered for task type: %s", task.TaskType)
		e.handleTaskFailure(ctx, task, execution, errMsg, false)
		return
	}

	now := time.Now()
	execution.Status = models.ExecutionStatusRunning
	execution.StartTime = &now
	execution.WorkerID = e.workerID
	if err := e.store.UpdateExecution(ctx, execution); err != nil {
		log.Printf("Failed to update execution status: %v", err)
		return
	}

	e.recordAuditLog(ctx, &models.AuditLog{
		ID:          uuid.New().String(),
		Event:       models.AuditEventTaskStarted,
		TaskID:      taskID,
		ExecutionID: executionID,
		WorkerID:    e.workerID,
		Message:     fmt.Sprintf("Task %s started execution", taskID),
		CreatedAt:   time.Now(),
	})

	timeout := e.calculateTimeout(task)
	ctxWithTimeout, cancel := context.WithTimeout(ctx, timeout)
	defer cancel()

	result, err := e.executeWithRetry(ctxWithTimeout, task, execution, handler)
	if err != nil {
		if ctxWithTimeout.Err() == context.DeadlineExceeded {
			e.handleTaskTimeout(ctx, task, execution, timeout)
		} else {
			e.handleTaskFailure(ctx, task, execution, err.Error(), true)
		}
	} else {
		e.handleTaskSuccess(ctx, task, execution, result)
	}
}

func (e *Executor) calculateTimeout(task *models.Task) time.Duration {
	if task.TimeoutSec <= 0 {
		return e.defaultTimeout
	}
	timeout := time.Duration(task.TimeoutSec) * time.Second
	if timeout > e.maxTimeout {
		return e.maxTimeout
	}
	return timeout
}

func (e *Executor) recordAuditLog(ctx context.Context, log *models.AuditLog) {
	if err := e.store.RecordAuditLog(ctx, log); err != nil {
		log.Printf("Failed to record audit log: %v", err)
	}
}

func (e *Executor) executeWithRetry(ctx context.Context, task *models.Task, execution *models.TaskExecution, handler TaskHandler) (string, error) {
	var result string
	var lastErr error

	for attempt := 0; attempt <= task.MaxRetries; attempt++ {
		if ctx.Err() != nil {
			return "", ctx.Err()
		}

		execution.RetryCount = attempt
		execution.UpdatedAt = time.Now()
		if err := e.store.UpdateExecution(ctx, execution); err != nil {
			log.Printf("Failed to update retry count: %v", err)
		}

		attemptStart := time.Now()
		result, lastErr = handler(ctx, task.Payload)
		attemptDuration := time.Since(attemptStart)

		if lastErr == nil {
			return result, nil
		}

		log.Printf("Task %s execution %s attempt %d failed in %dms: %v", task.ID, execution.ID, attempt, attemptDuration.Milliseconds(), lastErr)

		e.recordAuditLog(ctx, &models.AuditLog{
			ID:          uuid.New().String(),
			Event:       models.AuditEventTaskRetried,
			TaskID:      task.ID,
			ExecutionID: execution.ID,
			WorkerID:    e.workerID,
			Message:     fmt.Sprintf("Task retry %d/%d, error: %s", attempt, task.MaxRetries, lastErr),
			DurationMs:  attemptDuration.Milliseconds(),
			RetryCount:  attempt,
			CreatedAt:   time.Now(),
		})

		if attempt < task.MaxRetries {
			nextRetry := retry.CalculateNextRetryTime(attempt, task.RetryDelay)
			waitTime := time.Until(nextRetry)
			select {
			case <-ctx.Done():
				return "", ctx.Err()
			case <-time.After(waitTime):
			}
		}
	}

	return "", lastErr
}

func (e *Executor) handleTaskSuccess(ctx context.Context, task *models.Task, execution *models.TaskExecution, result string) {
	now := time.Now()
	execution.Status = models.ExecutionStatusSuccess
	execution.EndTime = &now
	execution.Result = result
	duration := now.Sub(*execution.StartTime)
	execution.DurationMs = duration.Milliseconds()
	execution.UpdatedAt = now

	if err := e.store.UpdateExecution(ctx, execution); err != nil {
		log.Printf("Failed to update execution success: %v", err)
	}

	if err := e.scheduler.UpdateTaskNextRun(ctx, task); err != nil {
		log.Printf("Failed to update task next run: %v", err)
	}

	if err := e.scheduler.TriggerDependentTasks(ctx, task.ID); err != nil {
		log.Printf("Failed to trigger dependent tasks: %v", err)
	}

	e.recordAuditLog(ctx, &models.AuditLog{
		ID:          uuid.New().String(),
		Event:       models.AuditEventTaskCompleted,
		TaskID:      task.ID,
		ExecutionID: execution.ID,
		WorkerID:    e.workerID,
		Message:     fmt.Sprintf("Task completed successfully"),
		DurationMs:  execution.DurationMs,
		RetryCount:  execution.RetryCount,
		CreatedAt:   now,
	})

	log.Printf("Task %s executed successfully in %dms after %d retries", task.ID, execution.DurationMs, execution.RetryCount)
}

func (e *Executor) handleTaskFailure(ctx context.Context, task *models.Task, execution *models.TaskExecution, errMsg string, retryable bool) {
	now := time.Now()
	execution.Status = models.ExecutionStatusFailed
	execution.EndTime = &now
	execution.Error = errMsg
	duration := now.Sub(*execution.StartTime)
	execution.DurationMs = duration.Milliseconds()
	execution.UpdatedAt = now

	if err := e.store.UpdateExecution(ctx, execution); err != nil {
		log.Printf("Failed to update execution failure: %v", err)
	}

	if retryable && execution.RetryCount < task.MaxRetries {
		nextRunAt := retry.CalculateNextRetryTime(execution.RetryCount, task.RetryDelay)
		task.NextRunAt = &nextRunAt
		task.Status = models.TaskStatusPending
	} else {
		task.Status = models.TaskStatusFailed
		task.NextRunAt = nil
	}

	if err := e.store.UpdateTask(ctx, task); err != nil {
		log.Printf("Failed to update task status: %v", err)
	}

	e.recordAuditLog(ctx, &models.AuditLog{
		ID:          uuid.New().String(),
		Event:       models.AuditEventTaskFailed,
		TaskID:      task.ID,
		ExecutionID: execution.ID,
		WorkerID:    e.workerID,
		Message:     fmt.Sprintf("Task failed: %s", errMsg),
		DurationMs:  execution.DurationMs,
		RetryCount:  execution.RetryCount,
		CreatedAt:   now,
	})

	log.Printf("Task %s failed after %d retries in %dms: %s", task.ID, execution.RetryCount, execution.DurationMs, errMsg)
}

func (e *Executor) handleTaskTimeout(ctx context.Context, task *models.Task, execution *models.TaskExecution, timeout time.Duration) {
	now := time.Now()
	execution.Status = models.ExecutionStatusTimeout
	execution.EndTime = &now
	execution.Error = fmt.Sprintf("task execution timeout after %v", timeout)
	duration := now.Sub(*execution.StartTime)
	execution.DurationMs = duration.Milliseconds()
	execution.UpdatedAt = now

	if err := e.store.UpdateExecution(ctx, execution); err != nil {
		log.Printf("Failed to update execution timeout: %v", err)
	}

	if execution.RetryCount < task.MaxRetries {
		nextRunAt := retry.CalculateNextRetryTime(execution.RetryCount, task.RetryDelay)
		task.NextRunAt = &nextRunAt
		task.Status = models.TaskStatusPending
	} else {
		task.Status = models.TaskStatusFailed
		task.NextRunAt = nil
	}

	if err := e.store.UpdateTask(ctx, task); err != nil {
		log.Printf("Failed to update task status: %v", err)
	}

	e.recordAuditLog(ctx, &models.AuditLog{
		ID:          uuid.New().String(),
		Event:       models.AuditEventTaskTimeout,
		TaskID:      task.ID,
		ExecutionID: execution.ID,
		WorkerID:    e.workerID,
		Message:     fmt.Sprintf("Task timed out after %v", timeout),
		DurationMs:  execution.DurationMs,
		RetryCount:  execution.RetryCount,
		CreatedAt:   now,
	})

	log.Printf("Task %s timed out after %v, %d retries used", task.ID, timeout, execution.RetryCount)
}

func (e *Executor) recoverStuckTasks(ctx context.Context) {
	ticker := time.NewTicker(5 * time.Minute)
	defer ticker.Stop()

	for {
		select {
		case <-ctx.Done():
			return
		case <-e.stopChan:
			return
		case <-ticker.C:
			e.recoverRunningTasks(ctx)
		}
	}
}

func (e *Executor) recoverRunningTasks(ctx context.Context) {
	executions, _, err := e.store.ListExecutions(ctx, "", 0, 1000)
	if err != nil {
		log.Printf("Failed to list executions for recovery: %v", err)
		return
	}

	for _, exec := range executions {
		if exec.Status != models.ExecutionStatusRunning {
			continue
		}

		if exec.StartTime == nil {
			continue
		}

		elapsed := time.Since(*exec.StartTime)
		timeout := 10 * time.Minute

		if elapsed > timeout {
			log.Printf("Recovering stuck execution %s (elapsed: %v)", exec.ID, elapsed)

			execLockKey := fmt.Sprintf("execution:%s", exec.ID)
			lock, acquired, err := e.locker.Acquire(ctx, execLockKey, 1*time.Minute)
			if err != nil || !acquired {
				continue
			}

			task, err := e.store.GetTask(ctx, exec.TaskID)
			if err != nil {
				lock.Release(ctx)
				continue
			}

			exec.Status = models.ExecutionStatusTimeout
			now := time.Now()
			exec.EndTime = &now
			exec.Error = "task execution timeout"
			exec.DurationMs = elapsed.Milliseconds()
			e.store.UpdateExecution(ctx, exec)

			e.store.UpdateTaskStatus(ctx, task.ID, models.TaskStatusPending)
			lock.Release(ctx)
		}
	}
}

type HTTPTaskPayload struct {
	URL     string            `json:"url"`
	Method  string            `json:"method"`
	Headers map[string]string `json:"headers"`
	Body    string            `json:"body"`
}

func HTTPTaskHandler(ctx context.Context, payload string) (string, error) {
	var p HTTPTaskPayload
	if err := json.Unmarshal([]byte(payload), &p); err != nil {
		return "", fmt.Errorf("invalid payload: %w", err)
	}

	return fmt.Sprintf("HTTP task executed: %s %s", p.Method, p.URL), nil
}

type LogTaskPayload struct {
	Message string `json:"message"`
	Level   string `json:"level"`
}

func LogTaskHandler(ctx context.Context, payload string) (string, error) {
	var p LogTaskPayload
	if err := json.Unmarshal([]byte(payload), &p); err != nil {
		return "", fmt.Errorf("invalid payload: %w", err)
	}

	log.Printf("[%s] %s", p.Level, p.Message)
	return fmt.Sprintf("Logged: %s", p.Message), nil
}
