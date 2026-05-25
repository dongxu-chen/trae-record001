package main

import (
	"context"
	"db-bench/internal/analysis"
	"db-bench/internal/config"
	"db-bench/internal/engine"
	"db-bench/internal/storage"
	"fmt"
	"log"
	"os"
	"os/signal"
	"strings"
	"syscall"
	"time"

	"github.com/spf13/cobra"
)

var (
	configPath string
	dbType     string
	dbHost     string
	dbPort     int
	dbUser     string
	dbPassword string
	dbName     string
	duration   time.Duration
	concurrency int
	readRatio  float64
	writeRatio float64
	hotspotPct float64
	hotspotRatio float64
	hotspotDistribution string
	hotspotSkew float64
	totalRecords int
	rateLimit  int
	promPort   int
	gradualStartup bool
	gradualStartupStep float64
	gradualStartupInterval time.Duration
	dataDir string
	resumeRunID string
	autoTuneEnabled bool
	autoTuneMode string
	autoTuneTargetP99 float64
	autoTuneMinConcurrency int
	autoTuneMaxConcurrency int
	autoTuneStopOnInflection bool
	timeseriesInterval time.Duration
	snapshotInterval time.Duration
)

var rootCmd = &cobra.Command{
	Use:   "db-bench",
	Short: "Database performance benchmark tool",
	Long: `A high-performance database benchmark tool supporting MySQL, PostgreSQL, and MongoDB.
Features:
- Customizable read/write ratio
- Hotspot data distribution simulation with skew control
- Real-time metrics (QPS/TPS, latency percentiles P50/P99/P999, error rate)
- T-Digest algorithm for accurate latency percentile estimation
- Gradual worker startup for smooth load ramp-up
- Historical data persistence and comparison
- Resume interrupted benchmarks from checkpoints
- Automatic performance tuning with PID controller
- Prometheus integration for monitoring
- Grafana dashboard support`,
}

var runCmd = &cobra.Command{
	Use:   "run",
	Short: "Run a benchmark",
	RunE:  runBenchmark,
}

var historyCmd = &cobra.Command{
	Use:   "history",
	Short: "List benchmark history",
	Long:  "List all historical benchmark runs with summary metrics",
	RunE:  listHistory,
}

var replayCmd = &cobra.Command{
	Use:   "replay",
	Short: "Replay benchmark data",
	Long:  "Export or display historical benchmark time-series data",
	RunE:  replayData,
}

var compareCmd = &cobra.Command{
	Use:   "compare [run_ids...]",
	Short: "Compare multiple benchmark runs",
	Long:  "Compare performance metrics across multiple benchmark runs",
	Args:  cobra.MinimumNArgs(1),
	RunE:  compareRuns,
}

var resumeCmd = &cobra.Command{
	Use:   "resume [run_id]",
	Short: "Resume an interrupted benchmark",
	Long:  "Resume a benchmark from the last saved checkpoint",
	Args:  cobra.ExactArgs(1),
	RunE:  resumeBenchmark,
}

var autoCmd = &cobra.Command{
	Use:   "auto",
	Short: "Run in auto-tuning mode",
	Long:  "Automatically find the optimal concurrency level within latency constraints",
	RunE:  runAutoTune,
}

var analyzeCmd = &cobra.Command{
	Use:   "analyze [run_id]",
	Short: "Analyze a benchmark run",
	Long:  "Perform detailed analysis of a benchmark run including inflection point detection",
	Args:  cobra.ExactArgs(1),
	RunE:  analyzeRun,
}

var exportCmd = &cobra.Command{
	Use:   "export [run_id]",
	Short: "Export benchmark data to CSV",
	Long:  "Export time-series data of a benchmark run to CSV format",
	Args:  cobra.ExactArgs(1),
	RunE:  exportData,
}

var deleteCmd = &cobra.Command{
	Use:   "delete [run_id]",
	Short: "Delete a benchmark run",
	Long:  "Delete all data associated with a benchmark run",
	Args:  cobra.ExactArgs(1),
	RunE:  deleteRun,
}

