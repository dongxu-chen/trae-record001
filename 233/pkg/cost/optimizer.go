package cost

import (
	"math"
	"sync"
	"time"

	"github.com/cloud-autoscaler/pkg/cloud"
)

type InstancePricing struct {
	Provider      string
	InstanceType  string
	HourlyCost    float64
	MonthlyCost   float64
}

type InstanceMetricsHistory struct {
	InstanceID    string
	CPUHistory    []float64
	MemoryHistory []float64
	StartTime     time.Time
	LastUpdate    time.Time
}

type CostSavingSuggestion struct {
	Type            string  `json:"type"`
	InstanceID      string  `json:"instance_id"`
	InstanceType    string  `json:"instance_type"`
	CurrentCost     float64 `json:"current_cost"`
	SuggestedType   string  `json:"suggested_type,omitempty"`
	SuggestedCost   float64 `json:"suggested_cost,omitempty"`
	MonthlySaving   float64 `json:"monthly_saving"`
	AvgCPU          float64 `json:"avg_cpu"`
	AvgMemory       float64 `json:"avg_memory"`
	MaxCPU          float64 `json:"max_cpu"`
	MaxMemory       float64 `json:"max_memory"`
	Reason          string  `json:"reason"`
	Confidence      float64 `json:"confidence"`
}

type CostOptimizer struct {
	provider         cloud.Provider
	pricing          map[string]InstancePricing
	instanceMetrics  map[string]*InstanceMetricsHistory
	maxHistoryPoints int
	idleThreshold    float64
	underutilThreshold float64
	mu               sync.RWMutex
}

var defaultPricing = map[string]InstancePricing{
	"t2.micro":      {Provider: "aws", InstanceType: "t2.micro", HourlyCost: 0.0116, MonthlyCost: 8.5},
	"t2.small":      {Provider: "aws", InstanceType: "t2.small", HourlyCost: 0.023, MonthlyCost: 17.0},
	"t2.medium":     {Provider: "aws", InstanceType: "t2.medium", HourlyCost: 0.0464, MonthlyCost: 34.0},
	"t2.large":      {Provider: "aws", InstanceType: "t2.large", HourlyCost: 0.0928, MonthlyCost: 68.0},
	"ecs.g6.large":  {Provider: "aliyun", InstanceType: "ecs.g6.large", HourlyCost: 0.05, MonthlyCost: 36.0},
	"S5.MEDIUM4":    {Provider: "tencent", InstanceType: "S5.MEDIUM4", HourlyCost: 0.045, MonthlyCost: 32.4},
}

func NewCostOptimizer(provider cloud.Provider, maxHistoryPoints int) *CostOptimizer {
	return &CostOptimizer{
		provider:         provider,
		pricing:          defaultPricing,
		instanceMetrics:  make(map[string]*InstanceMetricsHistory),
		maxHistoryPoints: maxHistoryPoints,
		idleThreshold:    10.0,
		underutilThreshold: 30.0,
	}
}

func (c *CostOptimizer) UpdateInstanceMetrics(instanceID string, cpu, memory float64) {
	c.mu.Lock()
	defer c.mu.Unlock()

	metrics, exists := c.instanceMetrics[instanceID]
	if !exists {
		metrics = &InstanceMetricsHistory{
			InstanceID:    instanceID,
			CPUHistory:    make([]float64, 0, c.maxHistoryPoints),
			MemoryHistory: make([]float64, 0, c.maxHistoryPoints),
			StartTime:     time.Now(),
		}
		c.instanceMetrics[instanceID] = metrics
	}

	metrics.CPUHistory = append(metrics.CPUHistory, cpu)
	metrics.MemoryHistory = append(metrics.MemoryHistory, memory)
	metrics.LastUpdate = time.Now()

	if len(metrics.CPUHistory) > c.maxHistoryPoints {
		metrics.CPUHistory = metrics.CPUHistory[1:]
		metrics.MemoryHistory = metrics.MemoryHistory[1:]
	}
}

func (c *CostOptimizer) GetInstanceCost(instanceType string) (InstancePricing, bool) {
	c.mu.RLock()
	defer c.mu.RUnlock()
	pricing, ok := c.pricing[instanceType]
	return pricing, ok
}

func (c *CostOptimizer) CalculateHourlyCost(instanceType string, count int) float64 {
	if pricing, ok := c.GetInstanceCost(instanceType); ok {
		return pricing.HourlyCost * float64(count)
	}
	return 0
}

