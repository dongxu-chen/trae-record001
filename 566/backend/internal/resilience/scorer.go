package resilience

import (
	"math"
	"time"

	"github.com/google/uuid"
	"fault-injection-platform/internal/model"
)

type Scorer struct {
}

func NewScorer() *Scorer {
	return &Scorer{}
}

func (s *Scorer) CalculateScore(
	faultID string,
	serviceName string,
	baseline *model.ServiceMetrics,
	faultMetrics *model.ServiceMetrics,
	recoveryMetrics *model.ServiceMetrics,
	recoveryTrend []model.RecoveryTrendPoint,
	faultDuration time.Duration,
) *model.ResilienceReport {
	recoverySpeedScore := s.calculateRecoverySpeedScore(recoveryTrend, faultDuration)
	stabilityScore := s.calculateStabilityScore(baseline, recoveryMetrics, recoveryTrend)
	errorHandlingScore := s.calculateErrorHandlingScore(baseline, faultMetrics, recoveryMetrics)
	performanceScore := s.calculatePerformanceScore(baseline, recoveryMetrics)

	overallScore := recoverySpeedScore*0.35 + stabilityScore*0.25 + errorHandlingScore*0.25 + performanceScore*0.15

	recoveryTime := s.calculateRecoveryTime(recoveryTrend, baseline)
	maxDegradation := s.calculateMaxDegradation(recoveryTrend, baseline)

	grade := s.getGrade(overallScore)
	recommendations := s.generateRecommendations(recoverySpeedScore, stabilityScore, errorHandlingScore, performanceScore, maxDegradation)

	peakImpact := &model.MetricsDiff{
		AvgLatencyDiff:   math.Abs(recoveryMetrics.AvgLatency - baseline.AvgLatency),
		AvgLatencyChange: s.calculatePercentageChange(baseline.AvgLatency, recoveryMetrics.AvgLatency),
		P95LatencyDiff:   math.Abs(recoveryMetrics.P95Latency - baseline.P95Latency),
		P95LatencyChange: s.calculatePercentageChange(baseline.P95Latency, recoveryMetrics.P95Latency),
		ErrorRateDiff:    math.Abs(recoveryMetrics.ErrorRate - baseline.ErrorRate),
		ErrorRateChange:  s.calculatePercentageChange(baseline.ErrorRate, recoveryMetrics.ErrorRate),
	}

	score := &model.ResilienceScore{
		ID:                  uuid.New().String(),
		FaultID:             faultID,
		ServiceName:         serviceName,
		OverallScore:        roundFloat(overallScore, 2),
		RecoverySpeedScore:  roundFloat(recoverySpeedScore, 2),
		StabilityScore:      roundFloat(stabilityScore, 2),
		ErrorHandlingScore:  roundFloat(errorHandlingScore, 2),
		PerformanceScore:    roundFloat(performanceScore, 2),
		RecoveryTimeSeconds: roundFloat(recoveryTime, 2),
		MaxDegradationPct:   roundFloat(maxDegradation, 2),
		Grade:               grade,
		Recommendations:     recommendations,
		CalculatedAt:        time.Now(),
	}

	return &model.ResilienceReport{
		Score:           score,
		RecoveryTrend:   recoveryTrend,
		BaselineMetrics: baseline,
		PeakImpact:      peakImpact,
	}
}

func (s *Scorer) calculateRecoverySpeedScore(trend []model.RecoveryTrendPoint, faultDuration time.Duration) float64 {
	if len(trend) < 2 {
		return 50.0
	}

	var totalRecoveryTime float64
	var recoveryCount int
	isRecovered := false

	for i, point := range trend {
		if point.RecoveryPct >= 90 && !isRecovered {
			totalRecoveryTime += float64(i)
			recoveryCount++
			isRecovered = true
			break
		}
	}

	if !isRecovered {
		return 30.0
	}

	normalizedTime := totalRecoveryTime / float64(len(trend))
	score := 100 - (normalizedTime * 100)

	if score < 0 {
		score = 0
	}

	return score
}

func (s *Scorer) calculateStabilityScore(
	baseline *model.ServiceMetrics,
	recovery *model.ServiceMetrics,
	trend []model.RecoveryTrendPoint,
) float64 {
	if len(trend) < 3 {
		return 50.0
	}

	lastThird := trend[len(trend)*2/3:]
	if len(lastThird) == 0 {
		return 50.0
	}

	var variance float64
	var mean float64

	for _, point := range lastThird {
		mean += point.RecoveryPct
	}
	mean /= float64(len(lastThird))

	for _, point := range lastThird {
		diff := point.RecoveryPct - mean
		variance += diff * diff
	}
	variance /= float64(len(lastThird))

	stdDev := math.Sqrt(variance)
	stabilityScore := 100 - (stdDev * 2)

	if stabilityScore < 0 {
		stabilityScore = 0
	}

	return stabilityScore
}

func (s *Scorer) calculateErrorHandlingScore(
	baseline *model.ServiceMetrics,
	faultMetrics *model.ServiceMetrics,
	recovery *model.ServiceMetrics,
) float64 {
	baselineErrorRate := baseline.ErrorRate
	if baselineErrorRate == 0 {
		baselineErrorRate = 0.1
	}

	faultErrorRate := faultMetrics.ErrorRate
	recoveryErrorRate := recovery.ErrorRate

	errorSpike := faultErrorRate - baselineErrorRate
	errorRemain := recoveryErrorRate - baselineErrorRate

	if errorRemain < 0 {
		errorRemain = 0
	}

	errorRecoveryRatio := 1.0
	if errorSpike > 0 {
		errorRecoveryRatio = 1.0 - (errorRemain / errorSpike)
	}

	score := errorRecoveryRatio * 100

	thresholdPenalty := 0.0
	if recoveryErrorRate > baselineErrorRate*2 {
		thresholdPenalty = (recoveryErrorRate / (baselineErrorRate * 2)) * 20
	}

	score -= thresholdPenalty

	if score < 0 {
		score = 0
	}
	if score > 100 {
		score = 100
	}

	return score
}

