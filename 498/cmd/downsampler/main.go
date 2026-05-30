package main

import (
	"context"
	"flag"
	"fmt"
	"log"
	"os"
	"os/signal"
	"sync"
	"syscall"
	"time"

	"github.com/prometheus/downsampler/pkg/analysis"
	"github.com/prometheus/downsampler/pkg/config"
	"github.com/prometheus/downsampler/pkg/downsampling"
	promclient "github.com/prometheus/downsampler/pkg/prometheus"
	"github.com/prometheus/downsampler/pkg/proxy"
	"github.com/prometheus/downsampler/pkg/thanos"
)

type Scheduler struct {
	cfg                  *config.Config
	promClient           *promclient.Client
	downsampler          *downsampling.Engine
	thanosWriter         *thanos.Writer
	queryProxy           *proxy.TransparentProxy
	stats                *Stats
	errorStats           *ErrorStats
	recommendationStats  *RecommendationStats
	stopCh               chan struct{}
	wg                   sync.WaitGroup
}

type Stats struct {
	sync.Mutex
	TotalRuns       int64
	SuccessfulRuns  int64
	FailedRuns      int64
	TotalProcessed  int64
	TotalOutput     int64
	LastRunTime     time.Time
	LastSuccessTime time.Time
}

func NewStats() *Stats {
	return &Stats{}
}

func (s *Stats) RecordRun(success bool, processed, output int64) {
	s.Lock()
	defer s.Unlock()
	s.TotalRuns++
	if success {
		s.SuccessfulRuns++
		s.LastSuccessTime = time.Now()
	} else {
		s.FailedRuns++
	}
	s.TotalProcessed += processed
	s.TotalOutput += output
	s.LastRunTime = time.Now()
}

func (s *Stats) Get() map[string]interface{} {
	s.Lock()
	defer s.Unlock()
	return map[string]interface{}{
		"total_runs":        s.TotalRuns,
		"successful_runs":   s.SuccessfulRuns,
		"failed_runs":       s.FailedRuns,
		"total_processed":   s.TotalProcessed,
		"total_output":      s.TotalOutput,
		"last_run_time":     s.LastRunTime,
		"last_success_time": s.LastSuccessTime,
	}
}

type ErrorStats struct {
	sync.Mutex
	Metrics       map[string]analysis.ErrorMetrics
	LastAnalysis  map[string]time.Time
}

func NewErrorStats() *ErrorStats {
	return &ErrorStats{
		Metrics:      make(map[string]analysis.ErrorMetrics),
		LastAnalysis: make(map[string]time.Time),
	}
}

func (es *ErrorStats) Record(metric string, metrics analysis.ErrorMetrics) {
	es.Lock()
	defer es.Unlock()
	es.Metrics[metric] = metrics
	es.LastAnalysis[metric] = time.Now()
}

func (es *ErrorStats) Get() map[string]interface{} {
	es.Lock()
	defer es.Unlock()
	result := make(map[string]interface{})
	for k, v := range es.Metrics {
		result[k] = map[string]interface{}{
			"mae":          v.MAE,
			"rmse":         v.RMSE,
			"mape":         v.MAPE,
			"correlation":  v.Correlation,
			"last_analyzed": es.LastAnalysis[k],
		}
	}
	return result
}

type RecommendationStats struct {
	sync.Mutex
	Recommendations map[string]analysis.Recommendation
	LastGenerated   time.Time
}

func NewRecommendationStats() *RecommendationStats {
	return &RecommendationStats{
		Recommendations: make(map[string]analysis.Recommendation),
	}
}

func (rs *RecommendationStats) Record(metric string, rec analysis.Recommendation) {
	rs.Lock()
	defer rs.Unlock()
	rs.Recommendations[metric] = rec
}

func (rs *RecommendationStats) Get() map[string]interface{} {
	rs.Lock()
	defer rs.Unlock()
	result := make(map[string]interface{})
	for k, v := range rs.Recommendations {
		result[k] = map[string]interface{}{
			"recommended_levels": v.RecommendedLevels,
			"estimated_error":    v.EstimatedError,
			"estimated_saving":   v.EstimatedSaving,
			"score":              v.Score,
			"adaptive_enabled":   v.AdaptiveEnabled,
		}
	}
	return map[string]interface{}{
		"recommendations": result,
		"last_generated":  rs.LastGenerated,
	}
}

