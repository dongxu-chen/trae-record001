package autoscaler

import (
	"fmt"
	"sync"
	"time"
)

type ScaleDirection string

const (
	ScaleUp   ScaleDirection = "scale_up"
	ScaleDown ScaleDirection = "scale_down"
	ScaleNone ScaleDirection = "no_scale"
)

type ScalingEvent struct {
	Timestamp          time.Time
	Direction          ScaleDirection
	Reason             string
	ExecutorCount      int
	PendingCount       int
	RunningCount       int
	AvgWaitTime        time.Duration
}

type Autoscaler struct {
	mu                 sync.Mutex
	minExecutors       int
	maxExecutors       int
	scaleUpThreshold   int
	scaleDownThreshold int
	cooldownPeriod     time.Duration
	lastScaleTime      time.Time
	lastScaleDir       ScaleDirection
	scalingEvents      []ScalingEvent
	scaleUpCallback    func() error
	scaleDownCallback  func() error
	executorCounter    int
}

func NewAutoscaler(
	minExecutors int,
	maxExecutors int,
	scaleUpThreshold int,
	scaleDownThreshold int,
	cooldownPeriod time.Duration,
	scaleUpCallback func() error,
	scaleDownCallback func() error,
) *Autoscaler {
	if minExecutors < 1 {
		minExecutors = 1
	}
	if maxExecutors < minExecutors {
		maxExecutors = minExecutors
	}
	if scaleUpThreshold < 1 {
		scaleUpThreshold = 3
	}
	if cooldownPeriod <= 0 {
		cooldownPeriod = 30 * time.Second
	}

	return &Autoscaler{
		minExecutors:       minExecutors,
		maxExecutors:       maxExecutors,
		scaleUpThreshold:   scaleUpThreshold,
		scaleDownThreshold: scaleDownThreshold,
		cooldownPeriod:     cooldownPeriod,
		lastScaleTime:      time.Time{},
		lastScaleDir:       ScaleNone,
		scalingEvents:      make([]ScalingEvent, 0),
		scaleUpCallback:    scaleUpCallback,
		scaleDownCallback:  scaleDownCallback,
		executorCounter:    100,
	}
}

func (a *Autoscaler) CheckAndScale(
	executorCount int,
	pendingCount int,
	runningCount int,
	avgWaitTime time.Duration,
) (ScaleDirection, string, error) {
	a.mu.Lock()
	defer a.mu.Unlock()

	now := time.Now()
	if !a.lastScaleTime.IsZero() && now.Sub(a.lastScaleTime) < a.cooldownPeriod {
		return ScaleNone, fmt.Sprintf("cool down period, next check at %v",
			a.lastScaleTime.Add(a.cooldownPeriod).Format("15:04:05")), nil
	}

	direction, reason := a.evaluateScaling(executorCount, pendingCount, runningCount, avgWaitTime)

	switch direction {
	case ScaleUp:
		if executorCount >= a.maxExecutors {
			return ScaleNone, fmt.Sprintf("max executors reached (%d/%d)", executorCount, a.maxExecutors), nil
		}

		if a.scaleUpCallback != nil {
			if err := a.scaleUpCallback(); err != nil {
				return ScaleNone, "", fmt.Errorf("scale up callback failed: %w", err)
			}
		}

		a.recordScalingEvent(ScaleUp, reason, executorCount+1, pendingCount, runningCount, avgWaitTime)
		return ScaleUp, fmt.Sprintf("scaled up to %d executors: %s", executorCount+1, reason), nil

	case ScaleDown:
		if executorCount <= a.minExecutors {
			return ScaleNone, fmt.Sprintf("min executors reached (%d/%d)", executorCount, a.minExecutors), nil
		}

		if a.scaleDownCallback != nil {
			if err := a.scaleDownCallback(); err != nil {
				return ScaleNone, "", fmt.Errorf("scale down callback failed: %w", err)
			}
		}

		a.recordScalingEvent(ScaleDown, reason, executorCount-1, pendingCount, runningCount, avgWaitTime)
		return ScaleDown, fmt.Sprintf("scaled down to %d executors: %s", executorCount-1, reason), nil

	default:
		return ScaleNone, fmt.Sprintf("no scaling needed (pending=%d, running=%d, executors=%d)",
			pendingCount, runningCount, executorCount), nil
	}
}

