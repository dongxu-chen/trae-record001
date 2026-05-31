package evaluator

import (
	"fmt"

	"authz-policy-recommender/backend/pkg/models"
	"authz-policy-recommender/backend/pkg/simulator"
)

type PolicyEffectivenessEvaluator struct {
	simulator *simulator.PolicySimulator
}

func NewPolicyEffectivenessEvaluator(ps *simulator.PolicySimulator) *PolicyEffectivenessEvaluator {
	return &PolicyEffectivenessEvaluator{
		simulator: ps,
	}
}

func (pe *PolicyEffectivenessEvaluator) EvaluateEffectiveness(req models.EffectivenessRequest) models.EffectivenessReport {
	beforeResults := make([]models.SimulationResult, 0, len(req.TestRequests))
	afterResults := make([]models.SimulationResult, 0, len(req.TestRequests))

	for _, testReq := range req.TestRequests {
		beforeReq := testReq
		beforeReq.Policies = req.BeforePolicies
		beforeResult := pe.simulator.Simulate(beforeReq)
		beforeResults = append(beforeResults, beforeResult)

		afterReq := testReq
		afterReq.Policies = req.AfterPolicies
		afterResult := pe.simulator.Simulate(afterReq)
		afterResults = append(afterResults, afterResult)
	}

	metrics := pe.calculateMetrics(beforeResults, afterResults)

	return models.EffectivenessReport{
		DeploymentID:  req.DeploymentID,
		BeforeWindow: req.BeforeWindow,
		AfterWindow:  req.AfterWindow,
		Metrics:     metrics,
		OverallScore: pe.calculateOverallScore(metrics),
		Recommendations: pe.generateRecommendations(beforeResults, afterResults, metrics),
		BeforeResults: beforeResults,
		AfterResults:  afterResults,
	}
}

func (pe *PolicyEffectivenessEvaluator) calculateMetrics(before, after []models.SimulationResult) []models.EffectivenessMetric {
	metrics := []models.EffectivenessMetric{}

	metrics = append(metrics, pe.calculateSuccessRate("Overall Success Rate", before, after))
	metrics = append(metrics, pe.calculateDenyRate("Deny Rate", before, after))
	metrics = append(metrics, pe.calculateAllowRate("Allow Rate", before, after))

	serviceMetrics := pe.calculateServiceLevelMetrics(before, after)
	metrics = append(metrics, serviceMetrics...)

	return metrics
}

func (pe *PolicyEffectivenessEvaluator) calculateSuccessRate(name string, before, after []models.SimulationResult) models.EffectivenessMetric {
	beforeAllowed := 0
	afterAllowed := 0

	for _, r := range before {
		if r.Allowed {
			beforeAllowed++
		}
	}

	for _, r := range after {
		if r.Allowed {
			afterAllowed++
		}
	}

	beforeRate := float64(beforeAllowed) / float64(len(before)) * 100
	afterRate := float64(afterAllowed) / float64(len(after)) * 100
	change := afterRate - beforeRate
	changePercent := 0.0
	if beforeRate > 0 {
		changePercent = (change / beforeRate) * 100
	}

	return models.EffectivenessMetric{
		MetricName:    name,
		BeforeValue:   beforeRate,
		AfterValue:    afterRate,
		Change:        change,
		ChangePercent: changePercent,
		Improved:      change >= 0,
	}
}

func (pe *PolicyEffectivenessEvaluator) calculateDenyRate(name string, before, after []models.SimulationResult) models.EffectivenessMetric {
	beforeDenied := 0
	afterDenied := 0

	for _, r := range before {
		if !r.Allowed {
			beforeDenied++
		}
	}

	for _, r := range after {
		if !r.Allowed {
			afterDenied++
		}
	}

	beforeRate := float64(beforeDenied) / float64(len(before)) * 100
	afterRate := float64(afterDenied) / float64(len(after)) * 100
	change := afterRate - beforeRate
	changePercent := 0.0
	if beforeRate > 0 {
		changePercent = (change / beforeRate) * 100
	}

	return models.EffectivenessMetric{
		MetricName:    name,
		BeforeValue:   beforeRate,
		AfterValue:    afterRate,
		Change:        change,
		ChangePercent: changePercent,
		Improved:      change <= 0,
	}
}

