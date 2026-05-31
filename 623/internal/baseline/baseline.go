package baseline

import (
	"math"
	"sync"
	"time"
)

type DynamicBaseline struct {
	history        []BaselineSample
	windowSize     int
	mu             sync.RWMutex
	baselineValue  float64
	thresholdMultiplier float64
	lastUpdate     time.Time
}

type BaselineSample struct {
	Timestamp time.Time
	Value     float64
}

type ThresholdType string

const (
	ThresholdConnectionRate ThresholdType = "connection_rate"
	ThresholdSlowConnection ThresholdType = "slow_connection"
	ThresholdIdleTime       ThresholdType = "idle_time"
)

func NewDynamicBaseline(windowSize int, thresholdMultiplier float64) *DynamicBaseline {
	return &DynamicBaseline{
		history:            make([]BaselineSample, 0, windowSize),
		windowSize:         windowSize,
		thresholdMultiplier: thresholdMultiplier,
		lastUpdate:         time.Now(),
	}
}

func (b *DynamicBaseline) AddSample(value float64) {
	b.mu.Lock()
	defer b.mu.Unlock()

	sample := BaselineSample{
		Timestamp: time.Now(),
		Value:     value,
	}

	b.history = append(b.history, sample)

	if len(b.history) > b.windowSize {
		b.history = b.history[1:]
	}

	b.calculateBaseline()
}

func (b *DynamicBaseline) calculateBaseline() {
	if len(b.history) < 10 {
		return
	}

	values := make([]float64, len(b.history))
	for i, s := range b.history {
		values[i] = s.Value
	}

	mean := calculateMean(values)
	stdDev := calculateStdDev(values, mean)

	b.baselineValue = mean + (stdDev * b.thresholdMultiplier)
	b.lastUpdate = time.Now()
}

func (b *DynamicBaseline) GetThreshold() float64 {
	b.mu.RLock()
	defer b.mu.RUnlock()

	if b.baselineValue == 0 && len(b.history) > 0 {
		return b.history[len(b.history)-1].Value * b.thresholdMultiplier
	}

	return b.baselineValue
}

func (b *DynamicBaseline) IsAnomaly(value float64) bool {
	threshold := b.GetThreshold()
	if threshold == 0 {
		return false
	}
	return value > threshold
}

func (b *DynamicBaseline) GetStats() map[string]interface{} {
	b.mu.RLock()
	defer b.mu.RUnlock()

	values := make([]float64, len(b.history))
	for i, s := range b.history {
		values[i] = s.Value
	}

	mean := calculateMean(values)
	stdDev := calculateStdDev(values, mean)

	return map[string]interface{}{
		"baseline":         b.baselineValue,
		"threshold":        b.GetThreshold(),
		"mean":             mean,
		"std_dev":          stdDev,
		"sample_count":     len(b.history),
		"last_sample":      b.history[len(b.history)-1].Value,
		"last_update":      b.lastUpdate,
		"multiplier":       b.thresholdMultiplier,
	}
}

func (b *DynamicBaseline) SetMultiplier(multiplier float64) {
	b.mu.Lock()
	defer b.mu.Unlock()
	b.thresholdMultiplier = multiplier
}

func calculateMean(values []float64) float64 {
	if len(values) == 0 {
		return 0
	}

	sum := 0.0
	for _, v := range values {
		sum += v
	}
	return sum / float64(len(values))
}

func calculateStdDev(values []float64, mean float64) float64 {
	if len(values) == 0 {
		return 0
	}

	variance := 0.0
	for _, v := range values {
		variance += math.Pow(v-mean, 2)
	}
	variance /= float64(len(values))
	return math.Sqrt(variance)
}

type BaselineManager struct {
	baselines map[ThresholdType]*DynamicBaseline
	mu        sync.RWMutex
}

func NewBaselineManager() *BaselineManager {
	return &BaselineManager{
		baselines: map[ThresholdType]*DynamicBaseline{
			ThresholdConnectionRate: NewDynamicBaseline(360, 3.0),
			ThresholdSlowConnection: NewDynamicBaseline(1000, 2.5),
			ThresholdIdleTime:       NewDynamicBaseline(1000, 4.0),
		},
	}
}

func (bm *BaselineManager) RecordSample(thresholdType ThresholdType, value float64) {
	bm.mu.RLock()
	baseline, exists := bm.baselines[thresholdType]
	bm.mu.RUnlock()

	if exists {
		baseline.AddSample(value)
	}
}

func (bm *BaselineManager) IsAnomaly(thresholdType ThresholdType, value float64) bool {
	bm.mu.RLock()
	baseline, exists := bm.baselines[thresholdType]
	bm.mu.RUnlock()

	if !exists {
		return false
	}
	return baseline.IsAnomaly(value)
}

func (bm *BaselineManager) GetThreshold(thresholdType ThresholdType) float64 {
	bm.mu.RLock()
	baseline, exists := bm.baselines[thresholdType]
	bm.mu.RUnlock()

	if !exists {
		return 0
	}
	return baseline.GetThreshold()
}

func (bm *BaselineManager) GetStats(thresholdType ThresholdType) map[string]interface{} {
	bm.mu.RLock()
	baseline, exists := bm.baselines[thresholdType]
	bm.mu.RUnlock()

	if !exists {
		return nil
	}
	return baseline.GetStats()
}

func (bm *BaselineManager) GetAllStats() map[string]interface{} {
	bm.mu.RLock()
	defer bm.mu.RUnlock()

	result := make(map[string]interface{})
	for t, baseline := range bm.baselines {
		result[string(t)] = baseline.GetStats()
	}
	return result
}

func (bm *BaselineManager) SetMultiplier(thresholdType ThresholdType, multiplier float64) {
	bm.mu.RLock()
	baseline, exists := bm.baselines[thresholdType]
	bm.mu.RUnlock()

	if exists {
		baseline.SetMultiplier(multiplier)
	}
}
