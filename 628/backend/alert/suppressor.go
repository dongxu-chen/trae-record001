package alert

import (
	"sync"
	"time"

	"anomaly-detector/model"
)

type Suppressor struct {
	window time.Duration
	seen   map[string]time.Time
	mu     sync.RWMutex
}

func NewSuppressor(window time.Duration) *Suppressor {
	if window <= 0 {
		window = 5 * time.Minute
	}
	return &Suppressor{
		window: window,
		seen:   make(map[string]time.Time),
	}
}

func (s *Suppressor) Suppress(alert *model.Alert) bool {
	s.mu.Lock()
	defer s.mu.Unlock()

	key := alert.GroupKey
	if lastSeen, ok := s.seen[key]; ok {
		if time.Since(lastSeen) < s.window {
			alert.Suppressed = true
			return true
		}
	}

	s.seen[key] = time.Now()
	alert.Suppressed = false
	return false
}

func (s *Suppressor) IsSuppressed(alert *model.Alert) bool {
	s.mu.RLock()
	defer s.mu.RUnlock()

	key := alert.GroupKey
	if lastSeen, ok := s.seen[key]; ok {
		return time.Since(lastSeen) < s.window
	}
	return false
}

func (s *Suppressor) CleanExpired() {
	s.mu.Lock()
	defer s.mu.Unlock()

	now := time.Now()
	for key, lastSeen := range s.seen {
		if now.Sub(lastSeen) > s.window*2 {
			delete(s.seen, key)
		}
	}
}

func (s *Suppressor) SuppressBySimilarity(anomalies []model.Anomaly, existingAlerts []model.Alert) bool {
	for _, alert := range existingAlerts {
		if alert.Acknowledged {
			continue
		}

		overlap := 0
		alertMetrics := make(map[string]bool)
		for _, a := range alert.Anomalies {
			alertMetrics[a.Metric] = true
		}

		for _, a := range anomalies {
			if alertMetrics[a.Metric] {
				overlap++
			}
		}

		similarity := float64(overlap) / float64(len(anomalies)+len(alert.Anomalies)-overlap)
		if similarity > 0.7 {
			return true
		}
	}

	return false
}
