package prediction

import (
	"math"
	"sync"
	"time"
)

type MetricsDataPoint struct {
	Timestamp time.Time
	CPU       float64
	Memory    float64
}

type PredictionResult struct {
	Timestamp       time.Time
	PredictedCPU    float64
	PredictedMemory float64
	Confidence      float64
}

type TimeSeriesPredictor struct {
	history     []MetricsDataPoint
	maxHistory  int
	windowSize  int
	mu          sync.RWMutex
}

func NewTimeSeriesPredictor(maxHistory, windowSize int) *TimeSeriesPredictor {
	return &TimeSeriesPredictor{
		history:    make([]MetricsDataPoint, 0, maxHistory),
		maxHistory: maxHistory,
		windowSize: windowSize,
	}
}

func (p *TimeSeriesPredictor) AddDataPoint(cpu, memory float64) {
	p.mu.Lock()
	defer p.mu.Unlock()

	p.history = append(p.history, MetricsDataPoint{
		Timestamp: time.Now(),
		CPU:       cpu,
		Memory:    memory,
	})

	if len(p.history) > p.maxHistory {
		p.history = p.history[1:]
	}
}

func (p *TimeSeriesPredictor) Predict(stepsAhead int) []PredictionResult {
	p.mu.RLock()
	defer p.mu.RUnlock()

	if len(p.history) < p.windowSize {
		return nil
	}

	results := make([]PredictionResult, stepsAhead)
	lastTime := p.history[len(p.history)-1].Timestamp

	cpuTrend, cpuIntercept := p.linearRegressionCPU()
	memTrend, memIntercept := p.linearRegressionMemory()

	for i := 0; i < stepsAhead; i++ {
		t := float64(len(p.history) + i)
		predictedCPU := cpuTrend*t + cpuIntercept
		predictedMemory := memTrend*t + memIntercept

		predictedCPU = math.Max(0, math.Min(100, predictedCPU))
		predictedMemory = math.Max(0, math.Min(100, predictedMemory))

		confidence := p.calculateConfidence()

		results[i] = PredictionResult{
			Timestamp:       lastTime.Add(time.Duration(i+1) * time.Minute),
			PredictedCPU:    predictedCPU,
			PredictedMemory: predictedMemory,
			Confidence:      confidence,
		}
	}

	return results
}

func (p *TimeSeriesPredictor) linearRegressionCPU() (slope, intercept float64) {
	n := float64(len(p.history))
	var sumX, sumY, sumXY, sumX2 float64

	for i, dp := range p.history {
		x := float64(i)
		y := dp.CPU
		sumX += x
		sumY += y
		sumXY += x * y
		sumX2 += x * x
	}

	slope = (n*sumXY - sumX*sumY) / (n*sumX2 - sumX*sumX)
	intercept = (sumY - slope*sumX) / n
	return
}

func (p *TimeSeriesPredictor) linearRegressionMemory() (slope, intercept float64) {
	n := float64(len(p.history))
	var sumX, sumY, sumXY, sumX2 float64

	for i, dp := range p.history {
		x := float64(i)
		y := dp.Memory
		sumX += x
		sumY += y
		sumXY += x * y
		sumX2 += x * x
	}

	slope = (n*sumXY - sumX*sumY) / (n*sumX2 - sumX*sumX)
	intercept = (sumY - slope*sumX) / n
	return
}

func (p *TimeSeriesPredictor) calculateConfidence() float64 {
	historyRatio := float64(len(p.history)) / float64(p.maxHistory)
	return math.Min(1.0, historyRatio*0.8+0.2)
}

func (p *TimeSeriesPredictor) MovingAveragePredict(stepsAhead, period int) []PredictionResult {
	p.mu.RLock()
	defer p.mu.RUnlock()

	if len(p.history) < period {
		return nil
	}

	results := make([]PredictionResult, stepsAhead)
	lastTime := p.history[len(p.history)-1].Timestamp

	var cpuSum, memSum float64
	for i := len(p.history) - period; i < len(p.history); i++ {
		cpuSum += p.history[i].CPU
		memSum += p.history[i].Memory
	}

	avgCPU := cpuSum / float64(period)
	avgMemory := memSum / float64(period)

	for i := 0; i < stepsAhead; i++ {
		results[i] = PredictionResult{
			Timestamp:       lastTime.Add(time.Duration(i+1) * time.Minute),
			PredictedCPU:    avgCPU,
			PredictedMemory: avgMemory,
			Confidence:      p.calculateConfidence(),
		}
	}

	return results
}

func (p *TimeSeriesPredictor) GetHistory() []MetricsDataPoint {
	p.mu.RLock()
	defer p.mu.RUnlock()
	history := make([]MetricsDataPoint, len(p.history))
	copy(history, p.history)
	return history
}

func (p *TimeSeriesPredictor) IsReady() bool {
	p.mu.RLock()
	defer p.mu.RUnlock()
	return len(p.history) >= p.windowSize
}
