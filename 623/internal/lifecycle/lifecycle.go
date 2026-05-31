package lifecycle

import (
	"sync"
	"time"
)

type ConnectionLifecycle struct {
	events   map[uint64][]LifecycleEvent
	mu       sync.RWMutex
	maxPerID int
}

type LifecycleEvent struct {
	ConnectionID uint64
	ClientID     string
	ClientIP     string
	EventType    string
	Timestamp    time.Time
	Duration     time.Duration
	Detail       string
}

type Phase string

const (
	PhaseCreated      Phase = "created"
	PhaseAuthenticating Phase = "authenticating"
	PhaseActive       Phase = "active"
	PhaseQuerying     Phase = "querying"
	PhaseIdle         Phase = "idle"
	PhaseReleasing    Phase = "releasing"
	PhaseClosed       Phase = "closed"
	PhasePreWarmed    Phase = "pre_warmed"
	PhaseLeased       Phase = "leased"
	PhaseReturned     Phase = "returned"
	PhaseExpired      Phase = "expired"
	PhaseStormBlocked Phase = "storm_blocked"
	PhaseRateLimited  Phase = "rate_limited"
	PhaseLeakDetected Phase = "leak_detected"
	PhaseForceClosed  Phase = "force_closed"
)

type ConnectionTimeline struct {
	ConnectionID uint64
	ClientID     string
	ClientIP     string
	Events       []LifecycleEvent
	CurrentPhase Phase
	CreatedAt    time.Time
	Duration     time.Duration
}

func NewConnectionLifecycle() *ConnectionLifecycle {
	return &ConnectionLifecycle{
		events:   make(map[uint64][]LifecycleEvent),
		maxPerID: 100,
	}
}

func (cl *ConnectionLifecycle) RecordEvent(connID uint64, clientID, clientIP string, phase Phase, detail string) {
	cl.mu.Lock()
	defer cl.mu.Unlock()

	event := LifecycleEvent{
		ConnectionID: connID,
		ClientID:     clientID,
		ClientIP:     clientIP,
		EventType:    string(phase),
		Timestamp:    time.Now(),
		Detail:       detail,
	}

	cl.events[connID] = append(cl.events[connID], event)

	if len(cl.events[connID]) > cl.maxPerID {
		cl.events[connID] = cl.events[connID][1:]
	}
}

func (cl *ConnectionLifecycle) RecordTimedEvent(connID uint64, clientID, clientIP string, phase Phase, duration time.Duration, detail string) {
	cl.mu.Lock()
	defer cl.mu.Unlock()

	event := LifecycleEvent{
		ConnectionID: connID,
		ClientID:     clientID,
		ClientIP:     clientIP,
		EventType:    string(phase),
		Timestamp:    time.Now(),
		Duration:     duration,
		Detail:       detail,
	}

	cl.events[connID] = append(cl.events[connID], event)

	if len(cl.events[connID]) > cl.maxPerID {
		cl.events[connID] = cl.events[connID][1:]
	}
}

func (cl *ConnectionLifecycle) GetTimeline(connID uint64) *ConnectionTimeline {
	cl.mu.RLock()
	defer cl.mu.RUnlock()

	events, exists := cl.events[connID]
	if !exists || len(events) == 0 {
		return nil
	}

	timeline := &ConnectionTimeline{
		ConnectionID: connID,
		Events:       make([]LifecycleEvent, len(events)),
		CurrentPhase: Phase(events[len(events)-1].EventType),
	}

	copy(timeline.Events, events)

	first := events[0]
	timeline.ClientID = first.ClientID
	timeline.ClientIP = first.ClientIP
	timeline.CreatedAt = first.Timestamp
	timeline.Duration = time.Since(first.Timestamp)

	return timeline
}

func (cl *ConnectionLifecycle) GetRecentTimelines(limit int) []ConnectionTimeline {
	cl.mu.RLock()
	defer cl.mu.RUnlock()

	ids := make([]uint64, 0, len(cl.events))
	for id := range cl.events {
		ids = append(ids, id)
	}

	start := 0
	if len(ids) > limit {
		start = len(ids) - limit
	}
	ids = ids[start:]

	result := make([]ConnectionTimeline, 0, len(ids))
	for _, id := range ids {
		events := cl.events[id]
		if len(events) == 0 {
			continue
		}

		timeline := ConnectionTimeline{
			ConnectionID: id,
			Events:       make([]LifecycleEvent, len(events)),
			CurrentPhase: Phase(events[len(events)-1].EventType),
		}

		copy(timeline.Events, events)

		first := events[0]
		timeline.ClientID = first.ClientID
		timeline.ClientIP = first.ClientIP
		timeline.CreatedAt = first.Timestamp
		timeline.Duration = time.Since(first.Timestamp)

		result = append(result, timeline)
	}

	return result
}

func (cl *ConnectionLifecycle) GetActiveConnections() []ConnectionTimeline {
	cl.mu.RLock()
	defer cl.mu.RUnlock()

	result := make([]ConnectionTimeline, 0)

	for id, events := range cl.events {
		if len(events) == 0 {
			continue
		}

		lastPhase := Phase(events[len(events)-1].EventType)
		if lastPhase == PhaseClosed || lastPhase == PhaseExpired || lastPhase == PhaseForceClosed {
			continue
		}

		timeline := ConnectionTimeline{
			ConnectionID: id,
			Events:       make([]LifecycleEvent, len(events)),
			CurrentPhase: lastPhase,
		}

		copy(timeline.Events, events)

		first := events[0]
		timeline.ClientID = first.ClientID
		timeline.ClientIP = first.ClientIP
		timeline.CreatedAt = first.Timestamp
		timeline.Duration = time.Since(first.Timestamp)

		result = append(result, timeline)
	}

	return result
}

func (cl *ConnectionLifecycle) GetPhaseStats() map[string]int64 {
	cl.mu.RLock()
	defer cl.mu.RUnlock()

	stats := make(map[string]int64)
	for _, events := range cl.events {
		if len(events) > 0 {
			phase := events[len(events)-1].EventType
			stats[phase]++
		}
	}

	return stats
}

func (cl *ConnectionLifecycle) GetStats() map[string]interface{} {
	cl.mu.RLock()
	defer cl.mu.RUnlock()

	phaseStats := make(map[string]int64)
	totalEvents := 0

	for _, events := range cl.events {
		if len(events) > 0 {
			phase := events[len(events)-1].EventType
			phaseStats[phase]++
		}
		totalEvents += len(events)
	}

	return map[string]interface{}{
		"tracked_connections": len(cl.events),
		"total_events":       totalEvents,
		"phase_distribution": phaseStats,
	}
}

func (cl *ConnectionLifecycle) CleanupOldConnections(maxAge time.Duration) {
	cl.mu.Lock()
	defer cl.mu.Unlock()

	now := time.Now()
	for id, events := range cl.events {
		if len(events) == 0 {
			delete(cl.events, id)
			continue
		}

		lastEvent := events[len(events)-1]
		if now.Sub(lastEvent.Timestamp) > maxAge {
			delete(cl.events, id)
		}
	}
}
