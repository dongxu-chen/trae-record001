package predictor

import (
	"context"
	"math"
	"sort"
	"sync"
	"time"
)

type TrafficDataPoint struct {
	Timestamp    time.Time
	QueueName    string
	Vhost        string
	PublishRate  float64
	DeliverRate  float64
	MessageCount int64
}

type PredictionResult struct {
	QueueName         string
	Vhost             string
	PredictedMessages float64
	PredictedPublish  float64
	PredictedDeliver  float64
	Confidence        float64
	Trend             string
	Timestamp         time.Time
}

type BurstInfo struct {
	QueueName       string
	Vhost           string
	IsBursting      bool
	BurstStart      time.Time
	BurstDuration   time.Duration
	BurstMagnitude  float64
	NormalBaseline  float64
	CurrentRate     float64
}

type TimeSeriesPredictor struct {
	mu                   sync.RWMutex
	history              map[string][]TrafficDataPoint
	maxDataPoints        int
	collectionInterval   time.Duration
	burstDetectionWindow int
	burstThreshold       float64
	burstQueues          map[string]BurstInfo
}

func NewTimeSeriesPredictor(maxDataPoints int, collectionInterval time.Duration) *TimeSeriesPredictor {
	return &TimeSeriesPredictor{
		history:              make(map[string][]TrafficDataPoint),
		maxDataPoints:        maxDataPoints,
		collectionInterval:   collectionInterval,
		burstDetectionWindow: 10,
		burstThreshold:       3.0,
		burstQueues:          make(map[string]BurstInfo),
	}
}

func (p *TimeSeriesPredictor) SetBurstThreshold(threshold float64) {
	p.mu.Lock()
	defer p.mu.Unlock()
	p.burstThreshold = threshold
}

func (p *TimeSeriesPredictor) SetBurstDetectionWindow(window int) {
	p.mu.Lock()
	defer p.mu.Unlock()
	p.burstDetectionWindow = window
}

func (p *TimeSeriesPredictor) Record(data TrafficDataPoint) {
	p.mu.Lock()
	defer p.mu.Unlock()

	key := data.Vhost + ":" + data.QueueName

	p.history[key] = append(p.history[key], data)

	if len(p.history[key]) > p.maxDataPoints {
		p.history[key] = p.history[key][len(p.history[key])-p.maxDataPoints:]
	}

	p.detectBurst(key)
}

func (p *TimeSeriesPredictor) detectBurst(key string) {
	data := p.history[key]
	if len(data) < p.burstDetectionWindow {
		return
	}

	recentData := data[max(0, len(data)-p.burstDetectionWindow):]

	var baselineSum float64
	baselineCount := 0
	windowSize := min(p.burstDetectionWindow, 5)

	for i := 0; i < len(recentData)-windowSize; i++ {
		baselineSum += recentData[i].PublishRate
		baselineCount++
	}

	baseline := 0.0
	if baselineCount > 0 {
		baseline = baselineSum / float64(baselineCount)
	}

	currentRate := recentData[len(recentData)-1].PublishRate

	burstInfo := BurstInfo{
		QueueName:      data[0].QueueName,
		Vhost:          data[0].Vhost,
		NormalBaseline: baseline,
		CurrentRate:    currentRate,
	}

	if baseline > 0 && currentRate > baseline*p.burstThreshold {
		existing, exists := p.burstQueues[key]
		if exists {
			burstInfo.IsBursting = true
			burstInfo.BurstStart = existing.BurstStart
			burstInfo.BurstDuration = time.Since(existing.BurstStart)
			burstInfo.BurstMagnitude = currentRate / baseline
		} else {
			burstInfo.IsBursting = true
			burstInfo.BurstStart = time.Now()
			burstInfo.BurstDuration = 0
			burstInfo.BurstMagnitude = currentRate / baseline
		}
		p.burstQueues[key] = burstInfo
	} else {
		if existing, exists := p.burstQueues[key]; exists && existing.IsBursting {
			burstInfo.IsBursting = false
			burstInfo.BurstStart = existing.BurstStart
			burstInfo.BurstDuration = time.Since(existing.BurstStart)
			burstInfo.BurstMagnitude = existing.BurstMagnitude
			p.burstQueues[key] = burstInfo
		}
	}
}

