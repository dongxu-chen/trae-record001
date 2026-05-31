package injection

import (
	"fmt"
	"math"
	"math/rand"
	"time"

	"anomaly-detector/detector"
	"anomaly-detector/model"
)

type Injector struct {
	detectionConfig model.DetectionConfig
}

func NewInjector(detectionConfig model.DetectionConfig) *Injector {
	return &Injector{
		detectionConfig: detectionConfig,
	}
}

func (inj *Injector) Inject(series model.TimeSeries, config model.InjectionConfig) model.InjectionResult {
	data := make([]float64, len(series.Points))
	for i, p := range series.Points {
		data[i] = p.Value
	}

	originalData := make([]float64, len(data))
	copy(originalData, data)

	injectedData := make([]float64, len(data))
	copy(injectedData, data)

	startIdx := config.StartIndex
	if startIdx < 0 || startIdx >= len(data) {
		startIdx = len(data) / 2
	}

	duration := config.Duration
	if duration <= 0 {
		duration = 5
	}
	if startIdx+duration > len(data) {
		duration = len(data) - startIdx
	}

	magnitude := config.Magnitude
	if magnitude == 0 {
		dataStd := stdDev(data)
		if dataStd == 0 {
			dataStd = 1
		}
		magnitude = dataStd * 3
	}

	injectedData = inj.applyInjection(injectedData, config.Type, startIdx, duration, magnitude)

	injectedPoints := make([]model.TimeSeriesPoint, len(series.Points))
	for i, p := range series.Points {
		injectedPoints[i] = model.TimeSeriesPoint{
			Timestamp: p.Timestamp,
			Value:     injectedData[i],
		}
	}

	injectedSeries := model.TimeSeries{
		Name:   series.Name + "_injected",
		Labels: series.Labels,
		Points: injectedPoints,
	}

	det := detector.NewDetector(inj.detectionConfig)
	detectedAnomalies := det.Detect(injectedSeries)

	detectionMap := make(map[int]bool)
	for _, a := range detectedAnomalies {
		for idx := startIdx; idx < startIdx+duration; idx++ {
			if a.Timestamp.Equal(series.Points[idx].Timestamp) {
				detectionMap[idx] = true
				break
			}
		}
	}

	injectedCount := duration
	detectedCount := len(detectionMap)

	sensitivity := 0.0
	if injectedCount > 0 {
		sensitivity = float64(detectedCount) / float64(injectedCount)
	}

	detectionDelay := 0
	if detectedCount > 0 {
		for i := startIdx; i < startIdx+duration; i++ {
			if detectionMap[i] {
				detectionDelay = i - startIdx
				break
			}
		}
	}

	falsePositiveCount := 0
	for _, a := range detectedAnomalies {
		isInjected := false
		for idx := startIdx; idx < startIdx+duration; idx++ {
			if idx < len(series.Points) && a.Timestamp.Equal(series.Points[idx].Timestamp) {
				isInjected = true
				break
			}
		}
		if !isInjected {
			falsePositiveCount++
		}
	}

	falsePositiveRate := 0.0
	totalNonInjected := len(data) - injectedCount
	if totalNonInjected > 0 {
		falsePositiveRate = float64(falsePositiveCount) / float64(totalNonInjected)
	}

	var details []model.DetectionDetail
	stlResult := detector.STLDecompose(injectedData, inj.getPeriod(len(injectedData)), 3)
	expected := make([]float64, len(injectedData))
	for i := range injectedData {
		expected[i] = stlResult.Trend[i] + stlResult.Seasonal[i]
	}

	for i := startIdx; i < startIdx+duration && i < len(injectedData); i++ {
		deviation := 0.0
		if expected[i] != 0 {
			deviation = (injectedData[i] - expected[i]) / math.Abs(expected[i]) * 100
		}
		score := 0.0
		if std := stdDev(stlResult.Remainder); std > 0 {
			score = math.Abs(injectedData[i]-expected[i]) / (1.4826 * mad(stlResult.Remainder))
		}

		details = append(details, model.DetectionDetail{
			Index:    i,
			Detected: detectionMap[i],
			Expected: expected[i],
			Actual:   injectedData[i],
			Score:    score,
		})
	}

	return model.InjectionResult{
		InjectedMetric:   series.Name,
		InjectionType:    config.Type,
		OriginalSeries:   originalData[startIdx : startIdx+duration],
		InjectedSeries:   injectedData[startIdx : startIdx+duration],
		DetectedCount:    detectedCount,
		InjectedCount:    injectedCount,
		Sensitivity:      sensitivity,
		DetectionDelay:   detectionDelay,
		FalsePositiveRate: falsePositiveRate,
		DetectionDetails: details,
	}
}

func (inj *Injector) RunDrill(
	series []model.TimeSeries,
	configs []model.InjectionConfig,
) []model.InjectionResult {
	var results []model.InjectionResult

	for _, cfg := range configs {
		var targetSeries model.TimeSeries
		found := false
		for _, ts := range series {
			if ts.Name == cfg.Metric {
				targetSeries = ts
				found = true
				break
			}
		}

		if !found {
			if len(series) > 0 {
				targetSeries = series[0]
			} else {
				continue
			}
		}

		result := inj.Inject(targetSeries, cfg)
		results = append(results, result)
	}

	return results
}

func (inj *Injector) GenerateDrillConfigs(series []model.TimeSeries) []model.InjectionConfig {
	var configs []model.InjectionConfig

	types := []model.InjectionType{
		model.InjectionSpike,
		model.InjectionDrop,
		model.InjectionGradual,
		model.InjectionOscillation,
	}

	for _, ts := range series {
		n := len(ts.Points)
		if n < 20 {
			continue
		}

		startIdx := n / 2

		for _, injType := range types {
			configs = append(configs, model.InjectionConfig{
				Metric:     ts.Name,
				Type:       injType,
				Magnitude:  0,
				StartIndex: startIdx + rand.Intn(n/6),
				Duration:   3 + rand.Intn(8),
			})
		}
	}

	return configs
}

