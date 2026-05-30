package adaptive

import (
	"math"
	"sync"
	"time"
)

type AdaptiveController struct {
	config         AdaptiveConfig
	currentInterval time.Duration
	history        []IntervalSample
	mu             sync.RWMutex
	lastAdjustment time.Time
	changeRate     float64
	trendDirection float64
}

type AdaptiveConfig struct {
	MinInterval     time.Duration
	MaxInterval     time.Duration
	DefaultInterval time.Duration
	AdjustThreshold float64
	SmoothingFactor float64
	MaxAdjustStep   float64
}

type IntervalSample struct {
	Timestamp      time.Time
	Interval       time.Duration
	ChangeRate     float64
	QueryCount     int
	NewQueryCount  int
	DirtyCount     int
	HitRate        float64
}

type ChangeMetrics struct {
	ChangeRate        float64
	NewQueryRate      float64
	HitRateTrend      float64
	DirtyRate         float64
	RecommendedInterval time.Duration
	Confidence        float64
}

func DefaultAdaptiveConfig() AdaptiveConfig {
	return AdaptiveConfig{
		MinInterval:     30 * time.Second,
		MaxInterval:     30 * time.Minute,
		DefaultInterval: 5 * time.Minute,
		AdjustThreshold: 0.2,
		SmoothingFactor: 0.3,
		MaxAdjustStep:   0.5,
	}
}

func NewAdaptiveController(config AdaptiveConfig) *AdaptiveController {
	if config.MinInterval == 0 {
		config.MinInterval = 30 * time.Second
	}
	if config.MaxInterval == 0 {
		config.MaxInterval = 30 * time.Minute
	}
	if config.DefaultInterval == 0 {
		config.DefaultInterval = 5 * time.Minute
	}
	if config.AdjustThreshold == 0 {
		config.AdjustThreshold = 0.2
	}
	if config.SmoothingFactor == 0 {
		config.SmoothingFactor = 0.3
	}
	if config.MaxAdjustStep == 0 {
		config.MaxAdjustStep = 0.5
	}

	return &AdaptiveController{
		config:         config,
		currentInterval: config.DefaultInterval,
		history:        make([]IntervalSample, 0, 100),
	}
}

func (ac *AdaptiveController) GetCurrentInterval() time.Duration {
	ac.mu.RLock()
	defer ac.mu.RUnlock()
	return ac.currentInterval
}

func (ac *AdaptiveController) GetChangeRate() float64 {
	ac.mu.RLock()
	defer ac.mu.RUnlock()
	return ac.changeRate
}

func (ac *AdaptiveController) RecordSample(
	queryCount int,
	newQueryCount int,
	dirtyCount int,
	hitRate float64,
) time.Duration {
	ac.mu.Lock()
	defer ac.mu.Unlock()

	now := time.Now()

	changeRate := 0.0
	if queryCount > 0 {
		changeRate = float64(newQueryCount+dirtyCount) / float64(queryCount)
	}

	alpha := ac.config.SmoothingFactor
	ac.changeRate = alpha*changeRate + (1-alpha)*ac.changeRate

	if len(ac.history) >= 2 {
		prev := ac.history[len(ac.history)-1]
		ac.trendDirection = ac.changeRate - prev.ChangeRate
	}

	sample := IntervalSample{
		Timestamp:      now,
		Interval:       ac.currentInterval,
		ChangeRate:     changeRate,
		QueryCount:     queryCount,
		NewQueryCount:  newQueryCount,
		DirtyCount:     dirtyCount,
		HitRate:        hitRate,
	}
	ac.history = append(ac.history, sample)

	if len(ac.history) > 100 {
		ac.history = ac.history[1:]
	}

	if now.Sub(ac.lastAdjustment) >= ac.currentInterval/2 {
		ac.adjustInterval()
		ac.lastAdjustment = now
	}

	return ac.currentInterval
}

