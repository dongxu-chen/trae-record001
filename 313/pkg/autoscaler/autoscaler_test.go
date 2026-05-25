package autoscaler

import (
	"testing"
	"time"
)

func TestNewAutoscaler(t *testing.T) {
	scaleUpCalled := false
	scaleDownCalled := false

	scaleUp := func() error {
		scaleUpCalled = true
		return nil
	}
	scaleDown := func() error {
		scaleDownCalled = true
		return nil
	}

	a := NewAutoscaler(2, 10, 3, 1, 30*time.Second, scaleUp, scaleDown)

	if a == nil {
		t.Fatal("NewAutoscaler returned nil")
	}

	if a.minExecutors != 2 {
		t.Errorf("expected minExecutors 2, got %d", a.minExecutors)
	}

	if a.maxExecutors != 10 {
		t.Errorf("expected maxExecutors 10, got %d", a.maxExecutors)
	}

	if a.scaleUpThreshold != 3 {
		t.Errorf("expected scaleUpThreshold 3, got %d", a.scaleUpThreshold)
	}

	if a.scaleDownThreshold != 1 {
		t.Errorf("expected scaleDownThreshold 1, got %d", a.scaleDownThreshold)
	}

	if a.cooldownPeriod != 30*time.Second {
		t.Errorf("expected cooldownPeriod 30s, got %v", a.cooldownPeriod)
	}
}

func TestNewAutoscaler_InvalidMinExecutors(t *testing.T) {
	a := NewAutoscaler(0, 10, 3, 1, 30*time.Second, nil, nil)
	if a.minExecutors != 1 {
		t.Errorf("expected minExecutors 1 when 0 provided, got %d", a.minExecutors)
	}
}

func TestNewAutoscaler_MaxLessThanMin(t *testing.T) {
	a := NewAutoscaler(5, 3, 3, 1, 30*time.Second, nil, nil)
	if a.maxExecutors != 5 {
		t.Errorf("expected maxExecutors 5 when less than min, got %d", a.maxExecutors)
	}
}

func TestNewAutoscaler_InvalidScaleUpThreshold(t *testing.T) {
	a := NewAutoscaler(2, 10, 0, 1, 30*time.Second, nil, nil)
	if a.scaleUpThreshold != 3 {
		t.Errorf("expected scaleUpThreshold 3 when 0 provided, got %d", a.scaleUpThreshold)
	}
}

func TestNewAutoscaler_InvalidCooldown(t *testing.T) {
	a := NewAutoscaler(2, 10, 3, 1, 0, nil, nil)
	if a.cooldownPeriod != 30*time.Second {
		t.Errorf("expected cooldownPeriod 30s when 0 provided, got %v", a.cooldownPeriod)
	}
}

func TestCheckAndScale_ScaleUp(t *testing.T) {
	scaleUpCount := 0
	scaleDownCount := 0

	scaleUp := func() error {
		scaleUpCount++
		return nil
	}
	scaleDown := func() error {
		scaleDownCount++
		return nil
	}

	a := NewAutoscaler(2, 10, 3, 1, 0, scaleUp, scaleDown)

	direction, reason, err := a.CheckAndScale(3, 5, 3, 10*time.Second)
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}

	if direction != ScaleUp {
		t.Errorf("expected ScaleUp, got %s", direction)
	}

	if reason == "" {
		t.Error("expected non-empty reason")
	}

	if scaleUpCount != 1 {
		t.Errorf("expected scaleUp called 1 time, got %d", scaleUpCount)
	}

	if scaleDownCount != 0 {
		t.Errorf("expected scaleDown called 0 times, got %d", scaleDownCount)
	}
}

func TestCheckAndScale_ScaleUpMaxReached(t *testing.T) {
	scaleUpCalled := false

	scaleUp := func() error {
		scaleUpCalled = true
		return nil
	}

	a := NewAutoscaler(2, 5, 3, 1, 0, scaleUp, nil)

	direction, reason, err := a.CheckAndScale(5, 5, 5, 10*time.Second)
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}

	if direction != ScaleNone {
		t.Errorf("expected ScaleNone when max reached, got %s", direction)
	}

	if scaleUpCalled {
		t.Error("expected scaleUp not called when max reached")
	}

	if reason == "" {
		t.Error("expected non-empty reason")
	}
}

