package main

import (
	"context"
	"flag"
	"fmt"
	"math"
	"os"
	"os/signal"
	"sort"
	"strings"
	"syscall"
	"time"

	corev1 "k8s.io/api/core/v1"
	metav1 "k8s.io/apimachinery/pkg/apis/meta/v1"
	"k8s.io/client-go/kubernetes"
	"k8s.io/client-go/rest"
	"k8s.io/client-go/tools/clientcmd"

	"container-autoscaler/pkg/adjuster"
	"container-autoscaler/pkg/analyzer"
	"container-autoscaler/pkg/audit"
	"container-autoscaler/pkg/config"
	"container-autoscaler/pkg/monitor"
	"container-autoscaler/pkg/nodepressure"
	"container-autoscaler/pkg/predictor"
	"container-autoscaler/pkg/types"
	"container-autoscaler/pkg/utils"
)

func main() {
	configPath := flag.String("config", "config.yaml", "Path to configuration file")
	namespace := flag.String("namespace", "", "Kubernetes namespace to monitor")
	dryRun := flag.Bool("dry-run", false, "Run in dry-run mode")
	once := flag.Bool("once", false, "Run once and exit")
	backtest := flag.Bool("backtest", false, "Run backtest simulation over historical data")
	auditReport := flag.Bool("audit-report", false, "Generate audit report")
	nodePressureCheck := flag.Bool("check-pressure", false, "Check node pressure status")
	flag.Parse()

	logger := utils.NewLogger("info")

	cfg, err := config.LoadConfig(*configPath)
	if err != nil {
		logger.Fatal("Failed to load config: %v", err)
	}

	if *namespace != "" {
		cfg.Kubernetes.Namespace = *namespace
	}
	if *dryRun {
		cfg.DryRun = true
	}
	if *backtest {
		cfg.Backtest.Enabled = true
	}

	if cfg.DryRun {
		logger.Info("Running in DRY-RUN mode - no actual changes will be made")
	}

	logger = utils.NewLogger(cfg.LogLevel)

	promMonitor, err := monitor.NewPrometheusMonitor(cfg.Prometheus, logger)
	if err != nil {
		logger.Fatal("Failed to create Prometheus monitor: %v", err)
	}

	k8sAdjuster, err := adjuster.NewKubernetesAdjuster(cfg.Kubernetes, cfg.Scaling, logger)
	if err != nil {
		logger.Fatal("Failed to create Kubernetes adjuster: %v", err)
	}

	kubeClient, err := createKubernetesClient(cfg.Kubernetes)
	if err != nil {
		logger.Fatal("Failed to create Kubernetes client: %v", err)
	}

	auditor, err := audit.NewAuditor(cfg.Audit, logger)
	if err != nil {
		logger.Warning("Failed to create auditor: %v", err)
		auditor = nil
	}

	nodePressureMonitor := nodepressure.NewNodePressureMonitor(kubeClient, cfg.NodePressure, logger)

	resourceAnalyzer := analyzer.NewResourceAnalyzer(cfg.Analysis, logger)
	regressionAnalyzer := analyzer.NewRegressionAnalyzer(logger)
	timeSeriesPredictor := predictor.NewTimeSeriesPredictor(cfg.Prediction, logger)

	autoscaler := NewAutoScaler(
		cfg,
		promMonitor,
		k8sAdjuster,
		resourceAnalyzer,
		regressionAnalyzer,
		timeSeriesPredictor,
		auditor,
		nodePressureMonitor,
		logger,
	)

	ctx, cancel := context.WithCancel(context.Background())
	defer cancel()

	sigCh := make(chan os.Signal, 1)
	signal.Notify(sigCh, syscall.SIGINT, syscall.SIGTERM)

	go func() {
		sig := <-sigCh
		logger.Info("Received signal %v, shutting down...", sig)
		cancel()
	}()

	if *nodePressureCheck {
		if err := nodePressureMonitor.RefreshNodePressures(ctx); err != nil {
			logger.Error("Failed to refresh node pressures: %v", err)
		}
		nodePressureMonitor.PrintNodePressureSummary()
		return
	}

	if *auditReport && auditor != nil {
		report := auditor.GenerateReport(time.Now().AddDate(0, 0, -7), time.Now())
		auditor.PrintReport(report)
		return
	}

	if cfg.Backtest.Enabled {
		if err := autoscaler.RunBacktest(ctx); err != nil {
			logger.Error("Backtest failed: %v", err)
			os.Exit(1)
		}
		logger.Info("Backtest completed successfully")
		return
	}

	if *once {
		if err := autoscaler.RunOnce(ctx); err != nil {
			logger.Error("Run failed: %v", err)
			os.Exit(1)
		}
		logger.Info("Single run completed successfully")
		return
	}

	if err := autoscaler.Run(ctx); err != nil {
		logger.Fatal("Fatal error: %v", err)
	}
}

