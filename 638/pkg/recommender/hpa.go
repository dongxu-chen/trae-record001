package recommender

import (
	"fmt"
	"math"
	"sync"
	"time"

	"github.com/k8s-autoscaler/pkg/metrics"
)

type MetricType string

const (
	MetricCPU     MetricType = "CPU"
	MetricMemory  MetricType = "Memory"
	MetricQPS     MetricType = "QPS"
	MetricLatency MetricType = "Latency"
)

type HPAMetric struct {
	Type               MetricType `json:"type"`
	TargetUtilization  float64    `json:"targetUtilization"`
	CurrentUtilization float64    `json:"currentUtilization"`
	Weight             float64    `json:"weight"`
}

type HPARecommendation struct {
	Name           string      `json:"name"`
	Namespace      string      `json:"namespace"`
	MinReplicas    int32       `json:"minReplicas"`
	MaxReplicas    int32       `json:"maxReplicas"`
	TargetReplicas int32       `json:"targetReplicas"`
	Metrics        []HPAMetric `json:"metrics"`
	Score          float64     `json:"score"`
	Reason         string      `json:"reason"`
	CostImpact     float64     `json:"costImpact"`
	CompositeLoad  float64     `json:"compositeLoad"`
	FusionMetrics  []HPAMetric `json:"fusionMetrics"`
	UsedComposite  bool        `json:"usedComposite"`
}

type RecommenderConfig struct {
	CPUTarget              float64
	MemoryTarget           float64
	QPSTarget              float64
	LatencyTarget          float64
	ScaleUpCooldown        time.Duration
	ScaleDownCooldown      time.Duration
	MaxScaleUpRatio        float64
	MaxScaleDownRatio      float64
	CompositeTarget        float64
	FusionWeights          map[MetricType]float64
	EnableCompositeThreshold bool
}

type HPARecommender struct {
	config        RecommenderConfig
	lastScaleUp   map[string]time.Time
	lastScaleDown map[string]time.Time
	mu            sync.Mutex
}

func NewHPARecommender(config RecommenderConfig) *HPARecommender {
	if config.CompositeTarget == 0 {
		config.CompositeTarget = 0.75
	}
	if config.FusionWeights == nil {
		config.FusionWeights = map[MetricType]float64{
			MetricCPU:    0.4,
			MetricMemory: 0.3,
			MetricQPS:    0.3,
		}
	}
	return &HPARecommender{
		config:        config,
		lastScaleUp:   make(map[string]time.Time),
		lastScaleDown: make(map[string]time.Time),
	}
}

func (r *HPARecommender) Config() *RecommenderConfig {
	return &r.config
}

func (r *HPARecommender) CalculateCompositeLoad(m metrics.WorkloadMetrics) float64 {
	replicas := m.Replicas
	if replicas <= 0 {
		replicas = 1
	}
	var composite float64
	if r.config.CPUTarget > 0 {
		avgCPU := m.AggCPU / float64(replicas)
		ratio := avgCPU / r.config.CPUTarget
		weight := r.config.FusionWeights[MetricCPU]
		composite += ratio * weight
	}
	if r.config.MemoryTarget > 0 {
		avgMemory := m.AggMemory / float64(replicas)
		ratio := avgMemory / r.config.MemoryTarget
		weight := r.config.FusionWeights[MetricMemory]
		composite += ratio * weight
	}
	if r.config.QPSTarget > 0 {
		avgQPS := m.AggQPS / float64(replicas)
		ratio := avgQPS / r.config.QPSTarget
		weight := r.config.FusionWeights[MetricQPS]
		composite += ratio * weight
	}
	return composite
}

