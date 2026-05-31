package scaler

import (
	"math"
	"sync"
	"time"

	"github.com/k8s-autoscaler/pkg/metrics"
	"github.com/k8s-autoscaler/pkg/predictor"
)

type ScaleDecision struct {
	Deployment       string                      `json:"deployment"`
	Namespace        string                      `json:"namespace"`
	CurrentReplicas  int32                       `json:"currentReplicas"`
	DesiredReplicas  int32                       `json:"desiredReplicas"`
	Reason           string                      `json:"reason"`
	Confidence       float64                     `json:"confidence"`
	PredictedCPU     float64                     `json:"predictedCPU"`
	PredictedQPS     float64                     `json:"predictedQPS"`
	PredictedLatency float64                     `json:"predictedLatency"`
	ScaleDirection   string                      `json:"scaleDirection"`
	Timestamp        time.Time                   `json:"timestamp"`
	DetectedPatterns []predictor.PeriodicPattern `json:"detectedPatterns,omitempty"`
	FourierComponents []predictor.FourierComponent `json:"fourierComponents,omitempty"`
}

type PredictiveScalerConfig struct {
	LookAheadDuration   time.Duration
	ScaleUpThreshold    float64
	ScaleDownThreshold  float64
	MinReplicas         int32
	MaxReplicas         int32
	PredictionWeights   []float64
	StabilizationWindow time.Duration
}

type PredictiveScaler struct {
	config        PredictiveScalerConfig
	engine        *predictor.PredictionEngine
	lastScaleTime map[string]time.Time
	mu            sync.Mutex
}

func NewPredictiveScaler(config PredictiveScalerConfig, engine *predictor.PredictionEngine) *PredictiveScaler {
	return &PredictiveScaler{
		config:        config,
		engine:        engine,
		lastScaleTime: make(map[string]time.Time),
	}
}

func (s *PredictiveScaler) Config() *PredictiveScalerConfig {
	return &s.config
}

func (s *PredictiveScaler) Evaluate(namespace, deployment string, currentReplicas int32, historicalMetrics []predictor.TimeSeriesPoint, currentMetrics metrics.WorkloadMetrics) ScaleDecision {
	_, ensemble, patterns, fourier := s.predictFutureValues(historicalMetrics)

	now := time.Now()
	cutoff := now.Add(s.config.LookAheadDuration)

	var peakPredicted float64
	for _, pv := range ensemble.PredictedValues {
		if pv.Timestamp.After(now) && !pv.Timestamp.After(cutoff) {
			if pv.Value > peakPredicted {
				peakPredicted = pv.Value
			}
		}
	}

	desired := s.calculateDesiredFromPrediction(ensemble, currentReplicas, currentMetrics)

	if desired < s.config.MinReplicas {
		desired = s.config.MinReplicas
	}
	if desired > s.config.MaxReplicas {
		desired = s.config.MaxReplicas
	}

	direction := "none"
	reason := ""

	if desired > currentReplicas {
		direction = "up"
		reason = "predicted load increase requires scale up"
	} else if desired < currentReplicas {
		direction = "down"
		reason = "predicted load decrease allows scale down"
	} else {
		reason = "current replica count meets predicted demand"
	}

	if !s.shouldScale(deployment, currentReplicas, desired) {
		desired = currentReplicas
		direction = "none"
		reason = "stabilization window active, scaling deferred"
	}

	predictedCPU := currentMetrics.AggCPU
	predictedQPS := currentMetrics.AggQPS
	predictedLatency := currentMetrics.AggLatency

	if len(historicalMetrics) > 0 {
		currentMetricValue := historicalMetrics[len(historicalMetrics)-1].Value
		if currentMetricValue > 0 {
			ratio := peakPredicted / currentMetricValue
			predictedCPU = currentMetrics.AggCPU * ratio
			predictedQPS = currentMetrics.AggQPS * ratio
		}
	}

	return ScaleDecision{
		Deployment:       deployment,
		Namespace:        namespace,
		CurrentReplicas:  currentReplicas,
		DesiredReplicas:  desired,
		Reason:           reason,
		Confidence:       ensemble.Confidence,
		PredictedCPU:     predictedCPU,
		PredictedQPS:     predictedQPS,
		PredictedLatency: predictedLatency,
		ScaleDirection:   direction,
		Timestamp:        now,
		DetectedPatterns: patterns,
		FourierComponents: fourier,
	}
}

func (s *PredictiveScaler) predictFutureValues(data []predictor.TimeSeriesPoint) ([]predictor.PredictionResult, predictor.PredictionResult, []predictor.PeriodicPattern, []predictor.FourierComponent) {
	if len(data) < 2 {
		empty := predictor.PredictionResult{Algorithm: "WeightedEnsemble"}
		return nil, empty, nil, nil
	}

	interval := data[len(data)-1].Timestamp.Sub(data[0].Timestamp) / time.Duration(len(data)-1)
	if interval <= 0 {
		interval = time.Minute
	}

	steps := int(s.config.LookAheadDuration / interval)
	if steps < 1 {
		steps = 1
	}

	results := s.engine.Predict(data, steps)
	ensemble := s.engine.WeightedEnsemble(results, s.config.PredictionWeights)

	patterns := s.engine.DetectPeriodicity(data)
	fourier := s.engine.FastFourierTransform(data)

	return results, ensemble, patterns, fourier
}

func (s *PredictiveScaler) calculateDesiredFromPrediction(ensemble predictor.PredictionResult, currentReplicas int32, currentMetrics metrics.WorkloadMetrics) int32 {
	if currentReplicas <= 0 || len(ensemble.PredictedValues) == 0 {
		return currentReplicas
	}

	now := time.Now()
	cutoff := now.Add(s.config.LookAheadDuration)

	var peakPredicted float64
	for _, pv := range ensemble.PredictedValues {
		if pv.Timestamp.After(now) && !pv.Timestamp.After(cutoff) {
			if pv.Value > peakPredicted {
				peakPredicted = pv.Value
			}
		}
	}

	capacityPerReplica := currentMetrics.AggCPU / float64(currentReplicas)
	if capacityPerReplica <= 0 {
		return currentReplicas
	}

	utilization := peakPredicted / (capacityPerReplica * float64(currentReplicas))

	if utilization > s.config.ScaleUpThreshold {
		desired := int32(math.Ceil(peakPredicted / capacityPerReplica))
		if desired < 1 {
			desired = 1
		}
		return desired
	} else if utilization < s.config.ScaleDownThreshold {
		desired := int32(math.Ceil(peakPredicted / capacityPerReplica))
		if desired < 1 {
			desired = 1
		}
		return desired
	}

	return currentReplicas
}

func (s *PredictiveScaler) shouldScale(deployment string, current, desired int32) bool {
	if current == desired {
		return true
	}

	s.mu.Lock()
	lastTime, exists := s.lastScaleTime[deployment]
	s.mu.Unlock()

	if !exists {
		s.mu.Lock()
		s.lastScaleTime[deployment] = time.Now()
		s.mu.Unlock()
		return true
	}

	if time.Since(lastTime) < s.config.StabilizationWindow {
		return false
	}

	s.mu.Lock()
	s.lastScaleTime[deployment] = time.Now()
	s.mu.Unlock()
	return true
}
