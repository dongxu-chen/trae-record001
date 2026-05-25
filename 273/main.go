package main

import (
	"context"
	"encoding/json"
	"flag"
	"fmt"
	"log"
	"os"
	"os/signal"
	"scheduler/config"
	"scheduler/internal/api"
	"scheduler/internal/discovery"
	"scheduler/internal/models"
	"scheduler/internal/queue"
	"scheduler/internal/scheduler"
	"scheduler/internal/store"
	"syscall"
	"time"

	"github.com/gin-gonic/gin"
)

func main() {
	configPath := flag.String("config", "config.yaml", "Path to config file")
	nodeID := flag.String("node-id", "", "Node ID (overrides config)")
	flag.Parse()

	cfg, err := config.Load(*configPath)
	if err != nil {
		log.Fatalf("Failed to load config: %v", err)
	}

	if *nodeID != "" {
		cfg.Server.NodeID = *nodeID
	}

	log.Printf("Starting scheduler node: %s", cfg.Server.NodeID)

	store, err := store.NewPostgresStore(
		cfg.Postgres.Host,
		cfg.Postgres.Port,
		cfg.Postgres.User,
		cfg.Postgres.Password,
		cfg.Postgres.DBName,
		cfg.Postgres.MaxConnections,
	)
	if err != nil {
		log.Fatalf("Failed to connect to postgres: %v", err)
	}
	defer store.Close()

	discovery, err := discovery.NewEtcdClient(
		cfg.Etcd.Endpoints,
		cfg.Etcd.DialTimeout,
		cfg.Etcd.RootPrefix,
		cfg.Etcd.LeaseTTL,
	)
	if err != nil {
		log.Fatalf("Failed to connect to etcd: %v", err)
	}
	defer discovery.Close()

	queue, err := queue.NewRedisQueue(
		cfg.Redis.Addr,
		cfg.Redis.Password,
		cfg.Redis.DB,
		cfg.Redis.PoolSize,
		cfg.Redis.TaskQueuePrefix,
		cfg.Redis.NodeTasksPrefix,
	)
	if err != nil {
		log.Fatalf("Failed to connect to redis: %v", err)
	}
	defer queue.Close()

	sched := scheduler.NewScheduler(cfg, store, discovery, queue)

	registerExampleHandlers(sched)

	if err := sched.Start(); err != nil {
		log.Fatalf("Failed to start scheduler: %v", err)
	}
	defer sched.Stop()

	r := gin.Default()

	handler := api.NewHandler(sched)
	handler.RegisterRoutes(r)

	addr := fmt.Sprintf("%s:%d", cfg.Server.Host, cfg.Server.Port)
	go func() {
		log.Printf("HTTP server listening on %s", addr)
		if err := r.Run(addr); err != nil {
			log.Printf("HTTP server error: %v", err)
		}
	}()

	sigCh := make(chan os.Signal, 1)
	signal.Notify(sigCh, syscall.SIGINT, syscall.SIGTERM)
	<-sigCh

	log.Println("Shutting down...")
}

func registerExampleHandlers(s *scheduler.Scheduler) {
	s.RegisterHandler("echo", func(ctx context.Context, task *models.Task) error {
		log.Printf("Echo task executed: %s, payload: %s", task.ID, string(task.Payload))
		return nil
	})

	s.RegisterHandler("log", func(ctx context.Context, task *models.Task) error {
		var data map[string]interface{}
		if err := json.Unmarshal(task.Payload, &data); err != nil {
			return err
		}
		log.Printf("Log task %s: %+v", task.ID, data)
		return nil
	})

	s.RegisterHandler("heavy_compute", func(ctx context.Context, task *models.Task) error {
		log.Printf("Starting heavy compute task: %s (shard %d/%d)",
			task.ID, task.ShardIndex, task.ShardTotal)

		select {
		case <-time.After(100 * time.Millisecond):
		case <-ctx.Done():
			return ctx.Err()
		}

		log.Printf("Completed heavy compute task: %s", task.ID)
		return nil
	})

	s.RegisterHandler("data_processing", func(ctx context.Context, task *models.Task) error {
		log.Printf("Data processing task: %s, shard: %d/%d",
			task.ID, task.ShardIndex, task.ShardTotal)
		return nil
	})
}
