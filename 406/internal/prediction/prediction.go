package prediction

import (
	"math"
	"sync"
	"time"
	"health-check/internal/config"
	"health-check/internal/model"
)

type Predictor struct {
	cfg          *config.PredictionConfig
	history      map[string][]TimeSeriesPoint
	mu           sync.RWMutex
	lastPredictions map[string]*model.PredictionResult
}

type TimeSeriesPoint struct {
	Timestamp  time.Time
	Value      float64
	Latency    float64
	StatusCode int
}

type Algorithm string

const (
	AlgorithmMA      Algorithm = "ma"
	AlgorithmEMA     Algorithm = "ema"
	AlgorithmAR      Algorithm = "ar"
	AlgorithmLinear  Algorithm = "linear"
)

func NewPredictor(cfg *config.PredictionConfig) *Predictor {
	return &Predictor{
		cfg:              cfg,
		history:          make(map[string][]TimeSeriesPoint),
		lastPredictions:  make(map[string]*model.PredictionResult),
	}
}

func (p *Predictor) RecordResult(result *model.ProbeResult) {
	if !p.cfg.Enabled {
		return
	}

	p.mu.Lock()
	defer p.mu.Unlock()

	value := 0.0
	if result.Status == model.StatusUp {
		value = 100.0
	} else if result.Status == model.StatusDegrade {
		value = 50.0
	}

	point := TimeSeriesPoint{
		Timestamp:  result.Timestamp,
		Value:      value,
		Latency:    float64(result.Latency.Milliseconds()),
		StatusCode: result.HTTPStatus,
	}

	history := p.history[result.EndpointID]
	history = append(history, point)
	if len(history) > p.cfg.HistorySize {
		history = history[len(history)-p.cfg.HistorySize:]
	}
	p.history[result.EndpointID] = history
}

func (p *Predictor) Predict(endpointID string) *model.PredictionResult {
	if !p.cfg.Enabled {
		return nil
	}

	p.mu.RLock()
	defer p.mu.RUnlock()

	history, ok := p.history[endpointID]
	if !ok || len(history) < 10 {
		return nil
	}

	var predictedValue float64
	var trend model.TrendDirection
	var trendMagnitude float64
	var confidence float64

	algo := Algorithm(p.cfg.Algorithm)
	switch algo {
	case AlgorithmEMA:
		predictedValue, trend, trendMagnitude, confidence = p.predictEMA(history)
	case AlgorithmLinear:
		predictedValue, trend, trendMagnitude, confidence = p.predictLinear(history)
	case AlgorithmAR:
		predictedValue, trend, trendMagnitude, confidence = p.predictAR(history)
	default:
		predictedValue, trend, trendMagnitude, confidence = p.predictMA(history)
	}

	warning := predictedValue < p.cfg.WarningThreshold
	critical := predictedValue < p.cfg.CriticalThreshold

	message := ""
	if critical {
		message = "Critical: Predicted availability will drop significantly"
	} else if warning {
		message = "Warning: Predicted availability is declining"
	} else if trend == model.TrendDegrading {
		message = "Notice: Availability trend is degrading"
	} else if trend == model.TrendImproving {
		message = "Notice: Availability trend is improving"
	}

	result := &model.PredictionResult{
		EndpointID:     endpointID,
		Timestamp:      time.Now(),
		PredictedValue: predictedValue,
		TrendDirection: trend,
		TrendMagnitude: trendMagnitude,
		Confidence:     confidence,
		Warning:        warning,
		Critical:       critical,
		Message:        message,
	}

	p.lastPredictions[endpointID] = result

	return result
}

func (p *Predictor) predictMA(history []TimeSeriesPoint) (float64, model.TrendDirection, float64, float64) {
	n := len(history)
	window := p.cfg.PredictionWindow
	if window > n {
		window = n
	}

	var recentSum float64
	for i := n - window; i < n; i++ {
		recentSum += history[i].Value
	}
	recentAvg := recentSum / float64(window)

	var olderSum float64
	olderWindow := window
	if n-window < window {
		olderWindow = n - window
	}
	if olderWindow > 0 {
		for i := n - window - olderWindow; i < n-window; i++ {
			olderSum += history[i].Value
		}
		olderAvg := olderSum / float64(olderWindow)

		trendMagnitude := recentAvg - olderAvg
		trend := model.TrendStable
		if trendMagnitude > 5 {
			trend = model.TrendImproving
		} else if trendMagnitude < -5 {
			trend = model.TrendDegrading
		}

		confidence := 0.7 + (float64(n)/float64(p.cfg.HistorySize))*0.3
		return recentAvg, trend, trendMagnitude, confidence
	}

	return recentAvg, model.TrendStable, 0, 0.5
}

func (p *Predictor) predictEMA(history []TimeSeriesPoint) (float64, model.TrendDirection, float64, float64) {
	alpha := 2.0 / (float64(p.cfg.PredictionWindow) + 1)
	ema := history[0].Value

	for i := 1; i < len(history); i++ {
		ema = alpha*history[i].Value + (1-alpha)*ema
	}

	n := len(history)
	half := n / 2
	if half > 0 {
		oldEma := history[0].Value
		for i := 1; i < half; i++ {
			oldEma = alpha*history[i].Value + (1-alpha)*oldEma
		}

		trendMagnitude := ema - oldEma
		trend := model.TrendStable
		if trendMagnitude > 5 {
			trend = model.TrendImproving
		} else if trendMagnitude < -5 {
			trend = model.TrendDegrading
		}

		confidence := 0.75 + (float64(n)/float64(p.cfg.HistorySize))*0.25
		return ema, trend, trendMagnitude, confidence
	}

	return ema, model.TrendStable, 0, 0.6
}