var versionCmd = &cobra.Command{
	Use:   "version",
	Short: "Print the version number",
	Run: func(cmd *cobra.Command, args []string) {
		fmt.Println("db-bench v2.0.0")
	},
}

func init() {
	rootCmd.PersistentFlags().StringVarP(&configPath, "config", "c", "", "Path to config file")
	rootCmd.PersistentFlags().StringVar(&dataDir, "data-dir", "./data", "Data directory for storing results")

	runCmd.Flags().StringVar(&dbType, "db-type", "", "Database type (mysql, postgres, mongodb)")
	runCmd.Flags().StringVar(&dbHost, "db-host", "", "Database host")
	runCmd.Flags().IntVar(&dbPort, "db-port", 0, "Database port")
	runCmd.Flags().StringVar(&dbUser, "db-user", "", "Database user")
	runCmd.Flags().StringVar(&dbPassword, "db-password", "", "Database password")
	runCmd.Flags().StringVar(&dbName, "db-name", "", "Database name")
	runCmd.Flags().DurationVarP(&duration, "duration", "d", 0, "Benchmark duration (e.g., 60s, 5m)")
	runCmd.Flags().IntVarP(&concurrency, "concurrency", "n", 0, "Number of concurrent workers")
	runCmd.Flags().Float64Var(&readRatio, "read-ratio", 0, "Read ratio (0.0-1.0)")
	runCmd.Flags().Float64Var(&writeRatio, "write-ratio", 0, "Write ratio (0.0-1.0)")
	runCmd.Flags().Float64Var(&hotspotPct, "hotspot-pct", 0, "Hotspot data percentage (0-100)")
	runCmd.Flags().Float64Var(&hotspotRatio, "hotspot-ratio", 0, "Hotspot access ratio (0.0-1.0)")
	runCmd.Flags().StringVar(&hotspotDistribution, "hotspot-dist", "", "Hotspot distribution (uniform, zipf)")
	runCmd.Flags().Float64Var(&hotspotSkew, "hotspot-skew", 0, "Hotspot Zipf skew factor (1.0-5.0)")
	runCmd.Flags().IntVar(&totalRecords, "records", 0, "Total number of records")
	runCmd.Flags().IntVar(&rateLimit, "rate-limit", 0, "Rate limit (ops/sec, 0 for unlimited)")
	runCmd.Flags().IntVar(&promPort, "prom-port", 0, "Prometheus exporter port")
	runCmd.Flags().BoolVar(&gradualStartup, "gradual-startup", true, "Enable gradual worker startup")
	runCmd.Flags().Float64Var(&gradualStartupStep, "gradual-step", 0, "Gradual startup step size (0.0-1.0)")
	runCmd.Flags().DurationVar(&gradualStartupInterval, "gradual-interval", 0, "Gradual startup interval")
	runCmd.Flags().DurationVar(&timeseriesInterval, "ts-interval", 5*time.Second, "Time-series recording interval")
	runCmd.Flags().DurationVar(&snapshotInterval, "snapshot-interval", 30*time.Second, "Checkpoint snapshot interval")

	autoCmd.Flags().StringVar(&dbType, "db-type", "", "Database type (mysql, postgres, mongodb)")
	autoCmd.Flags().StringVar(&dbHost, "db-host", "", "Database host")
	autoCmd.Flags().IntVar(&dbPort, "db-port", 0, "Database port")
	autoCmd.Flags().StringVar(&dbUser, "db-user", "", "Database user")
	autoCmd.Flags().StringVar(&dbPassword, "db-password", "", "Database password")
	autoCmd.Flags().StringVar(&dbName, "db-name", "", "Database name")
	autoCmd.Flags().StringVar(&autoTuneMode, "auto-mode", "latency", "Auto-tune mode (latency, throughput)")
	autoCmd.Flags().Float64Var(&autoTuneTargetP99, "target-p99", 100, "Target P99 latency in milliseconds")
	autoCmd.Flags().IntVar(&autoTuneMinConcurrency, "min-conn", 1, "Minimum concurrency")
	autoCmd.Flags().IntVar(&autoTuneMaxConcurrency, "max-conn", 1000, "Maximum concurrency")
	autoCmd.Flags().BoolVar(&autoTuneStopOnInflection, "stop-on-peak", true, "Stop when peak QPS is detected")
	autoCmd.Flags().DurationVar(&timeseriesInterval, "ts-interval", 5*time.Second, "Time-series recording interval")
	autoCmd.Flags().DurationVar(&snapshotInterval, "snapshot-interval", 30*time.Second, "Checkpoint snapshot interval")

	historyCmd.Flags().IntP("limit", "l", 20, "Maximum number of runs to display")

	replayCmd.Flags().String("format", "text", "Output format (text, json, csv)")
	replayCmd.Flags().Int("sample", 0, "Sample rate for data points")

	compareCmd.Flags().String("format", "text", "Output format (text, json)")

	rootCmd.AddCommand(runCmd)
	rootCmd.AddCommand(historyCmd)
	rootCmd.AddCommand(replayCmd)
	rootCmd.AddCommand(compareCmd)
	rootCmd.AddCommand(resumeCmd)
	rootCmd.AddCommand(autoCmd)
	rootCmd.AddCommand(analyzeCmd)
	rootCmd.AddCommand(exportCmd)
	rootCmd.AddCommand(deleteCmd)
	rootCmd.AddCommand(versionCmd)
}

