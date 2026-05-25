package main

import (
	"context"
	"fmt"
	"os"
	"os/signal"
	"syscall"
	"time"

	"github.com/spf13/cobra"
	"go.uber.org/zap"
	"go.uber.org/zap/zapcore"

	"autoscaler/internal/config"
	"autoscaler/internal/types"
	"autoscaler/pkg/cloud"
	"autoscaler/pkg/controller"
	"autoscaler/pkg/monitor"
	"autoscaler/pkg/predict"
	"autoscaler/pkg/strategy"
)

var (
	cfgFile     string
	logLevel    string
	dryRun      bool
	once        bool
	showVersion bool
	dryRunMode  string
	replayStart string
	replayEnd   string
	Version     = "dev"
	BuildTime   = "unknown"
)

var rootCmd = &cobra.Command{
	Use:   "autoscaler",
	Short: "Server resource elastic scaling tool",
	Long: `An intelligent server resource elastic scaling tool that monitors CPU, memory, 
and network metrics, automatically adjusts resource specifications based on elastic policies.

Supports vertical scaling (instance type change) and horizontal scaling (add/remove nodes),
with cooldown time to avoid oscillation. Implemented with Go + Prometheus API + Cloud SDK + Time Series Prediction.`,
	RunE: runAutoscaler,
}

var dryRunCmd = &cobra.Command{
	Use:   "dry-run",
	Short: "Run scaling simulation without actual execution",
	Long:  `Simulate the scaling process to verify policies and assess cost impact without making actual changes.`,
	RunE:  runDryRun,
}

var replayCmd = &cobra.Command{
	Use:   "replay",
	Short: "Replay scaling history with visualization",
	Long:  `Replay historical scaling records and generate visual reports showing decision processes and effects.`,
	RunE:  runReplay,
}

func init() {
	rootCmd.PersistentFlags().StringVarP(&cfgFile, "config", "c", "configs/config.yaml", "config file path")
	rootCmd.PersistentFlags().StringVarP(&logLevel, "log-level", "l", "", "log level (debug, info, warn, error)")
	rootCmd.PersistentFlags().BoolVar(&dryRun, "dry-run", false, "dry run mode, no actual scaling")
	rootCmd.PersistentFlags().BoolVar(&once, "once", false, "run only once and exit")
	rootCmd.PersistentFlags().BoolVar(&showVersion, "version", false, "show version information")
	rootCmd.PersistentFlags().StringVar(&dryRunMode, "dry-run-mode", "", "dry run mode: off|simulate|validate|report")

	dryRunCmd.Flags().StringVar(&dryRunMode, "mode", "report", "dry run mode: simulate|validate|report")
	rootCmd.AddCommand(dryRunCmd)

	replayCmd.Flags().StringVar(&replayStart, "start", "", "replay start time (RFC3339 format)")
	replayCmd.Flags().StringVar(&replayEnd, "end", "", "replay end time (RFC3339 format)")
	rootCmd.AddCommand(replayCmd)
}

func main() {
	if err := rootCmd.Execute(); err != nil {
		fmt.Fprintf(os.Stderr, "Error: %v\n", err)
		os.Exit(1)
	}
}

