package queue

import (
	"context"
	"encoding/json"
	"fmt"
	"scheduler/internal/models"
	"time"

	"github.com/go-redis/redis/v8"
)

type RedisQueue struct {
	client           *redis.Client
	taskQueuePrefix  string
	nodeTasksPrefix  string
}

type TaskMessage struct {
	TaskID      string    `json:"task_id"`
	TaskType    string    `json:"task_type"`
	ShardKey    string    `json:"shard_key,omitempty"`
	ShardIndex  int       `json:"shard_index"`
	ShardTotal  int       `json:"shard_total"`
	Priority    int       `json:"priority"`
	ExecuteTime time.Time `json:"execute_time"`
}

func NewRedisQueue(addr, password string, db, poolSize int, taskQueuePrefix, nodeTasksPrefix string) (*RedisQueue, error) {
	client := redis.NewClient(&redis.Options{
		Addr:     addr,
		Password: password,
		DB:       db,
		PoolSize: poolSize,
	})

	ctx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
	defer cancel()

	if err := client.Ping(ctx).Err(); err != nil {
		return nil, err
	}

	return &RedisQueue{
		client:           client,
		taskQueuePrefix:  taskQueuePrefix,
		nodeTasksPrefix:  nodeTasksPrefix,
	}, nil
}

func (q *RedisQueue) Close() error {
	return q.client.Close()
}

func (q *RedisQueue) getReadyQueueKey() string {
	return q.taskQueuePrefix + "ready"
}

func (q *RedisQueue) getDelayQueueKey() string {
	return q.taskQueuePrefix + "delay"
}

func (q *RedisQueue) getNodeTasksKey(nodeID string) string {
	return q.nodeTasksPrefix + nodeID
}

func (q *RedisQueue) EnqueueTask(ctx context.Context, task *models.Task) error {
	msg := &TaskMessage{
		TaskID:      task.ID,
		TaskType:    task.TaskType,
		ShardKey:    task.ShardKey,
		ShardIndex:  task.ShardIndex,
		ShardTotal:  task.ShardTotal,
		Priority:    task.Priority,
		ExecuteTime: task.NextRunTime,
	}

	data, err := json.Marshal(msg)
	if err != nil {
		return err
	}

	now := time.Now()
	if task.NextRunTime.After(now) {
		score := float64(task.NextRunTime.UnixNano()) / 1e6
		return q.client.ZAdd(ctx, q.getDelayQueueKey(), &redis.Z{
			Score:  score,
			Member: data,
		}).Err()
	}

	score := float64(-task.Priority)
	return q.client.ZAdd(ctx, q.getReadyQueueKey(), &redis.Z{
		Score:  score,
		Member: data,
	}).Err()
}

func (q *RedisQueue) DequeueTask(ctx context.Context, nodeID string, timeout time.Duration) (*TaskMessage, error) {
	result, err := q.client.BZPopMin(ctx, timeout, q.getReadyQueueKey()).Result()
	if err != nil {
		if err == redis.Nil {
			return nil, nil
		}
		return nil, err
	}

	if result == nil {
		return nil, nil
	}

	var msg TaskMessage
	if err := json.Unmarshal([]byte(result.Member.(string)), &msg); err != nil {
		return nil, err
	}

	if err := q.client.SAdd(ctx, q.getNodeTasksKey(nodeID), msg.TaskID).Err(); err != nil {
		return nil, err
	}

	return &msg, nil
}

func (q *RedisQueue) TryDequeueTask(ctx context.Context, nodeID string) (*TaskMessage, error) {
	result, err := q.client.ZPopMin(ctx, q.getReadyQueueKey(), 1).Result()
	if err != nil {
		if err == redis.Nil {
			return nil, nil
		}
		return nil, err
	}

	if len(result) == 0 {
		return nil, nil
	}

	var msg TaskMessage
	if err := json.Unmarshal([]byte(result[0].Member.(string)), &msg); err != nil {
		return nil, err
	}

	if err := q.client.SAdd(ctx, q.getNodeTasksKey(nodeID), msg.TaskID).Err(); err != nil {
		return nil, err
	}

	return &msg, nil
}

func (q *RedisQueue) MoveDelayToReady(ctx context.Context) (int64, error) {
	now := float64(time.Now().UnixNano()) / 1e6

	script := `
		local delay_key = KEYS[1]
		local ready_key = KEYS[2]
		local now = tonumber(ARGV[1])
		
		local items = redis.call('ZRANGEBYSCORE', delay_key, '-inf', now, 'WITHSCORES')
		local count = 0
		
		for i = 1, #items, 2 do
			local member = items[i]
			redis.call('ZREM', delay_key, member)
			redis.call('ZADD', ready_key, 0, member)
			count = count + 1
		end
		
		return count
	`

	result, err := q.client.Eval(ctx, script, []string{q.getDelayQueueKey(), q.getReadyQueueKey()}, now).Int64()
	if err != nil {
		return 0, err
	}
	return result, nil
}

func (q *RedisQueue) CompleteTask(ctx context.Context, nodeID, taskID string) error {
	return q.client.SRem(ctx, q.getNodeTasksKey(nodeID), taskID).Err()
}

