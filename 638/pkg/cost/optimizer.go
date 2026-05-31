package cost

import (
	"fmt"
	"math"
	"sort"

	"github.com/k8s-autoscaler/pkg/metrics"
)

type ResourceCost struct {
	ResourceType    string  `json:"resourceType"`
	RequestQuantity float64 `json:"requestQuantity"`
	UsedQuantity    float64 `json:"usedQuantity"`
	UnitCost        float64 `json:"unitCost"`
	TotalCost       float64 `json:"totalCost"`
	WasteCost       float64 `json:"wasteCost"`
}

type SLAConstraint struct {
	Name     string  `json:"name"`
	Type     string  `json:"type"`
	Value    float64 `json:"value"`
	Operator string  `json:"operator"`
	Priority int     `json:"priority"`
}

type SLAViolation struct {
	Constraint      SLAConstraint `json:"constraint"`
	CurrentValue    float64       `json:"currentValue"`
	ViolationAmount float64       `json:"violationAmount"`
	Severity        string        `json:"severity"`
}

type CostAnalysis struct {
	Namespace           string         `json:"namespace"`
	Deployment          string         `json:"deployment"`
	CurrentReplicas     int32          `json:"currentReplicas"`
	RecommendedReplicas int32          `json:"recommendedReplicas"`
	ResourceCosts       []ResourceCost `json:"resourceCosts"`
	TotalMonthlyCost    float64        `json:"totalMonthlyCost"`
	PotentialSavings    float64        `json:"potentialSavings"`
	SavingsPercent      float64        `json:"savingsPercent"`
	Recommendations     []string       `json:"recommendations"`
	SLAConstraints      []SLAConstraint `json:"slaConstraints,omitempty"`
	SLAViolations       []SLAViolation  `json:"slaViolations,omitempty"`
	SLAScore            float64         `json:"slaScore"`
}

type NodeCost struct {
	NodeType   string  `json:"nodeType"`
	HourlyCost float64 `json:"hourlyCost"`
	CPU        int64   `json:"cpu"`
	Memory     int64   `json:"memory"`
}

type CostOptimizer struct {
	nodeCosts       []NodeCost
	overheadPercent float64
	slaConstraints  []SLAConstraint
}

func NewCostOptimizer(nodeCosts []NodeCost) *CostOptimizer {
	defaultSLA := []SLAConstraint{
		{
			Name:     "minReplicas",
			Type:     "MinReplicas",
			Value:    1,
			Operator: ">=",
			Priority: 100,
		},
		{
			Name:     "availability",
			Type:     "Availability",
			Value:    99.9,
			Operator: ">=",
			Priority: 80,
		},
	}
	return &CostOptimizer{
		nodeCosts:       nodeCosts,
		overheadPercent: 0.15,
		slaConstraints:  defaultSLA,
	}
}

func NewCostOptimizerWithSLA(nodeCosts []NodeCost, sla []SLAConstraint) *CostOptimizer {
	return &CostOptimizer{
		nodeCosts:       nodeCosts,
		overheadPercent: 0.15,
		slaConstraints:  sla,
	}
}

func (o *CostOptimizer) cpuUnitCostHourly() float64 {
	var totalCost, totalCPU float64
	for _, nc := range o.nodeCosts {
		totalCost += nc.HourlyCost
		totalCPU += float64(nc.CPU)
	}
	if totalCPU == 0 {
		return 0
	}
	return (totalCost * 0.5) / totalCPU
}

func (o *CostOptimizer) memUnitCostHourly() float64 {
	var totalCost, totalMem float64
	for _, nc := range o.nodeCosts {
		totalCost += nc.HourlyCost
		totalMem += float64(nc.Memory)
	}
	if totalMem == 0 {
		return 0
	}
	return (totalCost * 0.5) / totalMem
}

func (o *CostOptimizer) p95(values []float64) float64 {
	if len(values) == 0 {
		return 0
	}
	sorted := make([]float64, len(values))
	copy(sorted, values)
	sort.Float64s(sorted)
	idx := int(math.Ceil(0.95*float64(len(sorted)))) - 1
	if idx < 0 {
		idx = 0
	}
	if idx >= len(sorted) {
		idx = len(sorted) - 1
	}
	return sorted[idx]
}