func createKubernetesClient(cfg config.KubernetesConfig) (kubernetes.Interface, error) {
	var config *rest.Config
	var err error

	if cfg.KubeconfigPath != "" {
		config, err = clientcmd.BuildConfigFromFlags("", cfg.KubeconfigPath)
	} else {
		config, err = rest.InClusterConfig()
	}
	if err != nil {
		return nil, fmt.Errorf("building kubernetes config: %w", err)
	}

	client, err := kubernetes.NewForConfig(config)
	if err != nil {
		return nil, fmt.Errorf("creating kubernetes client: %w", err)
	}

	return client, nil
}

type AutoScaler struct {
	config            *config.Config
	promMonitor       *monitor.PrometheusMonitor
	k8sAdjuster       *adjuster.KubernetesAdjuster
	resourceAnalyzer  *analyzer.ResourceAnalyzer
	regressionAnalyzer *analyzer.RegressionAnalyzer
	predictor         *predictor.TimeSeriesPredictor
	auditor           *audit.Auditor
	nodePressure      *nodepressure.NodePressureMonitor
	logger            *utils.Logger
}

func NewAutoScaler(
	cfg *config.Config,
	promMonitor *monitor.PrometheusMonitor,
	k8sAdjuster *adjuster.KubernetesAdjuster,
	resourceAnalyzer *analyzer.ResourceAnalyzer,
	regressionAnalyzer *analyzer.RegressionAnalyzer,
	predictor *predictor.TimeSeriesPredictor,
	auditor *audit.Auditor,
	nodePressure *nodepressure.NodePressureMonitor,
	logger *utils.Logger,
) *AutoScaler {
	return &AutoScaler{
		config:            cfg,
		promMonitor:       promMonitor,
		k8sAdjuster:       k8sAdjuster,
		resourceAnalyzer:  resourceAnalyzer,
		regressionAnalyzer: regressionAnalyzer,
		predictor:         predictor,
		auditor:           auditor,
		nodePressure:      nodePressure,
		logger:            logger,
	}
}

func (a *AutoScaler) Run(ctx context.Context) error {
	a.logger.Info("Starting container autoscaler")
	a.logger.Info("Check interval: %s", a.config.CheckInterval)
	a.logger.Info("Namespace: %s", a.config.Kubernetes.Namespace)

	ticker := time.NewTicker(a.config.CheckInterval)
	defer ticker.Stop()

	for {
		select {
		case <-ctx.Done():
			a.logger.Info("AutoScaler shutting down...")
			return nil
		case <-ticker.C:
			if err := a.RunOnce(ctx); err != nil {
				a.logger.Error("Run cycle failed: %v", err)
			}
		}
	}
}