func (p *TimeSeriesPredictor) IsBursting(queueName, vhost string) bool {
	p.mu.RLock()
	defer p.mu.RUnlock()

	key := vhost + ":" + queueName
	info, exists := p.burstQueues[key]
	return exists && info.IsBursting
}

func (p *TimeSeriesPredictor) GetBurstInfo(queueName, vhost string) (BurstInfo, bool) {
	p.mu.RLock()
	defer p.mu.RUnlock()

	key := vhost + ":" + queueName
	info, exists := p.burstQueues[key]
	return info, exists
}

func (p *TimeSeriesPredictor) GetAllBurstQueues() map[string]BurstInfo {
	p.mu.RLock()
	defer p.mu.RUnlock()

	result := make(map[string]BurstInfo)
	for k, v := range p.burstQueues {
		if v.IsBursting {
			result[k] = v
		}
	}
	return result
}

func (p *TimeSeriesPredictor) GetBurstQueueNames() map[string]bool {
	p.mu.RLock()
	defer p.mu.RUnlock()

	result := make(map[string]bool)
	for k, v := range p.burstQueues {
		if v.IsBursting {
			result[k] = true
		}
	}
	return result
}

func (p *TimeSeriesPredictor) Predict(queueName, vhost string, predictionWindow time.Duration) (*PredictionResult, bool) {
	p.mu.RLock()
	defer p.mu.RUnlock()

	key := vhost + ":" + queueName
	data, exists := p.history[key]
	if !exists || len(data) < 5 {
		return nil, false
	}

	n := len(data)
	x := make([]float64, n)
	yPublish := make([]float64, n)
	yDeliver := make([]float64, n)
	yMessages := make([]float64, n)

	for i, dp := range data {
		x[i] = float64(i)
		yPublish[i] = dp.PublishRate
		yDeliver[i] = dp.DeliverRate
		yMessages[i] = float64(dp.MessageCount)
	}

	publishSlope, publishIntercept := linearRegression(x, yPublish)
	deliverSlope, deliverIntercept := linearRegression(x, yDeliver)
	messagesSlope, messagesIntercept := linearRegression(x, yMessages)

	publishConfidence := calculateConfidence(x, yPublish, publishSlope, publishIntercept)
	deliverConfidence := calculateConfidence(x, yDeliver, deliverSlope, deliverIntercept)
	messagesConfidence := calculateConfidence(x, yMessages, messagesSlope, messagesIntercept)
	confidence := (publishConfidence + deliverConfidence + messagesConfidence) / 3

	steps := float64(predictionWindow / p.collectionInterval)
	futureX := float64(n) + steps

	predictedPublish := publishSlope*futureX + publishIntercept
	predictedDeliver := deliverSlope*futureX + deliverIntercept
	predictedMessages := messagesSlope*futureX + messagesIntercept

	if predictedPublish < 0 {
		predictedPublish = 0
	}
	if predictedDeliver < 0 {
		predictedDeliver = 0
	}
	if predictedMessages < 0 {
		predictedMessages = 0
	}

	trend := "stable"
	if messagesSlope > 0.1 {
		trend = "increasing"
	} else if messagesSlope < -0.1 {
		trend = "decreasing"
	}

	return &PredictionResult{
		QueueName:         queueName,
		Vhost:             vhost,
		PredictedMessages: predictedMessages,
		PredictedPublish:  predictedPublish,
		PredictedDeliver:  predictedDeliver,
		Confidence:        confidence,
		Trend:             trend,
		Timestamp:         time.Now(),
	}, true
}

func linearRegression(x, y []float64) (slope, intercept float64) {
	n := float64(len(x))

	var sumX, sumY, sumXY, sumXX float64
	for i := 0; i < len(x); i++ {
		sumX += x[i]
		sumY += y[i]
		sumXY += x[i] * y[i]
		sumXX += x[i] * x[i]
	}

	slope = (n*sumXY - sumX*sumY) / (n*sumXX - sumX*sumX)
	intercept = (sumY - slope*sumX) / n

	return slope, intercept
}