func (a *Autoscaler) evaluateScaling(
	executorCount int,
	pendingCount int,
	runningCount int,
	avgWaitTime time.Duration,
) (ScaleDirection, string) {

	if pendingCount >= a.scaleUpThreshold && executorCount < a.maxExecutors {
		return ScaleUp, fmt.Sprintf("pending tasks (%d) >= threshold (%d)",
			pendingCount, a.scaleUpThreshold)
	}

	if avgWaitTime > 30*time.Second && executorCount < a.maxExecutors {
		return ScaleUp, fmt.Sprintf("avg wait time (%v) > threshold (30s)", avgWaitTime)
	}

	if pendingCount <= a.scaleDownThreshold &&
		runningCount < executorCount &&
		executorCount > a.minExecutors {

		idleCount := executorCount - runningCount
		if idleCount > 0 {
			return ScaleDown, fmt.Sprintf("%d idle executors, pending tasks <= %d",
				idleCount, a.scaleDownThreshold)
		}
	}

	return ScaleNone, ""
}

func (a *Autoscaler) recordScalingEvent(
	direction ScaleDirection,
	reason string,
	executorCount int,
	pendingCount int,
	runningCount int,
	avgWaitTime time.Duration,
) {
	event := ScalingEvent{
		Timestamp:     time.Now(),
		Direction:     direction,
		Reason:        reason,
		ExecutorCount: executorCount,
		PendingCount:  pendingCount,
		RunningCount:  runningCount,
		AvgWaitTime:   avgWaitTime,
	}

	a.scalingEvents = append(a.scalingEvents, event)
	a.lastScaleTime = event.Timestamp
	a.lastScaleDir = direction

	if len(a.scalingEvents) > 100 {
		a.scalingEvents = a.scalingEvents[1:]
	}
}

func (a *Autoscaler) SetScaleUpCallback(callback func() error) {
	a.mu.Lock()
	defer a.mu.Unlock()
	a.scaleUpCallback = callback
}

func (a *Autoscaler) SetScaleDownCallback(callback func() error) {
	a.mu.Lock()
	defer a.mu.Unlock()
	a.scaleDownCallback = callback
}

func (a *Autoscaler) GetScalingHistory() []ScalingEvent {
	a.mu.Lock()
	defer a.mu.Unlock()

	history := make([]ScalingEvent, len(a.scalingEvents))
	copy(history, a.scalingEvents)
	return history
}

func (a *Autoscaler) PrintStatus() {
	a.mu.Lock()
	defer a.mu.Unlock()

	fmt.Println("\n=== Autoscaler Status ===")
	fmt.Printf("Executors Range: %d-%d\n", a.minExecutors, a.maxExecutors)
	fmt.Printf("Scale Up Threshold: %d pending tasks\n", a.scaleUpThreshold)
	fmt.Printf("Scale Down Threshold: %d pending tasks\n", a.scaleDownThreshold)
	fmt.Printf("Cooldown Period: %v\n", a.cooldownPeriod)

	if !a.lastScaleTime.IsZero() {
		fmt.Printf("Last Scale: %v (%s) at %s\n",
			a.lastScaleDir,
			a.lastScaleTime.Format("15:04:05"),
			time.Since(a.lastScaleTime).Round(time.Second))
	}

	coolDownRemaining := time.Duration(0)
	if !a.lastScaleTime.IsZero() {
		elapsed := time.Since(a.lastScaleTime)
		if elapsed < a.cooldownPeriod {
			coolDownRemaining = a.cooldownPeriod - elapsed
		}
	}
	if coolDownRemaining > 0 {
		fmt.Printf("Cool Down Remaining: %v\n", coolDownRemaining.Round(time.Second))
	}

	if len(a.scalingEvents) > 0 {
		fmt.Println("\nRecent Scaling Events:")
		fmt.Printf("%-20s %-12s %-8s %-8s %-8s %s\n",
			"Time", "Direction", "Executors", "Pending", "Running", "Reason")
		fmt.Println("--------------------------------------------------------------------------------")

		startIdx := 0
		if len(a.scalingEvents) > 5 {
			startIdx = len(a.scalingEvents) - 5
		}
		for i := startIdx; i < len(a.scalingEvents); i++ {
			event := a.scalingEvents[i]
			fmt.Printf("%-20s %-12s %-8d %-8d %-8d %s\n",
				event.Timestamp.Format("15:04:05"),
				event.Direction,
				event.ExecutorCount,
				event.PendingCount,
				event.RunningCount,
				event.Reason)
		}
		fmt.Println("================================================================================")
	}
	fmt.Println()
}

func (sd ScaleDirection) String() string {
	switch sd {
	case ScaleUp:
		return "SCALE_UP"
	case ScaleDown:
		return "SCALE_DOWN"
	default:
		return "NO_SCALE"
	}
}
