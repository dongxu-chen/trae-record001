package heartbeat

import (
	"context"
	"fmt"
	"log"
	"time"

	"scheduler/internal/models"
	"scheduler/internal/store"

	"github.com/go-redis/redis/v8"
	"github.com/google/uuid"
)

const (
	heartbeatKeyPrefix = "scheduler:worker:heartbeat:"
	heartbeatInterval  = 5 * time.Second
	heartbeatTimeout   = 15 * time.Second
)

type HeartbeatManager struct {
	store       *store.MySQLStore
	redisClient *redis.Client
	workerID    string
	workerCount int
	stopChan    chan struct{}
}

func NewHeartbeatManager(store *store.MySQLStore, redisClient *redis.Client, workerID string, workerCount int) *HeartbeatManager {
	return &HeartbeatManager{
		store:       store,
		redisClient: redisClient,
		workerID:    workerID,
		workerCount: workerCount,
		stopChan:    make(chan struct{}),
	}
}

func (h *HeartbeatManager) Start(ctx context.Context) error {
	if err := h.registerWorker(ctx); err != nil {
		return fmt.Errorf("failed to register worker: %w", err)
	}

	go h.heartbeatLoop(ctx)
	go h.checkFailedNodes(ctx)

	return nil
}

func (h *HeartbeatManager) Stop() {
	close(h.stopChan)
	h.unregisterWorker()
}

func (h *HeartbeatManager) registerWorker(ctx context.Context) error {
	now := time.Now()
	node := &models.WorkerNode{
		ID:            h.workerID,
		WorkerCount:   h.workerCount,
		Status:        models.WorkerStatusOnline,
		LastHeartbeat: now,
		StartedAt:     now,
		CreatedAt:     now,
		UpdatedAt:     now,
	}

	if err := h.store.UpsertWorkerNode(ctx, node); err != nil {
		return err
	}

	heartbeatKey := heartbeatKeyPrefix + h.workerID
	if err := h.redisClient.Set(ctx, heartbeatKey, now.Unix(), heartbeatTimeout).Err(); err != nil {
		return err
	}

	log.Printf("Worker %s registered successfully", h.workerID)
	return nil
}

func (h *HeartbeatManager) unregisterWorker() {
	ctx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
	defer cancel()

	heartbeatKey := heartbeatKeyPrefix + h.workerID
	h.redisClient.Del(ctx, heartbeatKey)

	if err := h.store.UpdateWorkerStatus(ctx, h.workerID, models.WorkerStatusOffline); err != nil {
		log.Printf("Failed to update worker status: %v", err)
	}

	log.Printf("Worker %s unregistered", h.workerID)
}

func (h *HeartbeatManager) heartbeatLoop(ctx context.Context) {
	ticker := time.NewTicker(heartbeatInterval)
	defer ticker.Stop()

	for {
		select {
		case <-ctx.Done():
			return
		case <-h.stopChan:
			return
		case <-ticker.C:
			if err := h.sendHeartbeat(ctx); err != nil {
				log.Printf("Failed to send heartbeat: %v", err)
			}
		}
	}
}

func (h *HeartbeatManager) sendHeartbeat(ctx context.Context) error {
	now := time.Now()
	heartbeatKey := heartbeatKeyPrefix + h.workerID

	if err := h.redisClient.Set(ctx, heartbeatKey, now.Unix(), heartbeatTimeout).Err(); err != nil {
		return err
	}

	if err := h.store.UpdateHeartbeat(ctx, h.workerID, now); err != nil {
		return err
	}

	return nil
}

func (h *HeartbeatManager) checkFailedNodes(ctx context.Context) {
	ticker := time.NewTicker(30 * time.Second)
	defer ticker.Stop()

	for {
		select {
		case <-ctx.Done():
			return
		case <-h.stopChan:
			return
		case <-ticker.C:
			h.detectAndRecoverFailedNodes(ctx)
		}
	}
}

func (h *HeartbeatManager) detectAndRecoverFailedNodes(ctx context.Context) {
	leaderKey := "scheduler:heartbeat:leader"
	lock, acquired, err := h.store.GetRedisLocker().Acquire(ctx, leaderKey, 10*time.Second)
	if err != nil || !acquired {
		return
	}
	defer lock.Release(ctx)

	threshold := time.Now().Add(-heartbeatTimeout)
	failedNodes, err := h.store.GetFailedWorkerNodes(ctx, threshold)
	if err != nil {
		log.Printf("Failed to get failed nodes: %v", err)
		return
	}

	for _, node := range failedNodes {
		log.Printf("Detected failed node: %s, last heartbeat: %v", node.ID, node.LastHeartbeat)

		if err := h.store.UpdateWorkerStatus(ctx, node.ID, models.WorkerStatusFailed); err != nil {
			log.Printf("Failed to update node status: %v", err)
			continue
		}

		if err := h.recoverTasksFromFailedNode(ctx, node.ID); err != nil {
			log.Printf("Failed to recover tasks from node %s: %v", node.ID, err)
		}

		h.store.RecordAuditLog(ctx, &models.AuditLog{
			ID:        uuid.New().String(),
			Event:     models.AuditEventNodeFailed,
			WorkerID:  node.ID,
			Message:   fmt.Sprintf("Worker node %s failed, tasks reassigned", node.ID),
			CreatedAt: time.Now(),
		})
	}
}

func (h *HeartbeatManager) recoverTasksFromFailedNode(ctx context.Context, workerID string) error {
	runningExecutions, err := h.store.GetRunningExecutionsByWorker(ctx, workerID)
	if err != nil {
		return err
	}

	for _, exec := range runningExecutions {
		log.Printf("Recovering execution %s (task %s) from failed node %s", exec.ID, exec.TaskID, workerID)

		now := time.Now()
		exec.Status = models.ExecutionStatusTimeout
		exec.EndTime = &now
		exec.Error = "worker node failed, task reassigned"
		exec.DurationMs = now.Sub(*exec.StartTime).Milliseconds()
		exec.UpdatedAt = now

		if err := h.store.UpdateExecution(ctx, &exec); err != nil {
			log.Printf("Failed to update execution %s: %v", exec.ID, err)
			continue
		}

		task, err := h.store.GetTask(ctx, exec.TaskID)
		if err != nil {
			log.Printf("Failed to get task %s: %v", exec.TaskID, err)
			continue
		}

		task.Status = models.TaskStatusPending
		task.NextRunAt = &now
		if err := h.store.UpdateTask(ctx, task); err != nil {
			log.Printf("Failed to update task %s: %v", task.ID, err)
			continue
		}

		h.store.RecordAuditLog(ctx, &models.AuditLog{
			ID:          uuid.New().String(),
			Event:       models.AuditEventTaskReassigned,
			TaskID:      task.ID,
			ExecutionID: exec.ID,
			WorkerID:    workerID,
			Message:     fmt.Sprintf("Task reassigned from failed node %s", workerID),
			CreatedAt:   time.Now(),
		})

		log.Printf("Task %s recovered and rescheduled", task.ID)
	}

	return nil
}

func (h *HeartbeatManager) GetWorkerID() string {
	return h.workerID
}
