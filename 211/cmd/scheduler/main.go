package main

import (
	"log"

	"scheduler/config"
	"scheduler/internal/executor"
	"scheduler/internal/http"
	"scheduler/internal/scheduler"
	"scheduler/internal/store"
	"scheduler/pkg/lock"
)

func main() {
	cfg := config.Load()

	store, err := store.NewMySQLStore(cfg.MySQLDSN)
	if err != nil {
		log.Fatalf("Failed to connect to MySQL: %v", err)
	}
	log.Println("Connected to MySQL successfully")

	locker, err := lock.NewRedisLock(cfg.RedisAddr, cfg.RedisPassword, cfg.RedisDB)
	if err != nil {
		log.Fatalf("Failed to connect to Redis: %v", err)
	}
	log.Println("Connected to Redis successfully")

	sched := scheduler.NewScheduler(store, locker, cfg.SchedulerID)
	exec := executor.NewExecutor(store, locker, sched, cfg.SchedulerID, 5)

	exec.RegisterHandler("http", executor.HTTPTaskHandler)
	exec.RegisterHandler("log", executor.LogTaskHandler)

	server := http.NewServer(store, locker, sched, exec, cfg.HTTPPort)
	if err := server.Start(); err != nil {
		log.Fatalf("Server error: %v", err)
	}
}
