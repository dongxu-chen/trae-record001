package prediction

import (
	"math"
	"sort"
	"sync"
	"time"
)

type HitRatePrediction struct {
	CurrentHitRate     float64
	PredictedHitRate   float64
	HitRateImprovement float64
	PreheatedCount     int
	TotalHotQueries    int
	CoverageRate       float64
	Confidence         float64
	Details            *PredictionDetails
}

type PredictionDetails struct {
	QueryLevelPredictions []QueryHitPrediction
	ClusterLevelPredictions []ClusterHitPrediction
	TimeSeriesProjection []TimePoint
}

type QueryHitPrediction struct {
	Fingerprint      string
	CurrentHitRate   float64
	PredictedHitRate float64
	Frequency        int
	HotScore         float64
	ExpectedSaves    float64
	Priority         float64
}

type ClusterHitPrediction struct {
	ClusterID        int
	Size             int
	AvgFrequency     float64
	CurrentHitRate   float64
	PredictedHitRate float64
	HotScore         float64
}

type TimePoint struct {
	Time             time.Time
	PredictedHitRate float64
	LowerBound       float64
	UpperBound       float64
}

type HitRatePredictor struct {
	history    []HitRateSnapshot
	queryStats map[string]*QueryHitStats
	mu         sync.RWMutex
	windowSize time.Duration
}

type HitRateSnapshot struct {
	Timestamp      time.Time
	TotalQueries   int64
	CacheHits      int64
	HotQueries     int
	PreheatedCount int
	HitRate        float64
}

type QueryHitStats struct {
	Fingerprint string
	TotalCalls  int64
	CacheHits   int64
	FirstSeen   time.Time
	LastSeen    time.Time
	TotalLatency float64
	HotScore    float64
}

func NewHitRatePredictor(windowSize time.Duration) *HitRatePredictor {
	if windowSize == 0 {
		windowSize = 24 * time.Hour
	}
	return &HitRatePredictor{
		history:    make([]HitRateSnapshot, 0),
		queryStats: make(map[string]*QueryHitStats),
		windowSize: windowSize,
	}
}

func (hp *HitRatePredictor) RecordQuery(fingerprint string, cacheHit bool, latency float64) {
	hp.mu.Lock()
	defer hp.mu.Unlock()

	stats, exists := hp.queryStats[fingerprint]
	if !exists {
		stats = &QueryHitStats{
			Fingerprint: fingerprint,
			FirstSeen:   time.Now(),
		}
		hp.queryStats[fingerprint] = stats
	}

	stats.TotalCalls++
	if cacheHit {
		stats.CacheHits++
	}
	stats.TotalLatency += latency
	stats.LastSeen = time.Now()
}

func (hp *HitRatePredictor) RecordSnapshot(snapshot HitRateSnapshot) {
	hp.mu.Lock()
	defer hp.mu.Unlock()

	hp.history = append(hp.history, snapshot)

	cutoff := time.Now().Add(-hp.windowSize)
	filtered := make([]HitRateSnapshot, 0, len(hp.history))
	for _, s := range hp.history {
		if s.Timestamp.After(cutoff) {
			filtered = append(filtered, s)
		}
	}
	hp.history = filtered
}

func (hp *HitRatePredictor) Predict(preheatedFingerprints map[string]bool, topN int) *HitRatePrediction {
	hp.mu.RLock()
	defer hp.mu.RUnlock()

	allQueries := make([]*QueryHitStats, 0, len(hp.queryStats))
	for _, q := range hp.queryStats {
		allQueries = append(allQueries, q)
	}

	sort.Slice(allQueries, func(i, j int) bool {
		scoreI := float64(allQueries[i].TotalCalls)*0.6 + allQueries[i].HotScore*0.4
		scoreJ := float64(allQueries[j].TotalCalls)*0.6 + allQueries[j].HotScore*0.4
		return scoreI > scoreJ
	})

	if topN <= 0 || topN > len(allQueries) {
		topN = len(allQueries)
	}
	allQueries = allQueries[:topN]

	currentTotal := int64(0)
	currentHits := int64(0)
	predictedHits := int64(0)
	preheatedCount := 0

	queryPredictions := make([]QueryHitPrediction, 0, len(allQueries))

	for _, q := range allQueries {
		currentTotal += q.TotalCalls
		currentHits += q.CacheHits

		currentRate := 0.0
		if q.TotalCalls > 0 {
			currentRate = float64(q.CacheHits) / float64(q.TotalCalls)
		}

		predictedRate := currentRate
		_, willPreheat := preheatedFingerprints[q.Fingerprint]
		if willPreheat {
			preheatedCount++
			if currentRate < 0.8 {
				predictedRate = 0.85 + currentRate*0.15
			} else {
				predictedRate = 0.95 + currentRate*0.05
			}
		}

		expectedSaves := float64(q.TotalCalls) * (predictedRate - currentRate)
		hotScore := float64(q.TotalCalls) * 0.6 + q.HotScore * 0.4

		queryPredictions = append(queryPredictions, QueryHitPrediction{
			Fingerprint:      q.Fingerprint,
			CurrentHitRate:   currentRate,
			PredictedHitRate: predictedRate,
			Frequency:        int(q.TotalCalls),
			HotScore:         q.HotScore,
			ExpectedSaves:    expectedSaves,
			Priority:         expectedSaves,
		})

		predictedHits += int64(float64(q.TotalCalls) * predictedRate)
	}

	currentRate := 0.0
	predictedRate := 0.0
	if currentTotal > 0 {
		currentRate = float64(currentHits) / float64(currentTotal)
		predictedRate = float64(predictedHits) / float64(currentTotal)
	}

	coverageRate := 0.0
	if len(allQueries) > 0 {
		coverageRate = float64(preheatedCount) / float64(len(allQueries))
	}

	confidence := hp.calculateConfidence(allQueries)

	timeProjection := hp.projectTimeSeries(currentRate, predictedRate, preheatedCount)

	return &HitRatePrediction{
		CurrentHitRate:     currentRate,
		PredictedHitRate:   predictedRate,
		HitRateImprovement: predictedRate - currentRate,
		PreheatedCount:     preheatedCount,
		TotalHotQueries:    len(allQueries),
		CoverageRate:       coverageRate,
		Confidence:         confidence,
		Details: &PredictionDetails{
			QueryLevelPredictions:   queryPredictions,
			TimeSeriesProjection:   timeProjection,
		},
	}
}