func (o *CostOptimizer) CheckSLAViolations(m metrics.WorkloadMetrics, replicas int32) []SLAViolation {
	var violations []SLAViolation
	for _, constraint := range o.slaConstraints {
		var currentValue float64
		var violated bool
		var violationAmount float64

		switch constraint.Type {
		case "Availability":
			currentValue = 100 - (100 / (float64(replicas) + 1)) * 0.5
		case "LatencyP99":
			currentValue = m.AggLatency
		case "Throughput":
			currentValue = m.AggQPS
		case "MinReplicas":
			currentValue = float64(replicas)
		default:
			continue
		}

		switch constraint.Operator {
		case ">=":
			if currentValue < constraint.Value {
				violated = true
				violationAmount = constraint.Value - currentValue
			}
		case "<=":
			if currentValue > constraint.Value {
				violated = true
				violationAmount = currentValue - constraint.Value
			}
		}

		if violated {
			severity := "warning"
			if violationAmount > constraint.Value*0.1 {
				severity = "critical"
			}
			violations = append(violations, SLAViolation{
				Constraint:      constraint,
				CurrentValue:    currentValue,
				ViolationAmount: violationAmount,
				Severity:        severity,
			})
		}
	}
	return violations
}

func (o *CostOptimizer) CalculateSLAScore(violations []SLAViolation) float64 {
	score := 100.0
	for _, v := range violations {
		if v.Severity == "critical" {
			score -= 20
		} else {
			score -= 5
		}
	}
	if score < 0 {
		score = 0
	}
	return score
}

func (o *CostOptimizer) AnalyzeWorkload(namespace, deployment string, m metrics.WorkloadMetrics, recommendedReplicas int32) CostAnalysis {
	replicas := m.Replicas
	if replicas <= 0 {
		replicas = 1
	}

	var cpuValues, memValues []float64
	for _, p := range m.Pods {
		cpuValues = append(cpuValues, p.CPU)
		memValues = append(memValues, p.Memory)
	}

	p95CPU := o.p95(cpuValues)
	p95Mem := o.p95(memValues)

	cpuUnitMonthly := o.cpuUnitCostHourly() * 730
	memUnitMonthly := o.memUnitCostHourly() * 730

	cpuResourceCost := o.CalculateWaste(p95CPU*float64(replicas), m.AggCPU, cpuUnitMonthly)
	cpuResourceCost.ResourceType = "CPU"

	memResourceCost := o.CalculateWaste(p95Mem*float64(replicas), m.AggMemory, memUnitMonthly)
	memResourceCost.ResourceType = "Memory"

	totalMonthly := cpuResourceCost.TotalCost + memResourceCost.TotalCost

	adjustedReplicas := recommendedReplicas
	for {
		recViolations := o.CheckSLAViolations(m, adjustedReplicas)
		if len(recViolations) == 0 {
			break
		}
		hasMinReplicaViolation := false
		for _, v := range recViolations {
			if v.Constraint.Type == "MinReplicas" || v.Constraint.Type == "Availability" {
				hasMinReplicaViolation = true
				break
			}
		}
		if !hasMinReplicaViolation {
			break
		}
		adjustedReplicas++
		if adjustedReplicas > replicas*10 {
			break
		}
	}

	recommendedCost := o.EstimateMonthlyCost(adjustedReplicas, p95CPU*(1+o.overheadPercent), p95Mem*(1+o.overheadPercent))

	savings := totalMonthly - recommendedCost
	if savings < 0 {
		savings = 0
	}

	savingsPercent := 0.0
	if totalMonthly > 0 {
		savingsPercent = (savings / totalMonthly) * 100
	}

	var recommendations []string
	recommendations = append(recommendations, o.GenerateRightSizingAdvice(m)...)

	if adjustedReplicas < replicas {
		recommendations = append(recommendations, fmt.Sprintf("Reduce replicas from %d to %d to save %.2f%% cost", replicas, adjustedReplicas, savingsPercent))
	} else if adjustedReplicas > replicas {
		recommendations = append(recommendations, fmt.Sprintf("Increase replicas from %d to %d for better reliability", replicas, adjustedReplicas))
	}

	currentViolations := o.CheckSLAViolations(m, replicas)
	recViolations := o.CheckSLAViolations(m, adjustedReplicas)

	slaScore := o.CalculateSLAScore(recViolations)

	if len(currentViolations) > 0 {
		for _, v := range currentViolations {
			recommendations = append(recommendations, fmt.Sprintf("SLA %s: %s violation - current %.2f, required %.2f", v.Severity, v.Constraint.Name, v.CurrentValue, v.Constraint.Value))
		}
	}

	if adjustedReplicas != recommendedReplicas {
		recommendations = append(recommendations, fmt.Sprintf("Adjusted recommended replicas from %d to %d to meet SLA constraints", recommendedReplicas, adjustedReplicas))
	}

	recommendations = append(recommendations, fmt.Sprintf("SLA Score: %.0f/100", slaScore))

	return CostAnalysis{
		Namespace:           namespace,
		Deployment:          deployment,
		CurrentReplicas:     replicas,
		RecommendedReplicas: adjustedReplicas,
		ResourceCosts:       []ResourceCost{cpuResourceCost, memResourceCost},
		TotalMonthlyCost:    totalMonthly,
		PotentialSavings:    savings,
		SavingsPercent:      savingsPercent,
		Recommendations:     recommendations,
		SLAConstraints:      o.slaConstraints,
		SLAViolations:       recViolations,
		SLAScore:            slaScore,
	}
}

