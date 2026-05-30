package main

import (
	"context"
	"flag"
	"fmt"
	"net/http"
	"os"
	"os/signal"
	"syscall"

	"github.com/sirupsen/logrus"

	"kafka-autoscaler/pkg/autoscaler"
	"kafka-autoscaler/pkg/config"
	kafkaclient "kafka-autoscaler/pkg/kafka"
	k8sclient "kafka-autoscaler/pkg/kubernetes"
	"kafka-autoscaler/pkg/predictor"
	promclient "kafka-autoscaler/pkg/prometheus"
	"kafka-autoscaler/pkg/rebalancer"
)

var (
	configPath = flag.String("config", "config/config.yaml", "Path to configuration file")
	logLevel   = flag.String("log-level", "", "Log level (debug, info, warn, error)")
	version    = "1.0.0"
)

func main() {
	flag.Parse()

	ctx, cancel := context.WithCancel(context.Background())
	defer cancel()

	logger := logrus.New()
	logger.SetOutput(os.Stdout)
	logger.SetFormatter(&logrus.JSONFormatter{
		TimestampFormat: "2006-01-02T15:04:05.000Z07:00",
	})

	logger.Infof("Starting Kafka Autoscaler v%s", version)

	cfg, err := config.LoadConfig(*configPath)
	if err != nil {
		logger.Fatalf("Failed to load config: %v", err)
	}

	if *logLevel != "" {
		cfg.Log.Level = *logLevel
	}

	level, err := logrus.ParseLevel(cfg.Log.Level)
	if err != nil {
		logger.Warnf("Invalid log level '%s', using 'info'", cfg.Log.Level)
		level = logrus.InfoLevel
	}
	logger.SetLevel(level)

	if cfg.Log.Format == "text" {
		logger.SetFormatter(&logrus.TextFormatter{
			FullTimestamp: true,
		})
	}

	kafkaClient, err := kafkaclient.NewClient(cfg.Kafka.Brokers, logger)
	if err != nil {
		logger.Fatalf("Failed to create Kafka client: %v", err)
	}
	defer kafkaClient.Close()

	logger.Info("Kafka client connected successfully")

	if err := kafkaClient.HealthCheck(ctx); err != nil {
		logger.Warnf("Kafka health check failed: %v", err)
	}

	k8sClient, err := k8sclient.NewClient(k8sclient.ClientConfig{
		InCluster:      cfg.Kubernetes.InCluster,
		KubeConfigPath: cfg.Kubernetes.KubeConfigPath,
	}, logger)
	if err != nil {
		logger.Fatalf("Failed to create Kubernetes client: %v", err)
	}
	defer k8sClient.Close()

	logger.Info("Kubernetes client connected successfully")

	if err := k8sClient.HealthCheck(ctx); err != nil {
		logger.Warnf("Kubernetes health check failed: %v", err)
	}

	promCollector := promclient.NewCollector(promclient.CollectorConfig{
		ScrapeInterval: cfg.Prometheus.ScrapeInterval,
		MaxHistorySize: cfg.Prometheus.MaxHistorySize,
		ListenAddress:  cfg.Prometheus.ListenAddress,
	}, logger)
	defer promCollector.Shutdown(ctx)

	logger.Infof("Prometheus metrics server started on %s", cfg.Prometheus.ListenAddress)

	predictor := predictor.NewPredictor(logger)

	autoScalers := make([]*autoscaler.AutoScaler, 0, len(cfg.Autoscalers))
	for _, scalerCfg := range cfg.Autoscalers {
		mode := autoscaler.ScalingMode(scalerCfg.Mode)

		scalerConfig := &autoscaler.ScalerConfig{
			ConsumerGroupID:             scalerCfg.ConsumerGroupID,
			K8sDeployment:               scalerCfg.K8sDeployment,
			K8sNamespace:                scalerCfg.K8sNamespace,
			K8sResourceType:             scalerCfg.K8sResourceType,
			MinReplicas:                 scalerCfg.MinReplicas,
			MaxReplicas:                 scalerCfg.MaxReplicas,
			ScaleUpThreshold:            scalerCfg.ScaleUpThreshold,
			ScaleDownThreshold:          scalerCfg.ScaleDownThreshold,
			ScaleUpIncrement:            scalerCfg.ScaleUpIncrement,
			ScaleDownDecrement:          scalerCfg.ScaleDownDecrement,
			CooldownPeriod:              scalerCfg.CooldownPeriod,
			PredictionWindow:            scalerCfg.PredictionWindow,
			UsePrediction:               scalerCfg.UsePrediction,
			TargetLag:                   scalerCfg.TargetLag,
			Mode:                        mode,
			EnablePartitionRebalance:    scalerCfg.EnablePartitionRebalance,
			EnableRollingScale:          scalerCfg.EnableRollingScale,
			RollingScaleInterval:        scalerCfg.RollingScaleInterval,
			MessageProcessingLatency:    scalerCfg.MessageProcessingLatency,
			EnableScaleDownAfterLagClear: scalerCfg.EnableScaleDownAfterLagClear,
			ScaleDownAfterLagDelay:      scalerCfg.ScaleDownAfterLagDelay,
			EnableSelfHealing:           scalerCfg.EnableSelfHealing,
			SelfHealingThreshold:        scalerCfg.SelfHealingThreshold,
			SelfHealingCooldown:         scalerCfg.SelfHealingCooldown,
			EnableSlowPartitionDetection: scalerCfg.EnableSlowPartitionDetection,
			SlowPartitionThreshold:      scalerCfg.SlowPartitionThreshold,
		}

		scaler := autoscaler.NewAutoScaler(
			kafkaClient,
			k8sClient,
			promCollector,
			predictor,
			scalerConfig,
			logger,
		)

		if err := scaler.Start(); err != nil {
			logger.Errorf("Failed to start autoscaler for %s: %v", scalerCfg.ConsumerGroupID, err)
			continue
		}

		autoScalers = append(autoScalers, scaler)
		logger.Infof("Autoscaler started for consumer group: %s", scalerCfg.ConsumerGroupID)
	}

	var rebalancerInstance *rebalancer.Rebalancer
	if cfg.Rebalancer.Enabled {
		strategy := rebalancer.AssignmentStrategy(cfg.Rebalancer.Strategy)

		rebalancerInstance = rebalancer.NewRebalancer(
			kafkaClient,
			&rebalancer.RebalanceConfig{
				Strategy:              strategy,
				MaxConcurrentMoves:    cfg.Rebalancer.MaxConcurrentMoves,
				MinPartitionCount:     cfg.Rebalancer.MinPartitionCount,
				RebalanceInterval:     cfg.Rebalancer.RebalanceInterval,
				EnableUnevenDetection: cfg.Rebalancer.EnableUnevenDetection,
				UnevenThresholdRatio:  cfg.Rebalancer.UnevenThresholdRatio,
				DryRun:                cfg.Rebalancer.DryRun,
				KeyPrefixDelimiter:    cfg.Rebalancer.KeyPrefixDelimiter,
			},
			logger,
		)

		rebalancerInstance.Start()
		logger.Info("Partition rebalancer started")
	}

	setupStatusEndpoint(logger, autoScalers, rebalancerInstance)

	sigChan := make(chan os.Signal, 1)
	signal.Notify(sigChan, syscall.SIGINT, syscall.SIGTERM)

	logger.Info("Kafka Autoscaler is running. Press Ctrl+C to stop.")

	sig := <-sigChan
	logger.Infof("Received signal: %v, shutting down...", sig)

	for _, scaler := range autoScalers {
		scaler.Stop()
	}

	if rebalancerInstance != nil {
		rebalancerInstance.Stop()
	}

	logger.Info("Kafka Autoscaler stopped successfully")
}