func (inj *Injector) ComputeDrillSummary(results []model.InjectionResult) map[string]interface{} {
	if len(results) == 0 {
		return map[string]interface{}{
			"total_tests": 0,
			"summary":     "无演练结果",
		}
	}

	totalTests := len(results)
	totalSensitivity := 0.0
	totalFPR := 0.0
	totalDelay := 0
	detectedTests := 0

	byType := make(map[string]struct {
		count       int
		sensitivity float64
		fpr         float64
		delay       int
		detected    int
	})

	for _, r := range results {
		totalSensitivity += r.Sensitivity
		totalFPR += r.FalsePositiveRate
		totalDelay += r.DetectionDelay
		if r.Sensitivity > 0 {
			detectedTests++
		}

		typeKey := string(r.InjectionType)
		entry, ok := byType[typeKey]
		if !ok {
			entry = struct {
				count       int
				sensitivity float64
				fpr         float64
				delay       int
				detected    int
			}{}
		}
		entry.count++
		entry.sensitivity += r.Sensitivity
		entry.fpr += r.FalsePositiveRate
		entry.delay += r.DetectionDelay
		if r.Sensitivity > 0 {
			entry.detected++
		}
		byType[typeKey] = entry
	}

	avgSensitivity := totalSensitivity / float64(totalTests)
	avgFPR := totalFPR / float64(totalTests)
	avgDelay := 0
	if detectedTests > 0 {
		avgDelay = totalDelay / detectedTests
	}

	typeBreakdown := make(map[string]map[string]interface{})
	for k, v := range byType {
		typeBreakdown[k] = map[string]interface{}{
			"count":             v.count,
			"avg_sensitivity":   v.sensitivity / float64(v.count),
			"avg_false_positive": v.fpr / float64(v.count),
			"avg_delay":         v.delay / maxInt(v.detected, 1),
			"detection_rate":    float64(v.detected) / float64(v.count),
		}
	}

	grade := "优秀"
	if avgSensitivity >= 0.9 && avgFPR <= 0.05 {
		grade = "优秀"
	} else if avgSensitivity >= 0.7 && avgFPR <= 0.1 {
		grade = "良好"
	} else if avgSensitivity >= 0.5 {
		grade = "一般"
	} else {
		grade = "需改进"
	}

	return map[string]interface{}{
		"total_tests":      totalTests,
		"detection_rate":   float64(detectedTests) / float64(totalTests),
		"avg_sensitivity":  avgSensitivity,
		"avg_false_positive_rate": avgFPR,
		"avg_detection_delay":     avgDelay,
		"grade":            grade,
		"by_type":          typeBreakdown,
		"summary": fmt.Sprintf("共%d项测试，平均灵敏度%.1f%%，平均误报率%.1f%%，评级: %s",
			totalTests, avgSensitivity*100, avgFPR*100, grade),
	}
}

func (inj *Injector) applyInjection(
	data []float64,
	injType model.InjectionType,
	startIdx, duration int,
	magnitude float64,
) []float64 {
	result := make([]float64, len(data))
	copy(result, data)

	switch injType {
	case model.InjectionSpike:
		for i := startIdx; i < startIdx+duration && i < len(result); i++ {
			result[i] += magnitude
		}

	case model.InjectionDrop:
		for i := startIdx; i < startIdx+duration && i < len(result); i++ {
			result[i] -= magnitude
			if result[i] < 0 {
				result[i] = 0
			}
		}

	case model.InjectionGradual:
		for i := startIdx; i < startIdx+duration && i < len(result); i++ {
			progress := float64(i-startIdx) / float64(duration)
			result[i] += magnitude * progress
		}

	case model.InjectionOscillation:
		for i := startIdx; i < startIdx+duration && i < len(result); i++ {
			phase := float64(i-startIdx) * math.Pi / 2.0
			result[i] += magnitude * math.Sin(phase) * (0.5 + 0.5*rand.Float64())
		}
	}

	return result
}

func (inj *Injector) getPeriod(dataLen int) int {
	if inj.detectionConfig.Period > 0 {
		return inj.detectionConfig.Period
	}
	p := dataLen / 10
	if p < 2 {
		p = 2
	}
	return p
}

func stdDev(data []float64) float64 {
	if len(data) < 2 {
		return 0
	}
	m := mean(data)
	sum := 0.0
	for _, v := range data {
		d := v - m
		sum += d * d
	}
	return math.Sqrt(sum / float64(len(data)-1))
}

func mean(data []float64) float64 {
	if len(data) == 0 {
		return 0
	}
	sum := 0.0
	for _, v := range data {
		sum += v
	}
	return sum / float64(len(data))
}

func mad(data []float64) float64 {
	if len(data) == 0 {
		return 0
	}
	m := median(data)
	sum := 0.0
	for _, v := range data {
		sum += math.Abs(v - m)
	}
	return sum / float64(len(data))
}

func median(data []float64) float64 {
	if len(data) == 0 {
		return 0
	}
	sorted := make([]float64, len(data))
	copy(sorted, data)
	n := len(sorted)
	for i := 0; i < n-1; i++ {
		for j := i + 1; j < n; j++ {
			if sorted[i] > sorted[j] {
				sorted[i], sorted[j] = sorted[j], sorted[i]
			}
		}
	}
	if n%2 == 0 {
		return (sorted[n/2-1] + sorted[n/2]) / 2
	}
	return sorted[n/2]
}

func maxInt(a, b int) int {
	if a > b {
		return a
	}
	return b
}
