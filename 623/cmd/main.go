package main

import (
	"db-guardian/internal/api"
	"db-guardian/internal/baseline"
	"db-guardian/internal/config"
	"db-guardian/internal/leak"
	"db-guardian/internal/lifecycle"
	"db-guardian/internal/limiter"
	"db-guardian/internal/pool"
	"db-guardian/internal/prewarm"
	"db-guardian/internal/proxy"
	"db-guardian/pkg/logger"
	"os"
	"os/signal"
	"syscall"
)

func main() {
	cfg := config.Load()
	log := logger.New(cfg.LogLevel)

	baselineManager := baseline.NewBaselineManager()
	leakDetector := leak.NewLeakDetector(log)
	clientIDLimiter := limiter.NewClientIDLimiter(cfg.Limiter)
	connectionLimiter := limiter.NewConnectionLimiter(cfg.Limiter)
	clientLimiter := limiter.NewClientRateLimiter(cfg.Limiter)
	analyzer := proxy.NewConnectionAnalyzer(cfg.Analyzer, log, baselineManager)

	scalingPool := pool.NewAutoScalingPool(cfg.Proxy, cfg.Limiter, log)
	preWarmEngine := prewarm.NewPreWarmEngine(scalingPool, baselineManager, log)
	lifecycleTracker := lifecycle.NewConnectionLifecycle()

	analyzer.SetScalingPool(scalingPool)
	analyzer.SetPreWarmEngine(preWarmEngine)

	dbProxy := proxy.NewMySQLProxy(cfg.Proxy, analyzer, connectionLimiter, clientLimiter, clientIDLimiter, leakDetector, scalingPool, preWarmEngine, lifecycleTracker, log)
	go func() {
		if err := dbProxy.Start(); err != nil {
			log.Error("Proxy server error: %v", err)
		}
	}()

	apiServer := api.NewServer(cfg.API, dbProxy, analyzer, connectionLimiter, clientLimiter, clientIDLimiter, leakDetector, baselineManager, scalingPool, preWarmEngine, lifecycleTracker, log)
	go func() {
		if err := apiServer.Start(); err != nil {
			log.Error("API server error: %v", err)
		}
	}()

	log.Info("DB Guardian started successfully")
	log.Info("Proxy listening on %s:%d", cfg.Proxy.Host, cfg.Proxy.Port)
	log.Info("API server listening on %s:%d", cfg.API.Host, cfg.API.Port)

	sigChan := make(chan os.Signal, 1)
	signal.Notify(sigChan, syscall.SIGINT, syscall.SIGTERM)
	<-sigChan

	log.Info("Shutting down...")
	preWarmEngine.Stop()
	scalingPool.Stop()
	dbProxy.Stop()
	apiServer.Stop()
	log.Info("DB Guardian stopped")
}