func (a *AutoScaler) RunOnce(ctx context.Context) error {
	a.logger.Info("Starting analysis cycle...")

	namespace := a.config.Kubernetes.Namespace
	if namespace == "" {
		namespace = "default"
	}

	if a.config.NodePressure.Enabled && a.nodePressure != nil {
		if err := a.nodePressure.RefreshNodePressures(ctx); err != nil {
			a.logger.Warning("Failed to refresh node pressures: %v", err)
		}
		a.nodePressure.PrintNodePressureSummary()
	}

	metrics, err := a.promMonitor.GetContainerMetrics(ctx, namespace)
	if err != nil {
		return fmt.Errorf("collecting metrics: %w", err)
	}

	if len(metrics) == 0 {
		a.logger.Info("No container metrics found in namespace: %s", namespace)
		return nil
	}

	a.logger.Info("Collected metrics for %d containers", len(metrics))

	cpuTimeSeries, err := a.promMonitor.GetMetricTimeSeries(ctx, namespace, "cpu")
	if err != nil {
		a.logger.Error("Failed to get CPU time series: %v", err)
	}

	memoryTimeSeries, err := a.promMonitor.GetMetricTimeSeries(ctx, namespace, "memory")
	if err != nil {
		a.logger.Error("Failed to get memory time series: %v", err)
	}

	for _, metric := range metrics {
		if err := a.processContainer(ctx, metric, cpuTimeSeries, memoryTimeSeries); err != nil {
			a.logger.Error("Error processing container %s/%s/%s: %v",
				metric.Namespace, metric.PodName, metric.ContainerName, err)
		}
	}

	if a.auditor != nil {
		_ = a.auditor.CleanupOldRecords()
	}

	a.logger.Info("Analysis cycle completed")
	return nil
}

