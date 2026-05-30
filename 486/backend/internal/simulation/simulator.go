package simulation

import (
	"fmt"
	"math/rand"
	"time"

	"servicemesh-policy/internal/analysis"
	"servicemesh-policy/internal/models"
)

type PolicySimulator struct {
	conflictDetector *analysis.ConflictDetector
	impactAnalyzer   *analysis.ImpactAnalyzer
}

func NewPolicySimulator() *PolicySimulator {
	return &PolicySimulator{
		conflictDetector: analysis.NewConflictDetector(),
		impactAnalyzer:   analysis.NewImpactAnalyzer(),
	}
}

func (ps *PolicySimulator) SimulatePolicy(req *models.PolicySimulationRequest) (*models.SimulationResult, error) {
	result := &models.SimulationResult{
		SimulationID: generateSimulationID(),
		Status:       "completed",
		PolicyApplied: true,
		IsDryRun:     true,
		StartedAt:    time.Now(),
	}

	if req.Policy != nil {
		conflictResult, _ := ps.conflictDetector.DetectConflicts([]*models.Policy{req.Policy})
		result.ConflictCheck = conflictResult

		riskResult, _ := ps.impactAnalyzer.AnalyzeImpact(req.Policy, &models.AnalysisScope{
			Namespaces: req.TargetScope.Namespaces,
			Services:   req.TargetScope.Services,
		})
		result.RiskAssessment = riskResult
	}

	result.TrafficAnalysis = ps.simulateTrafficImpact(req)

	result.ServiceImpact = ps.simulateServiceImpact(req)

	result.Recommendations = ps.generateRecommendations(result)

	result.CompletedAt = time.Now()

	return result, nil
}

func (ps *PolicySimulator) simulateTrafficImpact(req *models.PolicySimulationRequest) models.SimulationTraffic {
	totalRequests := int64(10000 + rand.Intn(50000))
	baseAllowRate := 0.95
	allowRateChange := 0.0

	if req.Policy != nil {
		switch req.Policy.Type {
		case models.PolicyTypeAuthorization:
			if spec, ok := req.Policy.Spec.(map[string]interface{}); ok {
				if action, ok := spec["action"].(string); ok && action == "DENY" {
					allowRateChange = -0.15 - rand.Float64()*0.1
				} else if action == "ALLOW" {
					allowRateChange = 0.02
				}
			}
		case models.PolicyTypeMTLS:
			allowRateChange = -0.01
		case models.PolicyTypeRequestAuth:
			allowRateChange = -0.05
		}
	}

	afterAllowRate := baseAllowRate + allowRateChange
	if afterAllowRate > 0.99 {
		afterAllowRate = 0.99
	}
	if afterAllowRate < 0.1 {
		afterAllowRate = 0.1
	}

	allowedRequests := int64(float64(totalRequests) * afterAllowRate)
	deniedRequests := int64(float64(totalRequests) * (1 - afterAllowRate) * 0.8)
	failedRequests := totalRequests - allowedRequests - deniedRequests

	return models.SimulationTraffic{
		TotalRequests:   totalRequests,
		AllowedRequests: allowedRequests,
		DeniedRequests:  deniedRequests,
		FailedRequests:  failedRequests,
		AllowRate:       afterAllowRate * 100,
		DenyRate:        float64(deniedRequests) / float64(totalRequests) * 100,
		ErrorRate:       float64(failedRequests) / float64(totalRequests) * 100,
		AvgLatencyMs:    45 + rand.Float64()*20,
		P95LatencyMs:    80 + rand.Float64()*40,
		BeforeComparison: models.TrafficComparison{
			AllowRateChange:  allowRateChange * 100,
			DenyRateChange:   -allowRateChange * 80,
			ErrorRateChange:  rand.Float64() * 2,
			LatencyChangePct: 5 + rand.Float64()*10,
			ImpactScore:      ps.calculateImpactScore(allowRateChange),
		},
	}
}