func main() {
	if err := rootCmd.Execute(); err != nil {
		fmt.Fprintf(os.Stderr, "Error: %v\n", err)
		os.Exit(1)
	}
}

func openStorage() (*storage.Storage, error) {
	store, err := storage.NewStorage(dataDir)
	if err != nil {
		return nil, fmt.Errorf("failed to open storage: %w", err)
	}
	return store, nil
}

func runBenchmark(cmd *cobra.Command, args []string) error {
	cfg, err := config.LoadConfig(configPath)
	if err != nil {
		return fmt.Errorf("failed to load config: %w", err)
	}

	overrideConfig(cfg)
	cfg.Storage.DataDir = dataDir
	cfg.Storage.TimeSeriesInterval = timeseriesInterval
	cfg.Storage.SnapshotInterval = snapshotInterval

	if err := configValidate(cfg); err != nil {
		return err
	}

	printConfig(cfg)

	ctx, cancel := context.WithCancel(context.Background())
	defer cancel()

	sigChan := make(chan os.Signal, 1)
	signal.Notify(sigChan, syscall.SIGINT, syscall.SIGTERM)
	go func() {
		sig := <-sigChan
		fmt.Printf("\nReceived signal: %v, shutting down...\n", sig)
		cancel()
	}()

	eng, err := engine.NewBenchmarkEngine(*cfg)
	if err != nil {
		return fmt.Errorf("failed to create benchmark engine: %w", err)
	}
	log.Printf("Run ID: %s", eng.GetRunID())

	if err := eng.Prepare(ctx); err != nil {
		return fmt.Errorf("failed to prepare benchmark: %w", err)
	}

	shutdownCtx, shutdownCancel := context.WithTimeout(context.Background(), 30*time.Second)
	defer shutdownCancel()
	defer eng.Shutdown(shutdownCtx)

	if err := eng.Run(ctx); err != nil {
		if ctx.Err() == context.Canceled {
			log.Println("Benchmark canceled by user")
			return nil
		}
		return fmt.Errorf("benchmark failed: %w", err)
	}

	log.Println("Benchmark completed successfully")
	return nil
}