func (a *AutoScaler) RunBacktest(ctx context.Context) error {
	a.logger.Info("=== Starting Backtest Simulation ===")
	a.logger.Info("Backtest period: %d days, step: %d minutes",
		a.config.Backtest.DaysToSimulate, a.config.Backtest.StepMinutes)

	namespace := a.config.Kubernetes.Namespace
	if namespace == "" {
		namespace = "default"
	}

	cpuTimeSeries, err := a.promMonitor.GetMetricTimeSeries(ctx, namespace, "cpu")
	if err != nil {
		return fmt.Errorf("getting CPU time series: %w", err)
	}

	memoryTimeSeries, err := a.promMonitor.GetMetricTimeSeries(ctx, namespace, "memory")
	if err != nil {
		return fmt.Errorf("getting memory time series: %w", err)
	}

	metrics, err := a.promMonitor.GetContainerMetrics(ctx, namespace)
	if err != nil {
		return fmt.Errorf("getting container metrics: %w", err)
	}

	totalWasteSaved := 0.0
	totalOriginalWaste := 0.0
	totalContentions := 0
	backtestCount := 0

	for key, cpuTS := range cpuTimeSeries {
		var podName, containerName, ns string
		for _, m := range metrics {
			if fmt.Sprintf("%s/%s/%s", m.Namespace, m.PodName, m.ContainerName) == key {
				podName = m.PodName
				containerName = m.ContainerName
				ns = m.Namespace
				break
			}
		}
		if podName == "" {
			parts := strings.Split(key, "/")
			if len(parts) == 3 {
				ns = parts[0]
				podName = parts[1]
				containerName = parts[2]
			}
		}

		a.logger.Info("--- Backtesting CPU for %s ---", key)

		cfg := adjuster.BacktestConfig{
			Namespace:      ns,
			PodName:        podName,
			ContainerName:  containerName,
			ResourceType:   corev1.ResourceCPU,
			DaysToSimulate: a.config.Backtest.DaysToSimulate,
			StepMinutes:    a.config.Backtest.StepMinutes,
			CooldownMinutes: a.config.Backtest.CooldownMinutes,
		}

		var initCPU, initCPUReq float64
		for _, m := range metrics {
			if fmt.Sprintf("%s/%s/%s", m.Namespace, m.PodName, m.ContainerName) == key {
				initCPU = m.CPULimit
				initCPUReq = m.CPURequest
				break
			}
		}
		if initCPU == 0 {
			initCPU = 500
			initCPUReq = 375
		}

		recommender := func(history []float64, currentLimit float64) (float64, float64, string) {
			return a.generateBacktestRecommendation(history, currentLimit, "cpu")
		}

		result := a.k8sAdjuster.RunBacktest(ctx, cpuTS, cfg, initCPU, initCPUReq, recommender)
		if result != nil {
			a.logger.Info("  CPU: %s", result.Recommendation)
			a.logger.Info("  Actions taken: %d, Original waste: %.0f, Simulated waste: %.0f, Saved: %.0f",
				len(result.Actions), result.OriginalWaste, result.SimulatedWaste, result.WasteSaved)
			totalWasteSaved += result.WasteSaved
			totalOriginalWaste += result.OriginalWaste
			totalContentions += result.ContentionCount
			backtestCount++
		}

		if memTS, ok := memoryTimeSeries[key]; ok {
			a.logger.Info("--- Backtesting Memory for %s ---", key)

			cfgMem := cfg
			cfgMem.ResourceType = corev1.ResourceMemory

			var initMem, initMemReq float64
			for _, m := range metrics {
				if fmt.Sprintf("%s/%s/%s", m.Namespace, m.PodName, m.ContainerName) == key {
					initMem = m.MemoryLimit
					initMemReq = m.MemoryRequest
					break
				}
			}
			if initMem == 0 {
				initMem = 512
				initMemReq = 384
			}

			memRecommender := func(history []float64, currentLimit float64) (float64, float64, string) {
				return a.generateBacktestRecommendation(history, currentLimit, "memory")
			}

			memResult := a.k8sAdjuster.RunBacktest(ctx, memTS, cfgMem, initMem, initMemReq, memRecommender)
			if memResult != nil {
				a.logger.Info("  Memory: %s", memResult.Recommendation)
				a.logger.Info("  Actions taken: %d, Original waste: %.0fMi, Simulated waste: %.0fMi, Saved: %.0fMi",
					len(memResult.Actions), memResult.OriginalWaste, memResult.SimulatedWaste, memResult.WasteSaved)
				totalWasteSaved += memResult.WasteSaved
				totalOriginalWaste += memResult.OriginalWaste
				totalContentions += memResult.ContentionCount
				backtestCount++
			}
		}
	}

	a.logger.Info("=== Backtest Summary ===")
	a.logger.Info("Containers backtested: %d", backtestCount)
	if totalOriginalWaste > 0 {
		a.logger.Info("Total original waste: %.0f units", totalOriginalWaste)
		a.logger.Info("Total simulated waste: %.0f units", totalOriginalWaste-totalWasteSaved)
		a.logger.Info("Total waste saved: %.0f units (%.1f%%)",
			totalWasteSaved, totalWasteSaved/totalOriginalWaste*100)
	}
	a.logger.Info("Total contentions avoided: %d", totalContentions)

	return nil
}