func (hp *HitRatePredictor) calculateConfidence(queries []*QueryHitStats) float64 {
	if len(queries) == 0 {
		return 0.0
	}

	totalSamples := int64(0)
	for _, q := range queries {
		totalSamples += q.TotalCalls
	}

	confidence := 1.0 - math.Exp(-float64(totalSamples)/1000.0)

	if len(hp.history) >= 10 {
		confidence = confidence*0.7 + 0.3
	}

	return confidence
}

func (hp *HitRatePredictor) projectTimeSeries(currentRate, targetRate float64, preheatedCount int) []TimePoint {
	projection := make([]TimePoint, 0)
	now := time.Now()

	halfLife := 30.0
	if preheatedCount > 0 {
		halfLife = float64(preheatedCount) / 10.0
	}

	for i := 0; i < 24; i++ {
		t := float64(i)
		rate := currentRate + (targetRate-currentRate)*(1.0-math.Exp(-t/halfLife))

		stdDev := 0.05 * (1.0 - math.Exp(-t/12.0))
		lower := math.Max(0, rate-2*stdDev)
		upper := math.Min(1.0, rate+2*stdDev)

		projection = append(projection, TimePoint{
			Time:             now.Add(time.Duration(i) * time.Hour),
			PredictedHitRate: rate,
			LowerBound:       lower,
			UpperBound:       upper,
		})
	}

	return projection
}

func (hp *HitRatePredictor) CalculateOptimalPreheatCount(
	targetHitRate float64,
	maxPreheat int,
) (int, float64) {
	hp.mu.RLock()
	defer hp.mu.RUnlock()

	queries := make([]*QueryHitStats, 0, len(hp.queryStats))
	for _, q := range hp.queryStats {
		queries = append(queries, q)
	}

	sort.Slice(queries, func(i, j int) bool {
		scoreI := float64(queries[i].TotalCalls) * (1.0 - float64(queries[i].CacheHits)/float64(queries[i].TotalCalls+1))
		scoreJ := float64(queries[j].TotalCalls) * (1.0 - float64(queries[j].CacheHits)/float64(queries[j].TotalCalls+1))
		return scoreI > scoreJ
	})

	totalCalls := int64(0)
	totalHits := int64(0)
	for _, q := range queries {
		totalCalls += q.TotalCalls
		totalHits += q.CacheHits
	}

	if totalCalls == 0 {
		return 0, 0
	}

	currentRate := float64(totalHits) / float64(totalCalls)
	bestCount := 0
	bestRate := currentRate

	accumulatedHits := float64(totalHits)
	for i, q := range queries {
		if i >= maxPreheat {
			break
		}

		currentQHits := float64(q.CacheHits)
		expectedHits := float64(q.TotalCalls) * 0.9
		accumulatedHits += (expectedHits - currentQHits)

		predictedRate := accumulatedHits / float64(totalCalls)
		if predictedRate > bestRate {
			bestRate = predictedRate
			bestCount = i + 1
		}

		if predictedRate >= targetHitRate {
			break
		}
	}

	return bestCount, bestRate
}

func (hp *HitRatePredictor) GetCurrentHitRate() float64 {
	hp.mu.RLock()
	defer hp.mu.RUnlock()

	totalCalls := int64(0)
	totalHits := int64(0)
	for _, q := range hp.queryStats {
		totalCalls += q.TotalCalls
		totalHits += q.CacheHits
	}

	if totalCalls == 0 {
		return 0
	}
	return float64(totalHits) / float64(totalCalls)
}

func (hp *HitRatePredictor) Prune(maxAge time.Duration) {
	hp.mu.Lock()
	defer hp.mu.Unlock()

	cutoff := time.Now().Add(-maxAge)
	for fp, q := range hp.queryStats {
		if q.LastSeen.Before(cutoff) {
			delete(hp.queryStats, fp)
		}
	}
}

func (hp *HitRatePredictor) GetQueryCount() int {
	hp.mu.RLock()
	defer hp.mu.RUnlock()
	return len(hp.queryStats)
}

func (hp *HitRatePredictor) UpdateHotScore(fingerprint string, hotScore float64) {
	hp.mu.Lock()
	defer hp.mu.Unlock()

	if stats, exists := hp.queryStats[fingerprint]; exists {
		stats.HotScore = hotScore
	}
}
