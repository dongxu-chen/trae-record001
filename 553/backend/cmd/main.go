package main

import (
	"context"
	"fmt"
	"log"
	"os"
	"os/signal"
	"syscall"
	"time"

	"github.com/robfig/cron/v3"
	"go.uber.org/zap"
	"go.uber.org/zap/zapcore"

	"es-shard-balancer/pkg/api"
	"es-shard-balancer/pkg/balancer"
	"es-shard-balancer/pkg/config"
	"es-shard-balancer/pkg/elasticsearch"
	"es-shard-balancer/pkg/monitor"
)

func main() {
	cfg, err := config.Load("config/config.yaml")
	if err != nil {
		log.Fatalf("Failed to load config: %v", err)
	}

	logger, err := setupLogger(cfg.Logging)
	if err != nil {
		log.Fatalf("Failed to setup logger: %v", err)
	}
	defer logger.Sync()

	client, err := elasticsearch.NewClient(&cfg.Elasticsearch)
	if err != nil {
		logger.Fatal("Failed to create Elasticsearch client", zap.Error(err))
	}

	loadMonitor := monitor.NewLoadMonitor(client, &cfg.Balancer.LoadAwareness, logger)
	speedCtrl := monitor.NewSpeedController(client, &cfg.Balancer.SpeedLimit, logger)
	shardHeatMonitor := monitor.NewShardHeatMonitor(client, &cfg.Balancer.ShardHeat, logger)
	autoScaler := monitor.NewAutoScaler(client, &cfg.Balancer.AutoScaling, logger)

	bal := balancer.NewBalancer(client, &cfg.Balancer, logger, loadMonitor, speedCtrl, shardHeatMonitor)
	handler := api.NewHandler(client, bal, cfg, logger, loadMonitor, speedCtrl, shardHeatMonitor, autoScaler)
	router := api.SetupRouter(handler, &cfg.Server)

	mainCtx, mainCancel := context.WithCancel(context.Background())
	defer mainCancel()

	if cfg.Balancer.LoadAwareness.Enabled {
		go loadMonitor.Start(mainCtx, 30*time.Second)
		logger.Info("Load monitor started",
			zap.Bool("avoid_high_load", cfg.Balancer.LoadAwareness.AvoidHighLoadNodes),
			zap.Int("history_size", cfg.Balancer.LoadAwareness.HistorySize),
		)
	}

	go speedCtrl.Start(mainCtx)

	if cfg.Balancer.ShardHeat.Enabled {
		go shardHeatMonitor.Start(mainCtx)
		logger.Info("Shard heat monitor started",
			zap.Float64("heat_threshold", cfg.Balancer.ShardHeat.HeatThreshold),
			zap.Float64("priority_boost", cfg.Balancer.ShardHeat.PriorityBoost),
		)
	}

	if cfg.Balancer.AutoScaling.Enabled {
		go autoScaler.Start(mainCtx)
		logger.Info("Auto scaler started",
			zap.Int("min_nodes", cfg.Balancer.AutoScaling.MinNodes),
			zap.Int("max_nodes", cfg.Balancer.AutoScaling.MaxNodes),
			zap.Float64("flood_threshold", cfg.Balancer.AutoScaling.FloodThreshold),
			zap.String("provider", cfg.Balancer.AutoScaling.Provider),
		)
	}

	if cfg.Balancer.LoadAwareness.Enabled {
		loadMonitor.CollectStats(mainCtx)
	}

	if cfg.Balancer.ShardHeat.Enabled {
		shardHeatMonitor.CollectStats(mainCtx)
	}

	if cfg.Balancer.Enabled {
		c := cron.New(cron.WithSeconds())
		_, err = c.AddFunc(cfg.Balancer.Schedule, func() {
			ctx, cancel := context.WithTimeout(context.Background(), time.Duration(cfg.Balancer.MigrationTimeout)*time.Second)
			defer cancel()

			result, err := bal.RunBalanceCycle(ctx)
			if err != nil {
				logger.Error("Balance cycle failed", zap.Error(err))
				return
			}

			logger.Info("Balance cycle completed",
				zap.Int("migrations_planned", result.MigrationsPlanned),
				zap.String("message", result.Message),
			)
		})
		if err != nil {
			logger.Fatal("Failed to setup cron job", zap.Error(err))
		}
		c.Start()
		logger.Info("Auto-balancer enabled", zap.String("schedule", cfg.Balancer.Schedule))
		defer c.Stop()
	}

	go func() {
		addr := fmt.Sprintf(":%d", cfg.Server.Port)
		logger.Info("Starting server", zap.String("addr", addr))
		if err := router.Run(addr); err != nil {
			logger.Fatal("Failed to start server", zap.Error(err))
		}
	}()

	quit := make(chan os.Signal, 1)
	signal.Notify(quit, syscall.SIGINT, syscall.SIGTERM)
	<-quit

	logger.Info("Shutting down server...")
}

func setupLogger(cfg config.LoggingConfig) (*zap.Logger, error) {
	var level zapcore.Level
	if err := level.UnmarshalText([]byte(cfg.Level)); err != nil {
		level = zapcore.InfoLevel
	}

	encoderConfig := zap.NewProductionEncoderConfig()
	encoderConfig.EncodeTime = zapcore.ISO8601TimeEncoder

	var encoder zapcore.Encoder
	if cfg.Format == "json" {
		encoder = zapcore.NewJSONEncoder(encoderConfig)
	} else {
		encoder = zapcore.NewConsoleEncoder(encoderConfig)
	}

	core := zapcore.NewCore(
		encoder,
		zapcore.AddSync(os.Stdout),
		level,
	)

	return zap.New(core, zap.AddCaller()), nil
}