func (r *HPARecommender) buildHPAMetrics(m metrics.WorkloadMetrics) ([]HPAMetric, []HPAMetric) {
	replicas := m.Replicas
	if replicas <= 0 {
		replicas = 1
	}
	avgCPU := m.AggCPU / float64(replicas)
	avgMemory := m.AggMemory / float64(replicas)
	avgQPS := m.AggQPS / float64(replicas)

	var result []HPAMetric
	var fusionMetrics []HPAMetric
	if r.config.CPUTarget > 0 {
		result = append(result, HPAMetric{
			Type:               MetricCPU,
			TargetUtilization:  r.config.CPUTarget,
			CurrentUtilization: avgCPU,
			Weight:             1.0,
		})
		fusionMetrics = append(fusionMetrics, HPAMetric{
			Type:               MetricCPU,
			TargetUtilization:  r.config.CPUTarget,
			CurrentUtilization: avgCPU / r.config.CPUTarget,
			Weight:             r.config.FusionWeights[MetricCPU],
		})
	}
	if r.config.MemoryTarget > 0 {
		result = append(result, HPAMetric{
			Type:               MetricMemory,
			TargetUtilization:  r.config.MemoryTarget,
			CurrentUtilization: avgMemory,
			Weight:             0.8,
		})
		fusionMetrics = append(fusionMetrics, HPAMetric{
			Type:               MetricMemory,
			TargetUtilization:  r.config.MemoryTarget,
			CurrentUtilization: avgMemory / r.config.MemoryTarget,
			Weight:             r.config.FusionWeights[MetricMemory],
		})
	}
	if r.config.QPSTarget > 0 {
		result = append(result, HPAMetric{
			Type:               MetricQPS,
			TargetUtilization:  r.config.QPSTarget,
			CurrentUtilization: avgQPS,
			Weight:             0.9,
		})
		fusionMetrics = append(fusionMetrics, HPAMetric{
			Type:               MetricQPS,
			TargetUtilization:  r.config.QPSTarget,
			CurrentUtilization: avgQPS / r.config.QPSTarget,
			Weight:             r.config.FusionWeights[MetricQPS],
		})
	}
	if r.config.LatencyTarget > 0 {
		result = append(result, HPAMetric{
			Type:               MetricLatency,
			TargetUtilization:  r.config.LatencyTarget,
			CurrentUtilization: m.AggLatency,
			Weight:             0.7,
		})
	}
	return result, fusionMetrics
}

func (r *HPARecommender) Recommend(namespace, deployment string, currentReplicas int32, m metrics.WorkloadMetrics) HPARecommendation {
	key := namespace + "/" + deployment
	hpaMetrics, fusionMetrics := r.buildHPAMetrics(m)
	desired, usedComposite := r.CalculateDesiredReplicas(currentReplicas, m)
	compositeLoad := r.CalculateCompositeLoad(m)

	r.mu.Lock()
	lastUp, hadUp := r.lastScaleUp[key]
	lastDown, hadDown := r.lastScaleDown[key]
	r.mu.Unlock()

	now := time.Now()
	reason := ""
	scaled := false

	if desired > currentReplicas {
		if hadUp && now.Sub(lastUp) < r.config.ScaleUpCooldown {
			desired = currentReplicas
			reason = "scale-up cooldown active"
		} else {
			maxAllowed := int32(math.Ceil(float64(currentReplicas) * r.config.MaxScaleUpRatio))
			if desired > maxAllowed {
				desired = maxAllowed
				reason = fmt.Sprintf("scale-up capped by max ratio %.1f", r.config.MaxScaleUpRatio)
			}
			scaled = true
		}
	} else if desired < currentReplicas {
		if hadDown && now.Sub(lastDown) < r.config.ScaleDownCooldown {
			desired = currentReplicas
			reason = "scale-down cooldown active"
		} else {
			minAllowed := int32(math.Floor(float64(currentReplicas) / r.config.MaxScaleDownRatio))
			if minAllowed < 1 {
				minAllowed = 1
			}
			if desired < minAllowed {
				desired = minAllowed
				reason = fmt.Sprintf("scale-down capped by max ratio %.1f", r.config.MaxScaleDownRatio)
			}
			scaled = true
		}
	}

	if scaled {
		r.mu.Lock()
		if desired > currentReplicas {
			r.lastScaleUp[key] = now
		} else if desired < currentReplicas {
			r.lastScaleDown[key] = now
		}
		r.mu.Unlock()
	}

	minReplicas := int32(1)
	if desired > 3 {
		minReplicas = desired / 3
	}
	maxReplicas := desired * 3
	if maxReplicas < desired+10 {
		maxReplicas = desired + 10
	}
	if maxReplicas > 1000 {
		maxReplicas = 1000
	}

	if desired < minReplicas {
		desired = minReplicas
	}
	if desired > maxReplicas {
		desired = maxReplicas
	}

	costImpact := 0.0
	if currentReplicas > 0 {
		costImpact = float64(desired-currentReplicas) / float64(currentReplicas) * 100.0
	}

	if reason == "" {
		if usedComposite {
			if desired > currentReplicas {
				reason = fmt.Sprintf("scaling up from %d to %d replicas based on composite threshold (composite load: %.2f, target: %.2f)", currentReplicas, desired, compositeLoad, r.config.CompositeTarget)
			} else if desired < currentReplicas {
				reason = fmt.Sprintf("scaling down from %d to %d replicas based on composite threshold (composite load: %.2f, target: %.2f)", currentReplicas, desired, compositeLoad, r.config.CompositeTarget)
			} else {
				reason = fmt.Sprintf("current replica count is optimal (composite load: %.2f, target: %.2f)", compositeLoad, r.config.CompositeTarget)
			}
		} else {
			if desired > currentReplicas {
				reason = fmt.Sprintf("scaling up from %d to %d replicas based on metric analysis", currentReplicas, desired)
			} else if desired < currentReplicas {
				reason = fmt.Sprintf("scaling down from %d to %d replicas based on metric analysis", currentReplicas, desired)
			} else {
				reason = "current replica count is optimal"
			}
		}
	}

	rec := HPARecommendation{
		Name:           deployment,
		Namespace:      namespace,
		MinReplicas:    minReplicas,
		MaxReplicas:    maxReplicas,
		TargetReplicas: desired,
		Metrics:        hpaMetrics,
		CostImpact:     costImpact,
		Reason:         reason,
		CompositeLoad:  compositeLoad,
		FusionMetrics:  fusionMetrics,
		UsedComposite:  usedComposite,
	}
	rec.Score = r.ScoreRecommendation(rec, m)

	return rec
}