func (s *Scorer) calculatePerformanceScore(
	baseline *model.ServiceMetrics,
	recovery *model.ServiceMetrics,
) float64 {
	baselineLatency := baseline.AvgLatency
	if baselineLatency == 0 {
		baselineLatency = 100
	}

	recoveryLatency := recovery.AvgLatency
	latencyRatio := recoveryLatency / baselineLatency

	score := 100.0

	if latencyRatio > 1.0 {
		score -= (latencyRatio - 1.0) * 50
	}

	baselineP99 := baseline.P99Latency
	if baselineP99 == 0 {
		baselineP99 = 200
	}

	recoveryP99 := recovery.P99Latency
	p99Ratio := recoveryP99 / baselineP99

	if p99Ratio > 1.0 {
		score -= (p99Ratio - 1.0) * 30
	}

	if score < 0 {
		score = 0
	}
	if score > 100 {
		score = 100
	}

	return score
}

func (s *Scorer) calculateRecoveryTime(trend []model.RecoveryTrendPoint, baseline *model.ServiceMetrics) float64 {
	if len(trend) < 2 {
		return 0
	}

	timePerPoint := 10.0

	for i, point := range trend {
		if point.RecoveryPct >= 90 {
			return float64(i) * timePerPoint
		}
	}

	return float64(len(trend)) * timePerPoint
}

func (s *Scorer) calculateMaxDegradation(trend []model.RecoveryTrendPoint, baseline *model.ServiceMetrics) float64 {
	if len(trend) == 0 {
		return 0
	}

	minRecovery := 100.0
	for _, point := range trend {
		if point.RecoveryPct < minRecovery {
			minRecovery = point.RecoveryPct
		}
	}

	return 100.0 - minRecovery
}

func (s *Scorer) calculatePercentageChange(baseline, current float64) float64 {
	if baseline == 0 {
		return 0
	}
	return ((current - baseline) / baseline) * 100
}

func (s *Scorer) getGrade(score float64) string {
	switch {
	case score >= 90:
		return "S"
	case score >= 80:
		return "A"
	case score >= 70:
		return "B"
	case score >= 60:
		return "C"
	case score >= 50:
		return "D"
	default:
		return "F"
	}
}

func (s *Scorer) generateRecommendations(
	recoverySpeed, stability, errorHandling, performance, maxDegradation float64,
) []string {
	recommendations := make([]string, 0)

	if recoverySpeed < 60 {
		recommendations = append(recommendations,
			"系统恢复速度较慢，建议优化：1) 增加熔断机制的快速恢复配置 2) 优化连接池参数 3) 考虑引入降级策略")
	}

	if stability < 70 {
		recommendations = append(recommendations,
			"系统恢复后稳定性不足，建议检查：1) 重试风暴防护 2) 限流阈值设置 3) 服务健康检查机制")
	}

	if errorHandling < 70 {
		recommendations = append(recommendations,
			"错误处理能力有待提升，建议：1) 完善降级逻辑 2) 增加重试机制 3) 优化错误边界处理")
	}

	if performance < 70 {
		recommendations = append(recommendations,
			"故障后性能恢复不完全，建议：1) 检查缓存预热机制 2) 优化数据库连接池 3) 考虑请求排队策略")
	}

	if maxDegradation > 50 {
		recommendations = append(recommendations,
			"故障期间系统退化严重，建议：1) 实施熔断机制 2) 增加服务降级 3) 优化限流策略")
	}

	if len(recommendations) == 0 {
		recommendations = append(recommendations,
			"系统韧性表现良好，建议定期进行故障注入测试，持续验证系统稳定性")
	}

	return recommendations
}

func (s *Scorer) GenerateRecoveryTrend(
	baseline *model.ServiceMetrics,
	comparison *model.ComparisonMetrics,
	timePoints int,
) []model.RecoveryTrendPoint {
	trend := make([]model.RecoveryTrendPoint, timePoints)
	startTime := time.Now().Add(-time.Duration(timePoints*10) * time.Second)

	baselineLatency := baseline.AvgLatency
	baselineErrorRate := baseline.ErrorRate
	if baselineLatency == 0 {
		baselineLatency = 100
	}
	if baselineErrorRate == 0 {
		baselineErrorRate = 0.1
	}

	for i := 0; i < timePoints; i++ {
		progress := float64(i) / float64(timePoints-1)
		recoveryProgress := s.calculateRecoveryProgress(progress)

		latencyMs := baselineLatency + (comparison.Diff.AvgLatencyDiff * (1 - recoveryProgress/100))
		errorRate := baselineErrorRate + (comparison.Diff.ErrorRateDiff * (1 - recoveryProgress/100))

		if latencyMs < baselineLatency {
			latencyMs = baselineLatency
		}
		if errorRate < baselineErrorRate {
			errorRate = baselineErrorRate
		}

		trend[i] = model.RecoveryTrendPoint{
			Timestamp:    startTime.Add(time.Duration(i*10) * time.Second),
			RecoveryPct:  roundFloat(recoveryProgress, 2),
			LatencyMs:    roundFloat(latencyMs, 2),
			ErrorRatePct: roundFloat(errorRate, 2),
		}
	}

	return trend
}

func (s *Scorer) calculateRecoveryProgress(progress float64) float64 {
	return 100 * (1 - math.Exp(-5*progress))
}

func roundFloat(val float64, precision int) float64 {
	ratio := math.Pow(10, float64(precision))
	return math.Round(val*ratio) / ratio
}
