package processor

import (
	"math/rand"
	"redis-keyspace-notifier/config"
	"redis-keyspace-notifier/models"
	"sync"
	"time"
)

type SamplingConfig struct {
	Enabled         bool
	EventTypeRates  map[string]float64
	DefaultRate     float64
	WindowSize      time.Duration
	ThresholdPerSec int
}

type EventSampler struct {
	config        SamplingConfig
	eventCounters map[string]*rateCounter
	mu            sync.RWMutex
}

type rateCounter struct {
	count     int
	windowStart time.Time
}

func NewEventSampler() *EventSampler {
	return &EventSampler{
		config: SamplingConfig{
			Enabled: true,
			EventTypeRates: map[string]float64{
				"expired": 0.1,
				"del":     0.5,
				"set":     1.0,
			},
			DefaultRate:     1.0,
			WindowSize:      time.Second,
			ThresholdPerSec: 100,
		},
		eventCounters: make(map[string]*rateCounter),
	}
}

func (s *EventSampler) ShouldProcess(event *models.KeyEvent) bool {
	if !s.config.Enabled {
		return true
	}

	key := s.getCounterKey(event)
	currentRate := s.getCurrentRate(event, key)

	rate, exists := s.config.EventTypeRates[event.EventType]
	if !exists {
		rate = s.config.DefaultRate
	}

	adjustedRate := rate
	if currentRate > float64(s.config.ThresholdPerSec) {
		adjustedRate = rate * (float64(s.config.ThresholdPerSec) / currentRate)
		if adjustedRate < 0.01 {
			adjustedRate = 0.01
		}
	}

	if adjustedRate >= 1.0 {
		return true
	}

	if rand.Float64() < adjustedRate {
		event.Sampled = true
		return true
	}

	return false
}

func (s *EventSampler) getCounterKey(event *models.KeyEvent) string {
	return event.EventType
}

func (s *EventSampler) getCurrentRate(event *models.KeyEvent, key string) float64 {
	s.mu.Lock()
	defer s.mu.Unlock()

	counter, exists := s.eventCounters[key]
	now := time.Now()

	if !exists {
		counter = &rateCounter{
			count:       1,
			windowStart: now,
		}
		s.eventCounters[key] = counter
		return 1.0
	}

	if now.Sub(counter.windowStart) > s.config.WindowSize {
		elapsed := now.Sub(counter.windowStart).Seconds()
		rate := float64(counter.count) / elapsed
		counter.count = 1
		counter.windowStart = now
		return rate
	}

	counter.count++
	elapsed := now.Sub(counter.windowStart).Seconds()
	if elapsed > 0 {
		return float64(counter.count) / elapsed
	}
	return float64(counter.count)
}

func (s *EventSampler) SetEventTypeRate(eventType string, rate float64) {
	s.mu.Lock()
	defer s.mu.Unlock()
	s.config.EventTypeRates[eventType] = rate
}

func (s *EventSampler) GetConfig() SamplingConfig {
	s.mu.RLock()
	defer s.mu.RUnlock()
	return s.config
}
