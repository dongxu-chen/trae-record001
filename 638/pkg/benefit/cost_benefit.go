package benefit

import (
	"sync"
	"time"

	"github.com/k8s-autoscaler/pkg/cost"
	"github.com/k8s-autoscaler/pkg/metrics"
)

type RevenueModel struct {
	RevenuePerQPS           float64 `json:"revenuePerQPS"`
	LatencyPenaltyPerSecond float64 `json:"latencyPenaltyPerSecond"`
	DowntimeCostPerMinute   float64 `json:"downtimeCostPerMinute"`
	SLAErrorPenalty         float64 `json:"slaErrorPenalty"`
}

type ScaleAction struct {
	Service     string    `json:"service"`
	Namespace   string    `json:"namespace"`
	OldReplicas int32     `json:"oldReplicas"`
	NewReplicas int32     `json:"newReplicas"`
	Action      string    `json:"action"`
	Timestamp   time.Time `json:"timestamp"`
}

type CostBreakdown struct {
	AdditionalComputeCost float64 `json:"additionalComputeCost"`
	ResourceWasteCost     float64 `json:"resourceWasteCost"`
	TotalCost             float64 `json:"totalCost"`
}

type BenefitBreakdown struct {
	RevenueGain             float64 `json:"revenueGain"`
	LatencyPenaltyAvoided   float64 `json:"latencyPenaltyAvoided"`
	DowntimeAvoided         float64 `json:"downtimeAvoided"`
	SLAErrorPenaltyAvoided  float64 `json:"slaErrorPenaltyAvoided"`
	TotalBenefit            float64 `json:"totalBenefit"`
}

type CostBenefitResult struct {
	Action           ScaleAction      `json:"action"`
	Cost             CostBreakdown    `json:"cost"`
	Benefit          BenefitBreakdown `json:"benefit"`
	NetBenefit       float64          `json:"netBenefit"`
	BenefitCostRatio float64          `json:"benefitCostRatio"`
	Recommendation   string           `json:"recommendation"`
	PaybackHours     float64          `json:"paybackHours"`
	BreakevenQPS     float64          `json:"breakevenQPS"`
	Confidence       float64          `json:"confidence"`
}

type CostBenefitAnalyzer struct {
	revenueModel RevenueModel
	nodeCosts    []cost.NodeCost
	history      []CostBenefitResult
	mu           sync.RWMutex
}

func NewCostBenefitAnalyzer(model RevenueModel, nodeCosts []cost.NodeCost) *CostBenefitAnalyzer {
	return &CostBenefitAnalyzer{
		revenueModel: model,
		nodeCosts:    nodeCosts,
		history:      make([]CostBenefitResult, 0, 100),
	}
}

