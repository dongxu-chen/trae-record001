package processor

import (
	"redis-keyspace-notifier/models"
	"sort"
	"sync"
	"time"
)

type LatencyAnalyzer struct {
	latencies   []float64
	maxSize     int
	mu          sync.RWMutex
	eventTypeStats map[string]*LatencyTracker
}

type LatencyTracker struct {
	latencies []float64
	count     int64
	total     float64
}

func NewLatencyAnalyzer(maxSize int) *LatencyAnalyzer {
	return &LatencyAnalyzer{
		latencies:      make([]float64, 0, maxSize),
		maxSize:        maxSize,
		eventTypeStats: make(map[string]*LatencyTracker),
	}
}

func (a *LatencyAnalyzer) Record(event *models.KeyEvent) {
	if event.Timestamp.IsZero() {
		return
	}

	latency := float64(time.Since(event.Timestamp).Milliseconds())
	event.LatencyMs = int64(latency)
	event.ProcessedAt = time.Now()

	a.mu.Lock()
	defer a.mu.Unlock()

	if len(a.latencies) >= a.maxSize {
		a.latencies = a.latencies[1:]
	}
	a.latencies = append(a.latencies, latency)

	tracker, exists := a.eventTypeStats[event.EventType]
	if !exists {
		tracker = &LatencyTracker{
			latencies: make([]float64, 0, 1000),
		}
		a.eventTypeStats[event.EventType] = tracker
	}
	tracker.count++
	tracker.total += latency
	if len(tracker.latencies) >= 1000 {
		tracker.latencies = tracker.latencies[1:]
	}
	tracker.latencies = append(tracker.latencies, latency)
}

func (a *LatencyAnalyzer) GetStats() models.LatencyStats {
	a.mu.RLock()
	defer a.mu.RUnlock()

	if len(a.latencies) == 0 {
		return models.LatencyStats{}
	}

	sorted := make([]float64, len(a.latencies))
	copy(sorted, a.latencies)
	sort.Float64s(sorted)

	n := len(sorted)
	total := 0.0
	for _, v := range sorted {
		total += v
	}

	return models.LatencyStats{
		AvgMs: total / float64(n),
		P50Ms: percentile(sorted, 0.50),
		P95Ms: percentile(sorted, 0.95),
		P99Ms: percentile(sorted, 0.99),
		MaxMs: sorted[n-1],
		MinMs: sorted[0],
		Count: int64(n),
	}
}

func (a *LatencyAnalyzer) GetStatsByEventType(eventType string) models.LatencyStats {
	a.mu.RLock()
	defer a.mu.RUnlock()

	tracker, exists := a.eventTypeStats[eventType]
	if !exists || len(tracker.latencies) == 0 {
		return models.LatencyStats{}
	}

	sorted := make([]float64, len(tracker.latencies))
	copy(sorted, tracker.latencies)
	sort.Float64s(sorted)

	n := len(sorted)

	return models.LatencyStats{
		AvgMs: tracker.total / float64(tracker.count),
		P50Ms: percentile(sorted, 0.50),
		P95Ms: percentile(sorted, 0.95),
		P99Ms: percentile(sorted, 0.99),
		MaxMs: sorted[n-1],
		MinMs: sorted[0],
		Count: tracker.count,
	}
}

func percentile(sorted []float64, p float64) float64 {
	n := len(sorted)
	if n == 0 {
		return 0
	}
	index := int(float64(n-1) * p)
	return sorted[index]
}

func (a *LatencyAnalyzer) Reset() {
	a.mu.Lock()
	defer a.mu.Unlock()
	a.latencies = make([]float64, 0, a.maxSize)
	a.eventTypeStats = make(map[string]*LatencyTracker)
}
