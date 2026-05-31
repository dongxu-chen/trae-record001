package main

import (
	"context"
	"flag"
	"log"
	"os"
	"os/signal"
	"syscall"
	"time"

	"redis-cluster-scaler/internal/api"
	"redis-cluster-scaler/internal/backup"
	"redis-cluster-scaler/internal/cluster"
	"redis-cluster-scaler/internal/cost"
	"redis-cluster-scaler/internal/failover"
	"redis-cluster-scaler/internal/migration"
	"redis-cluster-scaler/internal/monitor"
	"redis-cluster-scaler/internal/scaler"
	"redis-cluster-scaler/internal/simulation"
	"redis-cluster-scaler/pkg/config"
)

func main() {
	configPath := flag.String("config", "config.yaml", "path to configuration file")
	flag.Parse()

	cfg, err := config.Load(*configPath)
	if err != nil {
		log.Fatalf("Failed to load config: %v", err)
	}

	log.Println("Starting Redis Cluster Auto-Scaler...")

	clusterMgr := cluster.NewManager(cfg.Cluster)
	defer clusterMgr.Close()

	ctx, cancel := context.WithCancel(context.Background())
	defer cancel()

	for i := 0; i < 10; i++ {
		err = clusterMgr.Ping(ctx)
		if err == nil {
			break
		}
		log.Printf("Waiting for Redis cluster connection... (attempt %d/10)", i+1)
		time.Sleep(3 * time.Second)
	}
	if err != nil {
		log.Fatalf("Failed to connect to Redis cluster: %v", err)
	}
	log.Println("Connected to Redis cluster")

	mon := monitor.New(
		clusterMgr,
		cfg.Cluster,
		cfg.Monitor.HistorySize,
		time.Duration(cfg.Monitor.IntervalSeconds)*time.Second,
	)
	go mon.Start(ctx)
	log.Println("Monitor started")

	backupMgr := backup.New(cfg.Backup, cfg.Cluster, clusterMgr)
	go backupMgr.Start(ctx)
	log.Println("Backup manager started")

	migrator := migration.New(cfg.Migration, clusterMgr, backupMgr)

	costMgr := cost.New(cfg.Cost, clusterMgr)
	log.Println("Cost manager started")

	simMgr := simulation.New(cfg.Simulation, clusterMgr, costMgr)
	log.Println("Simulation manager started")

	failoverMgr := failover.New(cfg.Failover, cfg.Cluster, clusterMgr)
	go failoverMgr.Start(ctx)
	log.Println("Failover manager started")

	sc := scaler.New(cfg.Scaler, cfg.Cluster, clusterMgr, mon, migrator)
	go sc.Start(ctx)
	log.Println("Scaler started")

	server := api.New(
		cfg.Server.Addr,
		clusterMgr,
		mon,
		sc,
		migrator,
		backupMgr,
		failoverMgr,
		costMgr,
		simMgr,
	)

	sigCh := make(chan os.Signal, 1)
	signal.Notify(sigCh, syscall.SIGINT, syscall.SIGTERM)

	go func() {
		log.Printf("API server starting on %s", cfg.Server.Addr)
		if err := server.Start(); err != nil {
			log.Fatalf("Server error: %v", err)
		}
	}()

	<-sigCh
	log.Println("Shutting down...")

	cancel()

	mon.Stop()
	sc.Stop()
	backupMgr.Stop()
	failoverMgr.Stop()

	log.Println("Shutdown complete")
}