func (ac *AdaptiveController) adjustInterval() {
	if len(ac.history) < 3 {
		return
	}

	metrics := ac.calculateMetrics()

	if metrics.Confidence < 0.5 {
		return
	}

	targetChangeRate := 0.3
	ratio := metrics.ChangeRate / targetChangeRate

	adjustFactor := 1.0
	if math.Abs(ratio-1.0) > ac.config.AdjustThreshold {
		adjustFactor = 1.0 / math.Sqrt(ratio)
		adjustFactor = math.Max(1.0-ac.config.MaxAdjustStep,
			math.Min(1.0+ac.config.MaxAdjustStep, adjustFactor))
	}

	if metrics.HitRateTrend < -0.05 {
		adjustFactor *= 0.8
	} else if metrics.HitRateTrend > 0.05 {
		adjustFactor *= 1.2
	}

	newIntervalSeconds := ac.currentInterval.Seconds() * adjustFactor
	newInterval := time.Duration(newIntervalSeconds) * time.Second

	newInterval = time.Duration(math.Max(
		float64(ac.config.MinInterval),
		math.Min(float64(ac.config.MaxInterval), float64(newInterval)),
	))

	if newInterval != ac.currentInterval {
		ac.currentInterval = newInterval
	}
}

func (ac *AdaptiveController) calculateMetrics() *ChangeMetrics {
	if len(ac.history) < 2 {
		return &ChangeMetrics{
			RecommendedInterval: ac.config.DefaultInterval,
			Confidence:        0.0,
		}
	}

	recent := ac.history[int(math.Max(0, float64(len(ac.history)-10))):]

	avgChangeRate := 0.0
	avgNewQueryRate := 0.0
	avgDirtyRate := 0.0
	hitRateTrend := 0.0

	for i, s := range recent {
		avgChangeRate += s.ChangeRate
		if s.QueryCount > 0 {
			avgNewQueryRate += float64(s.NewQueryCount) / float64(s.QueryCount)
			avgDirtyRate += float64(s.DirtyCount) / float64(s.QueryCount)
		}
		if i > 0 {
			hitRateTrend += s.HitRate - recent[i-1].HitRate
		}
	}

	n := float64(len(recent))
	avgChangeRate /= n
	avgNewQueryRate /= n
	avgDirtyRate /= n
	hitRateTrend /= n

	recommended := ac.config.DefaultInterval
	if avgChangeRate > 0.5 {
		recommended = ac.config.MinInterval
	} else if avgChangeRate > 0.2 {
		recommended = time.Duration(float64(ac.config.DefaultInterval) * 0.5)
	} else if avgChangeRate < 0.05 {
		recommended = ac.config.MaxInterval
	}

	confidence := math.Min(1.0, float64(len(recent))/10.0)

	return &ChangeMetrics{
		ChangeRate:          avgChangeRate,
		NewQueryRate:        avgNewQueryRate,
		HitRateTrend:        hitRateTrend,
		DirtyRate:           avgDirtyRate,
		RecommendedInterval: recommended,
		Confidence:          confidence,
	}
}

func (ac *AdaptiveController) GetMetrics() *ChangeMetrics {
	ac.mu.RLock()
	defer ac.mu.RUnlock()
	return ac.calculateMetrics()
}

func (ac *AdaptiveController) GetHistory() []IntervalSample {
	ac.mu.RLock()
	defer ac.mu.RUnlock()

	history := make([]IntervalSample, len(ac.history))
	copy(history, ac.history)
	return history
}

func (ac *AdaptiveController) Reset() {
	ac.mu.Lock()
	defer ac.mu.Unlock()

	ac.currentInterval = ac.config.DefaultInterval
	ac.history = ac.history[:0]
	ac.changeRate = 0
	ac.trendDirection = 0
	ac.lastAdjustment = time.Time{}
}

func (ac *AdaptiveController) ForceInterval(interval time.Duration) {
	ac.mu.Lock()
	defer ac.mu.Unlock()

	interval = time.Duration(math.Max(
		float64(ac.config.MinInterval),
		math.Min(float64(ac.config.MaxInterval), float64(interval)),
	))
	ac.currentInterval = interval
}
