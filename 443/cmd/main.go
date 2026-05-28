package main

import (
	"context"
	"cross-cloud-lb/pkg/cloud"
	"cross-cloud-lb/pkg/config"
	"cross-cloud-lb/pkg/cost"
	"cross-cloud-lb/pkg/failover"
	"cross-cloud-lb/pkg/healthcheck"
	"cross-cloud-lb/pkg/mirroring"
	"cross-cloud-lb/pkg/model"
	"cross-cloud-lb/pkg/prediction"
	"cross-cloud-lb/pkg/proximity"
	"cross-cloud-lb/pkg/session"
	"cross-cloud-lb/pkg/weight"
	"cross-cloud-lb/pkg/xds"
	"flag"
	"fmt"
	"net/http"
	_ "net/http/pprof"
	"os"
	"os/signal"
	"syscall"
	"time"

	"github.com/prometheus/client_golang/prometheus/promhttp"
	"go.uber.org/zap"
	"go.uber.org/zap/zapcore"
)

var (
	configPath  = flag.String("config", "config.yaml", "Path to configuration file")
	logLevel    = flag.String("log-level", "info", "Log level (debug, info, warn, error)")
	xdsPort     = flag.Uint("xds-port", 18000, "xDS gRPC server port")
	metricsPort = flag.Uint("metrics-port", 9090, "Metrics server port")
)

func main() {
	flag.Parse()

	logger := setupLogger(*logLevel)
	defer logger.Sync()

	ctx, cancel := context.WithCancel(context.Background())
	defer cancel()

	cfg, err := config.LoadConfig(*configPath)
	if err != nil {
		logger.Fatal("Failed to load configuration", zap.Error(err))
	}

	logger.Info("Starting cross-cloud load balancer", zap.String("name", cfg.Name))

	providers := initializeCloudProviders(logger)

	healthChecker := healthcheck.NewHealthChecker(cfg.HealthCheck, providers, logger)
	weightAdjuster := weight.NewWeightAdjuster(cfg.WeightAdjustment, logger)
	failoverManager := failover.NewFailoverManager(cfg.Failover, logger)
	sessionManager := session.NewSessionManager(cfg.SessionAffinity, logger, []byte("cross-cloud-lb-secret"))
	trafficMirrorer := mirroring.NewTrafficMirrorer(cfg.TrafficMirroring, logger)
	costManager := cost.NewCostManager(cfg.Cost, logger)
	trafficPredictor := prediction.NewTrafficPredictor(cfg.Prediction, logger)
	proximityRouter := proximity.NewProximityRouter(cfg.Proximity, logger)

	for _, cluster := range cfg.Clusters {
		healthChecker.RegisterCluster(&cluster)
		weightAdjuster.AddCluster(&cluster)
		failoverManager.RegisterCluster(&cluster)
		costManager.RegisterCluster(&cluster)
		trafficPredictor.RegisterCluster(cluster.ID)
		proximityRouter.RegisterCluster(&cluster)
	}

	xdsServer, err := xds.NewXDSServer(*cfg, logger, "cross-cloud-lb")
	if err != nil {
		logger.Fatal("Failed to create xDS server", zap.Error(err))
	}

	grpcServer := xds.NewGRPCServer(xdsServer, uint32(*xdsPort), logger)

	setupCallbacks(healthChecker, weightAdjuster, failoverManager, trafficMirrorer, costManager, trafficPredictor, proximityRouter, xdsServer, logger)

	xdsServer.UpdateClusters(convertToPointerSlice(cfg.Clusters))

	if err := xdsServer.Start(ctx); err != nil {
		logger.Fatal("Failed to start xDS server", zap.Error(err))
	}

	if err := grpcServer.Start(ctx); err != nil {
		logger.Fatal("Failed to start gRPC server", zap.Error(err))
	}

	healthChecker.Start(ctx)
	weightAdjuster.Start(ctx)
	failoverManager.Start(ctx)
	trafficPredictor.Start(ctx)

	go startMetricsServer(*metricsPort, logger, costManager, trafficPredictor, proximityRouter)

	go periodicClusterSync(ctx, providers, xdsServer, failoverManager, costManager, trafficPredictor, logger)

	sigCh := make(chan os.Signal, 1)
	signal.Notify(sigCh, syscall.SIGINT, syscall.SIGTERM)

	sig := <-sigCh
	logger.Info("Received signal, shutting down", zap.String("signal", sig.String()))

	cancel()

	grpcServer.Stop()
	xdsServer.Stop()
	healthChecker.Stop()
	weightAdjuster.Stop()
	failoverManager.Stop()
	trafficPredictor.Stop()

	logger.Info("Cross-cloud load balancer shutdown complete")
}