func (r *HPARecommender) CalculateDesiredReplicas(currentReplicas int32, m metrics.WorkloadMetrics) (int32, bool) {
	replicas := m.Replicas
	if replicas <= 0 {
		replicas = 1
	}

	var maxWeightedRatio float64

	if r.config.CPUTarget > 0 {
		avgCPU := m.AggCPU / float64(replicas)
		ratio := 1.0 * (avgCPU / r.config.CPUTarget)
		if ratio > maxWeightedRatio {
			maxWeightedRatio = ratio
		}
	}
	if r.config.MemoryTarget > 0 {
		avgMemory := m.AggMemory / float64(replicas)
		ratio := 0.8 * (avgMemory / r.config.MemoryTarget)
		if ratio > maxWeightedRatio {
			maxWeightedRatio = ratio
		}
	}
	if r.config.QPSTarget > 0 {
		avgQPS := m.AggQPS / float64(replicas)
		ratio := 0.9 * (avgQPS / r.config.QPSTarget)
		if ratio > maxWeightedRatio {
			maxWeightedRatio = ratio
		}
	}
	if r.config.LatencyTarget > 0 {
		ratio := 0.7 * (m.AggLatency / r.config.LatencyTarget)
		if ratio > maxWeightedRatio {
			maxWeightedRatio = ratio
		}
	}

	usedComposite := false
	if r.config.EnableCompositeThreshold {
		compositeLoad := r.CalculateCompositeLoad(m)
		compositeRatio := compositeLoad / r.config.CompositeTarget
		if compositeRatio > maxWeightedRatio {
			maxWeightedRatio = compositeRatio
			usedComposite = true
		}
	}

	if maxWeightedRatio == 0 {
		return currentReplicas, usedComposite
	}

	desired := int32(math.Ceil(float64(currentReplicas) * maxWeightedRatio))
	if desired < 1 {
		desired = 1
	}

	return desired, usedComposite
}

