package linkage

import (
	"math"
	"sync"
	"time"

	"github.com/k8s-autoscaler/pkg/metrics"
)

type ServiceDependency struct {
	SourceService       string  `json:"sourceService"`
	SourceNamespace     string  `json:"sourceNamespace"`
	TargetService       string  `json:"targetService"`
	TargetNamespace     string  `json:"targetNamespace"`
	CorrelationStrength float64 `json:"correlationStrength"`
	LagSeconds          int     `json:"lagSeconds"`
	MinTriggerScale     int     `json:"minTriggerScale"`
	Weight              float64 `json:"weight"`
}

type LinkageDecision struct {
	SourceService           string    `json:"sourceService"`
	SourceNamespace         string    `json:"sourceNamespace"`
	TargetService           string    `json:"targetService"`
	TargetNamespace         string    `json:"targetNamespace"`
	SourceScaleChange       int32     `json:"sourceScaleChange"`
	TargetRecommendedChange int32     `json:"targetRecommendedChange"`
	CorrelationStrength     float64   `json:"correlationStrength"`
	EffectiveTime           time.Time `json:"effectiveTime"`
	Reason                  string    `json:"reason"`
}

type LinkageGraph struct {
	dependencies          []ServiceDependency
	pendingDecisions      map[string]LinkageDecision
	mu                    sync.RWMutex
	minCorrelationThreshold float64
	maxLagSeconds         int
}

func NewLinkageGraph(deps []ServiceDependency) *LinkageGraph {
	return &LinkageGraph{
		dependencies:          deps,
		pendingDecisions:      make(map[string]LinkageDecision),
		minCorrelationThreshold: 0.5,
		maxLagSeconds:         3600,
	}
}

func (g *LinkageGraph) AddDependency(dep ServiceDependency) {
	g.mu.Lock()
	defer g.mu.Unlock()
	g.dependencies = append(g.dependencies, dep)
}

func (g *LinkageGraph) RemoveDependency(sourceNs, source, targetNs, target string) {
	g.mu.Lock()
	defer g.mu.Unlock()
	var filtered []ServiceDependency
	for _, d := range g.dependencies {
		if !(d.SourceNamespace == sourceNs && d.SourceService == source &&
			d.TargetNamespace == targetNs && d.TargetService == target) {
			filtered = append(filtered, d)
		}
	}
	g.dependencies = filtered
}

func (g *LinkageGraph) GetDependencies() []ServiceDependency {
	g.mu.RLock()
	defer g.mu.RUnlock()
	copy := make([]ServiceDependency, len(g.dependencies))
	for i, d := range g.dependencies {
		copy[i] = d
	}
	return copy
}

func (g *LinkageGraph) OnSourceScaled(sourceNs, source string, oldReplicas, newReplicas int32, timestamp time.Time) []LinkageDecision {
	g.mu.Lock()
	defer g.mu.Unlock()

	scaleChange := newReplicas - oldReplicas
	var decisions []LinkageDecision

	for _, dep := range g.dependencies {
		if dep.SourceNamespace != sourceNs || dep.SourceService != source {
			continue
		}

		if math.Abs(float64(scaleChange)) >= float64(dep.MinTriggerScale) &&
			dep.CorrelationStrength >= g.minCorrelationThreshold {

			targetChange := int32(math.Round(float64(scaleChange) * dep.Weight))

			decision := LinkageDecision{
				SourceService:           source,
				SourceNamespace:         sourceNs,
				TargetService:           dep.TargetService,
				TargetNamespace:         dep.TargetNamespace,
				SourceScaleChange:       scaleChange,
				TargetRecommendedChange: targetChange,
				CorrelationStrength:     dep.CorrelationStrength,
				EffectiveTime:           timestamp.Add(time.Duration(dep.LagSeconds) * time.Second),
				Reason:                  "Source service scaled, triggering dependent service scaling",
			}

			key := dep.TargetNamespace + "/" + dep.TargetService
			g.pendingDecisions[key] = decision
			decisions = append(decisions, decision)
		}
	}

	return decisions
}

func (g *LinkageGraph) GetPendingDecisions(targetNs, target string, now time.Time) []LinkageDecision {
	g.mu.Lock()
	defer g.mu.Unlock()

	key := targetNs + "/" + target
	var ready []LinkageDecision

	if decision, exists := g.pendingDecisions[key]; exists {
		if !decision.EffectiveTime.After(now) {
			ready = append(ready, decision)
			delete(g.pendingDecisions, key)
		}
	}

	return ready
}

func (g *LinkageGraph) GetAllPending() []LinkageDecision {
	g.mu.RLock()
	defer g.mu.RUnlock()

	var pending []LinkageDecision
	for _, d := range g.pendingDecisions {
		pending = append(pending, d)
	}
	return pending
}

func (g *LinkageGraph) AutoDiscoverCorrelations(ns1, svc1, ns2, svc2 string, historicalData []metrics.WorkloadMetrics, window int) float64 {
	var series1, series2 []float64

	for _, wm := range historicalData {
		if wm.Namespace == ns1 && wm.DeploymentName == svc1 {
			series1 = append(series1, float64(wm.Replicas))
		}
		if wm.Namespace == ns2 && wm.DeploymentName == svc2 {
			series2 = append(series2, float64(wm.Replicas))
		}
	}

	minLen := len(series1)
	if len(series2) < minLen {
		minLen = len(series2)
	}
	if window > 0 && window < minLen {
		minLen = window
	}

	if minLen < 2 {
		return 0
	}

	series1 = series1[:minLen]
	series2 = series2[:minLen]

	var sum1, sum2, sum1Sq, sum2Sq, sumProduct float64
	n := float64(minLen)

	for i := 0; i < minLen; i++ {
		sum1 += series1[i]
		sum2 += series2[i]
		sum1Sq += series1[i] * series1[i]
		sum2Sq += series2[i] * series2[i]
		sumProduct += series1[i] * series2[i]
	}

	numerator := n*sumProduct - sum1*sum2
	denominator := math.Sqrt((n*sum1Sq - sum1*sum1) * (n*sum2Sq - sum2*sum2))

	if denominator == 0 {
		return 0
	}

	return numerator / denominator
}
