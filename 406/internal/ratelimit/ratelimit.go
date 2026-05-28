package ratelimit

import (
	"math"
	"math/rand"
	"sync"
	"time"
	"health-check/internal/model"
)

type RateLimiter interface {
	Allow() bool
	Wait() time.Duration
	GetDelay() time.Duration
}

type TokenBucket struct {
	mu         sync.Mutex
	rate       float64
	capacity   float64
	tokens     float64
	lastUpdate time.Time
	delayCfg   *model.DelayConfig
}

func NewTokenBucket(rate, capacity int, delayCfg *model.DelayConfig) *TokenBucket {
	return &TokenBucket{
		rate:       float64(rate),
		capacity:   float64(capacity),
		tokens:     float64(capacity),
		lastUpdate: time.Now(),
		delayCfg:   delayCfg,
	}
}

func (tb *TokenBucket) Allow() bool {
	tb.mu.Lock()
	defer tb.mu.Unlock()

	now := time.Now()
	elapsed := now.Sub(tb.lastUpdate).Seconds()
	tb.tokens = math.Min(tb.capacity, tb.tokens+elapsed*tb.rate)
	tb.lastUpdate = now

	if tb.tokens >= 1.0 {
		tb.tokens -= 1.0
		return true
	}
	return false
}

func (tb *TokenBucket) Wait() time.Duration {
	if tb.Allow() {
		return tb.GetDelay()
	}
	return time.Duration(0)
}

func (tb *TokenBucket) GetDelay() time.Duration {
	if tb.delayCfg == nil {
		return 0
	}

	switch tb.delayCfg.Strategy {
	case model.DelayFixed:
		return time.Duration(tb.delayCfg.FixedDelayMs) * time.Millisecond
	case model.DelayRandom:
		min := tb.delayCfg.MinDelayMs
		max := tb.delayCfg.MaxDelayMs
		if max <= min {
			return time.Duration(min) * time.Millisecond
		}
		return time.Duration(min+rand.Intn(max-min)) * time.Millisecond
	case model.DelayExponential:
		delay := float64(tb.delayCfg.MinDelayMs) * math.Pow(2, float64(rand.Intn(5)))
		maxDelay := float64(tb.delayCfg.MaxDelayMs)
		if delay > maxDelay {
			delay = maxDelay
		}
		return time.Duration(delay) * time.Millisecond
	default:
		return 0
	}
}

type FixedWindow struct {
	mu       sync.Mutex
	window   time.Duration
	maxReq   int
	count    int
	resetAt  time.Time
	delayCfg *model.DelayConfig
}

func NewFixedWindow(windowSeconds, maxReq int, delayCfg *model.DelayConfig) *FixedWindow {
	return &FixedWindow{
		window:   time.Duration(windowSeconds) * time.Second,
		maxReq:   maxReq,
		count:    0,
		resetAt:  time.Now().Add(time.Duration(windowSeconds) * time.Second),
		delayCfg: delayCfg,
	}
}

func (fw *FixedWindow) Allow() bool {
	fw.mu.Lock()
	defer fw.mu.Unlock()

	now := time.Now()
	if now.After(fw.resetAt) {
		fw.count = 0
		fw.resetAt = now.Add(fw.window)
	}

	if fw.count < fw.maxReq {
		fw.count++
		return true
	}
	return false
}

func (fw *FixedWindow) Wait() time.Duration {
	if fw.Allow() {
		return fw.GetDelay()
	}
	return 0
}

func (fw *FixedWindow) GetDelay() time.Duration {
	if fw.delayCfg == nil {
		return 0
	}

	switch fw.delayCfg.Strategy {
	case model.DelayFixed:
		return time.Duration(fw.delayCfg.FixedDelayMs) * time.Millisecond
	case model.DelayRandom:
		min := fw.delayCfg.MinDelayMs
		max := fw.delayCfg.MaxDelayMs
		if max <= min {
			return time.Duration(min) * time.Millisecond
		}
		return time.Duration(min+rand.Intn(max-min)) * time.Millisecond
	case model.DelayExponential:
		delay := float64(fw.delayCfg.MinDelayMs) * math.Pow(2, float64(rand.Intn(5)))
		maxDelay := float64(fw.delayCfg.MaxDelayMs)
		if delay > maxDelay {
			delay = maxDelay
		}
		return time.Duration(delay) * time.Millisecond
	default:
		return 0
	}
}

type Manager struct {
	limiters map[string]RateLimiter
	mu       sync.RWMutex
}

func NewManager() *Manager {
	return &Manager{
		limiters: make(map[string]RateLimiter),
	}
}

func (m *Manager) GetOrCreate(endpointID string, cfg *model.RateLimitConfig) RateLimiter {
	m.mu.RLock()
	limiter, exists := m.limiters[endpointID]
	m.mu.RUnlock()

	if exists {
		return limiter
	}

	m.mu.Lock()
	defer m.mu.Unlock()

	if limiter, exists = m.limiters[endpointID]; exists {
		return limiter
	}

	switch cfg.Strategy {
	case model.RateLimitTokenBucket:
		limiter = NewTokenBucket(cfg.Rate, cfg.Capacity, cfg.Delay)
	case model.RateLimitFixedWindow:
		limiter = NewFixedWindow(1, cfg.Rate, cfg.Delay)
	default:
		limiter = NewTokenBucket(cfg.Rate, cfg.Capacity, cfg.Delay)
	}

	m.limiters[endpointID] = limiter
	return limiter
}

func (m *Manager) Remove(endpointID string) {
	m.mu.Lock()
	defer m.mu.Unlock()
	delete(m.limiters, endpointID)
}
