package analyzer

import (
	"fmt"
	"math"
	"sort"
	"time"

	"container-autoscaler/pkg/config"
	"container-autoscaler/pkg/types"
	"container-autoscaler/pkg/utils"
)

type ResourceAnalyzer struct {
	config config.AnalysisConfig
	logger *utils.Logger
}

func NewResourceAnalyzer(cfg config.AnalysisConfig, logger *utils.Logger) *ResourceAnalyzer {
	return &ResourceAnalyzer{
		config: cfg,
		logger: logger,
	}
}

func (a *ResourceAnalyzer) AnalyzeResource(
	ts types.TimeSeriesData,
	currentLimit float64,
	currentRequest float64,
	resourceType string,
	scalingConfig config.ScalingConfig,
) types.ResourceAnalysis {
	values := ts.Values
	n := len(values)

	result := types.ResourceAnalysis{
		CurrentLimit:   currentLimit,
		CurrentRequest: currentRequest,
	}

	if n == 0 {
		result.Recommendation = types.Recommendation{
			ProposedLimit:    currentLimit,
			ProposedRequest:  currentRequest,
			Confidence:       0,
			AdjustmentReason: "insufficient data",
		}
		return result
	}

	if n < a.config.MinDataPoints {
		a.logger.Warning("Insufficient data points: %d (min required: %d)", n, a.config.MinDataPoints)
	}

	cleanedTS := ts
	if a.config.OutlierRemovalEnabled {
		cleanedTS = RemoveOutliers3SigmaTS(ts)
		removed := n - len(cleanedTS.Values)
		if removed > 0 {
			a.logger.Debug("Removed %d outlier data points (3-sigma) for %s analysis", removed, resourceType)
		}
		values = cleanedTS.Values
		n = len(values)
	}

	sorted := make([]float64, n)
	copy(sorted, values)
	sort.Float64s(sorted)

	result.Percentile95 = percentile(sorted, 95)
	result.Percentile99 = percentile(sorted, 99)
	result.Mean = mean(values)
	result.StdDev = stdDev(values, result.Mean)
	result.Trend = calculateTrend(cleanedTS)
	result.Volatility = result.StdDev / result.Mean
	if math.IsNaN(result.Volatility) || math.IsInf(result.Volatility, 0) {
		result.Volatility = 0
	}

	if currentLimit > 0 {
		result.UtilizationRatio = result.Mean / currentLimit
	}

	result.RegressionModel = linearRegression(cleanedTS)

	if len(ts.Values) > 0 {
		result.CurrentUsage = ts.Values[len(ts.Values)-1]
	}

	result.Recommendation = a.generateRecommendation(
		result,
		resourceType,
		scalingConfig,
	)

	return result
}

func (a *ResourceAnalyzer) generateRecommendation(
	analysis types.ResourceAnalysis,
	resourceType string,
	scalingConfig config.ScalingConfig,
) types.Recommendation {
	var percentileThreshold float64
	var minLimit, maxLimit float64
	var requestRatio float64

	switch resourceType {
	case "cpu":
		percentileThreshold = scalingConfig.CPUPercentileThreshold
		minLimit = scalingConfig.MinCPULimit
		maxLimit = scalingConfig.MaxCPULimit
		requestRatio = scalingConfig.CPURequestRatio
	case "memory":
		percentileThreshold = scalingConfig.MemoryPercentileThreshold
		minLimit = scalingConfig.MinMemoryLimit
		maxLimit = scalingConfig.MaxMemoryLimit
		requestRatio = scalingConfig.MemoryRequestRatio
	default:
		return types.Recommendation{
			ProposedLimit:    analysis.CurrentLimit,
			ProposedRequest:  analysis.CurrentRequest,
			Confidence:       0,
			AdjustmentReason: "unknown resource type",
		}
	}

	targetUsage := percentile(
		[]float64{analysis.Percentile95, analysis.Percentile99},
		percentileThreshold,
	)

	headroom := targetUsage * 0.25
	proposedLimit := targetUsage + headroom

	if proposedLimit < minLimit {
		proposedLimit = minLimit
	}
	if proposedLimit > maxLimit {
		proposedLimit = maxLimit
	}

	proposedRequest := proposedLimit * requestRatio
	if proposedRequest < minLimit*requestRatio {
		proposedRequest = minLimit * requestRatio
	}

	maxAdjustment := analysis.CurrentLimit * scalingConfig.MaxAdjustmentPercent
	if proposedLimit > analysis.CurrentLimit+maxAdjustment {
		proposedLimit = analysis.CurrentLimit + maxAdjustment
	}
	if proposedLimit < analysis.CurrentLimit-maxAdjustment {
		proposedLimit = analysis.CurrentLimit - maxAdjustment
	}

	confidence := calculateConfidence(
		analysis,
		proposedLimit,
		analysis.CurrentLimit,
		scalingConfig,
	)

	reason := generateReason(
		analysis,
		proposedLimit,
		scalingConfig,
		resourceType,
	)

	return types.Recommendation{
		ProposedLimit:    proposedLimit,
		ProposedRequest:  proposedRequest,
		Confidence:       confidence,
		AdjustmentReason: reason,
	}
}