func (o *CostOptimizer) CalculateWaste(requested, used float64, unitCost float64) ResourceCost {
	totalCost := requested * unitCost
	wasteCost := (requested - used) * unitCost
	if wasteCost < 0 {
		wasteCost = 0
	}
	return ResourceCost{
		RequestQuantity: requested,
		UsedQuantity:    used,
		UnitCost:        unitCost,
		TotalCost:       totalCost,
		WasteCost:       wasteCost,
	}
}

func (o *CostOptimizer) EstimateMonthlyCost(replicas int32, cpuPerPod, memPerPod float64) float64 {
	cpuCostMonthly := cpuPerPod * o.cpuUnitCostHourly() * 730
	memCostMonthly := memPerPod * o.memUnitCostHourly() * 730
	return float64(replicas) * (cpuCostMonthly + memCostMonthly)
}

func (o *CostOptimizer) OptimizeResourceRequests(m metrics.WorkloadMetrics) map[string]float64 {
	replicas := m.Replicas
	if replicas <= 0 {
		replicas = 1
	}

	var cpuValues, memValues []float64
	for _, p := range m.Pods {
		cpuValues = append(cpuValues, p.CPU)
		memValues = append(memValues, p.Memory)
	}

	p95CPU := o.p95(cpuValues)
	p95Mem := o.p95(memValues)

	avgCPU := m.AggCPU / float64(replicas)
	avgMem := m.AggMemory / float64(replicas)

	violations := o.CheckSLAViolations(m, replicas)
	hasLatencyViolation := false
	for _, v := range violations {
		if v.Constraint.Type == "LatencyP99" {
			hasLatencyViolation = true
			break
		}
	}

	optimizedCPU := p95CPU * (1 + o.overheadPercent)
	optimizedMem := p95Mem * (1 + o.overheadPercent)

	if hasLatencyViolation && optimizedCPU < avgCPU {
		optimizedCPU = avgCPU
	}

	return map[string]float64{
		"CPU":    optimizedCPU,
		"Memory": optimizedMem,
	}
}

func (o *CostOptimizer) GenerateRightSizingAdvice(m metrics.WorkloadMetrics) []string {
	replicas := m.Replicas
	if replicas <= 0 {
		replicas = 1
	}

	optimized := o.OptimizeResourceRequests(m)
	avgCPU := m.AggCPU / float64(replicas)
	avgMem := m.AggMemory / float64(replicas)

	var advice []string

	currentCPURequest := avgCPU * 1.5
	if currentCPURequest > optimized["CPU"] && optimized["CPU"] > 0 {
		advice = append(advice, fmt.Sprintf("Reduce CPU request from %.0fm to %.0fm", currentCPURequest, optimized["CPU"]))
	} else if optimized["CPU"] > 0 {
		advice = append(advice, fmt.Sprintf("Increase CPU request from %.0fm to %.0fm", currentCPURequest, optimized["CPU"]))
	}

	currentMemRequest := avgMem * 1.5
	if currentMemRequest > optimized["Memory"] && optimized["Memory"] > 0 {
		advice = append(advice, fmt.Sprintf("Reduce Memory request from %.0fMi to %.0fMi", currentMemRequest/1024/1024, optimized["Memory"]/1024/1024))
	} else if optimized["Memory"] > 0 {
		advice = append(advice, fmt.Sprintf("Increase Memory request from %.0fMi to %.0fMi", currentMemRequest/1024/1024, optimized["Memory"]/1024/1024))
	}

	return advice
}