func calculateConfidence(x, y []float64, slope, intercept float64) float64 {
	if len(x) < 2 {
		return 0
	}

	var yMean float64
	for _, yi := range y {
		yMean += yi
	}
	yMean /= float64(len(y))

	var ssTotal, ssResidual float64
	for i := 0; i < len(x); i++ {
		predicted := slope*x[i] + intercept
		ssTotal += (y[i] - yMean) * (y[i] - yMean)
		ssResidual += (y[i] - predicted) * (y[i] - predicted)
	}

	if ssTotal == 0 {
		return 1.0
	}

	r2 := 1 - (ssResidual / ssTotal)
	if r2 < 0 {
		r2 = 0
	}
	return r2
}

func (p *TimeSeriesPredictor) GetHighLoadQueues(threshold float64) []PredictionResult {
	p.mu.RLock()
	defer p.mu.RUnlock()

	var results []PredictionResult

	for key := range p.history {
		last := p.history[key][len(p.history[key])-1]
		pred, ok := p.Predict(last.QueueName, last.Vhost, p.collectionInterval*10)
		if ok && pred.PredictedMessages > threshold && pred.Confidence > 0.5 {
			results = append(results, *pred)
		}
	}

	sort.Slice(results, func(i, j int) bool {
		return results[i].PredictedMessages > results[j].PredictedMessages
	})

	return results
}

func (p *TimeSeriesPredictor) StartCollector(ctx context.Context, collectFunc func() []TrafficDataPoint) {
	ticker := time.NewTicker(p.collectionInterval)
	defer ticker.Stop()

	for {
		select {
		case <-ctx.Done():
			return
		case <-ticker.C:
			dataPoints := collectFunc()
			for _, dp := range dataPoints {
				p.Record(dp)
			}
		}
	}
}

func (p *TimeSeriesPredictor) GetHistory(queueName, vhost string) []TrafficDataPoint {
	p.mu.RLock()
	defer p.mu.RUnlock()

	key := vhost + ":" + queueName
	history := make([]TrafficDataPoint, len(p.history[key]))
	copy(history, p.history[key])
	return history
}

func MovingAverage(data []float64, window int) []float64 {
	if len(data) < window {
		return nil
	}

	result := make([]float64, len(data)-window+1)
	for i := 0; i <= len(data)-window; i++ {
		sum := 0.0
		for j := 0; j < window; j++ {
			sum += data[i+j]
		}
		result[i] = sum / float64(window)
	}
	return result
}

func ExponentialSmoothing(data []float64, alpha float64) []float64 {
	if len(data) == 0 {
		return nil
	}

	result := make([]float64, len(data))
	result[0] = data[0]

	for i := 1; i < len(data); i++ {
		result[i] = alpha*data[i] + (1-alpha)*result[i-1]
	}

	return result
}

func CalculateSeasonality(data []float64, period int) []float64 {
	if len(data) < period*2 {
		return nil
	}

	seasonal := make([]float64, period)
	counts := make([]int, period)

	for i, val := range data {
		idx := i % period
		seasonal[idx] += val
		counts[idx]++
	}

	for i := range seasonal {
		if counts[i] > 0 {
			seasonal[i] /= float64(counts[i])
		}
	}

	return seasonal
}

func DetectAnomalies(data []float64, threshold float64) []int {
	if len(data) < 4 {
		return nil
	}

	mean := 0.0
	for _, v := range data {
		mean += v
	}
	mean /= float64(len(data))

	variance := 0.0
	for _, v := range data {
		variance += (v - mean) * (v - mean)
	}
	variance /= float64(len(data))
	std := math.Sqrt(variance)

	var anomalies []int
	for i, v := range data {
		zScore := math.Abs(v - mean)
		if std > 0 && zScore > threshold*std {
			anomalies = append(anomalies, i)
		}
	}

	return anomalies
}

func max(a, b int) int {
	if a > b {
		return a
	}
	return b
}

func min(a, b int) int {
	if a < b {
		return a
	}
	return b
}