func (q *RedisQueue) FailTask(ctx context.Context, nodeID, taskID string, retryDelay time.Duration) error {
	if err := q.client.SRem(ctx, q.getNodeTasksKey(nodeID), taskID).Err(); err != nil {
		return err
	}

	retryTime := time.Now().Add(retryDelay)
	score := float64(retryTime.UnixNano()) / 1e6

	taskKey := fmt.Sprintf("%s%s", q.taskQueuePrefix, taskID)
	existing, err := q.client.Get(ctx, taskKey).Result()
	if err == redis.Nil {
		return nil
	}
	if err != nil {
		return err
	}

	return q.client.ZAdd(ctx, q.getDelayQueueKey(), &redis.Z{
		Score:  score,
		Member: existing,
	}).Err()
}

func (q *RedisQueue) RemoveTask(ctx context.Context, taskID string) error {
	taskKey := fmt.Sprintf("%s%s", q.taskQueuePrefix, taskID)
	taskData, err := q.client.Get(ctx, taskKey).Result()
	if err == redis.Nil {
		return nil
	}
	if err != nil {
		return err
	}

	q.client.ZRem(ctx, q.getReadyQueueKey(), taskData)
	q.client.ZRem(ctx, q.getDelayQueueKey(), taskData)
	q.client.Del(ctx, taskKey)

	return nil
}

func (q *RedisQueue) GetNodeTaskCount(ctx context.Context, nodeID string) (int64, error) {
	return q.client.SCard(ctx, q.getNodeTasksKey(nodeID)).Result()
}

func (q *RedisQueue) GetNodeTasks(ctx context.Context, nodeID string) ([]string, error) {
	return q.client.SMembers(ctx, q.getNodeTasksKey(nodeID)).Result()
}

func (q *RedisQueue) ClearNodeTasks(ctx context.Context, nodeID string) error {
	return q.client.Del(ctx, q.getNodeTasksKey(nodeID)).Err()
}

func (q *RedisQueue) RequeueNodeTasks(ctx context.Context, nodeID string) (int64, error) {
	taskIDs, err := q.GetNodeTasks(ctx, nodeID)
	if err != nil {
		return 0, err
	}

	if len(taskIDs) == 0 {
		return 0, nil
	}

	var count int64
	for _, taskID := range taskIDs {
		taskKey := fmt.Sprintf("%s%s", q.taskQueuePrefix, taskID)
		taskData, err := q.client.Get(ctx, taskKey).Result()
		if err == nil && taskData != "" {
			if err := q.client.ZAdd(ctx, q.getReadyQueueKey(), &redis.Z{
				Score:  0,
				Member: taskData,
			}).Err(); err == nil {
				count++
			}
		}
	}

	q.ClearNodeTasks(ctx, nodeID)
	return count, nil
}

func (q *RedisQueue) GetQueueStats(ctx context.Context) (map[string]int64, error) {
	readyCount, err := q.client.ZCard(ctx, q.getReadyQueueKey()).Result()
	if err != nil {
		return nil, err
	}

	delayCount, err := q.client.ZCard(ctx, q.getDelayQueueKey()).Result()
	if err != nil {
		return nil, err
	}

	return map[string]int64{
		"ready": readyCount,
		"delay": delayCount,
	}, nil
}

func (q *RedisQueue) StoreTaskData(ctx context.Context, taskID string, data interface{}) error {
	taskKey := fmt.Sprintf("%s%s", q.taskQueuePrefix, taskID)
	jsonData, err := json.Marshal(data)
	if err != nil {
		return err
	}
	return q.client.Set(ctx, taskKey, jsonData, 24*time.Hour).Err()
}

func (q *RedisQueue) GetTaskData(ctx context.Context, taskID string, dest interface{}) error {
	taskKey := fmt.Sprintf("%s%s", q.taskQueuePrefix, taskID)
	data, err := q.client.Get(ctx, taskKey).Result()
	if err != nil {
		return err
	}
	return json.Unmarshal([]byte(data), dest)
}

type ShardTask struct {
	ShardKey   string
	ShardIndex int
	Payload    []byte
}

func (q *RedisQueue) EnqueueShardTask(ctx context.Context, shardKey string, shardIndex int, payload []byte) error {
	key := fmt.Sprintf("%sshards:%s", q.taskQueuePrefix, shardKey)
	data, err := json.Marshal(&ShardTask{
		ShardKey:   shardKey,
		ShardIndex: shardIndex,
		Payload:    payload,
	})
	if err != nil {
		return err
	}
	return q.client.LPush(ctx, key, data).Err()
}

func (q *RedisQueue) DequeueShardTask(ctx context.Context, shardKey string) (*ShardTask, error) {
	key := fmt.Sprintf("%sshards:%s", q.taskQueuePrefix, shardKey)
	result, err := q.client.RPop(ctx, key).Result()
	if err == redis.Nil {
		return nil, nil
	}
	if err != nil {
		return nil, err
	}

	var task ShardTask
	if err := json.Unmarshal([]byte(result), &task); err != nil {
		return nil, err
	}
	return &task, nil
}

func (q *RedisQueue) GetShardQueueLength(ctx context.Context, shardKey string) (int64, error) {
	key := fmt.Sprintf("%sshards:%s", q.taskQueuePrefix, shardKey)
	return q.client.LLen(ctx, key).Result()
}

func (q *RedisQueue) AcquireLock(ctx context.Context, key string, ttl time.Duration) (bool, error) {
	return q.client.SetNX(ctx, "lock:"+key, "1", ttl).Result()
}

func (q *RedisQueue) ReleaseLock(ctx context.Context, key string) error {
	return q.client.Del(ctx, "lock:"+key).Err()
}