func runAutoscaler(cmd *cobra.Command, args []string) error {
	if showVersion {
		fmt.Printf("autoscaler %s (built %s)\n", Version, BuildTime)
		return nil
	}

	logger, err := initLogger(logLevel)
	if err != nil {
		return fmt.Errorf("failed to initialize logger: %w", err)
	}
	defer logger.Sync()

	logger.Info("starting autoscaler",
		zap.String("version", Version),
		zap.String("build_time", BuildTime),
	)

	cfg, err := config.LoadConfig(cfgFile)
	if err != nil {
		return fmt.Errorf("failed to load config: %w", err)
	}

	logger.Info("config loaded successfully",
		zap.String("config_file", cfgFile),
		zap.String("provider", cfg.Cloud.Provider),
		zap.String("scaling_type", cfg.Autoscaler.ScalingType),
	)

	if dryRun {
		cfg.Autoscaler.DryRun = true
		logger.Info("dry run mode enabled")
	}

	if dryRunMode != "" {
		cfg.Autoscaler.DryRunMode = dryRunMode
		logger.Info("dry run mode set", zap.String("mode", dryRunMode))
	}

	monitorClient, err := initMonitor(cfg, logger)
	if err != nil {
		return fmt.Errorf("failed to initialize monitor: %w", err)
	}

	predictor := predict.NewPredictor(cfg.GetPredictorConfig())

	strategyCfg, err := cfg.GetStrategyConfig()
	if err != nil {
		return fmt.Errorf("failed to get strategy config: %w", err)
	}
	strategyEngine := strategy.NewStrategyEngine(strategyCfg, logger)

	cloudProvider, err := initCloudProvider(cfg, logger)
	if err != nil {
		return fmt.Errorf("failed to initialize cloud provider: %w", err)
	}

	autoscalerCfg, err := cfg.GetAutoscalerConfig()
	if err != nil {
		return fmt.Errorf("failed to get autoscaler config: %w", err)
	}

	autoscaler := controller.NewAutoscaler(
		autoscalerCfg,
		monitorClient,
		predictor,
		strategyEngine,
		cloudProvider,
		logger,
	)

	ctx, cancel := context.WithCancel(context.Background())
	defer cancel()

	sigCh := make(chan os.Signal, 1)
	signal.Notify(sigCh, syscall.SIGINT, syscall.SIGTERM)

	if once {
		logger.Info("running once mode")
		if err := autoscaler.DoScaling(ctx); err != nil {
			logger.Error("scaling failed", zap.Error(err))
			return err
		}
		logger.Info("once mode completed")
		return nil
	}

	if err := autoscaler.Start(ctx); err != nil {
		return fmt.Errorf("failed to start autoscaler: %w", err)
	}

	logger.Info("autoscaler is running, press Ctrl+C to stop")

	select {
	case sig := <-sigCh:
		logger.Info("received signal, shutting down", zap.String("signal", sig.String()))
	case <-ctx.Done():
		logger.Info("context cancelled, shutting down")
	}

	autoscaler.Stop()
	logger.Info("autoscaler stopped gracefully")

	return nil
}

func runDryRun(cmd *cobra.Command, args []string) error {
	logger, err := initLogger(logLevel)
	if err != nil {
		return fmt.Errorf("failed to initialize logger: %w", err)
	}
	defer logger.Sync()

	cfg, err := config.LoadConfig(cfgFile)
	if err != nil {
		return fmt.Errorf("failed to load config: %w", err)
	}

	if dryRunMode != "" {
		cfg.Autoscaler.DryRunMode = dryRunMode
	}
	cfg.Autoscaler.DryRun = true

	logger.Info("starting dry run",
		zap.String("mode", cfg.Autoscaler.DryRunMode),
	)

	monitorClient, err := initMonitor(cfg, logger)
	if err != nil {
		return fmt.Errorf("failed to initialize monitor: %w", err)
	}

	predictor := predict.NewPredictor(cfg.GetPredictorConfig())
	strategyCfg, err := cfg.GetStrategyConfig()
	if err != nil {
		return fmt.Errorf("failed to get strategy config: %w", err)
	}
	strategyEngine := strategy.NewStrategyEngine(strategyCfg, logger)
	cloudProvider, err := initCloudProvider(cfg, logger)
	if err != nil {
		return fmt.Errorf("failed to initialize cloud provider: %w", err)
	}

	autoscalerCfg, err := cfg.GetAutoscalerConfig()
	if err != nil {
		return fmt.Errorf("failed to get autoscaler config: %w", err)
	}

	autoscaler := controller.NewAutoscaler(
		autoscalerCfg,
		monitorClient,
		predictor,
		strategyEngine,
		cloudProvider,
		logger,
	)

	ctx, cancel := context.WithCancel(context.Background())
	defer cancel()

	if err := autoscaler.DoScaling(ctx); err != nil {
		logger.Error("dry run failed", zap.Error(err))
		return err
	}

	result := autoscaler.GetLastDryRun()
	if result != nil {
		printDryRunResult(result)
	}

	logger.Info("dry run completed successfully")
	return nil
}