func TestCheckAndScale_ScaleDown(t *testing.T) {
	scaleUpCount := 0
	scaleDownCount := 0

	scaleUp := func() error {
		scaleUpCount++
		return nil
	}
	scaleDown := func() error {
		scaleDownCount++
		return nil
	}

	a := NewAutoscaler(2, 10, 3, 1, 0, scaleUp, scaleDown)

	direction, reason, err := a.CheckAndScale(5, 0, 3, 0)
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}

	if direction != ScaleDown {
		t.Errorf("expected ScaleDown, got %s", direction)
	}

	if reason == "" {
		t.Error("expected non-empty reason")
	}

	if scaleUpCount != 0 {
		t.Errorf("expected scaleUp called 0 times, got %d", scaleUpCount)
	}

	if scaleDownCount != 1 {
		t.Errorf("expected scaleDown called 1 time, got %d", scaleDownCount)
	}
}

func TestCheckAndScale_ScaleDownMinReached(t *testing.T) {
	scaleDownCalled := false

	scaleDown := func() error {
		scaleDownCalled = true
		return nil
	}

	a := NewAutoscaler(2, 10, 3, 1, 0, nil, scaleDown)

	direction, reason, err := a.CheckAndScale(2, 0, 1, 0)
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}

	if direction != ScaleNone {
		t.Errorf("expected ScaleNone when min reached, got %s", direction)
	}

	if scaleDownCalled {
		t.Error("expected scaleDown not called when min reached")
	}

	if reason == "" {
		t.Error("expected non-empty reason")
	}
}

func TestCheckAndScale_NoScale(t *testing.T) {
	scaleUpCalled := false
	scaleDownCalled := false

	scaleUp := func() error {
		scaleUpCalled = true
		return nil
	}
	scaleDown := func() error {
		scaleDownCalled = true
		return nil
	}

	a := NewAutoscaler(2, 10, 3, 1, 0, scaleUp, scaleDown)

	direction, reason, err := a.CheckAndScale(3, 1, 3, 5*time.Second)
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}

	if direction != ScaleNone {
		t.Errorf("expected ScaleNone, got %s", direction)
	}

	if scaleUpCalled {
		t.Error("expected scaleUp not called")
	}

	if scaleDownCalled {
		t.Error("expected scaleDown not called")
	}

	if reason == "" {
		t.Error("expected non-empty reason")
	}
}

func TestCheckAndScale_CooldownPeriod(t *testing.T) {
	scaleUpCount := 0

	scaleUp := func() error {
		scaleUpCount++
		return nil
	}

	a := NewAutoscaler(2, 10, 3, 1, 30*time.Second, scaleUp, nil)

	direction, _, err := a.CheckAndScale(3, 5, 3, 10*time.Second)
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if direction != ScaleUp {
		t.Fatalf("expected first scale up to succeed, got %s", direction)
	}

	direction, _, err = a.CheckAndScale(4, 5, 3, 10*time.Second)
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}

	if direction != ScaleNone {
		t.Errorf("expected ScaleNone during cooldown, got %s", direction)
	}

	if scaleUpCount != 1 {
		t.Errorf("expected scaleUp called only 1 time during cooldown, got %d", scaleUpCount)
	}
}

func TestCheckAndScale_ScaleUpDueToWaitTime(t *testing.T) {
	scaleUpCalled := false

	scaleUp := func() error {
		scaleUpCalled = true
		return nil
	}

	a := NewAutoscaler(2, 10, 10, 1, 0, scaleUp, nil)

	direction, _, err := a.CheckAndScale(3, 2, 3, 45*time.Second)
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}

	if direction != ScaleUp {
		t.Errorf("expected ScaleUp due to long wait time, got %s", direction)
	}

	if !scaleUpCalled {
		t.Error("expected scaleUp called for long wait time")
	}
}

func TestCheckAndScale_ScaleDownNoIdleExecutors(t *testing.T) {
	scaleDownCalled := false

	scaleDown := func() error {
		scaleDownCalled = true
		return nil
	}

	a := NewAutoscaler(2, 10, 3, 1, 0, nil, scaleDown)

	direction, _, err := a.CheckAndScale(5, 0, 5, 0)
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}

	if direction != ScaleNone {
		t.Errorf("expected ScaleNone when no idle executors, got %s", direction)
	}

	if scaleDownCalled {
		t.Error("expected scaleDown not called when no idle executors")
	}
}