func (a *CostBenefitAnalyzer) Analyze(action ScaleAction, metricsBefore, metricsAfter metrics.WorkloadMetrics, slaViolationsBefore, slaViolationsAfter int) CostBenefitResult {
	replicaDiff := int(action.NewReplicas) - int(action.OldReplicas)
	avgHourlyCost := 0.0
	if len(a.nodeCosts) > 0 {
		for _, nc := range a.nodeCosts {
			avgHourlyCost += nc.HourlyCost
		}
		avgHourlyCost /= float64(len(a.nodeCosts))
	}

	additionalComputeCost := float64(replicaDiff) * avgHourlyCost
	if additionalComputeCost < 0 {
		additionalComputeCost = -additionalComputeCost
	}

	wasteBefore := 0.0
	for _, p := range metricsBefore.Pods {
		cpuRequest := p.CPU * 1.5
		memRequest := p.Memory * 1.5
		wasteBefore += (cpuRequest - p.CPU) + (memRequest - p.Memory)
	}
	wasteAfter := 0.0
	for _, p := range metricsAfter.Pods {
		cpuRequest := p.CPU * 1.5
		memRequest := p.Memory * 1.5
		wasteAfter += (cpuRequest - p.CPU) + (memRequest - p.Memory)
	}
	resourceWasteCost := (wasteAfter - wasteBefore) * 0.00001

	totalCost := additionalComputeCost + resourceWasteCost
	if totalCost < 0 {
		totalCost = 0
	}

	qpsIncrease := metricsAfter.AggQPS - metricsBefore.AggQPS
	if qpsIncrease < 0 {
		qpsIncrease = 0
	}
	revenueGain := qpsIncrease * a.revenueModel.RevenuePerQPS

	latencyBefore := metricsBefore.AggLatency
	latencyAfter := metricsAfter.AggLatency
	latencyImprovement := latencyBefore - latencyAfter
	if latencyImprovement < 0 {
		latencyImprovement = 0
	}
	latencyPenaltyAvoided := latencyImprovement * a.revenueModel.LatencyPenaltyPerSecond

	availabilityBefore := 100 - (100 / (float64(metricsBefore.Replicas) + 1)) * 0.5
	availabilityAfter := 100 - (100 / (float64(metricsAfter.Replicas) + 1)) * 0.5
	downtimeReduction := (availabilityAfter - availabilityBefore) / 100 * 60
	downtimeAvoided := downtimeReduction * a.revenueModel.DowntimeCostPerMinute
	if downtimeAvoided < 0 {
		downtimeAvoided = 0
	}

	slaViolationReduction := slaViolationsBefore - slaViolationsAfter
	if slaViolationReduction < 0 {
		slaViolationReduction = 0
	}
	slaErrorPenaltyAvoided := float64(slaViolationReduction) * a.revenueModel.SLAErrorPenalty

	totalBenefit := revenueGain + latencyPenaltyAvoided + downtimeAvoided + slaErrorPenaltyAvoided

	netBenefit := totalBenefit - totalCost

	benefitCostRatio := 0.0
	if totalCost > 0 {
		benefitCostRatio = totalBenefit / totalCost
	}

	recommendation := "REJECT"
	if benefitCostRatio > 2.0 {
		recommendation = "APPROVE"
	} else if benefitCostRatio > 1.2 {
		recommendation = "CAUTION"
	}

	paybackHours := 0.0
	if netBenefit > 0 {
		paybackHours = totalCost / (netBenefit / 24)
	}

	breakevenQPS := 0.0
	if a.revenueModel.RevenuePerQPS > 0 {
		breakevenQPS = additionalComputeCost / a.revenueModel.RevenuePerQPS
	}

	confidence := 0.5
	slaFactor := float64(slaViolationReduction)
	if slaFactor > 1 {
		slaFactor = 1
	}
	qpsFactor := qpsIncrease / 100
	if qpsFactor > 1 {
		qpsFactor = 1
	}
	confidence = 0.5 + 0.3*slaFactor + 0.2*qpsFactor

	result := CostBenefitResult{
		Action:           action,
		Cost: CostBreakdown{
			AdditionalComputeCost: additionalComputeCost,
			ResourceWasteCost:     resourceWasteCost,
			TotalCost:             totalCost,
		},
		Benefit: BenefitBreakdown{
			RevenueGain:            revenueGain,
			LatencyPenaltyAvoided:  latencyPenaltyAvoided,
			DowntimeAvoided:        downtimeAvoided,
			SLAErrorPenaltyAvoided: slaErrorPenaltyAvoided,
			TotalBenefit:           totalBenefit,
		},
		NetBenefit:       netBenefit,
		BenefitCostRatio: benefitCostRatio,
		Recommendation:   recommendation,
		PaybackHours:     paybackHours,
		BreakevenQPS:     breakevenQPS,
		Confidence:       confidence,
	}

	a.mu.Lock()
	a.history = append(a.history, result)
	if len(a.history) > 100 {
		a.history = a.history[len(a.history)-100:]
	}
	a.mu.Unlock()

	return result
}

func (a *CostBenefitAnalyzer) GetHistory() []CostBenefitResult {
	a.mu.RLock()
	defer a.mu.RUnlock()
	result := make([]CostBenefitResult, len(a.history))
	copy(result, a.history)
	return result
}

func (a *CostBenefitAnalyzer) EstimateBenefit(ns, service string, scaleTo int32, currentMetrics metrics.WorkloadMetrics) CostBenefitResult {
	replicaDiff := int(scaleTo) - int(currentMetrics.Replicas)
	action := "scale_up"
	if replicaDiff < 0 {
		action = "scale_down"
	}

	scaleAction := ScaleAction{
		Service:     service,
		Namespace:   ns,
		OldReplicas: currentMetrics.Replicas,
		NewReplicas: scaleTo,
		Action:      action,
		Timestamp:   time.Now(),
	}

	perReplicaQPS := 0.0
	perReplicaCPU := 0.0
	perReplicaMemory := 0.0
	if currentMetrics.Replicas > 0 {
		perReplicaQPS = currentMetrics.AggQPS / float64(currentMetrics.Replicas)
		perReplicaCPU = currentMetrics.AggCPU / float64(currentMetrics.Replicas)
		perReplicaMemory = currentMetrics.AggMemory / float64(currentMetrics.Replicas)
	}

	projectedPods := make([]metrics.PodMetrics, scaleTo)
	for i := int32(0); i < scaleTo; i++ {
		projectedPods[i] = metrics.PodMetrics{
			PodName: service + "-" + string(rune(i)),
			CPU:     perReplicaCPU,
			Memory:  perReplicaMemory,
			QPS:     perReplicaQPS,
			Latency: currentMetrics.AggLatency,
		}
	}

	projectedAggQPS := perReplicaQPS * float64(scaleTo)
	projectedLatency := currentMetrics.AggLatency
	if replicaDiff > 0 && projectedAggQPS > 0 {
		loadFactor := float64(currentMetrics.Replicas) / float64(scaleTo)
		projectedLatency = currentMetrics.AggLatency * loadFactor
	}

	metricsAfter := metrics.WorkloadMetrics{
		DeploymentName: service,
		Namespace:      ns,
		Replicas:       scaleTo,
		Pods:           projectedPods,
		AggCPU:         perReplicaCPU * float64(scaleTo),
		AggMemory:      perReplicaMemory * float64(scaleTo),
		AggQPS:         projectedAggQPS,
		AggLatency:     projectedLatency,
	}

	return a.Analyze(scaleAction, currentMetrics, metricsAfter, 0, 0)
}
