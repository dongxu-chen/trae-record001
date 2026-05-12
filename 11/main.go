package main

import (
	"context"
	"log"
	"net/http"
	"os"
	"os/signal"
	"syscall"
	"time"

	"github.com/gin-gonic/gin"
)

const (
	WorkerCount  = 3
	QueueBuffer  = 100
	ServerAddr   = ":8080"
)

func main() {
	ctx, cancel := context.WithCancel(context.Background())
	defer cancel()

	redisCfg := NewRedisConfigFromEnv()
	redisClient, err := NewRedisClient(redisCfg)
	if err != nil {
		log.Fatalf("Failed to connect to Redis: %v", err)
	}
	defer redisClient.Close()

	if err := redisClient.InitStreams(ctx); err != nil {
		log.Fatalf("Failed to init streams: %v", err)
	}

	queue := NewTaskQueue(redisClient, QueueBuffer)

	workers := make([]*Worker, WorkerCount)
	for i := 0; i < WorkerCount; i++ {
		workers[i] = NewWorker(i+1, queue, redisClient)
		workers[i].Start(ctx)
	}

	router := setupRouter(queue, redisClient)

	srv := &http.Server{
		Addr:    ServerAddr,
		Handler: router,
	}

	go func() {
		log.Printf("Server starting on %s (Redis: %s, Group: %s, Workers: %d)",
			ServerAddr, redisCfg.Addr, ConsumerGroup, WorkerCount)
		if err := srv.ListenAndServe(); err != nil && err != http.ErrServerClosed {
			log.Fatalf("Server failed: %s", err)
		}
	}()

	quit := make(chan os.Signal, 1)
	signal.Notify(quit, syscall.SIGINT, syscall.SIGTERM)
	<-quit

	log.Println("Shutting down server...")
	cancel()

	for _, w := range workers {
		w.Stop()
	}

	shutdownCtx, shutdownCancel := context.WithTimeout(context.Background(), 10*time.Second)
	defer shutdownCancel()
	if err := srv.Shutdown(shutdownCtx); err != nil {
		log.Fatalf("Server forced to shutdown: %s", err)
	}

	log.Println("Server exiting")
}

func setupRouter(queue *TaskQueue, rc *RedisClient) *gin.Engine {
	r := gin.Default()

	r.MaxMultipartMemory = 8 << 20
	r.Use(func(c *gin.Context) {
		c.Request.Body = http.MaxBytesReader(c.Writer, c.Request.Body, MaxPayloadSize+4096)
		c.Next()
	})

	r.POST("/tasks", func(c *gin.Context) {
		var req TaskRequest
		if err := c.ShouldBindJSON(&req); err != nil {
			c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
			return
		}

		if len(req.Payload) > MaxPayloadSize {
			c.JSON(http.StatusRequestEntityTooLarge, gin.H{"error": "payload too large"})
			return
		}

		task := queue.Submit(req.Type, req.Payload)
		if task == nil {
			c.JSON(http.StatusInternalServerError, gin.H{"error": "failed to submit task"})
			return
		}
		c.JSON(http.StatusAccepted, TaskResponse{Task: task})
	})

	r.GET("/tasks", func(c *gin.Context) {
		tasks := queue.List()
		c.JSON(http.StatusOK, gin.H{"tasks": tasks})
	})

	r.GET("/tasks/:id", func(c *gin.Context) {
		id := c.Param("id")
		task, ok := queue.Get(id)
		if !ok {
			c.JSON(http.StatusNotFound, gin.H{"error": "task not found"})
			return
		}
		c.JSON(http.StatusOK, TaskResponse{Task: task})
	})

	r.GET("/dlq", func(c *gin.Context) {
		ctx := c.Request.Context()
		tasks, err := queue.ListDLQ(ctx)
		if err != nil {
			c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
			return
		}
		c.JSON(http.StatusOK, gin.H{"tasks": tasks, "count": len(tasks)})
	})

	r.POST("/dlq/:id/retry", func(c *gin.Context) {
		ctx := c.Request.Context()
		id := c.Param("id")
		if err := queue.RequeueFromDLQ(ctx, id); err != nil {
			c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
			return
		}
		c.JSON(http.StatusOK, gin.H{"message": "task requeued"})
	})

	r.GET("/health", func(c *gin.Context) {
		ctx := c.Request.Context()
		if err := rc.Ping(ctx).Err(); err != nil {
			c.JSON(http.StatusServiceUnavailable, gin.H{"status": "unhealthy", "redis": "down"})
			return
		}
		c.JSON(http.StatusOK, gin.H{"status": "healthy", "redis": "ok"})
	})

	return r
}