func (pe *PolicyEffectivenessEvaluator) calculateAllowRate(name string, before, after []models.SimulationResult) models.EffectivenessMetric {
	return pe.calculateSuccessRate(name, before, after)
}

func (pe *PolicyEffectivenessEvaluator) calculateServiceLevelMetrics(before, after []models.SimulationResult) []models.EffectivenessMetric {
	return []models.EffectivenessMetric{}
}

func (pe *PolicyEffectivenessEvaluator) calculateOverallScore(metrics []models.EffectivenessMetric) float64 {
	totalScore := 0.0
	count := 0

	for _, m := range metrics {
		if m.Improved {
			totalScore += 100
		} else {
			totalScore += 50
		}
		count++
	}

	if count == 0 {
		return 0
	}

	return totalScore / float64(count)
}

func (pe *PolicyEffectivenessEvaluator) generateRecommendations(before, after []models.SimulationResult, metrics []models.EffectivenessMetric) []string {
	recommendations := []string{}

	changedCount := 0
	for i := range before {
		if before[i].Allowed != after[i].Allowed {
			changedCount++
		}
	}

	if changedCount > 0 {
		recommendations = append(recommendations,
			fmt.Sprintf("%d 请求的授权结果发生了变化，请检查策略变更是否符合预期", changedCount))
	}

	denyIncreased := false
	allowIncreased := false
	for _, m := range metrics {
		if m.MetricName == "Deny Rate" && m.Change > 0 {
			denyIncreased = true
		}
		if m.MetricName == "Allow Rate" && m.Change > 0 {
			allowIncreased = true
		}
	}

	if denyIncreased {
		recommendations = append(recommendations, "拒绝率上升，可能影响业务可用性，请检查策略是否过于严格")
	}

	if allowIncreased {
		recommendations = append(recommendations, "允许率上升，可能放宽了访问控制，请确保符合安全要求")
	}

	if len(recommendations) == 0 {
		recommendations = append(recommendations, "策略效果评估完成，未发现明显问题")
	}

	return recommendations
}

func (pe *PolicyEffectivenessEvaluator) CompareSuccessRates(
	beforePolicies, afterPolicies []models.AuthorizationPolicy,
	testRequests []models.SimulationRequest,
) []models.SuccessRateMetric {
	serviceStats := make(map[string]*models.SuccessRateMetric)

	for _, req := range testRequests {
		dest := req.Dest
		if _, exists := serviceStats[dest]; !exists {
			serviceStats[dest] = &models.SuccessRateMetric{
				ServiceName: dest,
			}
		}

		stats := serviceStats[dest]
		stats.TotalRequests++

		beforeReq := req
		beforeReq.Policies = beforePolicies
		beforeResult := pe.simulator.Simulate(beforeReq)
		if beforeResult.Allowed {
			stats.AllowedBefore++
		}

		afterReq := req
		afterReq.Policies = afterPolicies
		afterResult := pe.simulator.Simulate(afterReq)
		if afterResult.Allowed {
			stats.AllowedAfter++
		}
	}

	results := make([]models.SuccessRateMetric, 0, len(serviceStats))
	for _, stats := range serviceStats {
		if stats.TotalRequests > 0 {
			stats.RateBefore = float64(stats.AllowedBefore) / float64(stats.TotalRequests) * 100
			stats.RateAfter = float64(stats.AllowedAfter) / float64(stats.TotalRequests) * 100
			stats.RateChange = stats.RateAfter - stats.RateBefore
		}
		results = append(results, *stats)
	}

	return results
}