func setupStatusEndpoint(logger *logrus.Logger, autoScalers []*autoscaler.AutoScaler, rebalancerInstance *rebalancer.Rebalancer) {
	mux := http.NewServeMux()

	mux.HandleFunc("/health", func(w http.ResponseWriter, r *http.Request) {
		w.WriteHeader(http.StatusOK)
		w.Write([]byte("OK"))
	})

	mux.HandleFunc("/status", func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Content-Type", "application/json")

		status := map[string]interface{}{
			"version":      version,
			"autoscalers":  make([]map[string]interface{}, 0),
			"rebalancer":   nil,
		}

		scalersStatus := make([]map[string]interface{}, 0)
		for _, scaler := range autoScalers {
			scalersStatus = append(scalersStatus, scaler.GetStatus())
		}
		status["autoscalers"] = scalersStatus

		if rebalancerInstance != nil {
			status["rebalancer"] = rebalancerInstance.GetStatus()
		}

		w.WriteHeader(http.StatusOK)
		fmt.Fprintf(w, `{"status":"ok","autoscalers_count":%d}`, len(autoScalers))
	})

	go func() {
		addr := ":8080"
		logger.Infof("Status endpoint started on %s", addr)
		if err := http.ListenAndServe(addr, mux); err != nil && err != http.ErrServerClosed {
			logger.Errorf("Status endpoint error: %v", err)
		}
	}()
}
