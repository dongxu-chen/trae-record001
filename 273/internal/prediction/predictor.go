package prediction

import (
	"context"
	"math"
	"sort"
	"time"
)

type LoadPredictor struct {
	historicalData []LoadDataPoint
	windowSize     int
}

type LoadDataPoint struct {
	Timestamp     time.Time
	RunningTasks  int
	QueuedTasks   int
	AvgDurationMs int64
}

type PredictionResult struct {
	TimePoint         time.Time
	PredictedLoad     float64
	PredictedRunning  float64
	PredictedQueued   float64
	Confidence        float64
	Trend             string
	WarningLevel      string
	Recommendation    string
}

func NewLoadPredictor(windowSize int) *LoadPredictor {
	if windowSize <= 0 {
		windowSize = 100
	}
	return &LoadPredictor{
		windowSize: windowSize,
	}
}

func (p *LoadPredictor) AddDataPoint(point LoadDataPoint) {
	p.historicalData = append(p.historicalData, point)
	if len(p.historicalData) > p.windowSize {
		p.historicalData = p.historicalData[len(p.historicalData)-p.windowSize:]
	}
}

func (p *LoadPredictor) BatchAddDataPoints(points []LoadDataPoint) {
	p.historicalData = append(p.historicalData, points...)
	if len(p.historicalData) > p.windowSize {
		p.historicalData = p.historicalData[len(p.historicalData)-p.windowSize:]
	}
}

func (p *LoadPredictor) PredictNextHours(hours int) []PredictionResult {
	if len(p.historicalData) < 10 {
		return p.generateInsufficientDataPrediction(hours)
	}

	sortedData := make([]LoadDataPoint, len(p.historicalData))
	copy(sortedData, p.historicalData)
	sort.Slice(sortedData, func(i, j int) bool {
		return sortedData[i].Timestamp.Before(sortedData[j].Timestamp)
	})

	hourlyStats := p.calculateHourlyPatterns(sortedData)

	var predictions []PredictionResult
	now := time.Now()

	for i := 1; i <= hours; i++ {
		targetTime := now.Add(time.Duration(i) * time.Hour)
		pred := p.predictForHour(targetTime, sortedData, hourlyStats)
		predictions = append(predictions, pred)
	}

	return predictions
}

type HourlyStats struct {
	Hour             int
	AvgRunningTasks  float64
	AvgQueuedTasks   float64
	AvgDuration      float64
	SampleCount      int
	PeakRunningTasks float64
}

func (p *LoadPredictor) calculateHourlyPatterns(data []LoadDataPoint) map[int]*HourlyStats {
	hourlyMap := make(map[int]*HourlyStats)

	for _, point := range data {
		hour := point.Timestamp.Hour()
		if _, ok := hourlyMap[hour]; !ok {
			hourlyMap[hour] = &HourlyStats{Hour: hour}
		}
		stats := hourlyMap[hour]
		stats.AvgRunningTasks += float64(point.RunningTasks)
		stats.AvgQueuedTasks += float64(point.QueuedTasks)
		stats.AvgDuration += float64(point.AvgDurationMs)
		stats.SampleCount++
		if float64(point.RunningTasks) > stats.PeakRunningTasks {
			stats.PeakRunningTasks = float64(point.RunningTasks)
		}
	}

	for _, stats := range hourlyMap {
		if stats.SampleCount > 0 {
			stats.AvgRunningTasks /= float64(stats.SampleCount)
			stats.AvgQueuedTasks /= float64(stats.SampleCount)
			stats.AvgDuration /= float64(stats.SampleCount)
		}
	}

	return hourlyMap
}

func (p *LoadPredictor) predictForHour(targetTime time.Time, data []LoadDataPoint, hourlyStats map[int]*HourlyStats) PredictionResult {
	hour := targetTime.Hour()
	weekday := targetTime.Weekday()

	hourStats, hasHourStats := hourlyStats[hour]

	var basePrediction float64
	var predictedRunning, predictedQueued float64
	var confidence float64

	if hasHourStats && hourStats.SampleCount >= 3 {
		basePrediction = hourStats.AvgRunningTasks + hourStats.AvgQueuedTasks
		predictedRunning = hourStats.AvgRunningTasks
		predictedQueued = hourStats.AvgQueuedTasks
		confidence = math.Min(0.5+float64(hourStats.SampleCount)*0.05, 0.95)
	} else {
		globalAvg := p.calculateGlobalAverage(data)
		basePrediction = globalAvg
		predictedRunning = globalAvg * 0.7
		predictedQueued = globalAvg * 0.3
		confidence = 0.5
	}

	weekdayFactor := p.getWeekdayFactor(weekday)
	basePrediction *= weekdayFactor
	predictedRunning *= weekdayFactor
	predictedQueued *= weekdayFactor

	trend := p.calculateTrend(data)
	if trend > 0.1 {
		basePrediction *= 1.2
		predictedRunning *= 1.2
		predictedQueued *= 1.2
	} else if trend < -0.1 {
		basePrediction *= 0.85
		predictedRunning *= 0.85
		predictedQueued *= 0.85
	}

	warningLevel := "normal"
	recommendation := "系统负载正常"

	if basePrediction > 80 {
		warningLevel = "critical"
		recommendation = "负载预计将达到临界值，建议提前扩容或推迟非关键任务"
	} else if basePrediction > 60 {
		warningLevel = "warning"
		recommendation = "负载预计将升高，建议关注系统资源使用情况"
	}

	trendStr := "stable"
	if trend > 0.1 {
		trendStr = "rising"
	} else if trend < -0.1 {
		trendStr = "falling"
	}

	return PredictionResult{
		TimePoint:         targetTime,
		PredictedLoad:     math.Round(basePrediction*100) / 100,
		PredictedRunning:  math.Round(predictedRunning*100) / 100,
		PredictedQueued:   math.Round(predictedQueued*100) / 100,
		Confidence:        math.Round(confidence*100) / 100,
		Trend:             trendStr,
		WarningLevel:      warningLevel,
		Recommendation:    recommendation,
	}
}

