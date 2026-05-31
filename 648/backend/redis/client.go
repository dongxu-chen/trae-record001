package redis

import (
	"context"
	"fmt"
	"redis-keyspace-notifier/config"
	"redis-keyspace-notifier/logger"
	"sync"

	"github.com/go-redis/redis/v8"
	"go.uber.org/zap"
)

type Client struct {
	clients map[int]*redis.Client
	mu      sync.RWMutex
}

var (
	instance *Client
	once     sync.Once
)

func GetClient() *Client {
	once.Do(func() {
		instance = &Client{
			clients: make(map[int]*redis.Client),
		}
	})
	return instance
}

func (c *Client) Connect() error {
	c.mu.Lock()
	defer c.mu.Unlock()

	for _, db := range config.AppConfig.Redis.Databases {
		client := redis.NewClient(&redis.Options{
			Addr:     config.AppConfig.Redis.Address,
			Password: config.AppConfig.Redis.Password,
			DB:       db,
		})

		ctx := context.Background()
		if err := client.Ping(ctx).Err(); err != nil {
			return fmt.Errorf("failed to connect to Redis DB %d: %w", db, err)
		}

		if err := c.enableKeyspaceNotifications(client); err != nil {
			logger.Warn("Failed to enable keyspace notifications", zap.Int("db", db), zap.Error(err))
		}

		c.clients[db] = client
		logger.Info("Connected to Redis", zap.Int("db", db))
	}

	return nil
}

func (c *Client) enableKeyspaceNotifications(client *redis.Client) error {
	ctx := context.Background()
	return client.ConfigSet(ctx, "notify-keyspace-events", "Exg").Err()
}

func (c *Client) GetDB(db int) (*redis.Client, bool) {
	c.mu.RLock()
	defer c.mu.RUnlock()
	client, exists := c.clients[db]
	return client, exists
}

func (c *Client) GetAllDBs() map[int]*redis.Client {
	c.mu.RLock()
	defer c.mu.RUnlock()
	result := make(map[int]*redis.Client)
	for db, client := range c.clients {
		result[db] = client
	}
	return result
}

func (c *Client) Close() {
	c.mu.Lock()
	defer c.mu.Unlock()

	for db, client := range c.clients {
		if err := client.Close(); err != nil {
			logger.Error("Error closing Redis connection", zap.Int("db", db), zap.Error(err))
		}
	}
}
