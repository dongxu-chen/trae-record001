package window

import (
	"sync"
	"sync/atomic"
	"time"
	"health-check/internal/model"
)

type Slot struct {
	StartTime     int64
	TotalProbes   int64
	SuccessCount  int64
	FailureCount  int64
	DegradeCount  int64
	TotalLatency  int64
	MaxLatency    int64
	Latencies     []int64
}

type SlidingWindow struct {
	mu           sync.RWMutex
	duration     int64
	slotDuration int64
	slotCount    int
	slots        []*Slot
	cursor       int
}

func New(durationSeconds int, slotCount int) *SlidingWindow {
	if durationSeconds <= 0 {
		durationSeconds = 60
	}
	if slotCount <= 0 {
		slotCount = 60
	}

	slotDuration := int64(durationSeconds * 1000 / slotCount)
	slots := make([]*Slot, slotCount)
	now := time.Now().UnixMilli()

	for i := range slots {
		slots[i] = &Slot{
			StartTime: now - int64(slotCount-i-1)*slotDuration,
			Latencies: make([]int64, 0, 100),
		}
	}

	return &SlidingWindow{
		duration:     int64(durationSeconds * 1000),
		slotDuration: slotDuration,
		slotCount:    slotCount,
		slots:        slots,
		cursor:       0,
	}
}

func (sw *SlidingWindow) Record(result *model.ProbeResult) {
	sw.mu.Lock()
	defer sw.mu.Unlock()

	now := time.Now().UnixMilli()
	sw.advanceWindow(now)

	slot := sw.slots[sw.cursor]
	atomic.AddInt64(&slot.TotalProbes, 1)

	switch result.Status {
	case model.StatusUp:
		atomic.AddInt64(&slot.SuccessCount, 1)
	case model.StatusDown:
		atomic.AddInt64(&slot.FailureCount, 1)
	case model.StatusDegrade:
		atomic.AddInt64(&slot.DegradeCount, 1)
	}

	latency := result.Latency.Milliseconds()
	atomic.AddInt64(&slot.TotalLatency, latency)

	for {
		currentMax := atomic.LoadInt64(&slot.MaxLatency)
		if latency <= currentMax || atomic.CompareAndSwapInt64(&slot.MaxLatency, currentMax, latency) {
			break
		}
	}

	if len(slot.Latencies) < 1000 {
		slot.Latencies = append(slot.Latencies, latency)
	}
}

func (sw *SlidingWindow) advanceWindow(now int64) {
	currentSlot := sw.slots[sw.cursor]
	elapsed := now - currentSlot.StartTime

	if elapsed >= sw.slotDuration {
		steps := int(elapsed / sw.slotDuration)
		if steps > sw.slotCount {
			steps = sw.slotCount
		}

		for i := 0; i < steps; i++ {
			sw.cursor = (sw.cursor + 1) % sw.slotCount
			newSlotStart := currentSlot.StartTime + int64(i+1)*sw.slotDuration

			sw.slots[sw.cursor] = &Slot{
				StartTime: newSlotStart,
				Latencies: make([]int64, 0, 100),
			}
		}
	}
}

func (sw *SlidingWindow) GetStats() *model.WindowStats {
	sw.mu.RLock()
	defer sw.mu.RUnlock()

	now := time.Now().UnixMilli()
	var totalProbes, successCount, failureCount, degradeCount int64
	var totalLatency, maxLatency int64
	var allLatencies []int64

	cutoff := now - sw.duration
	for _, slot := range sw.slots {
		if slot.StartTime >= cutoff {
			totalProbes += atomic.LoadInt64(&slot.TotalProbes)
			successCount += atomic.LoadInt64(&slot.SuccessCount)
			failureCount += atomic.LoadInt64(&slot.FailureCount)
			degradeCount += atomic.LoadInt64(&slot.DegradeCount)
			totalLatency += atomic.LoadInt64(&slot.TotalLatency)

			slotMax := atomic.LoadInt64(&slot.MaxLatency)
			if slotMax > maxLatency {
				maxLatency = slotMax
			}

			allLatencies = append(allLatencies, slot.Latencies...)
		}
	}

	stats := &model.WindowStats{
		TotalProbes:   int(totalProbes),
		SuccessCount:  int(successCount),
		FailureCount:  int(failureCount),
		DegradeCount:  int(degradeCount),
		MaxLatency:    time.Duration(maxLatency) * time.Millisecond,
		StartTime:     time.UnixMilli(cutoff),
		EndTime:       time.UnixMilli(now),
	}

	if totalProbes > 0 {
		stats.AvgLatency = time.Duration(totalLatency/totalProbes) * time.Millisecond
		stats.Availability = float64(successCount) / float64(totalProbes) * 100
		stats.ErrorRate = float64(failureCount) / float64(totalProbes) * 100
	} else {
		stats.Availability = 100.0
	}

	if len(allLatencies) > 0 {
		stats.P95Latency = calculateP95(allLatencies)
	}

	return stats
}

func calculateP95(latencies []int64) time.Duration {
	if len(latencies) == 0 {
		return 0
	}

	sorted := make([]int64, len(latencies))
	copy(sorted, latencies)

	for i := 1; i < len(sorted); i++ {
		key := sorted[i]
		j := i - 1
		for j >= 0 && sorted[j] > key {
			sorted[j+1] = sorted[j]
			j--
		}
		sorted[j+1] = key
	}

	index := int(float64(len(sorted)) * 0.95)
	if index >= len(sorted) {
		index = len(sorted) - 1
	}

	return time.Duration(sorted[index]) * time.Millisecond
}

func (sw *SlidingWindow) GetAvailability() float64 {
	return sw.GetStats().Availability
}
