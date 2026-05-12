package main

import (
	"context"
	"encoding/json"
	"log"
	"sync"
	"time"

	"github.com/google/uuid"
	"github.com/redis/go-redis/v9"
)

type TaskQueue struct {
	redis   *RedisClient
	mu      sync.RWMutex
	cache   map[string]*Task
	localCh chan *Task
}

func NewTaskQueue(rc *RedisClient, bufferSize int) *TaskQueue {
	return &TaskQueue{
		redis:   rc,
		cache:   make(map[string]*Task),
		localCh: make(chan *Task, bufferSize),
	}
}

func (q *TaskQueue) Submit(taskType string, payload json.RawMessage) *Task {
	ctx := context.Background()

	task := &Task{
		ID:         uuid.New().String(),
		Type:       taskType,
		Payload:    payload,
		Status:     TaskStatusPending,
		CreatedAt:  nowFunc(),
		RetryCount: 0,
	}

	if err := q.redis.StoreTask(ctx, task); err != nil {
		log.Printf("StoreTask error: %v", err)
		return nil
	}

	streamID, err := q.redis.XAdd(ctx, &redis.XAddArgs{
		Stream: StreamKey,
		Values: map[string]interface{}{
			"task_id":    task.ID,
			"type":       task.Type,
			"retry_count": 0,
		},
	}).Result()

	if err != nil {
		log.Printf("XAdd error: %v", err)
		task.Status = TaskStatusFailed
		task.Error = err.Error()
		q.redis.StoreTask(ctx, task)
		return task
	}

	task.StreamID = streamID
	q.redis.StoreTask(ctx, task)

	q.mu.Lock()
	q.cache[task.ID] = cloneTask(task)
	q.mu.Unlock()

	return cloneTask(task)
}

func (q *TaskQueue) Dequeue() <-chan *Task {
	return q.localCh
}

func (q *TaskQueue) Get(id string) (*Task, bool) {
	ctx := context.Background()

	q.mu.RLock()
	if cached, ok := q.cache[id]; ok {
		q.mu.RUnlock()
		return cloneTask(cached), true
	}
	q.mu.RUnlock()

	task, err := q.redis.LoadTask(ctx, id)
	if err != nil {
		return nil, false
	}

	q.mu.Lock()
	q.cache[task.ID] = cloneTask(task)
	q.mu.Unlock()

	return cloneTask(task), true
}

func (q *TaskQueue) Update(id string, updater func(*Task)) {
	ctx := context.Background()

	q.mu.Lock()
	original, inCache := q.cache[id]
	q.mu.Unlock()

	var task *Task
	if inCache {
		task = cloneTask(original)
	} else {
		var err error
		task, err = q.redis.LoadTask(ctx, id)
		if err != nil {
			return
		}
	}

	updater(task)

	if err := q.redis.StoreTask(ctx, task); err != nil {
		log.Printf("Update StoreTask error: %v", err)
	}

	q.mu.Lock()
	q.cache[task.ID] = cloneTask(task)
	q.mu.Unlock()
}

func (q *TaskQueue) List() []*Task {
	ctx := context.Background()
	result := make([]*Task, 0)

	keys, err := q.redis.Keys(ctx, TaskHashPrefix+"*").Result()
	if err != nil {
		log.Printf("List Keys error: %v", err)
		return result
	}

	for _, key := range keys {
		id := key[len(TaskHashPrefix):]
		task, err := q.redis.LoadTask(ctx, id)
		if err == nil {
			result = append(result, cloneTask(task))
		}
	}

	return result
}

func (q *TaskQueue) Acknowledge(ctx context.Context, streamID string) error {
	return q.redis.XAck(ctx, StreamKey, ConsumerGroup, streamID).Err()
}

func (q *TaskQueue) MoveToDLQ(ctx context.Context, task *Task, errMsg string) error {
	endTime := nowFunc()
	task.Status = TaskStatusDeadLetter
	task.IsDeadLetter = true
	task.EndedAt = &endTime
	task.LastError = errMsg

	if task.StreamID != "" {
		if err := q.redis.XAck(ctx, StreamKey, ConsumerGroup, task.StreamID).Err(); err != nil {
			log.Printf("Ack before DLQ error: %v", err)
		}
	}

	dlqID, err := q.redis.XAdd(ctx, &redis.XAddArgs{
		Stream: DLQStreamKey,
		Values: map[string]interface{}{
			"task_id":    task.ID,
			"type":       task.Type,
			"error":      errMsg,
			"retry_count": task.RetryCount,
		},
	}).Result()
	if err != nil {
		log.Printf("XAdd DLQ error: %v", err)
	}
	task.StreamID = dlqID

	return q.redis.StoreTask(ctx, task)
}

func (q *TaskQueue) RequeueFromDLQ(ctx context.Context, taskID string) error {
	task, err := q.redis.LoadTask(ctx, taskID)
	if err != nil {
		return err
	}
	if !task.IsDeadLetter {
		return nil
	}

	endTime := nowFunc()
	task.Status = TaskStatusPending
	task.IsDeadLetter = false
	task.RetryCount = 0
	task.EndedAt = &endTime
	task.LastError = ""

	newStreamID, err := q.redis.XAdd(ctx, &redis.XAddArgs{
		Stream: StreamKey,
		Values: map[string]interface{}{
			"task_id":    task.ID,
			"type":       task.Type,
			"retry_count": 0,
		},
	}).Result()
	if err != nil {
		return err
	}
	task.StreamID = newStreamID

	return q.redis.StoreTask(ctx, task)
}

func (q *TaskQueue) ListDLQ(ctx context.Context) ([]*Task, error) {
	allTasks := q.List()
	dlqTasks := make([]*Task, 0)
	for _, t := range allTasks {
		if t.IsDeadLetter {
			dlqTasks = append(dlqTasks, t)
		}
	}
	return dlqTasks, nil
}

func cloneTask(t *Task) *Task {
	if t == nil {
		return nil
	}
	clone := *t
	clone.Payload = append(json.RawMessage(nil), t.Payload...)
	if resultJSON, ok := t.Result.(json.RawMessage); ok {
		clone.Result = append(json.RawMessage(nil), resultJSON...)
	}
	clone.StartedAt = cloneTimePtr(t.StartedAt)
	clone.EndedAt = cloneTimePtr(t.EndedAt)
	return &clone
}

func cloneTimePtr(t *time.Time) *time.Time {
	if t == nil {
		return nil
	}
	clone := *t
	return &clone
}
