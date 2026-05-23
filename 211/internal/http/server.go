package http

import (
	"context"
	"log"
	"net/http"
	"os"
	"os/signal"
	"syscall"
	"time"

	"scheduler/internal/executor"
	"scheduler/internal/http/handlers"
	"scheduler/internal/scheduler"
	"scheduler/internal/store"
	"scheduler/pkg/lock"

	"github.com/gin-gonic/gin"
)

type Server struct {
	engine    *gin.Engine
	store     *store.MySQLStore
	locker    *lock.RedisLock
	scheduler *scheduler.Scheduler
	executor  *executor.Executor
	httpAddr  string
}

func NewServer(store *store.MySQLStore, locker *lock.RedisLock, sched *scheduler.Scheduler, exec *executor.Executor, httpAddr string) *Server {
	engine := gin.Default()

	return &Server{
		engine:    engine,
		store:     store,
		locker:    locker,
		scheduler: sched,
		executor:  exec,
		httpAddr:  httpAddr,
	}
}

func (s *Server) setupRoutes() {
	taskHandler := handlers.NewTaskHandler(s.store, s.scheduler)

	api := s.engine.Group("/api/v1")
	{
		tasks := api.Group("/tasks")
		{
			tasks.POST("", taskHandler.CreateTask)
			tasks.GET("", taskHandler.ListTasks)
			tasks.GET("/:id", taskHandler.GetTask)
			tasks.PUT("/:id", taskHandler.UpdateTask)
			tasks.DELETE("/:id", taskHandler.DeleteTask)
			tasks.POST("/:id/trigger", taskHandler.TriggerTask)
			tasks.GET("/:id/executions", taskHandler.GetTaskExecutions)
			tasks.GET("/:id/audit", taskHandler.GetTaskAuditLogs)
		}

		executions := api.Group("/executions")
		{
			executions.GET("", taskHandler.ListAllExecutions)
			executions.GET("/:id", taskHandler.GetExecution)
		}

		audit := api.Group("/audit")
		{
			audit.GET("", taskHandler.ListAuditLogs)
		}

		workers := api.Group("/workers")
		{
			workers.GET("", taskHandler.ListWorkerNodes)
		}
	}

	s.engine.GET("/health", func(c *gin.Context) {
		c.JSON(http.StatusOK, gin.H{"status": "ok"})
	})
}

func (s *Server) Start() error {
	s.setupRoutes()

	ctx, cancel := context.WithCancel(context.Background())
	defer cancel()

	if err := s.scheduler.Start(ctx); err != nil {
		return err
	}

	if err := s.executor.Start(ctx); err != nil {
		return err
	}

	httpServer := &http.Server{
		Addr:    s.httpAddr,
		Handler: s.engine,
	}

	go func() {
		log.Printf("HTTP server starting on %s", s.httpAddr)
		if err := httpServer.ListenAndServe(); err != nil && err != http.ErrServerClosed {
			log.Fatalf("Failed to start HTTP server: %v", err)
		}
	}()

	quit := make(chan os.Signal, 1)
	signal.Notify(quit, syscall.SIGINT, syscall.SIGTERM)
	<-quit

	log.Println("Shutting down server...")

	shutdownCtx, shutdownCancel := context.WithTimeout(context.Background(), 10*time.Second)
	defer shutdownCancel()

	if err := httpServer.Shutdown(shutdownCtx); err != nil {
		log.Printf("HTTP server forced to shutdown: %v", err)
	}

	s.scheduler.Stop()
	s.executor.Stop()

	log.Println("Server exited properly")
	return nil
}