func runReplay(cmd *cobra.Command, args []string) error {
	logger, err := initLogger(logLevel)
	if err != nil {
		return fmt.Errorf("failed to initialize logger: %w", err)
	}
	defer logger.Sync()

	cfg, err := config.LoadConfig(cfgFile)
	if err != nil {
		return fmt.Errorf("failed to load config: %w", err)
	}

	cfg.Autoscaler.HistoryEnabled = true

	logger.Info("starting history replay",
		zap.String("start", replayStart),
		zap.String("end", replayEnd),
	)

	monitorClient, err := initMonitor(cfg, logger)
	if err != nil {
		return fmt.Errorf("failed to initialize monitor: %w", err)
	}

	predictor := predict.NewPredictor(cfg.GetPredictorConfig())
	strategyCfg, err := cfg.GetStrategyConfig()
	if err != nil {
		return fmt.Errorf("failed to get strategy config: %w", err)
	}
	strategyEngine := strategy.NewStrategyEngine(strategyCfg, logger)
	cloudProvider, err := initCloudProvider(cfg, logger)
	if err != nil {
		return fmt.Errorf("failed to initialize cloud provider: %w", err)
	}

	autoscalerCfg, err := cfg.GetAutoscalerConfig()
	if err != nil {
		return fmt.Errorf("failed to get autoscaler config: %w", err)
	}

	autoscaler := controller.NewAutoscaler(
		autoscalerCfg,
		monitorClient,
		predictor,
		strategyEngine,
		cloudProvider,
		logger,
	)

	ctx, cancel := context.WithCancel(context.Background())
	defer cancel()

	var startTime, endTime time.Time
	if replayStart != "" {
		startTime, _ = time.Parse(time.RFC3339, replayStart)
	}
	if replayEnd != "" {
		endTime, _ = time.Parse(time.RFC3339, replayEnd)
	}

	replayConfig := types.HistoryReplayConfig{
		StartTime: startTime,
		EndTime:   endTime,
		Visualize: true,
	}

	result, err := autoscaler.RunReplay(ctx, replayConfig)
	if err != nil {
		logger.Error("replay failed", zap.Error(err))
		return err
	}

	report, err := autoscaler.GenerateVisualReport(ctx, replayConfig)
	if err != nil {
		logger.Error("failed to generate report", zap.Error(err))
	} else {
		fmt.Println(report)
	}

	printReplayResult(result)

	logger.Info("history replay completed successfully",
		zap.Int("total_records", result.TotalSteps),
	)
	return nil
}

func printDryRunResult(result *types.DryRunResult) {
	fmt.Println("\n=== Dry Run Result ===")
	fmt.Printf("Mode: %s\n", result.Mode)
	fmt.Printf("Time: %s\n", result.Timestamp.Format(time.RFC3339))
	fmt.Printf("Would Execute: %v\n", result.WouldExecute)
	if result.Action != nil {
		fmt.Printf("Action: %s %d instances\n", result.Action.Type, result.Action.Step)
		fmt.Printf("Charge Type: %s\n", result.Action.ChargeType)
		if result.Action.CostEstimate != 0 {
			fmt.Printf("Cost Estimate: $%.4f/hour\n", result.Action.CostEstimate)
		}
	}
	fmt.Printf("Risk Level: %s\n", result.RiskLevel)
	if result.RiskAssessment != "" {
		fmt.Printf("Risk Assessment: %s\n", result.RiskAssessment)
	}
	if len(result.Recommendations) > 0 {
		fmt.Println("\nRecommendations:")
		for _, rec := range result.Recommendations {
			fmt.Printf("  - %s\n", rec)
		}
	}
	if len(result.ValidationErrors) > 0 {
		fmt.Println("\nValidation Errors:")
		for _, err := range result.ValidationErrors {
			fmt.Printf("  - %s\n", err)
		}
	}
	fmt.Println("=====================")
}