func NewScheduler(cfg *config.Config) (*Scheduler, error) {
	promClient, err := promclient.NewClient(cfg.Prometheus)
	if err != nil {
		return nil, fmt.Errorf("failed to create prometheus client: %w", err)
	}

	downsampler := downsampling.NewEngine(cfg.Global.Namespace)

	for _, rule := range cfg.MetricRules {
		if rule.AdaptiveDownsampling.Enabled {
			downsampler.InitAdaptive(rule.AdaptiveDownsampling)
			break
		}
	}

	for _, rule := range cfg.MetricRules {
		if rule.ErrorAnalysis.Enabled {
			downsampler.InitErrorAnalysis(rule.ErrorAnalysis)
			break
		}
	}

	for _, rule := range cfg.MetricRules {
		if rule.StrategyRecommendation.Enabled {
			downsampler.InitRecommendation(rule.StrategyRecommendation)
			break
		}
	}

	var thanosWriter *thanos.Writer
	if cfg.Thanos.Enabled {
		thanosWriter, err = thanos.NewWriter(cfg.Thanos, cfg.Global.Namespace)
		if err != nil {
			return nil, fmt.Errorf("failed to create thanos writer: %w", err)
		}
	}

	var queryProxy *proxy.TransparentProxy
	if cfg.Proxy.Enabled {
		queryProxy, err = proxy.NewTransparentProxy(cfg.Proxy, cfg.Prometheus, cfg.MetricRules, cfg.Global.Namespace)
		if err != nil {
			return nil, fmt.Errorf("failed to create transparent proxy: %w", err)
		}
	}

	return &Scheduler{
		cfg:               cfg,
		promClient:        promClient,
		downsampler:       downsampler,
		thanosWriter:      thanosWriter,
		queryProxy:        queryProxy,
		stats:             NewStats(),
		errorStats:        NewErrorStats(),
		recommendationStats: NewRecommendationStats(),
		stopCh:            make(chan struct{}),
	}, nil
}

func (s *Scheduler) Start() {
	if s.cfg.Proxy.Enabled && s.queryProxy != nil {
		s.wg.Add(1)
		go func() {
			defer s.wg.Done()
			if err := s.queryProxy.Start(); err != nil {
				log.Printf("Transparent proxy stopped with error: %v", err)
			}
		}()
	}

	s.wg.Add(1)
	go s.runScheduler()

	log.Printf("Downsampler started with %d metric rules", len(s.cfg.MetricRules))
	log.Printf("Scheduler interval: %v, lookback: %v", s.cfg.Scheduler.Interval, s.cfg.Scheduler.Lookback)
}

func (s *Scheduler) Stop() {
	close(s.stopCh)
	s.wg.Wait()
	log.Println("Downsampler stopped")
}

func (s *Scheduler) runScheduler() {
	defer s.wg.Done()

	ticker := time.NewTicker(s.cfg.Scheduler.Interval)
	defer ticker.Stop()

	if err := s.runOnce(); err != nil {
		log.Printf("Initial run failed: %v", err)
	}

	for {
		select {
		case <-ticker.C:
			if err := s.runOnce(); err != nil {
				log.Printf("Scheduled run failed: %v", err)
			}
		case <-s.stopCh:
			return
		}
	}
}

func (s *Scheduler) runOnce() error {
	ctx := context.Background()
	end := time.Now()
	start := end.Add(-s.cfg.Scheduler.Lookback)

	log.Printf("Starting downsampling run for period: %v to %v", start, end)

	var totalProcessed, totalOutput int64
	hasError := false

	for _, rule := range s.cfg.MetricRules {
		success, processed, output, err := s.processRule(ctx, rule, start, end)
		if err != nil {
			log.Printf("Error processing rule '%s': %v", rule.Name, err)
			hasError = true
			continue
		}

		totalProcessed += processed
		totalOutput += output
		reduction := 0.0
		if processed > 0 {
			reduction = (1 - float64(output)/float64(processed)) * 100
		}

		log.Printf("Rule '%s' completed: success=%v, input=%d, output=%d, reduction=%.2f%%",
			rule.Name, success, processed, output, reduction)
	}

	s.stats.RecordRun(!hasError, totalProcessed, totalOutput)

	if hasError {
		return fmt.Errorf("some rules failed during processing")
	}

	log.Printf("Downsampling run completed: total input=%d, total output=%d",
		totalProcessed, totalOutput)
	return nil
}

func (s *Scheduler) processRule(
	ctx context.Context,
	rule config.MetricRule,
	start, end time.Time,
) (bool, int64, int64, error) {
	for attempt := 0; attempt < s.cfg.Scheduler.MaxRetries; attempt++ {
		if attempt > 0 {
			log.Printf("Retrying rule '%s' (attempt %d/%d)", rule.Name, attempt+1, s.cfg.Scheduler.MaxRetries)
			time.Sleep(s.cfg.Scheduler.RetryInterval)
		}

		result, err := s.processRuleWithRetry(ctx, rule, start, end)
		if err == nil {
			return true, int64(result.InputCount), int64(result.OutputCount), nil
		}

		log.Printf("Attempt %d for rule '%s' failed: %v", attempt+1, rule.Name, err)
	}

	return false, 0, 0, fmt.Errorf("max retries exceeded for rule '%s'", rule.Name)
}