func TestScaleDirection_String(t *testing.T) {
	tests := []struct {
		dir      ScaleDirection
		expected string
	}{
		{ScaleUp, "SCALE_UP"},
		{ScaleDown, "SCALE_DOWN"},
		{ScaleNone, "NO_SCALE"},
		{ScaleDirection("unknown"), "NO_SCALE"},
	}

	for _, tt := range tests {
		t.Run(string(tt.dir), func(t *testing.T) {
			if tt.dir.String() != tt.expected {
				t.Errorf("expected %s, got %s", tt.expected, tt.dir.String())
			}
		})
	}
}

func TestGetScalingHistory(t *testing.T) {
	scaleUp := func() error { return nil }
	scaleDown := func() error { return nil }

	a := NewAutoscaler(2, 10, 3, 1, 0, scaleUp, scaleDown)

	history := a.GetScalingHistory()
	if len(history) != 0 {
		t.Errorf("expected empty history initially, got %d events", len(history))
	}

	a.CheckAndScale(3, 5, 3, 10*time.Second)

	history = a.GetScalingHistory()
	if len(history) != 1 {
		t.Errorf("expected 1 event after scale up, got %d", len(history))
	}

	if history[0].Direction != ScaleUp {
		t.Errorf("expected ScaleUp event, got %s", history[0].Direction)
	}

	if history[0].ExecutorCount != 4 {
		t.Errorf("expected ExecutorCount 4, got %d", history[0].ExecutorCount)
	}
}

func TestSetCallbacks(t *testing.T) {
	a := NewAutoscaler(2, 10, 3, 1, 0, nil, nil)

	customCalled := false
	customFunc := func() error {
		customCalled = true
		return nil
	}

	a.SetScaleUpCallback(customFunc)
	a.SetScaleDownCallback(customFunc)

	_, _, err := a.CheckAndScale(3, 5, 3, 10*time.Second)
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}

	if !customCalled {
		t.Error("expected custom scaleUp callback to be called")
	}
}

func TestEvaluateScaling(t *testing.T) {
	a := NewAutoscaler(2, 10, 3, 1, 0, nil, nil)

	tests := []struct {
		name          string
		executorCount int
		pendingCount  int
		runningCount  int
		avgWaitTime   time.Duration
		expectedDir   ScaleDirection
	}{
		{
			name:          "No scale - normal load",
			executorCount: 3,
			pendingCount:  2,
			runningCount:  3,
			avgWaitTime:   5 * time.Second,
			expectedDir:   ScaleNone,
		},
		{
			name:          "Scale up - pending above threshold",
			executorCount: 3,
			pendingCount:  5,
			runningCount:  3,
			avgWaitTime:   5 * time.Second,
			expectedDir:   ScaleUp,
		},
		{
			name:          "Scale up - long wait time",
			executorCount: 3,
			pendingCount:  2,
			runningCount:  3,
			avgWaitTime:   45 * time.Second,
			expectedDir:   ScaleUp,
		},
		{
			name:          "No scale up - already at max",
			executorCount: 10,
			pendingCount:  5,
			runningCount:  10,
			avgWaitTime:   5 * time.Second,
			expectedDir:   ScaleNone,
		},
		{
			name:          "Scale down - idle executors",
			executorCount: 5,
			pendingCount:  0,
			runningCount:  3,
			avgWaitTime:   0,
			expectedDir:   ScaleDown,
		},
		{
			name:          "No scale down - no idle executors",
			executorCount: 5,
			pendingCount:  0,
			runningCount:  5,
			avgWaitTime:   0,
			expectedDir:   ScaleNone,
		},
		{
			name:          "No scale down - already at min",
			executorCount: 2,
			pendingCount:  0,
			runningCount:  1,
			avgWaitTime:   0,
			expectedDir:   ScaleNone,
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			dir, _ := a.evaluateScaling(tt.executorCount, tt.pendingCount, tt.runningCount, tt.avgWaitTime)
			if dir != tt.expectedDir {
				t.Errorf("expected %s, got %s", tt.expectedDir, dir)
			}
		})
	}
}