func resumeBenchmark(cmd *cobra.Command, args []string) error {
	runID := args[0]

	cfg, err := config.LoadConfig(configPath)
	if err != nil {
		return fmt.Errorf("failed to load config: %w", err)
	}

	overrideConfig(cfg)
	cfg.Storage.DataDir = dataDir
	cfg.Storage.TimeSeriesInterval = timeseriesInterval
	cfg.Storage.SnapshotInterval = snapshotInterval

	if err := configValidate(cfg); err != nil {
		return err
	}

	ctx, cancel := context.WithCancel(context.Background())
	defer cancel()

	sigChan := make(chan os.Signal, 1)
	signal.Notify(sigChan, syscall.SIGINT, syscall.SIGTERM)
	go func() {
		sig := <-sigChan
		fmt.Printf("\nReceived signal: %v, shutting down...\n", sig)
		cancel()
	}()

	eng, err := engine.NewBenchmarkEngine(*cfg)
	if err != nil {
		return fmt.Errorf("failed to create benchmark engine: %w", err)
	}

	if err := eng.Prepare(ctx); err != nil {
		return fmt.Errorf("failed to prepare benchmark: %w", err)
	}

	if err := eng.ResumeFromSnapshot(ctx, runID); err != nil {
		return fmt.Errorf("failed to resume from snapshot: %w", err)
	}

	shutdownCtx, shutdownCancel := context.WithTimeout(context.Background(), 30*time.Second)
	defer shutdownCancel()
	defer eng.Shutdown(shutdownCtx)

	if err := eng.Run(ctx); err != nil {
		if ctx.Err() == context.Canceled {
			log.Println("Benchmark canceled by user")
			return nil
		}
		return fmt.Errorf("benchmark failed: %w", err)
	}

	log.Println("Benchmark resumed and completed successfully")
	return nil
}

func runAutoTune(cmd *cobra.Command, args []string) error {
	cfg, err := config.LoadConfig(configPath)
	if err != nil {
		return fmt.Errorf("failed to load config: %w", err)
	}

	overrideConfig(cfg)
	cfg.Storage.DataDir = dataDir
	cfg.Storage.TimeSeriesInterval = timeseriesInterval
	cfg.Storage.SnapshotInterval = snapshotInterval

	cfg.AutoTune.Enabled = true
	cfg.AutoTune.Mode = config.AutoTuneMode(autoTuneMode)
	cfg.AutoTune.TargetLatencyP99 = autoTuneTargetP99
	cfg.AutoTune.MinConcurrency = autoTuneMinConcurrency
	cfg.AutoTune.MaxConcurrency = autoTuneMaxConcurrency
	cfg.AutoTune.StopOnInflection = autoTuneStopOnInflection
	cfg.AutoTune.AdjustInterval = 10 * time.Second
	cfg.AutoTune.Kp = 0.5
	cfg.AutoTune.Ki = 0.01
	cfg.AutoTune.Kd = 0.1
	cfg.AutoTune.InflectionWindow = 3

	if err := configValidate(cfg); err != nil {
		return err
	}

	printConfig(cfg)

	ctx, cancel := context.WithCancel(context.Background())
	defer cancel()

	sigChan := make(chan os.Signal, 1)
	signal.Notify(sigChan, syscall.SIGINT, syscall.SIGTERM)
	go func() {
		sig := <-sigChan
		fmt.Printf("\nReceived signal: %v, shutting down...\n", sig)
		cancel()
	}()

	eng, err := engine.NewBenchmarkEngine(*cfg)
	if err != nil {
		return fmt.Errorf("failed to create benchmark engine: %w", err)
	}
	log.Printf("Run ID: %s", eng.GetRunID())

	if err := eng.Prepare(ctx); err != nil {
		return fmt.Errorf("failed to prepare benchmark: %w", err)
	}

	shutdownCtx, shutdownCancel := context.WithTimeout(context.Background(), 30*time.Second)
	defer shutdownCancel()
	defer eng.Shutdown(shutdownCtx)

	if err := eng.Run(ctx); err != nil {
		if ctx.Err() == context.Canceled {
			log.Println("Benchmark canceled by user")
			return nil
		}
		return fmt.Errorf("benchmark failed: %w", err)
	}

	log.Println("Auto-tune benchmark completed successfully")
	return nil
}