func (a *AutoScaler) generateBacktestRecommendation(
	history []float64,
	currentLimit float64,
	resourceType string,
) (float64, float64, string) {
	n := len(history)
	if n == 0 {
		return currentLimit, currentLimit * 0.75, "insufficient data"
	}

	sorted := make([]float64, n)
	copy(sorted, history)
	sort.Float64s(sorted)

	p95 := percentile(sorted, 95)
	p99 := percentile(sorted, 99)

	meanVal := mean(history)
	stdDevVal := stdDev(history, meanVal)

	var targetUsage float64
	switch resourceType {
	case "cpu":
		targetUsage = p95
	case "memory":
		targetUsage = p99
	default:
		targetUsage = p95
	}

	headroom := targetUsage * 0.25
	proposedLimit := targetUsage + headroom

	var minLimit, maxLimit, requestRatio float64
	switch resourceType {
	case "cpu":
		minLimit = a.config.Scaling.MinCPULimit
		maxLimit = a.config.Scaling.MaxCPULimit
		requestRatio = a.config.Scaling.CPURequestRatio
	case "memory":
		minLimit = a.config.Scaling.MinMemoryLimit
		maxLimit = a.config.Scaling.MaxMemoryLimit
		requestRatio = a.config.Scaling.MemoryRequestRatio
	default:
		minLimit = 100
		maxLimit = 4000
		requestRatio = 0.75
	}

	if proposedLimit < minLimit {
		proposedLimit = minLimit
	}
	if proposedLimit > maxLimit {
		proposedLimit = maxLimit
	}

	maxAdj := currentLimit * a.config.Scaling.MaxAdjustmentPercent
	if proposedLimit > currentLimit+maxAdj {
		proposedLimit = currentLimit + maxAdj
	}
	if proposedLimit < currentLimit-maxAdj {
		proposedLimit = currentLimit - maxAdj
	}

	proposedRequest := proposedLimit * requestRatio

	volatility := 0.0
	if meanVal > 0 {
		volatility = stdDevVal / meanVal
	}

	reason := fmt.Sprintf("P95=%.1f, P99=%.1f, mean=%.1f, vol=%.2f", p95, p99, meanVal, volatility)

	return proposedLimit, proposedRequest, reason
}

func percentile(sorted []float64, p float64) float64 {
	if len(sorted) == 0 {
		return 0
	}
	rank := p / 100.0 * float64(len(sorted)-1)
	lower := int(math.Floor(rank))
	upper := int(math.Ceil(rank))
	if lower == upper {
		return sorted[lower]
	}
	frac := rank - float64(lower)
	return sorted[lower]*(1-frac) + sorted[upper]*frac
}

func mean(values []float64) float64 {
	if len(values) == 0 {
		return 0
	}
	sum := 0.0
	for _, v := range values {
		sum += v
	}
	return sum / float64(len(values))
}

func stdDev(values []float64, meanVal float64) float64 {
	if len(values) == 0 {
		return 0
	}
	sumSquared := 0.0
	for _, v := range values {
		diff := v - meanVal
		sumSquared += diff * diff
	}
	return math.Sqrt(sumSquared / float64(len(values)))
}