func (p *LoadPredictor) calculateGlobalAverage(data []LoadDataPoint) float64 {
	if len(data) == 0 {
		return 0
	}
	var sum float64
	for _, d := range data {
		sum += float64(d.RunningTasks + d.QueuedTasks)
	}
	return sum / float64(len(data))
}

func (p *LoadPredictor) getWeekdayFactor(weekday time.Weekday) float64 {
	switch weekday {
	case time.Saturday, time.Sunday:
		return 0.6
	case time.Monday:
		return 1.3
	case time.Friday:
		return 0.9
	default:
		return 1.0
	}
}

func (p *LoadPredictor) calculateTrend(data []LoadDataPoint) float64 {
	if len(data) < 10 {
		return 0
	}

	recentData := data
	if len(data) > 20 {
		recentData = data[len(data)-20:]
	}

	n := len(recentData)
	var sumX, sumY, sumXY, sumX2 float64

	for i := 0; i < n; i++ {
		x := float64(i)
		y := float64(recentData[i].RunningTasks + recentData[i].QueuedTasks)
		sumX += x
		sumY += y
		sumXY += x * y
		sumX2 += x * x
	}

	slope := (float64(n)*sumXY - sumX*sumY) / (float64(n)*sumX2 - sumX*sumX)
	return slope
}

func (p *LoadPredictor) generateInsufficientDataPrediction(hours int) []PredictionResult {
	var predictions []PredictionResult
	now := time.Now()

	for i := 1; i <= hours; i++ {
		predictions = append(predictions, PredictionResult{
			TimePoint:      now.Add(time.Duration(i) * time.Hour),
			PredictedLoad:  0,
			Confidence:     0,
			Trend:          "unknown",
			WarningLevel:   "normal",
			Recommendation: "历史数据不足，无法进行准确预测",
		})
	}
	return predictions
}

func (p *LoadPredictor) GetPeakPrediction(hours int) (PredictionResult, int) {
	predictions := p.PredictNextHours(hours)
	if len(predictions) == 0 {
		return PredictionResult{}, 0
	}

	maxLoad := predictions[0]
	maxIndex := 0

	for i, p := range predictions {
		if p.PredictedLoad > maxLoad.PredictedLoad {
			maxLoad = p
			maxIndex = i
		}
	}

	return maxLoad, maxIndex + 1
}

func (p *LoadPredictor) PredictTaskCompletion(taskCount int, avgDurationMs int64, parallelism int) time.Duration {
	if parallelism <= 0 {
		parallelism = 10
	}

	activeTasks := len(p.historicalData)
	if activeTasks > 0 {
		parallelism = int(math.Max(float64(parallelism)*0.7, float64(parallelism-activeTasks)))
	}

	batches := (taskCount + parallelism - 1) / parallelism
	totalDuration := time.Duration(batches) * time.Duration(avgDurationMs) * time.Millisecond

	return totalDuration
}

func (p *LoadPredictor) GetCurrentLoad() map[string]interface{} {
	if len(p.historicalData) == 0 {
		return map[string]interface{}{
			"running_tasks": 0,
			"queued_tasks":  0,
			"avg_duration":  0,
		}
	}

	latest := p.historicalData[len(p.historicalData)-1]
	trend := p.calculateTrend(p.historicalData)

	trendStr := "stable"
	if trend > 0.1 {
		trendStr = "rising"
	} else if trend < -0.1 {
		trendStr = "falling"
	}

	return map[string]interface{}{
		"running_tasks": latest.RunningTasks,
		"queued_tasks":  latest.QueuedTasks,
		"avg_duration":  latest.AvgDurationMs,
		"trend":         trendStr,
		"trend_value":   math.Round(trend*100) / 100,
	}
}

func ConvertDBData(dbData []map[string]interface{}) []LoadDataPoint {
	var points []LoadDataPoint
	for _, d := range dbData {
		point := LoadDataPoint{
			Timestamp:     d["timestamp"].(time.Time),
			RunningTasks:  d["running_tasks"].(int),
			QueuedTasks:   d["queued_tasks"].(int),
			AvgDurationMs: d["avg_duration_ms"].(int64),
		}
		points = append(points, point)
	}
	return points
}
