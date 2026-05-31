package main

import (
	"context"
	"log"
	"os"
	"os/signal"
	"syscall"

	"pulsar-backlog-manager/api"
	"pulsar-backlog-manager/pkg/audit"
	"pulsar-backlog-manager/pkg/autoscaler"
	"pulsar-backlog-manager/pkg/config"
	"pulsar-backlog-manager/pkg/deadletter"
	"pulsar-backlog-manager/pkg/delay"
	"pulsar-backlog-manager/pkg/monitor"
	"pulsar-backlog-manager/pkg/partition"
	"pulsar-backlog-manager/pkg/prediction"
	"pulsar-backlog-manager/pkg/pulsar"
	"pulsar-backlog-manager/pkg/ratelimiter"
	"pulsar-backlog-manager/pkg/replay"
	"pulsar-backlog-manager/pkg/strategy"
)

func main() {
	cfg := config.Load()

	pulsarClient, err := pulsar.NewClient(cfg.Pulsar)
	if err != nil {
		log.Fatalf("Failed to create Pulsar client: %v", err)
	}
	defer pulsarClient.Close()

	auditLog := audit.NewAuditLogger()
	strategyManager := strategy.NewManager(cfg, auditLog)

	monitorService := monitor.NewMonitor(cfg.Monitor, pulsarClient, auditLog)

	autoScaler := autoscaler.NewAutoScaler(cfg.AutoScaler, pulsarClient, strategyManager, auditLog)
	monitorService.RegisterHandler(autoScaler.HandleBacklog)

	partitionManager := partition.NewManager(pulsarClient, strategyManager, auditLog)
	monitorService.RegisterHandler(partitionManager.HandleBacklog)

	rateLimiter := ratelimiter.NewRateLimiter(cfg.RateLimiter, pulsarClient, strategyManager, auditLog)
	monitorService.RegisterHandler(rateLimiter.HandleBacklog)

	predictor := prediction.NewPredictor(cfg.Prediction, pulsarClient, strategyManager, auditLog)
	monitorService.RegisterHandler(predictor.HandleBacklog)

	dlqHandler := deadletter.NewDeadLetterHandler(pulsarClient.GetNativeClient(), strategyManager, auditLog)
	monitorService.RegisterHandler(dlqHandler.HandleBacklog)

	delayProcessor := delay.NewDelayProcessor(strategyManager, auditLog)
	monitorService.RegisterHandler(delayProcessor.HandleBacklog)

	replayManager := replay.NewReplayManager(pulsarClient.GetNativeClient(), strategyManager, auditLog)

	ctx, cancel := context.WithCancel(context.Background())
	defer cancel()

	go monitorService.Start(ctx)
	go predictor.StartPredictionLoop(ctx)
	go autoScaler.StartSmoothScaler(ctx)

	apiServer := api.NewServer(cfg.Server, pulsarClient, monitorService, autoScaler,
		partitionManager, rateLimiter, predictor, strategyManager, auditLog,
		dlqHandler, replayManager, delayProcessor)

	go func() {
		if err := apiServer.Start(); err != nil {
			log.Printf("API server error: %v", err)
			cancel()
		}
	}()

	sigCh := make(chan os.Signal, 1)
	signal.Notify(sigCh, syscall.SIGINT, syscall.SIGTERM)
	<-sigCh

	log.Println("Shutting down gracefully...")
}