func setupLogger(level string) *zap.Logger {
	var zapLevel zapcore.Level
	switch level {
	case "debug":
		zapLevel = zapcore.DebugLevel
	case "warn":
		zapLevel = zapcore.WarnLevel
	case "error":
		zapLevel = zapcore.ErrorLevel
	default:
		zapLevel = zapcore.InfoLevel
	}

	config := zap.Config{
		Level:       zap.NewAtomicLevelAt(zapLevel),
		Development: false,
		Sampling: &zap.SamplingConfig{
			Initial:    100,
			Thereafter: 100,
		},
		Encoding: "json",
		EncoderConfig: zapcore.EncoderConfig{
			TimeKey:        "ts",
			LevelKey:       "level",
			NameKey:        "logger",
			CallerKey:      "caller",
			FunctionKey:    zapcore.OmitKey,
			MessageKey:     "msg",
			StacktraceKey:  "stacktrace",
			LineEnding:     zapcore.DefaultLineEnding,
			EncodeLevel:    zapcore.LowercaseLevelEncoder,
			EncodeTime:     zapcore.ISO8601TimeEncoder,
			EncodeDuration: zapcore.SecondsDurationEncoder,
			EncodeCaller:   zapcore.ShortCallerEncoder,
		},
		OutputPaths:      []string{"stdout"},
		ErrorOutputPaths: []string{"stderr"},
	}

	logger, _ := config.Build()
	return logger
}

func initializeCloudProviders(logger *zap.Logger) map[model.CloudProvider]cloud.Provider {
	providers := make(map[model.CloudProvider]cloud.Provider)

	awsProvider, err := cloud.NewAWSProvider(cloud.ProviderConfig{
		Provider: model.AWS,
		Region:   "us-east-1",
	})
	if err != nil {
		logger.Warn("Failed to initialize AWS provider", zap.Error(err))
	} else {
		providers[model.AWS] = awsProvider
		logger.Info("AWS provider initialized")
	}

	azureProvider, err := cloud.NewAzureProvider(cloud.ProviderConfig{
		Provider:       model.Azure,
		SubscriptionID: os.Getenv("AZURE_SUBSCRIPTION_ID"),
	})
	if err != nil {
		logger.Warn("Failed to initialize Azure provider", zap.Error(err))
	} else {
		providers[model.Azure] = azureProvider
		logger.Info("Azure provider initialized")
	}

	gcpProvider, err := cloud.NewGCPProvider(cloud.ProviderConfig{
		Provider:  model.GCP,
		ProjectID: os.Getenv("GCP_PROJECT_ID"),
	})
	if err != nil {
		logger.Warn("Failed to initialize GCP provider", zap.Error(err))
	} else {
		providers[model.GCP] = gcpProvider
		logger.Info("GCP provider initialized")
	}

	return providers
}

func setupCallbacks(
	hc *healthcheck.HealthCheckerImpl,
	wa *weight.WeightAdjusterImpl,
	fm *failover.FailoverManagerImpl,
	tm *mirroring.TrafficMirrorerImpl,
	cm *cost.CostManagerImpl,
	tp *prediction.TrafficPredictorImpl,
	pr *proximity.ProximityRouterImpl,
	xds *xds.XDSServerImpl,
	logger *zap.Logger,
) {
	hc.RegisterCallback(func(clusterID string, healthy bool) {
		logger.Info("Cluster health status changed",
			zap.String("cluster_id", clusterID),
			zap.Bool("healthy", healthy))
		fm.UpdateClusterHealth(clusterID, healthy)
	})

	wa.RegisterCallback(func(clusterID string, newWeight int) {
		if cm != nil {
			costAdjusted := cm.GetCostAdjustedWeight(clusterID, newWeight)
			if costAdjusted != newWeight {
				logger.Info("Cost-aware weight adjustment",
					zap.String("cluster_id", clusterID),
					zap.Int("base_weight", newWeight),
					zap.Int("cost_adjusted_weight", costAdjusted))
				newWeight = costAdjusted
			}
		}

		logger.Info("Cluster weight adjusted",
			zap.String("cluster_id", clusterID),
			zap.Int("new_weight", newWeight))

		weights := wa.GetAllWeights()
		weights[clusterID] = newWeight
		xds.UpdateWeights(weights)
	})

	fm.RegisterCallback(func(clusterID string, failedOver bool) {
		if failedOver {
			logger.Warn("Cluster entered failover state",
				zap.String("cluster_id", clusterID))

			if tm.GetConfig().TargetCluster == clusterID {
				logger.Warn("Mirroring target cluster failed, pausing mirroring")
				tm.UpdateConfig(model.TrafficMirroringConfig{
					Enabled:       false,
					TargetCluster: tm.GetConfig().TargetCluster,
					Percent:       tm.GetConfig().Percent,
				})
			}
		} else {
			logger.Info("Cluster recovered from failover",
				zap.String("cluster_id", clusterID))

			if tm.GetConfig().TargetCluster == clusterID && !tm.GetConfig().Enabled {
				logger.Info("Mirroring target cluster recovered, resuming mirroring")
				tm.UpdateConfig(model.TrafficMirroringConfig{
					Enabled:       true,
					TargetCluster: clusterID,
					Percent:       tm.GetConfig().Percent,
				})
			}
		}
	})
}