func printReplayResult(result *types.ReplayResult) {
	fmt.Println("\n=== Replay Result ===")
	fmt.Printf("Total Steps: %d\n", result.TotalSteps)
	fmt.Printf("Scale Ups: %d\n", result.ScaleUps)
	fmt.Printf("Scale Downs: %d\n", result.ScaleDowns)
	fmt.Printf("No Changes: %d\n", result.NoChanges)
	if len(result.Recommendations) > 0 {
		fmt.Println("\nRecommendations:")
		for _, rec := range result.Recommendations {
			fmt.Printf("  - %s\n", rec)
		}
	}
	fmt.Println("=====================")
}

func initLogger(level string) (*zap.Logger, error) {
	var logLevel zapcore.Level
	switch level {
	case "debug":
		logLevel = zapcore.DebugLevel
	case "info", "":
		logLevel = zapcore.InfoLevel
	case "warn":
		logLevel = zapcore.WarnLevel
	case "error":
		logLevel = zapcore.ErrorLevel
	default:
		return nil, fmt.Errorf("invalid log level: %s", level)
	}

	encoderConfig := zap.NewProductionEncoderConfig()
	encoderConfig.EncodeTime = zapcore.ISO8601TimeEncoder
	encoderConfig.EncodeLevel = zapcore.CapitalColorLevelEncoder

	core := zapcore.NewCore(
		zapcore.NewConsoleEncoder(encoderConfig),
		zapcore.AddSync(os.Stdout),
		logLevel,
	)

	return zap.New(core, zap.AddCaller(), zap.AddStacktrace(zapcore.ErrorLevel)), nil
}

func initMonitor(cfg *config.Config, logger *zap.Logger) (*monitor.PrometheusClient, error) {
	promCfg := cfg.GetPrometheusConfig()
	client, err := monitor.NewPrometheusClient(promCfg, logger)
	if err != nil {
		return nil, fmt.Errorf("failed to create prometheus client: %w", err)
	}

	ctx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
	defer cancel()

	_, err = client.QueryMetric(ctx, "up")
	if err != nil {
		logger.Warn("failed to connect to prometheus, will use simulated data", zap.Error(err))
	}

	return client, nil
}

func initCloudProvider(cfg *config.Config, logger *zap.Logger) (cloud.CloudProvider, error) {
	cloudCfg := cfg.GetCloudConfig()

	if cloudCfg.Type == types.ProviderMock {
		mockInstances := []types.InstanceInfo{
			{
				ID:         "mock-instance-1",
				Name:       "mock-server-1",
				Status:     "running",
				Flavor:     "ecs.medium",
				CPUCores:   2,
				MemoryGB:   4,
				PrivateIP:  "192.168.1.10",
				PublicIP:   "1.2.3.4",
				CreateTime: time.Now().Add(-24 * time.Hour),
			},
			{
				ID:         "mock-instance-2",
				Name:       "mock-server-2",
				Status:     "running",
				Flavor:     "ecs.medium",
				CPUCores:   2,
				MemoryGB:   4,
				PrivateIP:  "192.168.1.11",
				CreateTime: time.Now().Add(-24 * time.Hour),
			},
		}

		mockGroup := &types.InstanceGroup{
			ID:        "mock-group-1",
			Name:      "mock-scaling-group",
			Instances: mockInstances,
			MinSize:   1,
			MaxSize:   10,
			Desired:   2,
		}

		cloudCfg.MockData = &cloud.MockProviderConfig{
			Instances:     mockInstances,
			InstanceGroup: mockGroup,
			Flavors: []string{
				"ecs.small", "ecs.medium", "ecs.large", "ecs.xlarge", "ecs.2xlarge",
			},
		}

		logger.Info("using mock cloud provider with simulated instances",
			zap.Int("instance_count", len(mockInstances)),
		)
	}

	return cloud.NewCloudProvider(cloudCfg, logger)
}
