package main

import (
	"context"
	"log"
	"net/http"
	"os"
	"os/signal"
	"syscall"
	"time"

	"clickhouse-rate-limiter/api"
	"clickhouse-rate-limiter/clickhouse"
	"clickhouse-rate-limiter/config"
	"clickhouse-rate-limiter/limiter"
	"clickhouse-rate-limiter/priority"
)

func main() {
	cfg := config.Load()

	chClient, err := clickhouse.NewClient(cfg.ClickHouse)
	if err != nil {
		log.Fatalf("Failed to create ClickHouse client: %v", err)
	}
	defer chClient.Close()

	rateLimiter := limiter.NewRateLimiter(cfg.Limiter)

	priorityQueue := priority.NewPriorityQueue(cfg.Priority)

	handler := api.NewHandler(chClient, rateLimiter, priorityQueue, cfg)

	server := &http.Server{
		Addr:         cfg.Server.Address,
		Handler:      handler.Router(),
		ReadTimeout:  cfg.Server.ReadTimeout,
		WriteTimeout: cfg.Server.WriteTimeout,
	}

	go func() {
		log.Printf("Server starting on %s", cfg.Server.Address)
		if err := server.ListenAndServe(); err != nil && err != http.ErrServerClosed {
			log.Fatalf("Server failed: %v", err)
		}
	}()

	quit := make(chan os.Signal, 1)
	signal.Notify(quit, syscall.SIGINT, syscall.SIGTERM)
	<-quit

	log.Println("Shutting down server...")

	ctx, cancel := context.WithTimeout(context.Background(), 10*time.Second)
	defer cancel()

	if err := server.Shutdown(ctx); err != nil {
		log.Fatalf("Server forced to shutdown: %v", err)
	}

	log.Println("Server exited")
}
