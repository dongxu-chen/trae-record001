package main

import (
	"log"
	"time"
	"zk-inspector/config"
	"zk-inspector/internal/api"
	"zk-inspector/internal/collector"
	"zk-inspector/internal/health"
	"zk-inspector/internal/hotness"
	"zk-inspector/internal/predictor"
	"zk-inspector/internal/storage"
	"zk-inspector/internal/ttl"

	"github.com/gin-gonic/gin"
	"github.com/rs/cors"
)

func main() {
	cfg := config.Load()

	zkCollector, err := collector.NewZKCollector(cfg.ZKServers)
	if err != nil {
		log.Fatalf("Failed to create ZK collector: %v", err)
	}
	defer zkCollector.Close()

	memStorage := storage.NewMemoryStorage()
	pred := predictor.NewTimeSeriesPredictor()

	ttlManager := ttl.NewTTLManager(
		zkCollector.Conn(),
		ttl.TTLConfig{
			Enabled:           cfg.TTLEnabled,
			DefaultTTL:        time.Duration(cfg.TTLDefaultSeconds) * time.Second,
			CheckInterval:     cfg.TTLCheckInterval,
			MaxDeletePerCycle: cfg.TTLMaxDeletePerRun,
		},
		memStorage,
	)

	hotnessAnalyzer := hotness.NewHotnessAnalyzer(
		hotness.HotnessConfig{
			ColdThresholdDays: cfg.ColdThresholdDays,
			HotThresholdScore: cfg.HotThresholdScore,
			DecayFactor:     0.1,
			MaxRecordsPerNode: 1000,
		},
		memStorage,
	)

	healthScorer := health.NewHealthScorer(
		health.HealthConfig{
			MaxRecommendedNodes:     cfg.HealthMaxNodes,
			MaxRecommendedTotalSize: cfg.HealthMaxSize,
			MaxRecommendedDepth:    cfg.HealthMaxDepth,
			MaxRecommendedAlertCount: 5,
		},
		memStorage,
	)

	go zkCollector.StartCollection(memStorage, cfg.CollectionInterval)
	go pred.StartPredictionJob(memStorage, cfg.PredictionInterval)
	go ttlManager.StartCleanupJob()
	go hotnessAnalyzer.StartAnalysisJob(5 * time.Minute)

	go func() {
		time.Sleep(10 * time.Second)
		ttlManager.LoadAllTTL(memStorage.GetLatestSnapshot())
	}()

	r := gin.Default()

	c := cors.New(cors.Options{
		AllowedOrigins:   []string{"*"},
		AllowedMethods:   []string{"GET", "POST", "PUT", "DELETE"},
		AllowedHeaders:   []string{"*"},
		AllowCredentials: true,
	})

	handler := c.Handler(r)

	api.SetupRoutes(r, zkCollector, memStorage, pred, ttlManager, hotnessAnalyzer, healthScorer)

	log.Printf("Server starting on port %s...", cfg.Port)
	if err := r.Run(":" + cfg.Port); err != nil {
		log.Fatalf("Failed to start server: %v", err)
	}
}
