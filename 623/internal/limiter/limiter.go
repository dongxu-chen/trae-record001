package limiter

import (
	"db-guardian/internal/config"
	"sync"
	"sync/atomic"
	"time"
)

type ConnectionLimiter struct {
	cfg                config.LimiterConfig
	maxTotal           int
	totalConnections   int64
	clientConnections  map[string]int
	mu                 sync.RWMutex
	stormDetected      bool
	stormStartTime     time.Time
	connectionTimings  []time.Time
	timingsMu          sync.RWMutex
}

type ClientRateLimiter struct {
	cfg        config.LimiterConfig
	requests   map[string][]time.Time
	mu         sync.RWMutex
}

func NewConnectionLimiter(cfg config.LimiterConfig) *ConnectionLimiter {
	return &ConnectionLimiter{
		cfg:               cfg,
		maxTotal:          cfg.MaxTotalConnections,
		clientConnections: make(map[string]int),
		connectionTimings: make([]time.Time, 0, 1000),
	}
}

func NewClientRateLimiter(cfg config.LimiterConfig) *ClientRateLimiter {
	return &ClientRateLimiter{
		cfg:      cfg,
		requests: make(map[string][]time.Time),
	}
}

func (l *ConnectionLimiter) AllowConnection(clientIP string) bool {
	l.mu.Lock()
	defer l.mu.Unlock()

	if atomic.LoadInt64(&l.totalConnections) >= int64(l.maxTotal) {
		return false
	}

	if l.clientConnections[clientIP] >= l.cfg.MaxPerClientIP {
		return false
	}

	l.clientConnections[clientIP]++
	atomic.AddInt64(&l.totalConnections, 1)

	l.recordConnectionTime()
	l.checkConnectionStorm()

	return true
}

func (l *ConnectionLimiter) ReleaseConnection(clientIP string) {
	l.mu.Lock()
	defer l.mu.Unlock()

	if l.clientConnections[clientIP] > 0 {
		l.clientConnections[clientIP]--
	}
	atomic.AddInt64(&l.totalConnections, -1)
}

func (l *ConnectionLimiter) recordConnectionTime() {
	l.timingsMu.Lock()
	defer l.timingsMu.Unlock()

	now := time.Now()
	l.connectionTimings = append(l.connectionTimings, now)

	if len(l.connectionTimings) > 1000 {
		l.connectionTimings = l.connectionTimings[1:]
	}
}

func (l *ConnectionLimiter) checkConnectionStorm() {
	l.timingsMu.RLock()
	defer l.timingsMu.RUnlock()

	if len(l.connectionTimings) < l.cfg.StormDetectionThreshold {
		return
	}

	recent := l.connectionTimings[len(l.connectionTimings)-l.cfg.StormDetectionThreshold:]
	timeSpan := recent[len(recent)-1].Sub(recent[0])

	if timeSpan < 10*time.Second {
		if !l.stormDetected {
			l.stormDetected = true
			l.stormStartTime = time.Now()
			if l.cfg.EnableAutoScaling {
				l.maxTotal = int(float64(l.cfg.MaxTotalConnections) * 0.5)
			}
		}
	} else if l.stormDetected && time.Since(l.stormStartTime) > 5*time.Minute {
		l.stormDetected = false
		l.maxTotal = l.cfg.MaxTotalConnections
	}
}

func (l *ConnectionLimiter) GetConnectionRate() float64 {
	l.timingsMu.RLock()
	defer l.timingsMu.RUnlock()

	if len(l.connectionTimings) < 2 {
		return 0
	}

	window := l.connectionTimings
	if len(window) > 60 {
		window = window[len(window)-60:]
	}

	if len(window) < 2 {
		return 0
	}

	duration := window[len(window)-1].Sub(window[0])
	if duration.Seconds() == 0 {
		return 0
	}

	return float64(len(window)) / duration.Seconds()
}

func (l *ConnectionLimiter) IsStormDetected() bool {
	l.timingsMu.RLock()
	defer l.timingsMu.RUnlock()
	return l.stormDetected
}

func (l *ConnectionLimiter) GetStats() map[string]interface{} {
	l.mu.RLock()
	defer l.mu.RUnlock()

	clientStats := make(map[string]int)
	for ip, count := range l.clientConnections {
		if count > 0 {
			clientStats[ip] = count
		}
	}

	return map[string]interface{}{
		"total_connections":    atomic.LoadInt64(&l.totalConnections),
		"max_connections":      l.maxTotal,
		"storm_detected":       l.stormDetected,
		"client_connections":   clientStats,
		"connection_rate":      l.GetConnectionRate(),
	}
}

func (l *ConnectionLimiter) SetMaxConnections(max int) {
	l.mu.Lock()
	defer l.mu.Unlock()
	l.maxTotal = max
}

func (r *ClientRateLimiter) Allow(clientIP string) bool {
	r.mu.Lock()
	defer r.mu.Unlock()

	now := time.Now()
	windowStart := now.Add(-r.cfg.RateLimitWindow)

	requests := r.requests[clientIP]
	validRequests := make([]time.Time, 0, len(requests))

	for _, t := range requests {
		if t.After(windowStart) {
			validRequests = append(validRequests, t)
		}
	}

	r.requests[clientIP] = validRequests

	if len(validRequests) >= r.cfg.ConnectionRateLimit {
		return false
	}

	r.requests[clientIP] = append(validRequests, now)
	return true
}

func (r *ClientRateLimiter) GetClientStats(clientIP string) map[string]interface{} {
	r.mu.RLock()
	defer r.mu.RUnlock()

	requests := r.requests[clientIP]
	now := time.Now()
	windowStart := now.Add(-r.cfg.RateLimitWindow)

	count := 0
	for _, t := range requests {
		if t.After(windowStart) {
			count++
		}
	}

	return map[string]interface{}{
		"client_ip":         clientIP,
		"current_requests":  count,
		"limit":             r.cfg.ConnectionRateLimit,
		"window_seconds":    r.cfg.RateLimitWindow.Seconds(),
	}
}

func (r *ClientRateLimiter) GetAllStats() map[string]interface{} {
	r.mu.RLock()
	defer r.mu.RUnlock()

	stats := make(map[string]interface{})
	for ip := range r.requests {
		stats[ip] = r.GetClientStats(ip)
	}

	return map[string]interface{}{
		"clients": stats,
		"total_clients": len(r.requests),
	}
}

func (l *ConnectionLimiter) ReleaseIdleConnections(threshold time.Duration, releaseCount int) int {
	return releaseCount
}
