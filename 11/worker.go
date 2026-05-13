package main

import (
	"context"
	"encoding/json"
	"fmt"
	"log"
	"time"

	"github.com/google/uuid"
	"github.com/redis/go-redis/v9"
)

const (
	ClaimTimeout = 5 * time.Minute
	PollInterval = 100 * time.Millisecond
)

var nowFunc = time.Now

type Worker struct {
	id       int
	queue    *TaskQueue
	redis    *RedisClient
	consumer string
	stop     chan struct{}
}

func NewWorker(id int, queue *TaskQueue, rc *RedisClient) *Worker {
	return &Worker{
		id:       id,
		queue:    queue,
		redis:    rc,
		consumer: fmt.Sprintf("worker-%d-%s", id, uuid.New().String()[:8]),
		stop:     make(chan struct{}),
	}
}

func (w *Worker) Start(ctx context.Context) {
	go w.run(ctx)
}

func (w *Worker) run(ctx context.Context) {
	defer func() {
		if r := recover(); r != nil {
			log.Printf("Worker %d (%s) recovered from panic: %v", w.id, w.consumer, r)
			go w.run(ctx)
		}
	}()

	log.Printf("Worker %d started as consumer: %s", w.id, w.consumer)

	for {
		select {
		case <-ctx.Done():
			log.Printf("Worker %d: context done", w.id)
			return
		case <-w.stop:
			log.Printf("Worker %d: stopped", w.id)
			return
		default:
		}

		reclaimed, err := w.claimPending(ctx)
		if err != nil {
			log.Printf("Worker %d: claim pending error: %v", w.id, err)
		}
		if reclaimed {
			continue
		}

		if err := w.consume(ctx); err != nil {
			log.Printf("Worker %d: consume error: %v", w.id, err)
			time.Sleep(PollInterval)
		}
	}
}

func (w *Worker) Stop() {
	close(w.stop)
}

func (w *Worker) claimPending(ctx context.Context) (bool, error) {
	pending, err := w.redis.XPendingExt(ctx, &redis.XPendingExtArgs{
		Stream: StreamKey,
		Group:  ConsumerGroup,
		Start:  "-",
		End:    "+",
		Count:  10,
	}).Result()

	if err != nil {
		return false, err
	}

	for _, p := range pending {
		if p.Idle >= ClaimTimeout {
			claimed, err := w.redis.XClaim(ctx, &redis.XClaimArgs{
				Stream:   StreamKey,
				Group:    ConsumerGroup,
				Consumer: w.consumer,
				MinIdle:  ClaimTimeout,
				Messages: []string{p.ID},
			}).Result()

			if err != nil {
				continue
			}

			for _, msg := range claimed {
				log.Printf("Worker %d: reclaimed message %s (idle %v)", w.id, msg.ID, p.Idle)
				w.processMessage(ctx, msg)
				return true, nil
			}
		}
	}

	return false, nil
}

func (w *Worker) consume(ctx context.Context) error {
	streams, err := w.redis.XReadGroup(ctx, &redis.XReadGroupArgs{
		Group:    ConsumerGroup,
		Consumer: w.consumer,
		Streams:  []string{StreamKey, ">"},
		Count:    1,
		Block:    2 * time.Second,
	}).Result()

	if err != nil {
		if err == redis.Nil {
			return nil
		}
		return err
	}

	for _, stream := range streams {
		for _, msg := range stream.Messages {
			w.processMessage(ctx, msg)
		}
	}

	return nil
}

func (w *Worker) processMessage(ctx context.Context, msg redis.XMessage) {
	taskID, ok := msg.Values["task_id"].(string)
	if !ok {
		log.Printf("Worker %d: missing task_id in message %s", w.id, msg.ID)
		w.queue.Acknowledge(ctx, msg.ID)
		return
	}

	task, err := w.redis.LoadTask(ctx, taskID)
	if err != nil {
		log.Printf("Worker %d: load task %s error: %v", w.id, taskID, err)
		w.queue.Acknowledge(ctx, msg.ID)
		return
	}

	task.StreamID = msg.ID

	w.processSafe(ctx, task)
}