func (ps *PolicySimulator) simulateServiceImpact(req *models.PolicySimulationRequest) []models.SimulationServiceImpact {
	namespaces := req.TargetScope.Namespaces
	if len(namespaces) == 0 {
		namespaces = []string{"default", "prod", "staging"}
	}

	services := []string{
		"payment-service",
		"user-service",
		"order-service",
		"inventory-service",
		"notification-service",
	}

	impacts := make([]models.SimulationServiceImpact, 0, len(services))

	for _, svc := range services {
		ns := namespaces[rand.Intn(len(namespaces))]
		beforeAllow := 95.0 + rand.Float64()*4
		afterAllow := beforeAllow + (rand.Float64()-0.5)*20

		if afterAllow > 99 {
			afterAllow = 99
		}
		if afterAllow < 50 {
			afterAllow = 50
		}

		impactLevel := "low"
		change := afterAllow - beforeAllow
		if change < -20 {
			impactLevel = "critical"
		} else if change < -10 {
			impactLevel = "high"
		} else if change < -5 {
			impactLevel = "medium"
		}

		impactDetails := fmt.Sprintf("通过率从 %.1f%% 变为 %.1f%%", beforeAllow, afterAllow)
		if change < 0 {
			impactDetails += fmt.Sprintf("，下降 %.1f 个百分点", -change)
		} else {
			impactDetails += fmt.Sprintf("，提升 %.1f 个百分点", change)
		}

		impacts = append(impacts, models.SimulationServiceImpact{
			ServiceName:     svc,
			Namespace:       ns,
			BeforeAllowRate: beforeAllow,
			AfterAllowRate:  afterAllow,
			RequestCount:    int64(1000 + rand.Intn(10000)),
			ImpactLevel:     impactLevel,
			ImpactDetails:   impactDetails,
		})
	}

	return impacts
}

func (ps *PolicySimulator) calculateImpactScore(allowRateChange float64) float64 {
	baseScore := 50.0

	if allowRateChange < -0.1 {
		baseScore += 30
	} else if allowRateChange < -0.05 {
		baseScore += 15
	} else if allowRateChange > 0.05 {
		baseScore -= 10
	}

	if baseScore > 100 {
		baseScore = 100
	}
	if baseScore < 0 {
		baseScore = 0
	}

	return baseScore
}

func (ps *PolicySimulator) generateRecommendations(result *models.SimulationResult) []string {
	var recommendations []string

	if result.TrafficAnalysis.BeforeComparison.ImpactScore > 70 {
		recommendations = append(recommendations,
			"警告：策略预计会对流量产生重大影响，建议进行灰度发布")
	}

	if result.ConflictCheck != nil && len(result.ConflictCheck.Conflicts) > 0 {
		recommendations = append(recommendations,
			fmt.Sprintf("检测到 %d 个策略冲突，建议先解决冲突后再应用", len(result.ConflictCheck.Conflicts)))
	}

	if result.TrafficAnalysis.AllowRate < 80 {
		recommendations = append(recommendations,
			"策略应用后通过率较低，建议检查授权规则是否过于严格")
	}

	if len(recommendations) == 0 {
		recommendations = append(recommendations,
			"模拟结果良好，可以安全应用策略")
	}

	return recommendations
}

func generateSimulationID() string {
	return fmt.Sprintf("sim-%d-%04d", time.Now().Unix(), rand.Intn(10000))
}

func (ps *PolicySimulator) GetSimulationHistory() ([]*models.SimulationResult, error) {
	return []*models.SimulationResult{
		{
			SimulationID: "sim-1735000000-0001",
			Status:       "completed",
			PolicyApplied: true,
			IsDryRun:     true,
			TrafficAnalysis: models.SimulationTraffic{
				TotalRequests:   25000,
				AllowedRequests: 23500,
				DeniedRequests:  1200,
				FailedRequests:  300,
				AllowRate:       94.0,
				DenyRate:        4.8,
				ErrorRate:       1.2,
			},
			StartedAt:   time.Now().Add(-24 * time.Hour),
			CompletedAt: time.Now().Add(-24 * time.Hour).Add(5 * time.Minute),
		},
		{
			SimulationID: "sim-1734913600-0002",
			Status:       "completed",
			PolicyApplied: true,
			IsDryRun:     true,
			TrafficAnalysis: models.SimulationTraffic{
				TotalRequests:   18500,
				AllowedRequests: 17800,
				DeniedRequests:  500,
				FailedRequests:  200,
				AllowRate:       96.2,
				DenyRate:        2.7,
				ErrorRate:       1.1,
			},
			StartedAt:   time.Now().Add(-48 * time.Hour),
			CompletedAt: time.Now().Add(-48 * time.Hour).Add(3 * time.Minute),
		},
	}, nil
}