func calculateConfidence(
	analysis types.ResourceAnalysis,
	proposedLimit float64,
	currentLimit float64,
	scalingConfig config.ScalingConfig,
) float64 {
	baseConfidence := 0.5

	if analysis.UtilizationRatio > scalingConfig.UtilizationHighThreshold {
		baseConfidence += 0.2
	} else if analysis.UtilizationRatio < scalingConfig.UtilizationLowThreshold {
		baseConfidence += 0.15
	}

	r2 := analysis.RegressionModel.R2
	baseConfidence += r2 * 0.2

	changeRatio := math.Abs(proposedLimit-currentLimit) / currentLimit
	if changeRatio < 0.1 {
		baseConfidence += 0.1
	}

	if analysis.Volatility < 0.5 {
		baseConfidence += 0.1
	}

	if baseConfidence > 1.0 {
		baseConfidence = 1.0
	}
	if baseConfidence < 0.0 {
		baseConfidence = 0.0
	}

	return baseConfidence
}

func generateReason(
	analysis types.ResourceAnalysis,
	proposedLimit float64,
	scalingConfig config.ScalingConfig,
	resourceType string,
) string {
	var reason string

	if analysis.UtilizationRatio > scalingConfig.UtilizationHighThreshold {
		reason = fmt.Sprintf(
			"High utilization detected (%.2f%%), scaling up to prevent resource contention",
			analysis.UtilizationRatio*100,
		)
	} else if analysis.UtilizationRatio < scalingConfig.UtilizationLowThreshold {
		reason = fmt.Sprintf(
			"Low utilization detected (%.2f%%), scaling down to optimize resource usage",
			analysis.UtilizationRatio*100,
		)
	} else {
		reason = "Optimizing resource allocation based on historical usage patterns"
	}

	if analysis.Trend > 0.1 {
		reason += "; increasing trend detected"
	} else if analysis.Trend < -0.1 {
		reason += "; decreasing trend detected"
	}

	return reason
}

func percentile(sorted []float64, p float64) float64 {
	if len(sorted) == 0 {
		return 0
	}

	rank := p / 100.0 * float64(len(sorted)-1)
	lower := int(math.Floor(rank))
	upper := int(math.Ceil(rank))

	if lower == upper {
		return sorted[lower]
	}

	frac := rank - float64(lower)
	return sorted[lower]*(1-frac) + sorted[upper]*frac
}

func mean(values []float64) float64 {
	if len(values) == 0 {
		return 0
	}

	sum := 0.0
	for _, v := range values {
		sum += v
	}
	return sum / float64(len(values))
}

func stdDev(values []float64, mean float64) float64 {
	if len(values) == 0 {
		return 0
	}

	sumSquared := 0.0
	for _, v := range values {
		diff := v - mean
		sumSquared += diff * diff
	}
	return math.Sqrt(sumSquared / float64(len(values)))
}

func calculateTrend(ts types.TimeSeriesData) float64 {
	n := len(ts.Values)
	if n < 2 {
		return 0
	}

	half := n / 2
	firstHalf := mean(ts.Values[:half])
	secondHalf := mean(ts.Values[half:])

	if firstHalf == 0 {
		return 0
	}

	return (secondHalf - firstHalf) / firstHalf
}

func linearRegression(ts types.TimeSeriesData) types.RegressionResult {
	n := len(ts.Values)
	if n < 2 {
		return types.RegressionResult{}
	}

	x := make([]float64, n)
	for i := range x {
		x[i] = float64(i)
	}

	sumX := 0.0
	sumY := 0.0
	sumXY := 0.0
	sumX2 := 0.0

	for i := 0; i < n; i++ {
		sumX += x[i]
		sumY += ts.Values[i]
		sumXY += x[i] * ts.Values[i]
		sumX2 += x[i] * x[i]
	}

	denominator := float64(n)*sumX2 - sumX*sumX
	if denominator == 0 {
		return types.RegressionResult{}
	}

	slope := (float64(n)*sumXY - sumX*sumY) / denominator
	intercept := (sumY - slope*sumX) / float64(n)

	ssTotal := 0.0
	ssResidual := 0.0
	meanY := sumY / float64(n)

	for i := 0; i < n; i++ {
		predicted := slope*x[i] + intercept
		residual := ts.Values[i] - predicted
		ssResidual += residual * residual
		ssTotal += (ts.Values[i] - meanY) * (ts.Values[i] - meanY)
	}

	r2 := 0.0
	if ssTotal > 0 {
		r2 = 1 - ssTotal/ssResidual
	}

	return types.RegressionResult{
		Slope:      slope,
		Intercept:  intercept,
		R2:         r2,
		Confidence: math.Abs(r2),
	}
}

func (a *ResourceAnalyzer) MovingAverage(ts types.TimeSeriesData, window int) types.TimeSeriesData {
	if window <= 0 || window > len(ts.Values) {
		window = a.config.MovingAverageWindow
	}

	result := types.TimeSeriesData{
		Timestamps: make([]time.Time, 0),
		Values:     make([]float64, 0),
	}

	for i := window - 1; i < len(ts.Values); i++ {
		windowValues := ts.Values[i-window+1 : i+1]
		avg := mean(windowValues)
		result.Values = append(result.Values, avg)
		result.Timestamps = append(result.Timestamps, ts.Timestamps[i])
	}

	return result
}

func (a *ResourceAnalyzer) DetectAnomalies(ts types.TimeSeriesData) []int {
	anomalies := make([]int, 0)

	if len(ts.Values) < 3 {
		return anomalies
	}

	m := mean(ts.Values)
	s := stdDev(ts.Values, m)
	threshold := m + 3*s

	for i, v := range ts.Values {
		if v > threshold {
			anomalies = append(anomalies, i)
		}
	}

	return anomalies
}