func startMetricsServer(
	port uint,
	logger *zap.Logger,
	cm *cost.CostManagerImpl,
	tp *prediction.TrafficPredictorImpl,
	pr *proximity.ProximityRouterImpl,
) {
	mux := http.NewServeMux()
	mux.Handle("/metrics", promhttp.Handler())
	mux.HandleFunc("/health", func(w http.ResponseWriter, r *http.Request) {
		w.WriteHeader(http.StatusOK)
		w.Write([]byte("ok"))
	})

	mux.HandleFunc("/api/v1/costs", func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Content-Type", "application/json")
		w.WriteHeader(http.StatusOK)
	})

	mux.HandleFunc("/api/v1/predictions", func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Content-Type", "application/json")
		w.WriteHeader(http.StatusOK)
	})

	mux.HandleFunc("/api/v1/proximity", func(w http.ResponseWriter, r *http.Request) {
		clientIP := r.Header.Get("X-Forwarded-For")
		if clientIP == "" {
			clientIP = r.RemoteAddr
		}

		nearestCluster, distance := pr.GetNearestCluster(clientIP)
		sortedClusters := pr.GetSortedClustersByProximity(clientIP)

		logger.Debug("Proximity lookup",
			zap.String("client_ip", clientIP),
			zap.String("nearest_cluster", nearestCluster),
			zap.Float64("distance_km", distance),
			zap.Any("sorted_clusters", sortedClusters))

		w.Header().Set("Content-Type", "application/json")
		w.WriteHeader(http.StatusOK)
	})

	addr := fmt.Sprintf(":%d", port)
	logger.Info("Starting metrics and API server", zap.String("addr", addr))

	server := &http.Server{
		Addr:         addr,
		Handler:      mux,
		ReadTimeout:  10 * time.Second,
		WriteTimeout: 10 * time.Second,
	}

	if err := server.ListenAndServe(); err != nil && err != http.ErrServerClosed {
		logger.Error("Metrics server error", zap.Error(err))
	}
}

func periodicClusterSync(
	ctx context.Context,
	providers map[model.CloudProvider]cloud.Provider,
	xdsServer *xds.XDSServerImpl,
	failoverManager *failover.FailoverManagerImpl,
	costManager *cost.CostManagerImpl,
	trafficPredictor *prediction.TrafficPredictorImpl,
	logger *zap.Logger,
) {
	ticker := time.NewTicker(60 * time.Second)
	defer ticker.Stop()

	for {
		select {
		case <-ctx.Done():
			return
		case <-ticker.C:
			syncClusters(ctx, providers, xdsServer, failoverManager, costManager, trafficPredictor, logger)
		}
	}
}

func syncClusters(
	ctx context.Context,
	providers map[model.CloudProvider]cloud.Provider,
	xdsServer *xds.XDSServerImpl,
	failoverManager *failover.FailoverManagerImpl,
	costManager *cost.CostManagerImpl,
	trafficPredictor *prediction.TrafficPredictorImpl,
	logger *zap.Logger,
) {
	logger.Debug("Syncing cluster information from cloud providers")

	allClusters := make([]*model.Cluster, 0)
	for providerName, provider := range providers {
		clusters, err := provider.ListClusters(ctx)
		if err != nil {
			logger.Warn("Failed to list clusters from provider",
				zap.String("provider", string(providerName)),
				zap.Error(err))
			continue
		}
		allClusters = append(allClusters, clusters...)

		for _, cluster := range clusters {
			healthy, err := provider.CheckClusterHealth(ctx, cluster.ID)
			if err == nil {
				cluster.Healthy = healthy
				failoverManager.UpdateClusterHealth(cluster.ID, healthy)
			}
		}
	}

	if len(allClusters) > 0 {
		xdsServer.UpdateClusters(allClusters)

		if costManager != nil {
			costManager.RefreshPricing()
		}

		for _, cluster := range allClusters {
			if cluster.Healthy {
				trafficPredictor.RecordTraffic(cluster.ID, 100, 1024, 2048)

				if costManager != nil {
					costManager.GetCostAdjustedWeight(cluster.ID, cluster.Weight)
				}
			}
		}

		logger.Debug("Cluster sync completed", zap.Int("cluster_count", len(allClusters)))
	}
}

func convertToPointerSlice(clusters []model.Cluster) []*model.Cluster {
	result := make([]*model.Cluster, len(clusters))
	for i := range clusters {
		result[i] = &clusters[i]
	}
	return result
}