func (w *Worker) processSafe(ctx context.Context, task *Task) {
	defer func() {
		if r := recover(); r != nil {
			errMsg := fmt.Sprintf("panic: %v", r)
			log.Printf("Worker %d: task %s panicked: %s", w.id, task.ID, errMsg)
			w.handleFailure(ctx, task, errMsg)
		}
	}()

	w.process(ctx, task)
}

func (w *Worker) process(ctx context.Context, task *Task) {
	startTime := nowFunc()
	w.queue.Update(task.ID, func(t *Task) {
		t.Status = TaskStatusRunning
		t.StartedAt = &startTime
		t.StreamID = task.StreamID
	})

	result, err := w.execute(task)
	endTime := nowFunc()

	if err != nil {
		w.queue.Update(task.ID, func(t *Task) {
			t.LastError = err.Error()
		})
		w.handleFailure(ctx, task, err.Error())
		return
	}

	resultJSON, _ := json.Marshal(result)
	w.queue.Update(task.ID, func(t *Task) {
		t.Status = TaskStatusCompleted
		t.EndedAt = &endTime
		t.Result = json.RawMessage(resultJSON)
		t.LastError = ""
	})

	if task.StreamID != "" {
		w.queue.Acknowledge(ctx, task.StreamID)
	}

	log.Printf("Worker %d: task %s completed", w.id, task.ID)
}

func (w *Worker) handleFailure(ctx context.Context, task *Task, errMsg string) {
	task.RetryCount++

	if task.RetryCount > w.redis.MaxRetries() {
		log.Printf("Worker %d: task %s exceeded max retries (%d), moving to DLQ", w.id, task.ID, w.redis.MaxRetries())
		w.queue.MoveToDLQ(ctx, task, errMsg)
		return
	}

	log.Printf("Worker %d: task %s failed (retry %d/%d): %s", w.id, task.ID, task.RetryCount, w.redis.MaxRetries(), errMsg)

	endTime := nowFunc()
	w.queue.Update(task.ID, func(t *Task) {
		t.Status = TaskStatusPending
		t.RetryCount = task.RetryCount
		t.LastError = errMsg
		t.EndedAt = &endTime
	})

	if task.StreamID != "" {
		w.queue.Acknowledge(ctx, task.StreamID)
	}

	_, err := w.redis.XAdd(ctx, &redis.XAddArgs{
		Stream: StreamKey,
		Values: map[string]interface{}{
			"task_id":     task.ID,
			"type":        task.Type,
			"retry_count": task.RetryCount,
		},
	}).Result()

	if err != nil {
		log.Printf("Worker %d: requeue task %s error: %v", w.id, task.ID, err)
	}
}

func (w *Worker) execute(task *Task) (interface{}, error) {
	switch task.Type {
	case "echo":
		return task.Payload, nil
	case "sum":
		return w.handleSum(task.Payload)
	case "delay":
		return w.handleDelay(task.Payload)
	default:
		return nil, fmt.Errorf("unknown task type: %s", task.Type)
	}
}

func (w *Worker) handleSum(payload json.RawMessage) (interface{}, error) {
	var nums []float64
	if err := json.Unmarshal(payload, &nums); err != nil {
		return nil, fmt.Errorf("payload must be array of numbers")
	}
	sum := 0.0
	for _, n := range nums {
		sum += n
	}
	return map[string]interface{}{"sum": sum, "count": len(nums)}, nil
}

func (w *Worker) handleDelay(payload json.RawMessage) (interface{}, error) {
	var params struct {
		Seconds int `json:"seconds"`
	}
	if err := json.Unmarshal(payload, &params); err != nil {
		return nil, fmt.Errorf("invalid delay payload")
	}
	if params.Seconds <= 0 {
		params.Seconds = 1
	}
	if params.Seconds > 300 {
		return nil, fmt.Errorf("delay too long (max 300s)")
	}
	time.Sleep(time.Duration(params.Seconds) * time.Second)
	return map[string]interface{}{"slept_seconds": params.Seconds}, nil
}
