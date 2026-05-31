package prewarm

import (
	"db-guardian/internal/baseline"
	"db-guardian/internal/pool"
	"db-guardian/pkg/logger"
	"fmt"
	"sync"
	"time"
)

type PreWarmEngine struct {
	pool           *pool.AutoScalingPool
	baselineMgr    *baseline.BaselineManager
	log            *logger.Logger

	history        []ConnectionRateSample
	historyMu      sync.RWMutex
	maxHistorySize int

	predictionWindow time.Duration
	warmTriggerRate  float64
	warmBatchSize    int

	isPreWarming   bool
	preWarmCount   int64
	preWarmHits    int64
	preWarmMisses  int64

	stopChan chan struct{}
	wg       sync.WaitGroup
}

type ConnectionRateSample struct {
	Timestamp time.Time
	Rate      float64
}

type PredictionResult struct {
	PredictedRate float64
	Confidence    float64
	ShouldWarm    bool
	WarmCount     int
	Reason        string
}

func NewPreWarmEngine(pool *pool.AutoScalingPool, baselineMgr *baseline.BaselineManager, log *logger.Logger) *PreWarmEngine {
	engine := &PreWarmEngine{
		pool:            pool,
		baselineMgr:     baselineMgr,
		log:             log,
		history:         make([]ConnectionRateSample, 0, 720),
		maxHistorySize:  720,
		predictionWindow: 30 * time.Second,
		warmTriggerRate: 30.0,
		warmBatchSize:   20,
		stopChan:        make(chan struct{}),
	}

	engine.wg.Add(1)
	go engine.run()

	return engine
}

func (e *PreWarmEngine) RecordRate(rate float64) {
	e.historyMu.Lock()
	defer e.historyMu.Unlock()

	sample := ConnectionRateSample{
		Timestamp: time.Now(),
		Rate:      rate,
	}
	e.history = append(e.history, sample)

	if len(e.history) > e.maxHistorySize {
		e.history = e.history[1:]
	}
}

func (e *PreWarmEngine) run() {
	defer e.wg.Done()

	ticker := time.NewTicker(5 * time.Second)
	defer ticker.Stop()

	for {
		select {
		case <-ticker.C:
			e.evaluateAndPreWarm()
		case <-e.stopChan:
			return
		}
	}
}

func (e *PreWarmEngine) evaluateAndPreWarm() {
	prediction := e.predict()

	if prediction.ShouldWarm {
		created := e.pool.PreWarmConnections(prediction.WarmCount)
		if created > 0 {
			e.isPreWarming = true
			e.preWarmCount += int64(created)
			e.log.Info("Pre-warmed %d connections: predicted_rate=%.2f, reason=%s",
				created, prediction.PredictedRate, prediction.Reason)
		}
	} else {
		e.isPreWarming = false
	}

	e.pool.cleanupExpiredWarmConnections()
}

func (e *PreWarmEngine) predict() PredictionResult {
	e.historyMu.RLock()
	defer e.historyMu.RUnlock()

	if len(e.history) < 12 {
		return PredictionResult{
			PredictedRate: 0,
			Confidence:    0,
			ShouldWarm:    false,
			Reason:        "Insufficient data",
		}
	}

	shortTermRate := e.calculateRecentRate(1 * time.Minute)
	mediumTermRate := e.calculateRecentRate(5 * time.Minute)

	trend := e.calculateTrend()

	var predictedRate float64
	var confidence float64

	if trend > 0 {
		predictedRate = shortTermRate * (1 + trend)
		confidence = 0.7
	} else {
		predictedRate = shortTermRate
		confidence = 0.4
	}

	baselineThreshold := e.baselineMgr.GetThreshold(baseline.ThresholdConnectionRate)
	if baselineThreshold > 0 && predictedRate > baselineThreshold*0.7 {
		confidence = 0.85
	}

	shouldWarm := false
	warmCount := 0
	reason := ""

	if predictedRate > e.warmTriggerRate && trend > 0.1 {
		shouldWarm = true
		warmCount = e.warmBatchSize
		reason = fmt.Sprintf("Trend rising: rate=%.2f, trend=%.2f", predictedRate, trend)
	}

	if shortTermRate > mediumTermRate*1.5 && shortTermRate > 10 {
		shouldWarm = true
		warmCount = e.warmBatchSize * 2
		reason = fmt.Sprintf("Rate spike: short=%.2f > medium=%.2f", shortTermRate, mediumTermRate)
	}

	if baselineThreshold > 0 && shortTermRate > baselineThreshold*0.6 && trend > 0 {
		shouldWarm = true
		warmCount = e.warmBatchSize * 2
		reason = fmt.Sprintf("Approaching baseline threshold: rate=%.2f, threshold=%.2f", shortTermRate, baselineThreshold)
	}

	return PredictionResult{
		PredictedRate: predictedRate,
		Confidence:    confidence,
		ShouldWarm:    shouldWarm,
		WarmCount:     warmCount,
		Reason:        reason,
	}
}

func (e *PreWarmEngine) calculateRecentRate(window time.Duration) float64 {
	now := time.Now()
	cutoff := now.Add(-window)

	var totalRate float64
	count := 0

	for i := len(e.history) - 1; i >= 0; i-- {
		if e.history[i].Timestamp.Before(cutoff) {
			break
		}
		totalRate += e.history[i].Rate
		count++
	}

	if count == 0 {
		return 0
	}
	return totalRate / float64(count)
}

func (e *PreWarmEngine) calculateTrend() float64 {
	if len(e.history) < 12 {
		return 0
	}

	recent := e.history[len(e.history)-6:]
	older := e.history[len(e.history)-12 : len(e.history)-6]

	recentAvg := 0.0
	for _, s := range recent {
		recentAvg += s.Rate
	}
	recentAvg /= float64(len(recent))

	olderAvg := 0.0
	for _, s := range older {
		olderAvg += s.Rate
	}
	olderAvg /= float64(len(older))

	if olderAvg == 0 {
		return 0
	}

	return (recentAvg - olderAvg) / olderAvg
}

func (e *PreWarmEngine) RecordHit() {
	e.preWarmHits++
}

func (e *PreWarmEngine) RecordMiss() {
	e.preWarmMisses++
}

func (e *PreWarmEngine) GetStats() map[string]interface{} {
	prediction := e.predict()

	totalAttempts := e.preWarmHits + e.preWarmMisses
	hitRate := 0.0
	if totalAttempts > 0 {
		hitRate = float64(e.preWarmHits) / float64(totalAttempts) * 100
	}

	return map[string]interface{}{
		"is_pre_warming":    e.isPreWarming,
		"total_pre_warmed":  e.preWarmCount,
		"cache_hits":        e.preWarmHits,
		"cache_misses":      e.preWarmMisses,
		"hit_rate":          hitRate,
		"warm_pool_size":    e.pool.GetWarmPoolSize(),
		"warm_available":    e.pool.GetAvailableWarmCount(),
		"prediction": map[string]interface{}{
			"predicted_rate": prediction.PredictedRate,
			"confidence":     prediction.Confidence,
			"should_warm":    prediction.ShouldWarm,
			"warm_count":     prediction.WarmCount,
			"reason":         prediction.Reason,
		},
	}
}

func (e *PreWarmEngine) SetConfig(triggerRate float64, batchSize int) {
	e.warmTriggerRate = triggerRate
	e.warmBatchSize = batchSize
}

func (e *PreWarmEngine) Stop() {
	close(e.stopChan)
	e.wg.Wait()
}
