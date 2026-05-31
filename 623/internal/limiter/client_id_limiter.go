package limiter

import (
	"db-guardian/internal/config"
	"sync"
	"sync/atomic"
	"time"
)

type ClientIdentifier struct {
	ClientID  string
	ClientIP  string
	AppName   string
	ProcessID string
	Username  string
}

type ClientIDLimiter struct {
	cfg                config.LimiterConfig
	clientLimits       map[string]*ClientLimitState
	clientIdentifiers  map[string]*ClientIdentifier
	mu                 sync.RWMutex
	totalConnections   int64
	maxTotal           int
	rateLimitWindow    time.Duration
	connectionTimings  []time.Time
	timingsMu          sync.RWMutex
	stormDetected      bool
	stormStartTime     time.Time
}

type ClientLimitState struct {
	ID               string
	CurrentConnCount int64
	MaxConnLimit     int
	RequestTimings   []time.Time
	RateLimit        int
	Blocked          bool
	BlockedUntil     time.Time
	LastActive       time.Time
}

type ClientLimitConfig struct {
	ClientID      string
	MaxConnections int
	RateLimit     int
}

func NewClientIDLimiter(cfg config.LimiterConfig) *ClientIDLimiter {
	return &ClientIDLimiter{
		cfg:               cfg,
		clientLimits:      make(map[string]*ClientLimitState),
		clientIdentifiers: make(map[string]*ClientIdentifier),
		maxTotal:          cfg.MaxTotalConnections,
		rateLimitWindow:   cfg.RateLimitWindow,
		connectionTimings: make([]time.Time, 0, 1000),
	}
}

func (l *ClientIDLimiter) AllowConnection(clientID string, ident *ClientIdentifier) bool {
	l.mu.Lock()
	defer l.mu.Unlock()

	if atomic.LoadInt64(&l.totalConnections) >= int64(l.maxTotal) {
		return false
	}

	state, exists := l.clientLimits[clientID]
	if !exists {
		state = &ClientLimitState{
			ID:               clientID,
			CurrentConnCount: 0,
			MaxConnLimit:     l.cfg.MaxPerClientIP,
			RateLimit:        l.cfg.ConnectionRateLimit,
			RequestTimings:   make([]time.Time, 0, l.cfg.ConnectionRateLimit*2),
			LastActive:       time.Now(),
		}
		l.clientLimits[clientID] = state
		l.clientIdentifiers[clientID] = ident
	}

	if state.Blocked && time.Now().Before(state.BlockedUntil) {
		return false
	}
	state.Blocked = false

	if state.CurrentConnCount >= int64(state.MaxConnLimit) {
		return false
	}

	if !l.checkRateLimit(state) {
		return false
	}

	state.CurrentConnCount++
	state.LastActive = time.Now()
	atomic.AddInt64(&l.totalConnections, 1)

	l.recordConnectionTime()
	l.checkConnectionStorm()

	return true
}

func (l *ClientIDLimiter) checkRateLimit(state *ClientLimitState) bool {
	now := time.Now()
	windowStart := now.Add(-l.rateLimitWindow)

	validTimings := make([]time.Time, 0, len(state.RequestTimings))
	for _, t := range state.RequestTimings {
		if t.After(windowStart) {
			validTimings = append(validTimings, t)
		}
	}

	state.RequestTimings = validTimings

	if len(validTimings) >= state.RateLimit {
		l.triggerClientBlock(state)
		return false
	}

	state.RequestTimings = append(validTimings, now)
	return true
}

func (l *ClientIDLimiter) triggerClientBlock(state *ClientLimitState) {
	state.Blocked = true
	state.BlockedUntil = time.Now().Add(5 * time.Minute)
}

func (l *ClientIDLimiter) ReleaseConnection(clientID string) {
	l.mu.Lock()
	defer l.mu.Unlock()

	if state, exists := l.clientLimits[clientID]; exists {
		if state.CurrentConnCount > 0 {
			state.CurrentConnCount--
		}
		state.LastActive = time.Now()
	}
	atomic.AddInt64(&l.totalConnections, -1)
}

func (l *ClientIDLimiter) recordConnectionTime() {
	l.timingsMu.Lock()
	defer l.timingsMu.Unlock()

	now := time.Now()
	l.connectionTimings = append(l.connectionTimings, now)

	if len(l.connectionTimings) > 1000 {
		l.connectionTimings = l.connectionTimings[1:]
	}
}

