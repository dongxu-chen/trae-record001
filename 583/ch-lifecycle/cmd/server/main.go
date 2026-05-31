package main

import (
	"context"
	"fmt"
	"net/http"
	"os"
	"os/signal"
	"syscall"
	"time"

	"ch-lifecycle/config"
	ch "ch-lifecycle/internal/clickhouse"
	"ch-lifecycle/internal/policy"
	"ch-lifecycle/internal/lifecycle"
	"ch-lifecycle/internal/tiering"
	"ch-lifecycle/internal/scheduler"
	"ch-lifecycle/internal/advisor"
	"ch-lifecycle/internal/monitor"
	"ch-lifecycle/internal/archive"
	"ch-lifecycle/internal/router"
	"ch-lifecycle/internal/simulator"
	"ch-lifecycle/internal/api"
	"github.com/prometheus/client_golang/prometheus/promhttp"
	"go.uber.org/zap"
)

func main() {
	configPath := "config.yaml"
	if len(os.Args) > 1 {
		configPath = os.Args[1]
	}
	cfg, err := config.Load(configPath)
	if err != nil {
		fmt.Fprintf(os.Stderr, "failed to load config: %v\n", err)
		os.Exit(1)
	}
	logger := config.MustLogger()
	defer logger.Sync()
	chClient, err := ch.NewClient(cfg.ClickHouse, logger)
	if err != nil {
		logger.Fatal("failed to connect to ClickHouse", zap.Error(err))
	}
	defer chClient.Close()
	policyStore := policy.NewStore("policies.json", logger)
	mon := monitor.NewMonitor(chClient, logger)
	lifecycleManager := lifecycle.NewManager(chClient, policyStore, logger, mon)
	tieringEngine := tiering.NewEngine(chClient, policyStore, cfg.Storage, logger, mon)
	sched := scheduler.New(logger, lifecycleManager, tieringEngine)
	adv := advisor.NewAdvisor(chClient, logger)

	archiveStore := archive.NewArchiveStore("archive_jobs.json", logger)
	arch, err := archive.NewArchiver(chClient, cfg.Archive, logger, archiveStore)
	if err != nil {
		logger.Warn("failed to initialize archiver, continuing without archiving", zap.Error(err))
	}
	lifecycleManager.SetArchiver(arch)

	routingRuleStore := router.NewRoutingRuleStore("routing_rules.json", logger)
	routingConfig := router.RoutingConfig{
		EnableSmartRouting: true,
		DefaultSource:    router.QuerySourceHot,
		HotHost:         cfg.ClickHouse.Hosts[0],
		ColdHost:        cfg.ClickHouse.Hosts[0],
	}
	queryRouter := router.NewQueryRouter(chClient, routingConfig, routingRuleStore, logger)

	sim := simulator.NewSimulator(chClient, policyStore, logger)

	handler := api.NewHandler(chClient, policyStore, lifecycleManager, tieringEngine, sched, adv, mon, arch, queryRouter, sim, logger)
	if cfg.Scheduler.Enabled {
		if err := sched.Start(
			cfg.Scheduler.TTLCheckCron,
			cfg.Scheduler.TieringCron,
			cfg.Scheduler.CleanupCron,
			cfg.Scheduler.OptimizeCron,
		); err != nil {
			logger.Fatal("failed to start scheduler", zap.Error(err))
		}
		defer sched.Stop()
	}
	if cfg.Monitor.Enabled {
		collectInterval, err := time.ParseDuration(cfg.Monitor.CollectInterval)
		if err != nil {
			collectInterval = 30 * time.Second
		}
		monitorCtx, monitorCancel := context.WithCancel(context.Background())
		defer monitorCancel()
		go mon.StartCollection(monitorCtx, collectInterval)
		go func() {
			mux := http.NewServeMux()
			mux.Handle(cfg.Monitor.MetricsPath, promhttp.HandlerFor(mon.Registry(), promhttp.HandlerOpts{}))
			metricsAddr := fmt.Sprintf(":%d", cfg.Monitor.MetricsPort)
			logger.Info("starting metrics server", zap.String("addr", metricsAddr))
			if err := http.ListenAndServe(metricsAddr, mux); err != nil {
				logger.Error("metrics server error", zap.Error(err))
			}
		}()
	}
	router := handler.SetupRouter()
	server := &http.Server{
		Addr:         fmt.Sprintf(":%d", cfg.Server.Port),
		Handler:      router,
		ReadTimeout:  30 * time.Second,
		WriteTimeout: 60 * time.Second,
	}
	go func() {
		logger.Info("starting API server", zap.Int("port", cfg.Server.Port))
		if err := server.ListenAndServe(); err != nil && err != http.ErrServerClosed {
			logger.Fatal("server error", zap.Error(err))
		}
	}()
	quit := make(chan os.Signal, 1)
	signal.Notify(quit, syscall.SIGINT, syscall.SIGTERM)
	<-quit
	logger.Info("shutting down server...")
	shutdownCtx, shutdownCancel := context.WithTimeout(context.Background(), 30*time.Second)
	defer shutdownCancel()
	if err := server.Shutdown(shutdownCtx); err != nil {
		logger.Error("server shutdown error", zap.Error(err))
	}
	logger.Info("server stopped")
}
