package stats

import (
	"math"
	"sort"
	"sync"
	"time"
)

type QueryObservation struct {
	Fingerprint string
	Timestamp   time.Time
	Latency     float64
	RowsReturned int
	HitCache    bool
}

type TimeSeriesBucket struct {
	StartTime time.Time
	Count     int
	AvgLatency float64
	TotalRows  int64
}

type HotQueryPredictor struct {
	observations map[string][]QueryObservation
	decayFactor  float64
	windowSize   time.Duration
	mu           sync.RWMutex
}

func NewHotQueryPredictor(decayFactor float64, windowSize time.Duration) *HotQueryPredictor {
	if decayFactor <= 0 || decayFactor >= 1 {
		decayFactor = 0.95
	}
	if windowSize == 0 {
		windowSize = time.Hour
	}
	return &HotQueryPredictor{
		observations: make(map[string][]QueryObservation),
		decayFactor:  decayFactor,
		windowSize:   windowSize,
	}
}

func (h *HotQueryPredictor) Record(obs QueryObservation) {
	h.mu.Lock()
	defer h.mu.Unlock()
	h.observations[obs.Fingerprint] = append(h.observations[obs.Fingerprint], obs)
}

func (h *HotQueryPredictor) RecordBatch(obs []QueryObservation) {
	h.mu.Lock()
	defer h.mu.Unlock()
	for _, o := range obs {
		h.observations[o.Fingerprint] = append(h.observations[o.Fingerprint], o)
	}
}

type HotQueryResult struct {
	Fingerprint    string
	Score          float64
	FrequencyScore float64
	LatencyScore   float64
	TrendScore     float64
	PredictedFreq  float64
	CurrentFreq    int
	AvgLatency     float64
	P95Latency     float64
}

func (h *HotQueryPredictor) PredictHotQueries(now time.Time, topN int) []HotQueryResult {
	h.mu.RLock()
	defer h.mu.RUnlock()

	results := make([]HotQueryResult, 0, len(h.observations))

	for fp, obs := range h.observations {
		if len(obs) == 0 {
			continue
		}

		freqScore := h.computeFrequencyScore(obs, now)
		latScore := h.computeLatencyScore(obs, now)
		trendScore := h.computeTrendScore(obs, now)
		predictedFreq := h.predictFutureFrequency(obs, now)
		currentFreq := h.countRecent(obs, now, h.windowSize)
		avgLat := h.computeAvgLatency(obs, now)
		p95Lat := h.computeP95Latency(obs, now)

		totalScore := freqScore*0.4 + latScore*0.3 + trendScore*0.3

		results = append(results, HotQueryResult{
			Fingerprint:    fp,
			Score:          totalScore,
			FrequencyScore: freqScore,
			LatencyScore:   latScore,
			TrendScore:     trendScore,
			PredictedFreq:  predictedFreq,
			CurrentFreq:    currentFreq,
			AvgLatency:     avgLat,
			P95Latency:     p95Lat,
		})
	}

	sort.Slice(results, func(i, j int) bool {
		return results[i].Score > results[j].Score
	})

	if topN > 0 && topN < len(results) {
		results = results[:topN]
	}

	return results
}

func (h *HotQueryPredictor) computeFrequencyScore(obs []QueryObservation, now time.Time) float64 {
	score := 0.0
	for _, o := range obs {
		age := now.Sub(o.Timestamp).Hours()
		if age < 0 {
			age = 0
		}
		weight := math.Pow(h.decayFactor, age)
		score += weight
	}
	return score
}

func (h *HotQueryPredictor) computeLatencyScore(obs []QueryObservation, now time.Time) float64 {
	weightedLatency := 0.0
	totalWeight := 0.0

	for _, o := range obs {
		age := now.Sub(o.Timestamp).Hours()
		if age < 0 {
			age = 0
		}
		weight := math.Pow(h.decayFactor, age)
		weightedLatency += o.Latency * weight
		totalWeight += weight
	}

	if totalWeight == 0 {
		return 0
	}

	avgLat := weightedLatency / totalWeight
	return math.Log1p(avgLat)
}

func (h *HotQueryPredictor) computeTrendScore(obs []QueryObservation, now time.Time) float64 {
	if len(obs) < 2 {
		return 0
	}

	recentWindow := h.windowSize
	midPoint := now.Add(-recentWindow)

	var recentCount, olderCount float64
	for _, o := range obs {
		age := now.Sub(o.Timestamp)
		if age <= recentWindow {
			recentCount++
		} else if o.Timestamp.After(midPoint.Add(-recentWindow)) {
			olderCount++
		}
	}

	if olderCount == 0 {
		if recentCount > 0 {
			return 1.0
		}
		return 0
	}

	ratio := recentCount / olderCount
	if ratio > 2.0 {
		return 1.0
	}
	return ratio / 2.0
}