func (l *ClientIDLimiter) checkConnectionStorm() {
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

func (l *ClientIDLimiter) GetConnectionRate() float64 {
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

func (l *ClientIDLimiter) SetClientLimit(clientID string, maxConnections, rateLimit int) {
	l.mu.Lock()
	defer l.mu.Unlock()

	if state, exists := l.clientLimits[clientID]; exists {
		state.MaxConnLimit = maxConnections
		state.RateLimit = rateLimit
	} else {
		l.clientLimits[clientID] = &ClientLimitState{
			ID:               clientID,
			CurrentConnCount: 0,
			MaxConnLimit:     maxConnections,
			RateLimit:        rateLimit,
			RequestTimings:   make([]time.Time, 0, rateLimit*2),
			LastActive:       time.Now(),
		}
	}
}

func (l *ClientIDLimiter) UnblockClient(clientID string) bool {
	l.mu.Lock()
	defer l.mu.Unlock()

	if state, exists := l.clientLimits[clientID]; exists {
		state.Blocked = false
		state.BlockedUntil = time.Time{}
		return true
	}
	return false
}

func (l *ClientIDLimiter) GetClientStats(clientID string) map[string]interface{} {
	l.mu.RLock()
	defer l.mu.RUnlock()

	state, exists := l.clientLimits[clientID]
	if !exists {
		return nil
	}

	ident := l.clientIdentifiers[clientID]

	return map[string]interface{}{
		"client_id":          clientID,
		"current_connections": state.CurrentConnCount,
		"max_connections":    state.MaxConnLimit,
		"rate_limit":         state.RateLimit,
		"is_blocked":         state.Blocked,
		"blocked_until":      state.BlockedUntil,
		"last_active":        state.LastActive,
		"app_name":           ident.AppName,
		"process_id":         ident.ProcessID,
		"username":           ident.Username,
		"client_ip":          ident.ClientIP,
	}
}

func (l *ClientIDLimiter) GetAllClientStats() []map[string]interface{} {
	l.mu.RLock()
	defer l.mu.RUnlock()

	result := make([]map[string]interface{}, 0, len(l.clientLimits))
	for clientID := range l.clientLimits {
		result = append(result, l.GetClientStats(clientID))
	}

	for i := 0; i < len(result); i++ {
		for j := i + 1; j < len(result); j++ {
			if result[j]["current_connections"].(int64) > result[i]["current_connections"].(int64) {
				result[i], result[j] = result[j], result[i]
			}
		}
	}

	return result
}

func (l *ClientIDLimiter) GetStats() map[string]interface{} {
	l.mu.RLock()
	defer l.mu.RUnlock()

	blockedCount := 0
	activeClients := 0
	for _, state := range l.clientLimits {
		if state.Blocked {
			blockedCount++
		}
		if state.CurrentConnCount > 0 {
			activeClients++
		}
	}

	return map[string]interface{}{
		"total_connections":  atomic.LoadInt64(&l.totalConnections),
		"max_connections":    l.maxTotal,
		"storm_detected":     l.stormDetected,
		"total_clients":      len(l.clientLimits),
		"active_clients":     activeClients,
		"blocked_clients":    blockedCount,
		"connection_rate":    l.GetConnectionRate(),
	}
}

func (l *ClientIDLimiter) SetMaxTotalConnections(max int) {
	l.mu.Lock()
	defer l.mu.Unlock()
	l.maxTotal = max
}

func (l *ClientIDLimiter) IsStormDetected() bool {
	l.timingsMu.RLock()
	defer l.timingsMu.RUnlock()
	return l.stormDetected
}

func (l *ClientIDLimiter) GetTopClients(limit int) []map[string]interface{} {
	allStats := l.GetAllClientStats()
	if limit > 0 && limit < len(allStats) {
		return allStats[:limit]
	}
	return allStats
}

func (l *ClientIDLimiter) CleanupInactiveClients() {
	l.mu.Lock()
	defer l.mu.Unlock()

	now := time.Now()
	inactiveThreshold := 24 * time.Hour

	for clientID, state := range l.clientLimits {
		if state.CurrentConnCount == 0 && now.Sub(state.LastActive) > inactiveThreshold {
			delete(l.clientLimits, clientID)
			delete(l.clientIdentifiers, clientID)
		}
	}
}