func (r *HPARecommender) ScoreRecommendation(rec HPARecommendation, m metrics.WorkloadMetrics) float64 {
	resourceEfficiency := 0.0
	metricCount := 0
	for _, metric := range rec.Metrics {
		if metric.TargetUtilization > 0 {
			ratio := metric.CurrentUtilization / metric.TargetUtilization
			deviation := math.Abs(ratio - 1.0)
			score := math.Max(0, 100*(1-deviation))
			resourceEfficiency += score
			metricCount++
		}
	}
	if metricCount > 0 {
		resourceEfficiency /= float64(metricCount)
	}

	performanceHeadroom := 0.0
	for _, metric := range rec.Metrics {
		if metric.TargetUtilization > 0 {
			headroom := (metric.TargetUtilization - metric.CurrentUtilization) / metric.TargetUtilization
			if headroom < 0 {
				headroom = 0
			}
			idealHeadroom := 0.2
			var score float64
			if headroom <= idealHeadroom {
				score = (headroom / idealHeadroom) * 100
			} else {
				score = math.Max(0, 100-((headroom-idealHeadroom)/idealHeadroom)*50)
			}
			performanceHeadroom += score
		}
	}
	if metricCount > 0 {
		performanceHeadroom /= float64(metricCount)
	}

	costEfficiency := 0.0
	if rec.MaxReplicas > 0 {
		costEfficiency = (1.0 - float64(rec.TargetReplicas)/float64(rec.MaxReplicas)) * 100
	}

	stability := 100.0
	if rec.CostImpact != 0 {
		stability = math.Max(0, 100-math.Abs(rec.CostImpact)*2)
	}

	score := resourceEfficiency*0.30 + performanceHeadroom*0.30 + costEfficiency*0.20 + stability*0.20
	if score > 100 {
		score = 100
	}
	if score < 0 {
		score = 0
	}

	return math.Round(score*100) / 100
}

func (r *HPARecommender) GenerateHPASpec(rec HPARecommendation) map[string]interface{} {
	var metricSpecs []map[string]interface{}
	for _, metric := range rec.Metrics {
		switch metric.Type {
		case MetricCPU:
			metricSpecs = append(metricSpecs, map[string]interface{}{
				"type": "Resource",
				"resource": map[string]interface{}{
					"name": "cpu",
					"target": map[string]interface{}{
						"type":               "Utilization",
						"averageUtilization": int32(metric.TargetUtilization),
					},
				},
			})
		case MetricMemory:
			metricSpecs = append(metricSpecs, map[string]interface{}{
				"type": "Resource",
				"resource": map[string]interface{}{
					"name": "memory",
					"target": map[string]interface{}{
						"type":               "Utilization",
						"averageUtilization": int32(metric.TargetUtilization),
					},
				},
			})
		case MetricQPS:
			metricSpecs = append(metricSpecs, map[string]interface{}{
				"type": "Pods",
				"pods": map[string]interface{}{
					"metric": map[string]interface{}{
						"name": "http_requests_per_second",
					},
					"target": map[string]interface{}{
						"type":  "AverageValue",
						"value": fmt.Sprintf("%.0f", metric.TargetUtilization),
					},
				},
			})
		case MetricLatency:
			metricSpecs = append(metricSpecs, map[string]interface{}{
				"type": "External",
				"external": map[string]interface{}{
					"metric": map[string]interface{}{
						"name": "http_request_duration_seconds",
					},
					"target": map[string]interface{}{
						"type":  "AverageValue",
						"value": fmt.Sprintf("%.0fm", metric.TargetUtilization),
					},
				},
			})
		}
	}

	return map[string]interface{}{
		"apiVersion": "autoscaling/v2",
		"kind":       "HorizontalPodAutoscaler",
		"metadata": map[string]interface{}{
			"name":      rec.Name,
			"namespace": rec.Namespace,
		},
		"spec": map[string]interface{}{
			"scaleTargetRef": map[string]interface{}{
				"apiVersion": "apps/v1",
				"kind":       "Deployment",
				"name":       rec.Name,
			},
			"minReplicas": rec.MinReplicas,
			"maxReplicas": rec.MaxReplicas,
			"metrics":     metricSpecs,
		},
	}
}
