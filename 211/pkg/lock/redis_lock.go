package lock

import (
	"context"
	"fmt"
	"time"

	"github.com/go-redis/redis/v8"
	"github.com/google/uuid"
)

type RedisLock struct {
	client *redis.Client
	prefix string
}

type Lock struct {
	key    string
	value  string
	client *redis.Client
}

func NewRedisLock(addr, password string, db int) (*RedisLock, error) {
	client := redis.NewClient(&redis.Options{
		Addr:     addr,
		Password: password,
		DB:       db,
	})

	ctx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
	defer cancel()

	if err := client.Ping(ctx).Err(); err != nil {
		return nil, fmt.Errorf("redis ping failed: %w", err)
	}

	return &RedisLock{
		client: client,
		prefix: "scheduler:lock:",
	}, nil
}

func (rl *RedisLock) GetClient() *redis.Client {
	return rl.client
}

func (rl *RedisLock) Acquire(ctx context.Context, key string, ttl time.Duration) (*Lock, bool, error) {
	lockKey := rl.prefix + key
	value := uuid.New().String()

	ok, err := rl.client.SetNX(ctx, lockKey, value, ttl).Result()
	if err != nil {
		return nil, false, err
	}

	if !ok {
		return nil, false, nil
	}

	return &Lock{
		key:    lockKey,
		value:  value,
		client: rl.client,
	}, true, nil
}

func (l *Lock) Release(ctx context.Context) (bool, error) {
	script := `
		if redis.call("GET", KEYS[1]) == ARGV[1] then
			return redis.call("DEL", KEYS[1])
		else
			return 0
		end
	`

	result, err := l.client.Eval(ctx, script, []string{l.key}, l.value).Result()
	if err != nil {
		return false, err
	}

	return result.(int64) == 1, nil
}

func (rl *RedisLock) TryLock(ctx context.Context, key string, ttl time.Duration, maxAttempts int, retryInterval time.Duration) (*Lock, bool, error) {
	for i := 0; i < maxAttempts; i++ {
		lock, acquired, err := rl.Acquire(ctx, key, ttl)
		if err != nil {
			return nil, false, err
		}
		if acquired {
			return lock, true, nil
		}
		select {
		case <-ctx.Done():
			return nil, false, ctx.Err()
		case <-time.After(retryInterval):
		}
	}
	return nil, false, nil
}