func (p *Predictor) predictLinear(history []TimeSeriesPoint) (float64, model.TrendDirection, float64, float64) {
	n := float64(len(history))
	var sumX, sumY, sumXY, sumX2 float64

	for i, point := range history {
		x := float64(i)
		sumX += x
		sumY += point.Value
		sumXY += x * point.Value
		sumX2 += x * x
	}

	slope := (n*sumXY - sumX*sumY) / (n*sumX2 - sumX*sumX)
	intercept := (sumY - slope*sumX) / n

	predictedX := n
	predictedY := slope*predictedX + intercept

	trendMagnitude := slope * float64(p.cfg.PredictionWindow)
	trend := model.TrendStable
	if slope > 0.5 {
		trend = model.TrendImproving
	} else if slope < -0.5 {
		trend = model.TrendDegrading
	}

	var rSquared float64
	meanY := sumY / n
	var ssTotal, ssResidual float64
	for i, point := range history {
		yPred := slope*float64(i) + intercept
		ssTotal += (point.Value - meanY) * (point.Value - meanY)
		ssResidual += (point.Value - yPred) * (point.Value - yPred)
	}
	if ssTotal > 0 {
		rSquared = 1 - (ssResidual / ssTotal)
	}
	confidence := math.Max(0, math.Min(1, rSquared*0.7+0.3))

	return predictedY, trend, trendMagnitude, confidence
}

func (p *Predictor) predictAR(history []TimeSeriesPoint) (float64, model.TrendDirection, float64, float64) {
	n := len(history)
	order := 3
	if n < order+1 {
		return p.predictMA(history)
	}

	values := make([]float64, n)
	for i, p := range history {
		values[i] = p.Value
	}

	phi := make([]float64, order)
	for k := 0; k < order; k++ {
		var sumNum, sumDen float64
		for i := order; i < n; i++ {
			sumNum += values[i] * values[i-k-1]
			sumDen += values[i-k-1] * values[i-k-1]
		}
		if sumDen > 0 {
			phi[k] = sumNum / sumDen
		}
	}

	predicted := 0.0
	for k := 0; k < order; k++ {
		predicted += phi[k] * values[n-k-1]
	}

	if predicted < 0 {
		predicted = 0
	}
	if predicted > 100 {
		predicted = 100
	}

	window := 10
	if n < window {
		window = n
	}
	recentAvg := 0.0
	olderAvg := 0.0
	for i := 0; i < window; i++ {
		recentAvg += values[n-i-1]
		if n-window-i-1 >= 0 {
			olderAvg += values[n-window-i-1]
		}
	}
	recentAvg /= float64(window)
	olderAvg /= float64(window)

	trendMagnitude := recentAvg - olderAvg
	trend := model.TrendStable
	if trendMagnitude > 5 {
		trend = model.TrendImproving
	} else if trendMagnitude < -5 {
		trend = model.TrendDegrading
	}

	confidence := 0.65 + (float64(n)/float64(p.cfg.HistorySize))*0.35

	return predicted, trend, trendMagnitude, confidence
}

func (p *Predictor) PredictLatency(endpointID string) (float64, float64) {
	p.mu.RLock()
	defer p.mu.RUnlock()

	history, ok := p.history[endpointID]
	if !ok || len(history) < 5 {
		return 0, 0
	}

	n := len(history)
	window := 5
	if window > n {
		window = n
	}

	var sum float64
	for i := n - window; i < n; i++ {
		sum += history[i].Latency
	}
	avgLatency := sum / float64(window)

	var variance float64
	for i := n - window; i < n; i++ {
		diff := history[i].Latency - avgLatency
		variance += diff * diff
	}
	stdDev := math.Sqrt(variance / float64(window))

	return avgLatency, stdDev
}

func (p *Predictor) GetLastPrediction(endpointID string) *model.PredictionResult {
	p.mu.RLock()
	defer p.mu.RUnlock()

	return p.lastPredictions[endpointID]
}

func (p *Predictor) GetAllPredictions() map[string]*model.PredictionResult {
	p.mu.RLock()
	defer p.mu.RUnlock()

	result := make(map[string]*model.PredictionResult)
	for k, v := range p.lastPredictions {
		result[k] = v
	}
	return result
}

func (p *Predictor) GetHistory(endpointID string) []TimeSeriesPoint {
	p.mu.RLock()
	defer p.mu.RUnlock()

	history := p.history[endpointID]
	result := make([]TimeSeriesPoint, len(history))
	copy(result, history)
	return result
}

func (p *Predictor) PredictAll() map[string]*model.PredictionResult {
	results := make(map[string]*model.PredictionResult)

	p.mu.RLock()
	endpoints := make([]string, 0, len(p.history))
	for id := range p.history {
		endpoints = append(endpoints, id)
	}
	p.mu.RUnlock()

	for _, id := range endpoints {
		if pred := p.Predict(id); pred != nil {
			results[id] = pred
		}
	}

	return results
}

func (p *Predictor) DetectAnomalies(endpointID string) []string {
	history := p.GetHistory(endpointID)
	if len(history) < 10 {
		return nil
	}

	var anomalies []string
	avgLatency, stdDev := p.PredictLatency(endpointID)

	n := len(history)
	recent := history[n-1]

	if recent.Latency > avgLatency+2*stdDev {
		anomalies = append(anomalies, "High latency detected")
	}

	if recent.StatusCode >= 500 {
		anomalies = append(anomalies, "Server error detected")
	}

	successCount := 0
	checkWindow := 5
	if n < checkWindow {
		checkWindow = n
	}
	for i := n - checkWindow; i < n; i++ {
		if history[i].Value >= 100 {
			successCount++
		}
	}
	if successCount == 0 {
		anomalies = append(anomalies, "Consecutive failures detected")
	}

	return anomalies
}