func (c *CostOptimizer) CalculateMonthlyCost(instanceType string, count int) float64 {
	if pricing, ok := c.GetInstanceCost(instanceType); ok {
		return pricing.MonthlyCost * float64(count)
	}
	return 0
}

func (c *CostOptimizer) GetSuggestions() []CostSavingSuggestion {
	c.mu.RLock()
	defer c.mu.RUnlock()

	var suggestions []CostSavingSuggestion

	for instanceID, metrics := range c.instanceMetrics {
		if len(metrics.CPUHistory) < c.maxHistoryPoints/2 {
			continue
		}

		avgCPU, maxCPU := calculateStats(metrics.CPUHistory)
		avgMemory, maxMemory := calculateStats(metrics.MemoryHistory)

		runtime := time.Since(metrics.StartTime)
		minRuntime := 24 * time.Hour
		confidence := math.Min(1.0, runtime.Hours()/24.0)

		if maxCPU < c.idleThreshold && maxMemory < c.idleThreshold && runtime > minRuntime {
			pricing, _ := c.GetInstanceCost("t2.medium")
			suggestions = append(suggestions, CostSavingSuggestion{
				Type:          "terminate",
				InstanceID:    instanceID,
				CurrentCost:   pricing.MonthlyCost,
				MonthlySaving: pricing.MonthlyCost,
				AvgCPU:        avgCPU,
				AvgMemory:     avgMemory,
				MaxCPU:        maxCPU,
				MaxMemory:     maxMemory,
				Reason:        "Instance appears to be idle with consistently low utilization",
				Confidence:    confidence,
			})
			continue
		}

		if avgCPU < c.underutilThreshold && avgMemory < c.underutilThreshold && runtime > minRuntime {
			pricing, _ := c.GetInstanceCost("t2.medium")
			smallerPricing, _ := c.GetInstanceCost("t2.small")
			suggestions = append(suggestions, CostSavingSuggestion{
				Type:          "downsize",
				InstanceID:    instanceID,
				InstanceType:  "t2.medium",
				CurrentCost:   pricing.MonthlyCost,
				SuggestedType: "t2.small",
				SuggestedCost: smallerPricing.MonthlyCost,
				MonthlySaving: pricing.MonthlyCost - smallerPricing.MonthlyCost,
				AvgCPU:        avgCPU,
				AvgMemory:     avgMemory,
				MaxCPU:        maxCPU,
				MaxMemory:     maxMemory,
				Reason:        "Instance is underutilized, consider downsizing",
				Confidence:    confidence * 0.8,
			})
		}
	}

	return suggestions
}

func (c *CostOptimizer) GetTotalMonthlySaving() float64 {
	suggestions := c.GetSuggestions()
	var total float64
	for _, s := range suggestions {
		total += s.MonthlySaving
	}
	return total
}

func calculateStats(values []float64) (avg, max float64) {
	if len(values) == 0 {
		return 0, 0
	}

	var sum float64
	max = values[0]
	for _, v := range values {
		sum += v
		if v > max {
			max = v
		}
	}
	avg = sum / float64(len(values))
	return avg, max
}

func (c *CostOptimizer) CleanupStaleInstances(activeInstanceIDs []string) {
	c.mu.Lock()
	defer c.mu.Unlock()

	activeSet := make(map[string]bool)
	for _, id := range activeInstanceIDs {
		activeSet[id] = true
	}

	for id := range c.instanceMetrics {
		if !activeSet[id] {
			delete(c.instanceMetrics, id)
		}
	}
}

func (c *CostOptimizer) GetCostSummary(instanceType string, instanceCount int) map[string]interface{} {
	hourlyCost := c.CalculateHourlyCost(instanceType, instanceCount)
	monthlyCost := c.CalculateMonthlyCost(instanceType, instanceCount)
	suggestions := c.GetSuggestions()
	potentialSaving := c.GetTotalMonthlySaving()

	return map[string]interface{}{
		"instance_type":      instanceType,
		"instance_count":     instanceCount,
		"hourly_cost":        hourlyCost,
		"daily_cost":         hourlyCost * 24,
		"monthly_cost":       monthlyCost,
		"yearly_cost":        monthlyCost * 12,
		"optimization_count": len(suggestions),
		"potential_saving":   potentialSaving,
	}
}
