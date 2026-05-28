package scheduler

import (
	"sync"
	"time"
	"health-check/internal/config"
	"health-check/internal/model"
)

type WeightedScheduler struct {
	cfg          *config.SchedulingConfig
	endpoints    map[string]*model.Endpoint
	intervals    map[string]int
	healthScores map[string]float64
	mu           sync.RWMutex
	windowStats  map[string]*WindowHealth
	adjustTicker *time.Ticker
	stopChan     chan struct{}
}

type WindowHealth struct {
	totalProbes   int
	successProbes int
	avgLatency    time.Duration
}

func NewWeightedScheduler(cfg *config.SchedulingConfig) *WeightedScheduler {
	return &WeightedScheduler{
		cfg:          cfg,
		endpoints:    make(map[string]*model.Endpoint),
		intervals:    make(map[string]int),
		healthScores: make(map[string]float64),
		windowStats:  make(map[string]*WindowHealth),
		stopChan:     make(chan struct{}),
	}
}

func (s *WeightedScheduler) RegisterEndpoint(ep *model.Endpoint) {
	s.mu.Lock()
	defer s.mu.Unlock()

	s.endpoints[ep.ID] = ep
	s.healthScores[ep.ID] = 100.0
	s.windowStats[ep.ID] = &WindowHealth{}
	s.intervals[ep.ID] = s.calculateInterval(ep)
}

func (s *WeightedScheduler) UnregisterEndpoint(endpointID string) {
	s.mu.Lock()
	defer s.mu.Unlock()

	delete(s.endpoints, endpointID)
	delete(s.intervals, endpointID)
	delete(s.healthScores, endpointID)
	delete(s.windowStats, endpointID)
}

func (s *WeightedScheduler) GetInterval(endpointID string) int {
	s.mu.RLock()
	defer s.mu.RUnlock()

	if interval, ok := s.intervals[endpointID]; ok {
		return interval
	}
	return 10
}

func (s *WeightedScheduler) RecordResult(result *model.ProbeResult) {
	s.mu.Lock()
	defer s.mu.Unlock()

	stats, ok := s.windowStats[result.EndpointID]
	if !ok {
		stats = &WindowHealth{}
		s.windowStats[result.EndpointID] = stats
	}

	stats.totalProbes++
	if result.Status == model.StatusUp {
		stats.successProbes++
	}
	stats.avgLatency = (stats.avgLatency*time.Duration(stats.totalProbes-1) + result.Latency) / time.Duration(stats.totalProbes)
}

func (s *WeightedScheduler) calculateInterval(ep *model.Endpoint) int {
	weight := ep.Weight
	if weight <= 0 {
		weight = int(model.WeightMedium)
	}

	baseInterval := ep.Interval
	if baseInterval <= 0 {
		baseInterval = 10
	}

	weightRatio := float64(weight) / float64(model.WeightCritical)
	weightFactor := s.cfg.WeightFactor * (1 - weightRatio)

	healthScore := s.healthScores[ep.ID]
	if healthScore <= 0 {
		healthScore = 100
	}
	healthRatio := healthScore / 100.0
	healthFactor := s.cfg.HealthFactor * (1 - healthRatio)

	adjustFactor := weightFactor + healthFactor
	if adjustFactor < 0 {
		adjustFactor = 0
	}
	if adjustFactor > 0.9 {
		adjustFactor = 0.9
	}

	interval := float64(baseInterval) * (1 - adjustFactor)
	intervalInt := int(interval)

	if intervalInt < s.cfg.MinInterval {
		intervalInt = s.cfg.MinInterval
	}
	if intervalInt > s.cfg.MaxInterval {
		intervalInt = s.cfg.MaxInterval
	}

	return intervalInt
}

func (s *WeightedScheduler) StartAutoAdjust() {
	if !s.cfg.AutoAdjust {
		return
	}

	s.adjustTicker = time.NewTicker(time.Duration(s.cfg.AdjustInterval) * time.Second)

	go func() {
		for {
			select {
			case <-s.adjustTicker.C:
				s.adjustIntervals()
			case <-s.stopChan:
				return
			}
		}
	}()
}

func (s *WeightedScheduler) Stop() {
	if s.adjustTicker != nil {
		s.adjustTicker.Stop()
	}
	close(s.stopChan)
}

func (s *WeightedScheduler) adjustIntervals() {
	s.mu.Lock()
	defer s.mu.Unlock()

	for id, stats := range s.windowStats {
		if stats.totalProbes > 0 {
			availability := float64(stats.successProbes) / float64(stats.totalProbes) * 100
			s.healthScores[id] = availability
		}
		stats.totalProbes = 0
		stats.successProbes = 0
	}

	for id, ep := range s.endpoints {
		s.intervals[id] = s.calculateInterval(ep)
	}
}

func (s *WeightedScheduler) GetHealthScore(endpointID string) float64 {
	s.mu.RLock()
	defer s.mu.RUnlock()

	if score, ok := s.healthScores[endpointID]; ok {
		return score
	}
	return 100.0
}

func (s *WeightedScheduler) GetAllIntervals() map[string]int {
	s.mu.RLock()
	defer s.mu.RUnlock()

	result := make(map[string]int)
	for k, v := range s.intervals {
		result[k] = v
	}
	return result
}

func (s *WeightedScheduler) AdjustEndpointWeight(endpointID string, newWeight int) {
	s.mu.Lock()
	defer s.mu.Unlock()

	if ep, ok := s.endpoints[endpointID]; ok {
		ep.Weight = newWeight
		s.intervals[endpointID] = s.calculateInterval(ep)
	}
}

func (s *WeightedScheduler) GetNextScheduledTime(endpointID string, lastRun time.Time) time.Time {
	interval := s.GetInterval(endpointID)
	return lastRun.Add(time.Duration(interval) * time.Second)
}

func (s *WeightedScheduler) ShouldProbeNow(endpointID string, lastRun time.Time) bool {
	nextRun := s.GetNextScheduledTime(endpointID, lastRun)
	return time.Now().After(nextRun)
}

type SchedulePlan struct {
	EndpointID  string
	Priority    int
	Interval    int
	NextRun     time.Time
	HealthScore float64
}

func (s *WeightedScheduler) GetSchedulePlan() []SchedulePlan {
	s.mu.RLock()
	defer s.mu.RUnlock()

	var plans []SchedulePlan
	now := time.Now()

	for id, ep := range s.endpoints {
		interval := s.intervals[id]
		plans = append(plans, SchedulePlan{
			EndpointID:  id,
			Priority:    ep.Weight,
			Interval:    interval,
			NextRun:     now.Add(time.Duration(interval) * time.Second),
			HealthScore: s.healthScores[id],
		})
	}

	return plans
}
