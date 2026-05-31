package limiter

import (
	"math/rand"
	"sync"
	"time"

	"clickhouse-rate-limiter/config"
)

type State string

const (
	StateClosed   State = "closed"
	StateOpen     State = "open"
	StateHalfOpen State = "half_open"
)

type RecoveryStage int

const (
	StageProbe RecoveryStage = iota
	StageLowTraffic
	StageMediumTraffic
	StageHighTraffic
)

var recoveryStages = []struct {
	name            string
	allowRate       float64
	successRequired int
	minDuration     time.Duration
}{
	{"probe", 0.1, 3, 5 * time.Second},
	{"low_traffic", 0.3, 5, 10 * time.Second},
	{"medium_traffic", 0.6, 8, 15 * time.Second},
	{"high_traffic", 0.9, 10, 20 * time.Second},
}

type CircuitBreaker struct {
	config           config.CircuitBreakerConfig
	state            State
	failureCount     int
	successCount     int
	totalRequests    int
	halfOpenRequests int
	lastStateChange  time.Time
	recoveryStage    RecoveryStage
	stageStartTime   time.Time
	stageSuccesses   int
	mu               sync.RWMutex
	rand             *rand.Rand
}

func NewCircuitBreaker(cfg config.CircuitBreakerConfig) *CircuitBreaker {
	return &CircuitBreaker{
		config:          cfg,
		state:           StateClosed,
		lastStateChange: time.Now(),
		recoveryStage:   StageProbe,
		rand:            rand.New(rand.NewSource(time.Now().UnixNano())),
	}
}

func (cb *CircuitBreaker) Allow() bool {
	cb.mu.Lock()
	defer cb.mu.Unlock()

	switch cb.state {
	case StateClosed:
		return true

	case StateOpen:
		if time.Since(cb.lastStateChange) >= cb.config.Timeout {
			cb.transitionToHalfOpen()
			return cb.allowHalfOpen()
		}
		return false

	case StateHalfOpen:
		cb.advanceRecoveryStageIfNeeded()
		return cb.allowHalfOpen()

	default:
		return true
	}
}

func (cb *CircuitBreaker) transitionToHalfOpen() {
	cb.state = StateHalfOpen
	cb.recoveryStage = StageProbe
	cb.stageStartTime = time.Now()
	cb.stageSuccesses = 0
	cb.successCount = 0
	cb.halfOpenRequests = 0
	cb.lastStateChange = time.Now()
}

func (cb *CircuitBreaker) allowHalfOpen() bool {
	stage := recoveryStages[cb.recoveryStage]
	cb.halfOpenRequests++

	if cb.rand.Float64() < stage.allowRate {
		return true
	}

	return false
}

func (cb *CircuitBreaker) advanceRecoveryStageIfNeeded() {
	stage := recoveryStages[cb.recoveryStage]

	if time.Since(cb.stageStartTime) >= stage.minDuration &&
		cb.stageSuccesses >= stage.successRequired {

		if cb.recoveryStage < StageHighTraffic {
			cb.recoveryStage++
			cb.stageStartTime = time.Now()
			cb.stageSuccesses = 0
		} else {
			cb.transitionToClosed()
		}
	}
}

func (cb *CircuitBreaker) transitionToClosed() {
	cb.state = StateClosed
	cb.failureCount = 0
	cb.successCount = 0
	cb.totalRequests = 0
	cb.recoveryStage = StageProbe
	cb.lastStateChange = time.Now()
}

func (cb *CircuitBreaker) RecordSuccess() {
	cb.mu.Lock()
	defer cb.mu.Unlock()

	cb.totalRequests++

	switch cb.state {
	case StateHalfOpen:
		cb.successCount++
		cb.stageSuccesses++
		cb.advanceRecoveryStageIfNeeded()

	case StateClosed:
		cb.failureCount = 0
	}
}

func (cb *CircuitBreaker) RecordFailure() {
	cb.mu.Lock()
	defer cb.mu.Unlock()

	cb.failureCount++
	cb.totalRequests++

	if cb.totalRequests == 0 {
		return
	}

	failureRate := float64(cb.failureCount) / float64(cb.totalRequests)

	switch cb.state {
	case StateClosed:
		if failureRate >= cb.config.FailureThreshold {
			cb.transitionToOpen()
		}

	case StateHalfOpen:
		cb.transitionToOpen()
	}
}

func (cb *CircuitBreaker) transitionToOpen() {
	cb.state = StateOpen
	cb.lastStateChange = time.Now()
	cb.recoveryStage = StageProbe
	cb.stageSuccesses = 0
}

func (cb *CircuitBreaker) GetStatus() string {
	cb.mu.RLock()
	defer cb.mu.RUnlock()

	if cb.state == StateHalfOpen {
		stage := recoveryStages[cb.recoveryStage]
		return string(cb.state) + ":" + stage.name
	}

	return string(cb.state)
}

func (cb *CircuitBreaker) GetDetailedStatus() map[string]interface{} {
	cb.mu.RLock()
	defer cb.mu.RUnlock()

	failureRate := 0.0
	if cb.totalRequests > 0 {
		failureRate = float64(cb.failureCount) / float64(cb.totalRequests)
	}

	status := map[string]interface{}{
		"state":            string(cb.state),
		"failure_count":    cb.failureCount,
		"success_count":    cb.successCount,
		"total_requests":   cb.totalRequests,
		"failure_rate":     failureRate,
		"last_state_change": cb.lastStateChange,
	}

	if cb.state == StateHalfOpen {
		stage := recoveryStages[cb.recoveryStage]
		status["recovery_stage"] = map[string]interface{}{
			"stage":           cb.recoveryStage,
			"name":            stage.name,
			"allow_rate":      stage.allowRate,
			"success_required": stage.successRequired,
			"current_successes": cb.stageSuccesses,
			"elapsed_time":    time.Since(cb.stageStartTime),
			"min_duration":    stage.minDuration,
		}
		status["half_open_requests"] = cb.halfOpenRequests
	}

	return status
}

func (cb *CircuitBreaker) GetMetrics() (int, int, int, float64) {
	cb.mu.RLock()
	defer cb.mu.RUnlock()

	failureRate := 0.0
	if cb.totalRequests > 0 {
		failureRate = float64(cb.failureCount) / float64(cb.totalRequests)
	}

	return cb.failureCount, cb.successCount, cb.totalRequests, failureRate
}

func (cb *CircuitBreaker) GetRecoveryProgress() float64 {
	cb.mu.RLock()
	defer cb.mu.RUnlock()

	if cb.state != StateHalfOpen {
		if cb.state == StateClosed {
			return 100.0
		}
		return 0.0
	}

	stageProgress := float64(cb.recoveryStage) / float64(len(recoveryStages)-1) * 100
	return stageProgress
}

func (cb *CircuitBreaker) Reset() {
	cb.mu.Lock()
	defer cb.mu.Unlock()

	cb.state = StateClosed
	cb.failureCount = 0
	cb.successCount = 0
	cb.totalRequests = 0
	cb.recoveryStage = StageProbe
	cb.stageSuccesses = 0
	cb.halfOpenRequests = 0
	cb.lastStateChange = time.Now()
}
