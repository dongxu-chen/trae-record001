package main

import (
	"context"
	"errors"
	"fmt"
	"log"
	"os"
	"time"

	"github.com/redis/go-redis/v9"
)

const (
	StreamKey       = "tasks:stream"
	DLQStreamKey    = "tasks:dlq"
	TaskHashPrefix  = "tasks:hash:"
	ConsumerGroup   = "task-workers"
	DefaultMaxRetries = 3
)

type RedisConfig struct {
	Addr        string
	Password    string
	DB          int
	PoolSize    int
	MinIdleConn int
	MaxRetries  int
}

func NewRedisConfigFromEnv() *RedisConfig {
	return &RedisConfig{
		Addr:        getEnv("REDIS_ADDR", "localhost:6379"),
		Password:    getEnv("REDIS_PASSWORD", ""),
		DB:          getEnvInt("REDIS_DB", 0),
		PoolSize:    getEnvInt("REDIS_POOL_SIZE", 20),
		MinIdleConn: getEnvInt("REDIS_MIN_IDLE", 5),
		MaxRetries:  getEnvInt("MAX_RETRIES", DefaultMaxRetries),
	}
}

func getEnv(key, fallback string) string {
	if v := os.Getenv(key); v != "" {
		return v
	}
	return fallback
}

func getEnvInt(key string, fallback int) int {
	v := os.Getenv(key)
	if v == "" {
		return fallback
	}
	var i int
	fmt.Sscanf(v, "%d", &i)
	return i
}

type RedisClient struct {
	*redis.Client
	config *RedisConfig
}

func NewRedisClient(cfg *RedisConfig) (*RedisClient, error) {
	if cfg == nil {
		cfg = NewRedisConfigFromEnv()
	}

	client := redis.NewClient(&redis.Options{
		Addr:         cfg.Addr,
		Password:     cfg.Password,
		DB:           cfg.DB,
		PoolSize:     cfg.PoolSize,
		MinIdleConns: cfg.MinIdleConn,
		ReadTimeout:  5 * time.Second,
		WriteTimeout: 5 * time.Second,
	})

	ctx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
	defer cancel()

	if err := client.Ping(ctx).Err(); err != nil {
		return nil, fmt.Errorf("redis ping failed: %w", err)
	}

	return &RedisClient{Client: client, config: cfg}, nil
}

func (r *RedisClient) InitStreams(ctx context.Context) error {
	err := r.XGroupCreateMkStream(ctx, StreamKey, ConsumerGroup, "0").Err()
	if err != nil && !errors.Is(err, redis.Nil) && !isBusyGroupError(err) {
		return fmt.Errorf("create stream group failed: %w", err)
	}

	err = r.XGroupCreateMkStream(ctx, DLQStreamKey, ConsumerGroup, "0").Err()
	if err != nil && !errors.Is(err, redis.Nil) && !isBusyGroupError(err) {
		return fmt.Errorf("create dlq group failed: %w", err)
	}

	log.Println("Redis streams initialized")
	return nil
}

func (r *RedisClient) StoreTask(ctx context.Context, task *Task) error {
	key := TaskHashPrefix + task.ID

	data := map[string]interface{}{
		"id":         task.ID,
		"type":       task.Type,
		"payload":    string(task.Payload),
		"status":     string(task.Status),
		"retry_count": task.RetryCount,
		"created_at": task.CreatedAt.UnixNano(),
	}
	if task.StartedAt != nil {
		data["started_at"] = task.StartedAt.UnixNano()
	}
	if task.EndedAt != nil {
		data["ended_at"] = task.EndedAt.UnixNano()
	}
	if task.Error != "" {
		data["error"] = task.Error
	}
	if task.StreamID != "" {
		data["stream_id"] = task.StreamID
	}
	if task.LastError != "" {
		data["last_error"] = task.LastError
	}

	return r.HSet(ctx, key, data).Err()
}

func (r *RedisClient) LoadTask(ctx context.Context, id string) (*Task, error) {
	key := TaskHashPrefix + id
	data, err := r.HGetAll(ctx, key).Result()
	if err != nil {
		return nil, err
	}
	if len(data) == 0 {
		return nil, errors.New("task not found")
	}

	task := &Task{
		ID:        data["id"],
		Type:      data["type"],
		Payload:   json.RawMessage(data["payload"]),
		Status:    TaskStatus(data["status"]),
		Error:     data["error"],
		LastError: data["last_error"],
		StreamID:  data["stream_id"],
	}

	if createdStr, ok := data["created_at"]; ok {
		var ts int64
		fmt.Sscanf(createdStr, "%d", &ts)
		t := time.Unix(0, ts)
		task.CreatedAt = t
	}
	if startedStr, ok := data["started_at"]; ok && startedStr != "" {
		var ts int64
		fmt.Sscanf(startedStr, "%d", &ts)
		t := time.Unix(0, ts)
		task.StartedAt = &t
	}
	if endedStr, ok := data["ended_at"]; ok && endedStr != "" {
		var ts int64
		fmt.Sscanf(endedStr, "%d", &ts)
		t := time.Unix(0, ts)
		task.EndedAt = &t
	}
	if retryStr, ok := data["retry_count"]; ok {
		var n int
		fmt.Sscanf(retryStr, "%d", &n)
		task.RetryCount = n
	}

	return task, nil
}

func (r *RedisClient) MaxRetries() int {
	return r.config.MaxRetries
}

func isBusyGroupError(err error) bool {
	return err != nil && (err.Error() == "BUSYGROUP Consumer Group name already exists" ||
		len(err.Error()) > 9 && err.Error()[:9] == "BUSYGROUP")
}
