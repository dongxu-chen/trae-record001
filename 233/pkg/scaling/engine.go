package scaling

import (
	"context"
	"fmt"
	"math"
	"sync"
	"time"

	"github.com/cloud-autoscaler/pkg/cloud"
	"github.com/cloud-autoscaler/pkg/config"
	"github.com/cloud-autoscaler/pkg/metrics"
	"github.com/cloud-autoscaler/pkg/prediction"
)

type ScalingDecision int

const (
	DecisionNoChange ScalingDecision = iota
	DecisionScaleUp
	DecisionScaleDown
)

type MetricsSample struct {
	CPU     float64
	Memory  float64
	Time    time.Time
}

type ScalingStatus string

const (
	StatusIdle    ScalingStatus = "idle"
	StatusRunning ScalingStatus = "running"
)

type SlidingWindow struct {
	samples []MetricsSample
	size    int
	mu      sync.RWMutex
}

func NewSlidingWindow(size int) *SlidingWindow {
	return &SlidingWindow{
		samples: make([]MetricsSample, 0, size),
		size:    size,
	}
}

func (w *SlidingWindow) Add(sample MetricsSample) {
	w.mu.Lock()
	defer w.mu.Unlock()

	w.samples = append(w.samples, sample)
	if len(w.samples) > w.size {
		w.samples = w.samples[1:]
	}
}

func (w *SlidingWindow) Average() (cpu float64, memory float64, ok bool) {
	w.mu.RLock()
	defer w.mu.RUnlock()

	if len(w.samples) == 0 {
		return 0, 0, false
	}

	var cpuSum, memorySum float64
	for _, s := range w.samples {
		cpuSum += s.CPU
		memorySum += s.Memory
	}

	n := float64(len(w.samples))
	return cpuSum / n, memorySum / n, true
}

func (w *SlidingWindow) IsReady() bool {
	w.mu.RLock()
	defer w.mu.RUnlock()
	return len(w.samples) >= w.size
}

func (w *SlidingWindow) Samples() []MetricsSample {
	w.mu.RLock()
	defer w.mu.RUnlock()
	samples := make([]MetricsSample, len(w.samples))
	copy(samples, w.samples)
	return samples
}

type ScalingLock struct {
	status    ScalingStatus
	startTime time.Time
	mu        sync.Mutex
}

func (l *ScalingLock) TryLock() bool {
	l.mu.Lock()
	defer l.mu.Unlock()

	if l.status == StatusRunning {
		return false
	}
	l.status = StatusRunning
	l.startTime = time.Now()
	return true
}

func (l *ScalingLock) Unlock() {
	l.mu.Lock()
	defer l.mu.Unlock()
	l.status = StatusIdle
}

func (l *ScalingLock) GetStatus() ScalingStatus {
	l.mu.Lock()
	defer l.mu.Unlock()
	return l.status
}

type ScalingEngine struct {
	cfg             *config.ScalingConfig
	predictionCfg   *config.PredictionConfig
	instanceGroup   string
	provider        cloud.Provider
	metricsClient   *metrics.PrometheusClient
	predictor       *prediction.TimeSeriesPredictor
	lastScaleTime   time.Time
	slidingWindow   *SlidingWindow
	scalingLock     *ScalingLock
	mu              sync.RWMutex
}

func NewScalingEngine(
	cfg *config.ScalingConfig,
	predictionCfg *config.PredictionConfig,
	instanceGroup string,
	provider cloud.Provider,
	metricsClient *metrics.PrometheusClient,
) *ScalingEngine {
	engine := &ScalingEngine{
		cfg:           cfg,
		predictionCfg: predictionCfg,
		instanceGroup: instanceGroup,
		provider:      provider,
		metricsClient: metricsClient,
		lastScaleTime: time.Time{},
		slidingWindow: NewSlidingWindow(cfg.SlidingWindowSize),
		scalingLock:   &ScalingLock{},
	}

	if predictionCfg != nil && predictionCfg.Enabled {
		engine.predictor = prediction.NewTimeSeriesPredictor(
			predictionCfg.HistorySize,
			cfg.SlidingWindowSize,
		)
	}

	return engine
}

func (e *ScalingEngine) CollectMetrics(ctx context.Context) error {
	cpu, memory, err := e.metricsClient.GetMetrics(ctx)
	if err != nil {
		return fmt.Errorf("failed to get metrics: %w", err)
	}

	e.slidingWindow.Add(MetricsSample{
		CPU:    cpu,
		Memory: memory,
		Time:   time.Now(),
	})

	if e.predictor != nil {
		e.predictor.AddDataPoint(cpu, memory)
	}

	return nil
}

