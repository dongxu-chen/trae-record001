package processor

import (
	"redis-keyspace-notifier/models"
	"sync"
)

type EventStore struct {
	events []models.KeyEvent
	mu     sync.RWMutex
	maxSize int
	stats  models.EventStats
}

func NewEventStore(maxSize int) *EventStore {
	return &EventStore{
		events:  make([]models.KeyEvent, 0, maxSize),
		maxSize: maxSize,
	}
}

func (s *EventStore) Add(event models.KeyEvent) {
	s.mu.Lock()
	defer s.mu.Unlock()

	s.stats.TotalEvents++

	switch event.EventType {
	case "expired":
		s.stats.ExpiredEvents++
	case "del":
		s.stats.DeletedEvents++
	case "set":
		s.stats.SetEvents++
	}

	if event.Sampled {
		s.stats.SampledEvents++
	}

	if event.Processed {
		s.stats.ProcessedEvents++
	} else if event.Error != "" {
		s.stats.FailedEvents++
	}

	s.events = append(s.events, event)
	if len(s.events) > s.maxSize {
		s.events = s.events[1:]
	}
}

func (s *EventStore) GetAll() []models.KeyEvent {
	s.mu.RLock()
	defer s.mu.RUnlock()

	result := make([]models.KeyEvent, len(s.events))
	copy(result, s.events)
	return result
}

func (s *EventStore) GetRecent(limit int) []models.KeyEvent {
	s.mu.RLock()
	defer s.mu.RUnlock()

	if limit > len(s.events) {
		limit = len(s.events)
	}

	result := make([]models.KeyEvent, limit)
	start := len(s.events) - limit
	copy(result, s.events[start:])
	return result
}

func (s *EventStore) GetStats() models.EventStats {
	s.mu.RLock()
	defer s.mu.RUnlock()
	return s.stats
}

func (s *EventStore) Update(event models.KeyEvent) {
	s.mu.Lock()
	defer s.mu.Unlock()

	for i, e := range s.events {
		if e.ID == event.ID {
			s.events[i] = event
			if event.Processed && !e.Processed {
				s.stats.ProcessedEvents++
			}
			if event.Error != "" && e.Error == "" {
				s.stats.FailedEvents++
			}
			break
		}
	}
}

func (s *EventStore) Clear() {
	s.mu.Lock()
	defer s.mu.Unlock()

	s.events = make([]models.KeyEvent, 0, s.maxSize)
	s.stats = models.EventStats{}
}