func (a *AutoScaler) processContainer(
	ctx context.Context,
	metric types.ResourceMetrics,
	cpuTimeSeries map[string]types.TimeSeriesData,
	memoryTimeSeries map[string]types.TimeSeriesData,
) error {
	key := fmt.Sprintf("%s/%s/%s", metric.Namespace, metric.PodName, metric.ContainerName)

	a.logger.Debug("Processing container: %s", key)

	pod, err := a.k8sAdjuster.GetPod(ctx, metric.Namespace, metric.PodName)
	var nodeName string
	if err != nil {
		a.logger.Debug("Failed to get pod for node info: %v", err)
	} else {
		nodeName = pod.Spec.NodeName
	}

	var cpuDayPrediction *types.DayPrediction
	var memDayPrediction *types.DayPrediction
	if a.config.Prediction.HourlyPredictionEnabled {
		if cpuTS, ok := cpuTimeSeries[key]; ok {
			if pred, err := a.predictor.PredictNext24Hours(cpuTS, "cpu"); err == nil {
				cpuDayPrediction = pred
				a.logger.Info("24h CPU forecast for %s: peak=%.0fm at hour %d, avg=%.0fm",
					key, pred.PeakCPU, pred.PeakHour, pred.AvgCPU)
			}
		}
		if memTS, ok := memoryTimeSeries[key]; ok {
			if pred, err := a.predictor.PredictNext24Hours(memTS, "memory"); err == nil {
				memDayPrediction = pred
				a.logger.Info("24h Memory forecast for %s: peak=%.0fMi at hour %d, avg=%.0fMi",
					key, pred.PeakMemory, pred.PeakHour, pred.AvgMemory)
			}
		}
	}

	var cpuAnalysis types.ResourceAnalysis
	if cpuTS, ok := cpuTimeSeries[key]; ok {
		cpuAnalysis = a.resourceAnalyzer.AnalyzeResource(
			cpuTS,
			metric.CPULimit,
			metric.CPURequest,
			"cpu",
			a.config.Scaling,
		)

		if cpuDayPrediction != nil && cpuDayPrediction.RecommendedLimit > cpuAnalysis.Recommendation.ProposedLimit {
			cpuAnalysis.Recommendation.ProposedLimit = cpuDayPrediction.RecommendedLimit
			cpuAnalysis.Recommendation.ProposedRequest = cpuDayPrediction.RecommendedLimit * a.config.Scaling.CPURequestRatio
			cpuAnalysis.Recommendation.AdjustmentReason += "; 24h peak forecast adjustment"
		}

		if a.config.Prediction.Enabled {
			predFunc := a.predictor.Predict
			if a.config.Prediction.CyclicPredictionEnabled {
				predFunc = a.predictor.PredictWithCyclic
			}
			cpuPrediction, err := predFunc(cpuTS, 3)
			if err != nil {
				a.logger.Debug("CPU prediction failed for %s: %v", key, err)
			} else {
				a.logger.Debug("CPU prediction for %s: %.2f (confidence: %.2f)",
					key, cpuPrediction.CPUPredictedUsage, cpuPrediction.ConfidenceInterval)

				if cpuPrediction.CPUPredictedUsage > cpuAnalysis.CurrentLimit*0.8 &&
					cpuPrediction.ConfidenceInterval > 0.6 {
					a.logger.Info("CPU pre-adjustment needed for %s: predicted usage %.2f exceeds 80%% of current limit %.2f",
						key, cpuPrediction.CPUPredictedUsage, cpuAnalysis.CurrentLimit)
				}
			}
		}
	}

	var memoryAnalysis types.ResourceAnalysis
	if memTS, ok := memoryTimeSeries[key]; ok {
		memoryAnalysis = a.resourceAnalyzer.AnalyzeResource(
			memTS,
			metric.MemoryLimit,
			metric.MemoryRequest,
			"memory",
			a.config.Scaling,
		)

		if memDayPrediction != nil && memDayPrediction.RecommendedLimit > memoryAnalysis.Recommendation.ProposedLimit {
			memoryAnalysis.Recommendation.ProposedLimit = memDayPrediction.RecommendedLimit
			memoryAnalysis.Recommendation.ProposedRequest = memDayPrediction.RecommendedLimit * a.config.Scaling.MemoryRequestRatio
			memoryAnalysis.Recommendation.AdjustmentReason += "; 24h peak forecast adjustment"
		}

		if a.config.Prediction.Enabled {
			predFunc := a.predictor.Predict
			if a.config.Prediction.CyclicPredictionEnabled {
				predFunc = a.predictor.PredictWithCyclic
			}
			memPrediction, err := predFunc(memTS, 3)
			if err != nil {
				a.logger.Debug("Memory prediction failed for %s: %v", key, err)
			} else {
				a.logger.Debug("Memory prediction for %s: %.2fMi (confidence: %.2f)",
					key, memPrediction.MemoryPredictedUsage, memPrediction.ConfidenceInterval)

				if memPrediction.MemoryPredictedUsage > memoryAnalysis.CurrentLimit*0.8 &&
					memPrediction.ConfidenceInterval > 0.6 {
					a.logger.Info("Memory pre-adjustment needed for %s: predicted usage %.2fMi exceeds 80%% of current limit %.2fMi",
						key, memPrediction.MemoryPredictedUsage, memoryAnalysis.CurrentLimit)
				}
			}
		}
	}

	if cpuTS, ok := cpuTimeSeries[key]; ok {
		anomalies := a.resourceAnalyzer.DetectAnomalies(cpuTS)
		if len(anomalies) > 0 {
			a.logger.Warning("Detected %d CPU usage anomalies for %s", len(anomalies), key)
		}
	}

	if memoryTS, ok := memoryTimeSeries[key]; ok {
		anomalies := a.resourceAnalyzer.DetectAnomalies(memoryTS)
		if len(anomalies) > 0 {
			a.logger.Warning("Detected %d memory usage anomalies for %s", len(anomalies), key)
		}
	}

	if cpuAnalysis.CurrentLimit > 0 {
		a.logger.Info("Container %s CPU: usage=%.2fm, limit=%.2fm, utilization=%.2f%%, recommendation: %.2fm",
			key, cpuAnalysis.CurrentUsage, cpuAnalysis.CurrentLimit,
			cpuAnalysis.UtilizationRatio*100, cpuAnalysis.Recommendation.ProposedLimit)

		if a.k8sAdjuster.ShouldAdjust(cpuAnalysis.Recommendation, cpuAnalysis.CurrentLimit, 0.6) {
			isUpscale := cpuAnalysis.Recommendation.ProposedLimit > cpuAnalysis.CurrentLimit

			canAdjust := true
			scheduledTime := time.Time{}
			scheduleID := ""

			if isUpscale && a.config.NodePressure.Enabled && a.nodePressure != nil && nodeName != "" {
				canAdjust, scheduledTime, scheduleID = a.nodePressure.CheckAndScheduleAdjustment(
					ctx,
					metric.Namespace,
					metric.PodName,
					metric.ContainerName,
					nodeName,
					corev1.ResourceCPU,
					cpuAnalysis.Recommendation.ProposedLimit,
					cpuAnalysis.Recommendation.ProposedRequest,
					cpuAnalysis.CurrentLimit,
					cpuAnalysis.Recommendation.AdjustmentReason,
					cpuAnalysis.Recommendation.Confidence,
				)

				if !canAdjust {
					a.logger.Info("CPU upscale for %s deferred to %s (node pressure) - schedule ID: %s",
						key, scheduledTime.Format(time.RFC3339), scheduleID)
				}
			}

			if canAdjust {
				action := types.AdjustmentAction{
					Namespace:     metric.Namespace,
					PodName:       metric.PodName,
					ContainerName: metric.ContainerName,
					ResourceType:  corev1.ResourceCPU,
					NewLimit:      cpuAnalysis.Recommendation.ProposedLimit,
					NewRequest:    cpuAnalysis.Recommendation.ProposedRequest,
					OldLimit:      cpuAnalysis.CurrentLimit,
					OldRequest:    cpuAnalysis.CurrentRequest,
					Reason:        cpuAnalysis.Recommendation.AdjustmentReason,
					Confidence:    cpuAnalysis.Recommendation.Confidence,
					DryRun:        a.config.DryRun,
				}

				if err := a.k8sAdjuster.ValidateAction(action); err != nil {
					a.logger.Warning("CPU adjustment validation failed for %s: %v", key, err)
				} else {
					result, err := a.k8sAdjuster.AdjustResources(ctx, action)
					errMsg := ""
					if err != nil {
						errMsg = err.Error()
						a.logger.Error("CPU adjustment failed for %s: %v", key, err)
					} else {
						a.logger.Info("CPU adjustment result for %s: applied=%v, message=%s",
							key, result.Applied, result.Message)
					}

					if a.auditor != nil {
						a.auditor.RecordAdjustment(
							ctx,
							metric.Namespace,
							metric.PodName,
							metric.ContainerName,
							nodeName,
							corev1.ResourceCPU,
							cpuAnalysis.CurrentLimit,
							cpuAnalysis.CurrentRequest,
							cpuAnalysis.CurrentUsage,
							cpuAnalysis.Recommendation.ProposedLimit,
							cpuAnalysis.Recommendation.ProposedRequest,
							cpuAnalysis.Recommendation.AdjustmentReason,
							cpuAnalysis.Recommendation.Confidence,
							a.config.DryRun,
							err == nil && result.Applied,
							errMsg,
						)
					}
				}
			}
		}
	}

	if memoryAnalysis.CurrentLimit > 0 {
		a.logger.Info("Container %s Memory: usage=%.2fMi, limit=%.2fMi, utilization=%.2f%%, recommendation: %.2fMi",
			key, memoryAnalysis.CurrentUsage, memoryAnalysis.CurrentLimit,
			memoryAnalysis.UtilizationRatio*100, memoryAnalysis.Recommendation.ProposedLimit)

		if a.k8sAdjuster.ShouldAdjust(memoryAnalysis.Recommendation, memoryAnalysis.CurrentLimit, 0.6) {
			isUpscale := memoryAnalysis.Recommendation.ProposedLimit > memoryAnalysis.CurrentLimit

			canAdjust := true
			scheduledTime := time.Time{}
			scheduleID := ""

			if isUpscale && a.config.NodePressure.Enabled && a.nodePressure != nil && nodeName != "" {
				canAdjust, scheduledTime, scheduleID = a.nodePressure.CheckAndScheduleAdjustment(
					ctx,
					metric.Namespace,
					metric.PodName,
					metric.ContainerName,
					nodeName,
					corev1.ResourceMemory,
					memoryAnalysis.Recommendation.ProposedLimit,
					memoryAnalysis.Recommendation.ProposedRequest,
					memoryAnalysis.CurrentLimit,
					memoryAnalysis.Recommendation.AdjustmentReason,
					memoryAnalysis.Recommendation.Confidence,
				)

				if !canAdjust {
					a.logger.Info("Memory upscale for %s deferred to %s (node pressure) - schedule ID: %s",
						key, scheduledTime.Format(time.RFC3339), scheduleID)
				}
			}

			if canAdjust {
				action := types.AdjustmentAction{
					Namespace:     metric.Namespace,
					PodName:       metric.PodName,
					ContainerName: metric.ContainerName,
					ResourceType:  corev1.ResourceMemory,
					NewLimit:      memoryAnalysis.Recommendation.ProposedLimit,
					NewRequest:    memoryAnalysis.Recommendation.ProposedRequest,
					OldLimit:      memoryAnalysis.CurrentLimit,
					OldRequest:    memoryAnalysis.CurrentRequest,
					Reason:        memoryAnalysis.Recommendation.AdjustmentReason,
					Confidence:    memoryAnalysis.Recommendation.Confidence,
					DryRun:        a.config.DryRun,
				}

				if err := a.k8sAdjuster.ValidateAction(action); err != nil {
					a.logger.Warning("Memory adjustment validation failed for %s: %v", key, err)
				} else {
					result, err := a.k8sAdjuster.AdjustResources(ctx, action)
					errMsg := ""
					if err != nil {
						errMsg = err.Error()
						a.logger.Error("Memory adjustment failed for %s: %v", key, err)
					} else {
						a.logger.Info("Memory adjustment result for %s: applied=%v, message=%s",
							key, result.Applied, result.Message)
					}

					if a.auditor != nil {
						a.auditor.RecordAdjustment(
							ctx,
							metric.Namespace,
							metric.PodName,
							metric.ContainerName,
							nodeName,
							corev1.ResourceMemory,
							memoryAnalysis.CurrentLimit,
							memoryAnalysis.CurrentRequest,
							memoryAnalysis.CurrentUsage,
							memoryAnalysis.Recommendation.ProposedLimit,
							memoryAnalysis.Recommendation.ProposedRequest,
							memoryAnalysis.Recommendation.AdjustmentReason,
							memoryAnalysis.Recommendation.Confidence,
							a.config.DryRun,
							err == nil && result.Applied,
							errMsg,
						)
					}
				}
			}
		}
	}

	return nil
}