func listHistory(cmd *cobra.Command, args []string) error {
	limit, _ := cmd.Flags().GetInt("limit")

	store, err := openStorage()
	if err != nil {
		return err
	}
	defer store.Close()

	ctx := context.Background()
	runs, err := store.ListRuns(ctx, limit)
	if err != nil {
		return fmt.Errorf("failed to list runs: %w", err)
	}

	fmt.Println()
	fmt.Println(analysis.ListRunsTable(runs))
	fmt.Println()

	return nil
}

func replayData(cmd *cobra.Command, args []string) error {
	if len(args) == 0 {
		return fmt.Errorf("run_id is required")
	}
	runID := args[0]

	format, _ := cmd.Flags().GetString("format")
	sampleRate, _ := cmd.Flags().GetInt("sample")

	store, err := openStorage()
	if err != nil {
		return err
	}
	defer store.Close()

	ctx := context.Background()

	opts := analysis.ReplayOptions{
		OutputFormat: format,
		SampleRate:   sampleRate,
	}

	points, err := analysis.ReplayData(ctx, store, runID, opts)
	if err != nil {
		return fmt.Errorf("failed to replay data: %w", err)
	}

	switch format {
	case "json":
		data, err := analysis.MarshalJSON(points)
		if err != nil {
			return err
		}
		fmt.Println(string(data))
	case "csv":
		csv, err := analysis.ExportCSV(ctx, store, runID)
		if err != nil {
			return err
		}
		fmt.Println(csv)
	default:
		fmt.Printf("Replaying %d data points for run %s:\n\n", len(points), runID)
		fmt.Printf("%-10s  %8s  %8s  %8s  %8s  %8s  %8s\n",
			"Elapsed", "Conc", "QPS", "TPS", "P50", "P99", "P999")
		fmt.Println(strings.Repeat("-", 70))
		for i, p := range points {
			if sampleRate > 0 && i%sampleRate != 0 && i != len(points)-1 {
				continue
			}
			fmt.Printf("%8.1fs  %8d  %8.1f  %8.1f  %8.2f  %8.2f  %8.2f\n",
				p.ElapsedSec, p.Concurrency, p.QPS, p.TPS, p.P50, p.P99, p.P999)
		}
	}

	return nil
}

func compareRuns(cmd *cobra.Command, args []string) error {
	format, _ := cmd.Flags().GetString("format")

	store, err := openStorage()
	if err != nil {
		return err
	}
	defer store.Close()

	ctx := context.Background()

	summary, err := analysis.CompareRuns(ctx, store, args)
	if err != nil {
		return fmt.Errorf("failed to compare runs: %w", err)
	}

	switch format {
	case "json":
		report, err := analysis.GenerateJSONReport(summary)
		if err != nil {
			return err
		}
		fmt.Println(report)
	default:
		fmt.Println()
		fmt.Println(analysis.GenerateReport(summary))
	}

	return nil
}

func analyzeRun(cmd *cobra.Command, args []string) error {
	runID := args[0]

	store, err := openStorage()
	if err != nil {
		return err
	}
	defer store.Close()

	ctx := context.Background()

	result, err := analysis.AnalyzeRun(ctx, store, runID)
	if err != nil {
		return fmt.Errorf("failed to analyze run: %w", err)
	}

	fmt.Println()
	fmt.Println("=== Benchmark Analysis ===")
	fmt.Printf("Run ID: %s\n", result.RunID)
	fmt.Println()
	fmt.Println("Performance Metrics:")
	fmt.Printf("  Peak QPS:      %.2f ops/s (at %s)\n", result.PeakQPS, result.PeakQPSAt.Format("15:04:05"))
	fmt.Printf("  Average QPS:   %.2f ops/s\n", result.AvgQPS)
	fmt.Printf("  Stability:     %.1f%%\n", result.StabilityScore)
	fmt.Println()
	fmt.Println("Latency Metrics:")
	fmt.Printf("  Average P99:   %.2f ms\n", result.AvgP99)
	fmt.Printf("  Min P99:       %.2f ms\n", result.MinP99)
	fmt.Printf("  Max P99:       %.2f ms\n", result.MaxP99)
	fmt.Println()
	fmt.Println("Trend Analysis:")
	fmt.Printf("  Error Rate:    %s\n", result.ErrorRateTrend)
	fmt.Printf("  Latency:       %s\n", result.LatencyTrend)
	fmt.Println()
	fmt.Println("Inflection Point Analysis:")
	if result.SaturationPoint {
		fmt.Printf("  Saturation Detected: YES\n")
		fmt.Printf("  Inflection QPS:  %.2f ops/s\n", result.InflectionPoint)
		fmt.Printf("  Inflection P99:  %.2f ms\n", result.InflectionLatency)
		fmt.Printf("  Recommendation:  Do not exceed %.0f concurrent connections\n",
			result.InflectionPoint/10)
	} else {
		fmt.Printf("  Saturation Detected: NO\n")
		fmt.Printf("  Recommendation:  System can handle higher load\n")
	}
	fmt.Println()

	return nil
}