func (e *ScalingEngine) Evaluate(ctx context.Context) (ScalingDecision, int, error) {
	e.mu.RLock()
	defer e.mu.RUnlock()

	if !e.isCooldownComplete() {
		return DecisionNoChange, 0, nil
	}

	if e.scalingLock.GetStatus() == StatusRunning {
		return DecisionNoChange, 0, nil
	}

	avgCPU, avgMemory, ok := e.slidingWindow.Average()
	if !ok {
		return DecisionNoChange, 0, fmt.Errorf("not enough metrics data in sliding window")
	}

	currentCount, err := e.provider.GetInstanceCount(ctx)
	if err != nil {
		return DecisionNoChange, 0, fmt.Errorf("failed to get instance count: %w", err)
	}

	if e.cfg.Mode == "predictive" && e.predictor != nil && e.predictor.IsReady() {
		predictions := e.predictor.Predict(e.predictionCfg.PredictionSteps)
		if len(predictions) > 0 {
			maxPredictedCPU := avgCPU
			maxPredictedMemory := avgMemory
			minConfidence := e.predictionCfg.MinConfidence
			if minConfidence == 0 {
				minConfidence = 0.7
			}

			for _, pred := range predictions {
				if pred.Confidence >= minConfidence {
					if pred.PredictedCPU > maxPredictedCPU {
						maxPredictedCPU = pred.PredictedCPU
					}
					if pred.PredictedMemory > maxPredictedMemory {
						maxPredictedMemory = pred.PredictedMemory
					}
				}
			}

			if maxPredictedCPU > avgCPU || maxPredictedMemory > avgMemory {
				decision, count := e.calculateScalingDecision(
					currentCount,
					maxPredictedCPU,
					maxPredictedMemory,
				)
				if decision == DecisionScaleUp {
					return decision, count, nil
				}
			}
		}
	}

	decision, count := e.calculateScalingDecision(
		currentCount,
		avgCPU,
		avgMemory,
	)

	return decision, count, nil
}

func (e *ScalingEngine) isCooldownComplete() bool {
	if e.lastScaleTime.IsZero() {
		return true
	}
	return time.Since(e.lastScaleTime) >= e.cfg.CooldownPeriod
}

func (e *ScalingEngine) calculateScalingDecision(
	currentCount int,
	cpuUtilization float64,
	memoryUtilization float64,
) (ScalingDecision, int) {
	targetCPU := e.cfg.TargetCPUUtilization
	targetMemory := e.cfg.TargetMemoryUtilization

	cpuRatio := cpuUtilization / targetCPU
	memoryRatio := memoryUtilization / targetMemory
	maxRatio := math.Max(cpuRatio, memoryRatio)

	scaleUpThreshold := 1.0 + (e.cfg.ScaleUpThreshold / 100.0)
	scaleDownThreshold := 1.0 - (e.cfg.ScaleDownThreshold / 100.0)

	if maxRatio > scaleUpThreshold {
		desiredCount := int(math.Ceil(float64(currentCount) * maxRatio))
		desiredCount = e.clampCount(desiredCount)
		if desiredCount > currentCount {
			return DecisionScaleUp, desiredCount - currentCount
		}
	}

	if maxRatio < scaleDownThreshold {
		desiredCount := int(math.Floor(float64(currentCount) * maxRatio))
		desiredCount = e.clampCount(desiredCount)
		if desiredCount < currentCount {
			return DecisionScaleDown, currentCount - desiredCount
		}
	}

	return DecisionNoChange, 0
}

func (e *ScalingEngine) clampCount(count int) int {
	if count < e.cfg.MinInstances {
		return e.cfg.MinInstances
	}
	if count > e.cfg.MaxInstances {
		return e.cfg.MaxInstances
	}
	return count
}

func (e *ScalingEngine) Execute(ctx context.Context, decision ScalingDecision, count int) error {
	if !e.scalingLock.TryLock() {
		return fmt.Errorf("scaling operation already in progress for instance group %s", e.instanceGroup)
	}
	defer e.scalingLock.Unlock()

	e.mu.Lock()
	defer e.mu.Unlock()

	if count <= 0 {
		return nil
	}

	var err error
	switch decision {
	case DecisionScaleUp:
		err = e.provider.ScaleUp(ctx, count)
	case DecisionScaleDown:
		err = e.provider.ScaleDown(ctx, count)
	default:
		return nil
	}

	if err != nil {
		return fmt.Errorf("scaling operation failed: %w", err)
	}

	e.lastScaleTime = time.Now()
	return nil
}

func (e *ScalingEngine) GetStatus() map[string]interface{} {
	e.mu.RLock()
	defer e.mu.RUnlock()

	avgCPU, avgMemory, avgOk := e.slidingWindow.Average()

	status := map[string]interface{}{
		"instance_group":         e.instanceGroup,
		"last_scale_time":        e.lastScaleTime,
		"cooldown_complete":      e.isCooldownComplete(),
		"cooldown_remaining":     math.Max(0, e.cfg.CooldownPeriod.Seconds()-time.Since(e.lastScaleTime).Seconds()),
		"scaling_status":         e.scalingLock.GetStatus(),
		"window_ready":           e.slidingWindow.IsReady(),
		"window_size":            e.slidingWindow.size,
		"window_samples":         len(e.slidingWindow.Samples()),
		"avg_cpu_utilization":    avgCPU,
		"avg_memory_utilization": avgMemory,
		"avg_data_ready":         avgOk,
		"scaling_mode":           e.cfg.Mode,
	}

	if e.predictor != nil {
		status["prediction_ready"] = e.predictor.IsReady()
		if e.predictor.IsReady() {
			predictions := e.predictor.Predict(3)
			if len(predictions) > 0 {
				status["next_predicted_cpu"] = predictions[0].PredictedCPU
				status["next_predicted_memory"] = predictions[0].PredictedMemory
				status["prediction_confidence"] = predictions[0].Confidence
			}
		}
	}

	return status
}
