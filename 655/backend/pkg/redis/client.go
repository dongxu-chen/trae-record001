package redis

import (
	"context"
	"encoding/json"
	"fmt"
	"time"

	"github.com/go-redis/redis/v8"
)

type Client struct {
	client *redis.Client
	ctx    context.Context
}

type Config struct {
	Addr     string
	Password string
	DB       int
}

func NewClient(config Config) (*Client, error) {
	ctx := context.Background()
	rdb := redis.NewClient(&redis.Options{
		Addr:     config.Addr,
		Password: config.Password,
		DB:       config.DB,
	})

	_, err := rdb.Ping(ctx).Result()
	if err != nil {
		return nil, fmt.Errorf("failed to connect to redis: %w", err)
	}

	return &Client{
		client: rdb,
		ctx:    ctx,
	}, nil
}

func (c *Client) Set(key string, value interface{}, expiration time.Duration) error {
	data, err := json.Marshal(value)
	if err != nil {
		return fmt.Errorf("failed to marshal value: %w", err)
	}

	return c.client.Set(c.ctx, key, data, expiration).Err()
}

func (c *Client) Get(key string, dest interface{}) error {
	data, err := c.client.Get(c.ctx, key).Result()
	if err == redis.Nil {
		return fmt.Errorf("key not found: %s", key)
	}
	if err != nil {
		return fmt.Errorf("failed to get value: %w", err)
	}

	return json.Unmarshal([]byte(data), dest)
}

func (c *Client) Delete(key string) error {
	return c.client.Del(c.ctx, key).Err()
}

func (c *Client) DeletePattern(pattern string) error {
	keys, err := c.client.Keys(c.ctx, pattern).Result()
	if err != nil {
		return err
	}
	if len(keys) == 0 {
		return nil
	}
	return c.client.Del(c.ctx, keys...).Err()
}

func (c *Client) Exists(key string) (bool, error) {
	count, err := c.client.Exists(c.ctx, key).Result()
	if err != nil {
		return false, err
	}
	return count > 0, nil
}

func (c *Client) LPush(key string, values ...interface{}) error {
	return c.client.LPush(c.ctx, key, values...).Err()
}

func (c *Client) RPush(key string, values ...interface{}) error {
	return c.client.RPush(c.ctx, key, values...).Err()
}

func (c *Client) LRange(key string, start, stop int64) ([]string, error) {
	return c.client.LRange(c.ctx, key, start, stop).Result()
}

func (c *Client) ZAdd(key string, score float64, member string) error {
	return c.client.ZAdd(c.ctx, key, &redis.Z{Score: score, Member: member}).Err()
}

func (c *Client) ZRevRange(key string, start, stop int64) ([]string, error) {
	return c.client.ZRevRange(c.ctx, key, start, stop).Result()
}

func (c *Client) Incr(key string) (int64, error) {
	return c.client.Incr(c.ctx, key).Result()
}

func (c *Client) IncrBy(key string, value int64) (int64, error) {
	return c.client.IncrBy(c.ctx, key, value).Result()
}

func (c *Client) HSet(key, field string, value interface{}) error {
	data, err := json.Marshal(value)
	if err != nil {
		return err
	}
	return c.client.HSet(c.ctx, key, field, data).Err()
}

func (c *Client) HGet(key, field string, dest interface{}) error {
	data, err := c.client.HGet(c.ctx, key, field).Result()
	if err == redis.Nil {
		return fmt.Errorf("field not found: %s", field)
	}
	if err != nil {
		return err
	}
	return json.Unmarshal([]byte(data), dest)
}

func (c *Client) HGetAll(key string) (map[string]string, error) {
	return c.client.HGetAll(c.ctx, key).Result()
}

func (c *Client) HDel(key string, fields ...string) error {
	return c.client.HDel(c.ctx, key, fields...).Err()
}

func (c *Client) Expire(key string, expiration time.Duration) error {
	return c.client.Expire(c.ctx, key, expiration).Err()
}

func (c *Client) Keys(pattern string) ([]string, error) {
	return c.client.Keys(c.ctx, pattern).Result()
}

func (c *Client) Close() error {
	return c.client.Close()
}

func (c *Client) GetClient() *redis.Client {
	return c.client
}

func (c *Client) GetContext() context.Context {
	return c.ctx
}