func exportData(cmd *cobra.Command, args []string) error {
	runID := args[0]

	store, err := openStorage()
	if err != nil {
		return err
	}
	defer store.Close()

	ctx := context.Background()

	csv, err := analysis.ExportCSV(ctx, store, runID)
	if err != nil {
		return fmt.Errorf("failed to export data: %w", err)
	}

	fmt.Println(csv)
	return nil
}

func deleteRun(cmd *cobra.Command, args []string) error {
	runID := args[0]

	store, err := openStorage()
	if err != nil {
		return err
	}
	defer store.Close()

	ctx := context.Background()

	fmt.Printf("Are you sure you want to delete run %s? This cannot be undone. (y/N): ", runID)
	var confirm string
	fmt.Scanln(&confirm)

	if strings.ToLower(confirm) != "y" && strings.ToLower(confirm) != "yes" {
		fmt.Println("Delete canceled.")
		return nil
	}

	if err := store.DeleteRun(ctx, runID); err != nil {
		return fmt.Errorf("failed to delete run: %w", err)
	}

	fmt.Printf("Run %s deleted successfully.\n", runID)
	return nil
}

func overrideConfig(cfg *config.Config) {
	if dbType != "" {
		cfg.Database.Type = config.DatabaseType(dbType)
	}
	if dbHost != "" {
		cfg.Database.Host = dbHost
	}
	if dbPort > 0 {
		cfg.Database.Port = dbPort
	}
	if dbUser != "" {
		cfg.Database.User = dbUser
	}
	if dbPassword != "" {
		cfg.Database.Password = dbPassword
	}
	if dbName != "" {
		cfg.Database.Database = dbName
	}
	if duration > 0 {
		cfg.Scenario.Duration = duration
	}
	if concurrency > 0 {
		cfg.Scenario.Concurrency = concurrency
	}
	if readRatio > 0 || writeRatio > 0 {
		if readRatio == 0 && writeRatio == 0 {
		} else if readRatio == 0 {
			readRatio = 1.0 - writeRatio
		} else if writeRatio == 0 {
			writeRatio = 1.0 - readRatio
		}
		cfg.Scenario.ReadRatio = readRatio
		cfg.Scenario.WriteRatio = writeRatio
	}
	if hotspotPct > 0 {
		cfg.Scenario.HotspotPercentage = hotspotPct
	}
	if hotspotRatio > 0 {
		cfg.Scenario.HotspotAccessRatio = hotspotRatio
	}
	if hotspotDistribution != "" {
		cfg.Scenario.HotspotDistribution = config.HotspotDistributionType(hotspotDistribution)
	}
	if hotspotSkew > 0 {
		cfg.Scenario.HotspotSkew = hotspotSkew
	}
	if totalRecords > 0 {
		cfg.Scenario.TotalRecords = totalRecords
	}
	if rateLimit > 0 {
		cfg.Scenario.RateLimit = rateLimit
	}
	if promPort > 0 {
		cfg.Metrics.PrometheusPort = promPort
	}

	cfg.Scenario.GradualStartup = gradualStartup
	if gradualStartupStep > 0 {
		cfg.Scenario.GradualStartupStep = gradualStartupStep
	}
	if gradualStartupInterval > 0 {
		cfg.Scenario.GradualStartupInterval = gradualStartupInterval
	}

	if cfg.Database.Port == 0 {
		switch cfg.Database.Type {
		case config.MySQL:
			cfg.Database.Port = 3306
		case config.PostgreSQL:
			cfg.Database.Port = 5432
		case config.MongoDB:
			cfg.Database.Port = 27017
		}
	}
}