func (s *Scheduler) processRuleWithRetry(
	ctx context.Context,
	rule config.MetricRule,
	start, end time.Time,
) (*downsampling.BatchResult, error) {
	rawData, err := s.promClient.QueryRawDataForRule(ctx, rule, start, end)
	if err != nil {
		return nil, fmt.Errorf("failed to query raw data: %w", err)
	}

	batch := s.downsampler.ProcessQueryResult(rawData, rule, start, end)
	if batch.Error != nil {
		return nil, fmt.Errorf("downsampling failed: %w", batch.Error)
	}

	if len(batch.Points) == 0 {
		log.Printf("No downsampled points generated for rule '%s'", rule.Name)
		return batch, nil
	}

	if rule.ErrorAnalysis.Enabled && s.downsampler.GetErrorAnalyzer() != nil {
		for _, series := range rawData.Series {
			metricName := series.Labels["__name__"]
			errorMetrics := s.downsampler.EvaluateDownsampling(series.Samples, batch.Points)
			s.errorStats.Record(metricName, errorMetrics)

			if errorMetrics.MAPE > 0 {
				log.Printf("Error analysis for '%s': MAE=%.4f, RMSE=%.4f, MAPE=%.2f%%, Correlation=%.4f",
					metricName, errorMetrics.MAE, errorMetrics.RMSE, errorMetrics.MAPE, errorMetrics.Correlation)
			}

			if s.downsampler.GetErrorAnalyzer().IsErrorExceedsThreshold(errorMetrics) {
				log.Printf("WARNING: Error exceeds threshold for '%s': MAPE=%.2f%% > %.2f%%",
					metricName, errorMetrics.MAPE, rule.ErrorAnalysis.AlertThreshold*100)
			}
		}
	}

	if rule.StrategyRecommendation.Enabled && s.downsampler.GetRecommendationEngine() != nil {
		for _, series := range rawData.Series {
			if len(series.Samples) >= rule.StrategyRecommendation.MinSamples {
				rec := s.downsampler.RecommendStrategy(series)
				if rec != nil {
					metricName := series.Labels["__name__"]
					s.recommendationStats.Record(metricName, *rec)
					log.Printf("Strategy recommendation for '%s': levels=%v, saving=%.1f%%, error=%.1f%%, score=%.1f",
						metricName, rec.RecommendedLevels, rec.EstimatedSaving, rec.EstimatedError, rec.Score)
				}
			}
		}
	}

	if s.thanosWriter != nil {
		writeResult, err := s.thanosWriter.Write(ctx, batch.Points)
		if err != nil {
			return nil, fmt.Errorf("failed to write to thanos: %w", err)
		}
		if writeResult.FailedCount > 0 {
			log.Printf("Warning: %d points failed to write for rule '%s'", writeResult.FailedCount, rule.Name)
		}
		log.Printf("Wrote %d/%d points to Thanos for rule '%s' (took %v)",
			writeResult.SuccessCount, writeResult.TotalPoints, rule.Name, writeResult.Duration)
	}

	return batch, nil
}

func (s *Scheduler) PrintStatus() {
	stats := s.stats.Get()
	fmt.Println("\n=== Downsampler Status ===")
	for k, v := range stats {
		fmt.Printf("%s: %v\n", k, v)
	}

	errorStats := s.errorStats.Get()
	if len(errorStats) > 0 {
		fmt.Println("\n=== Error Analysis ===")
		for metric, data := range errorStats {
			if d, ok := data.(map[string]interface{}); ok {
				fmt.Printf("%s: MAE=%.4f, RMSE=%.4f, MAPE=%.2f%%, Correlation=%.4f\n",
					metric, d["mae"], d["rmse"], d["mape"], d["correlation"])
			}
		}
	}

	recStats := s.recommendationStats.Get()
	if recs, ok := recStats["recommendations"].(map[string]interface{}); ok && len(recs) > 0 {
		fmt.Println("\n=== Strategy Recommendations ===")
		for metric, data := range recs {
			if d, ok := data.(map[string]interface{}); ok {
				fmt.Printf("%s: levels=%v, saving=%.1f%%, error=%.1f%%, score=%.1f\n",
					metric, d["recommended_levels"], d["estimated_saving"],
					d["estimated_error"], d["score"])
			}
		}
	}

	fmt.Println("==========================\n")
}

func main() {
	configPath := flag.String("config", "configs/config.yaml", "Path to configuration file")
	once := flag.Bool("once", false, "Run downsampling once and exit")
	status := flag.Bool("status", false, "Print status and exit")
	flag.Parse()

	cfg, err := config.Load(*configPath)
	if err != nil {
		log.Fatalf("Failed to load configuration: %v", err)
	}
	log.Printf("Configuration loaded from %s", *configPath)

	scheduler, err := NewScheduler(cfg)
	if err != nil {
		log.Fatalf("Failed to create scheduler: %v", err)
	}

	if *status {
		scheduler.PrintStatus()
		return
	}

	if *once {
		log.Println("Running in one-shot mode")
		if err := scheduler.runOnce(); err != nil {
			log.Fatalf("One-shot run failed: %v", err)
		}
		log.Println("One-shot run completed successfully")
		return
	}

	scheduler.Start()

	sigCh := make(chan os.Signal, 1)
	signal.Notify(sigCh, syscall.SIGINT, syscall.SIGTERM)

	statsTicker := time.NewTicker(5 * time.Minute)
	defer statsTicker.Stop()

	for {
		select {
		case <-sigCh:
			log.Println("Received shutdown signal, stopping...")
			scheduler.Stop()
			return
		case <-statsTicker.C:
			scheduler.PrintStatus()
		}
	}
}
