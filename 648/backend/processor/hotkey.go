package processor

import (
	"fmt"
	"redis-keyspace-notifier/models"
	"sort"
	"strings"
	"sync"
	"time"
)

type KeyEventTracker struct {
	count       int64
	lastSeen    time.Time
	eventType   string
	db          int
}

type HotKeyAnalyzer struct {
	keyMap      map[string]*KeyEventTracker
	maxKeys     int
	mu          sync.RWMutex
	windowStart time.Time
	windowSize  time.Duration
}

func NewHotKeyAnalyzer(maxKeys int, windowSize time.Duration) *HotKeyAnalyzer {
	return &HotKeyAnalyzer{
		keyMap:      make(map[string]*KeyEventTracker),
		maxKeys:     maxKeys,
		windowStart: time.Now(),
		windowSize:  windowSize,
	}
}

func (a *HotKeyAnalyzer) Record(event *models.KeyEvent) {
	a.mu.Lock()
	defer a.mu.Unlock()

	a.checkRotateWindow()

	key := a.getKey(event)
	tracker, exists := a.keyMap[key]

	if !exists {
		if len(a.keyMap) >= a.maxKeys {
			a.evictLeastActive()
		}
		tracker = &KeyEventTracker{
			eventType: event.EventType,
			db:        event.DB,
		}
		a.keyMap[key] = tracker
	}

	tracker.count++
	tracker.lastSeen = time.Now()
}

func (a *HotKeyAnalyzer) getKey(event *models.KeyEvent) string {
	return fmt.Sprintf("%d:%s:%s", event.DB, event.EventType, event.Key)
}

func (a *HotKeyAnalyzer) checkRotateWindow() {
	if time.Since(a.windowStart) > a.windowSize {
		a.keyMap = make(map[string]*KeyEventTracker)
		a.windowStart = time.Now()
	}
}

func (a *HotKeyAnalyzer) evictLeastActive() {
	var leastKey string
	var leastCount int64 = 1<<63 - 1

	for k, v := range a.keyMap {
		if v.count < leastCount {
			leastCount = v.count
			leastKey = k
		}
	}

	if leastKey != "" {
		delete(a.keyMap, leastKey)
	}
}

func (a *HotKeyAnalyzer) GetTopKeys(limit int) []models.KeyEventCount {
	a.mu.RLock()
	defer a.mu.RUnlock()

	result := make([]models.KeyEventCount, 0, len(a.keyMap))

	for k, v := range a.keyMap {
		result = append(result, models.KeyEventCount{
			Key:       extractKeyFromTrackerKey(k),
			Count:     v.count,
			EventType: v.eventType,
			DB:        v.db,
		})
	}

	sort.Slice(result, func(i, j int) bool {
		return result[i].Count > result[j].Count
	})

	if len(result) > limit {
		result = result[:limit]
	}

	return result
}

func (a *HotKeyAnalyzer) GetTopKeysByEventType(eventType string, limit int) []models.KeyEventCount {
	a.mu.RLock()
	defer a.mu.RUnlock()

	result := make([]models.KeyEventCount, 0)

	for k, v := range a.keyMap {
		if v.eventType == eventType {
			result = append(result, models.KeyEventCount{
				Key:       extractKeyFromTrackerKey(k),
				Count:     v.count,
				EventType: v.eventType,
				DB:        v.db,
			})
		}
	}

	sort.Slice(result, func(i, j int) bool {
		return result[i].Count > result[j].Count
	})

	if len(result) > limit {
		result = result[:limit]
	}

	return result
}

func (a *HotKeyAnalyzer) GetTotalCount() int64 {
	a.mu.RLock()
	defer a.mu.RUnlock()

	var total int64
	for _, v := range a.keyMap {
		total += v.count
	}
	return total
}

func (a *HotKeyAnalyzer) Reset() {
	a.mu.Lock()
	defer a.mu.Unlock()
	a.keyMap = make(map[string]*KeyEventTracker)
	a.windowStart = time.Now()
}

func extractKeyFromTrackerKey(fullKey string) string {
	parts := strings.SplitN(fullKey, ":", 3)
	if len(parts) >= 3 {
		return parts[2]
	}
	return fullKey
}