func configValidate(cfg *config.Config) error {
	if cfg.Database.Type == "" {
		return fmt.Errorf("database type is required (--db-type or config file)")
	}
	return nil
}

func printConfig(cfg *config.Config) {
	fmt.Println("=== Benchmark Configuration ===")
	fmt.Printf("Database:     %s\n", cfg.Database.Type)
	fmt.Printf("Host:         %s:%d\n", cfg.Database.Host, cfg.Database.Port)
	fmt.Printf("Database:     %s\n", cfg.Database.Database)
	fmt.Printf("User:         %s\n", cfg.Database.User)
	fmt.Printf("Max Conn:     %d\n", cfg.Database.MaxConnections)
	fmt.Println()
	fmt.Printf("Scenario:     %s\n", cfg.Scenario.Name)
	fmt.Printf("Duration:     %s\n", cfg.Scenario.Duration)
	fmt.Printf("Concurrency:  %d\n", cfg.Scenario.Concurrency)
	fmt.Printf("Read Ratio:   %.1f%%\n", cfg.Scenario.ReadRatio*100)
	fmt.Printf("Write Ratio:  %.1f%%\n", cfg.Scenario.WriteRatio*100)
	fmt.Printf("Hotspot:      %.1f%% of data, %.0f%% of access\n",
		cfg.Scenario.HotspotPercentage, cfg.Scenario.HotspotAccessRatio*100)
	fmt.Printf("Hotspot Dist: %s (skew=%.2f)\n", cfg.Scenario.HotspotDistribution, cfg.Scenario.HotspotSkew)
	fmt.Printf("Records:      %d\n", cfg.Scenario.TotalRecords)
	if cfg.Scenario.RateLimit > 0 {
		fmt.Printf("Rate Limit:   %d ops/sec\n", cfg.Scenario.RateLimit)
	} else {
		fmt.Printf("Rate Limit:   unlimited\n")
	}
	if cfg.Scenario.GradualStartup {
		fmt.Printf("Gradual Up:   +%.0f%% every %s\n",
			cfg.Scenario.GradualStartupStep*100, cfg.Scenario.GradualStartupInterval)
	} else {
		fmt.Printf("Gradual Up:   disabled\n")
	}
	if cfg.AutoTune.Enabled {
		fmt.Println()
		fmt.Println("Auto-Tune:    enabled")
		fmt.Printf("  Mode:       %s\n", cfg.AutoTune.Mode)
		fmt.Printf("  Target P99: %.2fms\n", cfg.AutoTune.TargetLatencyP99)
		fmt.Printf("  Range:      [%d, %d]\n", cfg.AutoTune.MinConcurrency, cfg.AutoTune.MaxConcurrency)
		fmt.Printf("  Stop Peak:  %v\n", cfg.AutoTune.StopOnInflection)
	}
	if cfg.Storage.DataDir != "" {
		fmt.Println()
		fmt.Println("Storage:      enabled")
		fmt.Printf("  Data Dir:   %s\n", cfg.Storage.DataDir)
		fmt.Printf("  TS Interval: %s\n", cfg.Storage.TimeSeriesInterval)
		fmt.Printf("  Snap Interval: %s\n", cfg.Storage.SnapshotInterval)
	}
	fmt.Println()
	fmt.Printf("Prometheus:   :%d%s\n", cfg.Metrics.PrometheusPort, cfg.Metrics.PrometheusPath)
	fmt.Println("================================")
	fmt.Println()
}