func (h *HotQueryPredictor) predictFutureFrequency(obs []QueryObservation, now time.Time) float64 {
	if len(obs) < 3 {
		return float64(h.countRecent(obs, now, h.windowSize))
	}

	buckets := h.bucketByTime(obs, now, h.windowSize/4)
	if len(buckets) < 2 {
		return float64(buckets[0].Count)
	}

	var sumX, sumY, sumXY, sumX2 float64
	n := float64(len(buckets))
	for i, b := range buckets {
		x := float64(i)
		y := float64(b.Count)
		sumX += x
		sumY += y
		sumXY += x * y
		sumX2 += x * x
	}

	denom := n*sumX2 - sumX*sumX
	if denom == 0 {
		return sumY / n
	}

	slope := (n*sumXY - sumX*sumY) / denom
	intercept := (sumY - slope*sumX) / n

	predicted := intercept + slope*float64(len(buckets))
	if predicted < 0 {
		predicted = 0
	}
	return predicted
}

func (h *HotQueryPredictor) countRecent(obs []QueryObservation, now time.Time, window time.Duration) int {
	count := 0
	for _, o := range obs {
		if now.Sub(o.Timestamp) <= window {
			count++
		}
	}
	return count
}

func (h *HotQueryPredictor) computeAvgLatency(obs []QueryObservation, now time.Time) float64 {
	weightedSum := 0.0
	totalWeight := 0.0

	for _, o := range obs {
		age := now.Sub(o.Timestamp).Hours()
		if age < 0 {
			age = 0
		}
		w := math.Pow(h.decayFactor, age)
		weightedSum += o.Latency * w
		totalWeight += w
	}

	if totalWeight == 0 {
		return 0
	}
	return weightedSum / totalWeight
}

func (h *HotQueryPredictor) computeP95Latency(obs []QueryObservation, now time.Time) float64 {
	cutoff := now.Add(-24 * time.Hour)
	var recent []float64
	for _, o := range obs {
		if o.Timestamp.After(cutoff) {
			recent = append(recent, o.Latency)
		}
	}

	if len(recent) == 0 {
		return 0
	}

	sort.Float64s(recent)
	idx := int(math.Ceil(float64(len(recent))*0.95)) - 1
	if idx < 0 {
		idx = 0
	}
	if idx >= len(recent) {
		idx = len(recent) - 1
	}
	return recent[idx]
}

func (h *HotQueryPredictor) bucketByTime(obs []QueryObservation, now time.Time, bucketSize time.Duration) []TimeSeriesBucket {
	if len(obs) == 0 {
		return nil
	}

	earliest := obs[0].Timestamp
	for _, o := range obs {
		if o.Timestamp.Before(earliest) {
			earliest = o.Timestamp
		}
	}

	startOfFirstBucket := earliest.Truncate(bucketSize)
	numBuckets := int(now.Sub(startOfFirstBucket)/bucketSize) + 1

	buckets := make([]TimeSeriesBucket, numBuckets)
	for i := range buckets {
		buckets[i].StartTime = startOfFirstBucket.Add(time.Duration(i) * bucketSize)
	}

	for _, o := range obs {
		idx := int(o.Timestamp.Sub(startOfFirstBucket) / bucketSize)
		if idx >= 0 && idx < numBuckets {
			buckets[idx].Count++
			buckets[idx].AvgLatency += o.Latency
			buckets[idx].TotalRows += int64(o.RowsReturned)
		}
	}

	for i := range buckets {
		if buckets[i].Count > 0 {
			buckets[i].AvgLatency /= float64(buckets[i].Count)
		}
	}

	return buckets
}

func (h *HotQueryPredictor) Prune(maxAge time.Duration) {
	h.mu.Lock()
	defer h.mu.Unlock()

	cutoff := time.Now().Add(-maxAge)
	for fp, obs := range h.observations {
		var filtered []QueryObservation
		for _, o := range obs {
			if o.Timestamp.After(cutoff) {
				filtered = append(filtered, o)
			}
		}
		if len(filtered) == 0 {
			delete(h.observations, fp)
		} else {
			h.observations[fp] = filtered
		}
	}
}

func (h *HotQueryPredictor) GetObservationCount() int {
	h.mu.RLock()
	defer h.mu.RUnlock()
	total := 0
	for _, obs := range h.observations {
		total += len(obs)
	}
	return total
}

func (h *HotQueryPredictor) GetPatternCount() int {
	h.mu.RLock()
	defer h.mu.RUnlock()
	return len(h.observations)
}
