package limiter

import (
	"sync"
	"time"

	"clickhouse-rate-limiter/config"
	"golang.org/x/time/rate"
)

type RateLimiter struct {
	config         config.LimiterConfig
	globalLimiter  *rate.Limiter
	userLimiters   map[string]*userLimiter
	circuitBreaker *CircuitBreaker
	mu             sync.RWMutex
}

type userLimiter struct {
	limiter    *rate.Limiter
	lastAccess time.Time
}

type LimitStatus struct {
	Allowed      bool
	Reason       string
	GlobalTokens int
	UserTokens   int
}

func NewRateLimiter(cfg config.LimiterConfig) *RateLimiter {
	rl := &RateLimiter{
		config:         cfg,
		globalLimiter:  rate.NewLimiter(rate.Limit(cfg.GlobalRate), cfg.GlobalBurst),
		userLimiters:   make(map[string]*userLimiter),
		circuitBreaker: NewCircuitBreaker(cfg.CircuitBreaker),
	}

	go rl.cleanupUserLimiters()

	return rl
}

func (rl *RateLimiter) Allow(userID string, scanRows, memoryBytes int64) *LimitStatus {
	if !rl.circuitBreaker.Allow() {
		return &LimitStatus{
			Allowed: false,
			Reason:  "circuit_breaker_open",
		}
	}

	if scanRows > rl.config.MaxScanRows {
		rl.circuitBreaker.RecordFailure()
		return &LimitStatus{
			Allowed: false,
			Reason:  "scan_rows_exceeded",
		}
	}

	if memoryBytes > rl.config.MaxMemoryBytes {
		rl.circuitBreaker.RecordFailure()
		return &LimitStatus{
			Allowed: false,
			Reason:  "memory_exceeded",
		}
	}

	if !rl.globalLimiter.Allow() {
		return &LimitStatus{
			Allowed: false,
			Reason:  "global_rate_limit_exceeded",
		}
	}

	userLimiter := rl.getUserLimiter(userID)
	if !userLimiter.Allow() {
		return &LimitStatus{
			Allowed: false,
			Reason:  "user_rate_limit_exceeded",
		}
	}

	rl.circuitBreaker.RecordSuccess()

	return &LimitStatus{
		Allowed: true,
	}
}

func (rl *RateLimiter) getUserLimiter(userID string) *rate.Limiter {
	rl.mu.RLock()
	ul, exists := rl.userLimiters[userID]
	rl.mu.RUnlock()

	if exists {
		ul.lastAccess = time.Now()
		return ul.limiter
	}

	rl.mu.Lock()
	defer rl.mu.Unlock()

	if ul, exists = rl.userLimiters[userID]; exists {
		ul.lastAccess = time.Now()
		return ul.limiter
	}

	ul = &userLimiter{
		limiter:    rate.NewLimiter(rate.Limit(rl.config.UserRate), rl.config.UserBurst),
		lastAccess: time.Now(),
	}
	rl.userLimiters[userID] = ul

	return ul.limiter
}

func (rl *RateLimiter) cleanupUserLimiters() {
	ticker := time.NewTicker(5 * time.Minute)
	defer ticker.Stop()

	for range ticker.C {
		rl.mu.Lock()
		for userID, ul := range rl.userLimiters {
			if time.Since(ul.lastAccess) > time.Hour {
				delete(rl.userLimiters, userID)
			}
		}
		rl.mu.Unlock()
	}
}

func (rl *RateLimiter) GetCircuitBreakerStatus() string {
	return rl.circuitBreaker.GetStatus()
}

func (rl *RateLimiter) GetCircuitBreakerDetail() map[string]interface{} {
	return rl.circuitBreaker.GetDetailedStatus()
}

func (rl *RateLimiter) GetRecoveryProgress() float64 {
	return rl.circuitBreaker.GetRecoveryProgress()
}

func (rl *RateLimiter) RecordFailure() {
	rl.circuitBreaker.RecordFailure()
}

func (rl *RateLimiter) RecordSuccess() {
	rl.circuitBreaker.RecordSuccess()
}
