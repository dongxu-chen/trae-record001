package proxy

import (
	"db-guardian/internal/baseline"
	"db-guardian/internal/config"
	"db-guardian/internal/pool"
	"db-guardian/internal/prewarm"
	"db-guardian/pkg/logger"
	"fmt"
	"sync"
	"time"
)

type ConnectionAnalyzer struct {
	cfg                config.AnalyzerConfig
	log                *logger.Logger
	baselineManager    *baseline.BaselineManager
	scalingPool        *pool.AutoScalingPool
	preWarmEngine      *prewarm.PreWarmEngine
	slowConnections    []SlowConnectionRecord
	leakCandidates     []LeakCandidate
	connectionHistory  []ConnectionEvent
	mu                 sync.RWMutex
	connCounts         map[string]int64
	connCountHistory   map[string][]timePoint
	stormAlerts        []StormAlert
	queryStats         map[string]*QueryStats
	useDynamicBaseline bool
	wasStorm           bool
}

type SlowConnectionRecord struct {
	ClientIP  string
	Timestamp time.Time
	Duration  time.Duration
}

type LeakCandidate struct {
	ClientIP    string
	StartTime   time.Time
	Duration    time.Duration
	ConnectionCount int
}

type ConnectionEvent struct {
	Timestamp time.Time
	ClientIP  string
	Type      string
	Duration  time.Duration
}

type StormAlert struct {
	Timestamp   time.Time
	Description string
	Severity    string
}

type QueryStats struct {
	TotalQueries  int64
	SlowQueries   int64
	TotalDuration time.Duration
}

type timePoint struct {
	Time  time.Time
	Count int64
}

func NewConnectionAnalyzer(cfg config.AnalyzerConfig, log *logger.Logger, baselineManager *baseline.BaselineManager) *ConnectionAnalyzer {
	analyzer := &ConnectionAnalyzer{
		cfg:              cfg,
		log:              log,
		baselineManager:  baselineManager,
		connCounts:       make(map[string]int64),
		connCountHistory: make(map[string][]timePoint),
		queryStats:       make(map[string]*QueryStats),
		useDynamicBaseline: baselineManager != nil,
	}

	go analyzer.startStatsCollector()
	return analyzer
}

func (a *ConnectionAnalyzer) SetScalingPool(sp *pool.AutoScalingPool) {
	a.scalingPool = sp
}

func (a *ConnectionAnalyzer) SetPreWarmEngine(pe *prewarm.PreWarmEngine) {
	a.preWarmEngine = pe
}

func (a *ConnectionAnalyzer) RecordConnection(clientIP string, start, end time.Time) {
	a.mu.Lock()
	defer a.mu.Unlock()

	duration := end.Sub(start)
	a.connCounts[clientIP]++

	now := time.Now()
	a.connCountHistory["total"] = append(a.connCountHistory["total"], timePoint{now, a.connCounts[clientIP]})

	a.connectionHistory = append(a.connectionHistory, ConnectionEvent{
		Timestamp: now,
		ClientIP:  clientIP,
		Type:      "connect",
		Duration:  duration,
	})

	a.checkConnectionStorm()
}

func (a *ConnectionAnalyzer) CheckSlowConnection(clientIP string, duration time.Duration) {
	threshold := a.cfg.SlowConnectionThreshold
	isSlow := duration >= threshold

	if a.useDynamicBaseline {
		a.baselineManager.RecordSample(baseline.ThresholdSlowConnection, duration.Seconds())
		isSlow = a.baselineManager.IsAnomaly(baseline.ThresholdSlowConnection, duration.Seconds())
	}

	if !isSlow {
		return
	}

	a.mu.Lock()
	defer a.mu.Unlock()

	record := SlowConnectionRecord{
		ClientIP:  clientIP,
		Timestamp: time.Now(),
		Duration:  duration,
	}
	a.slowConnections = append(a.slowConnections, record)

	if len(a.slowConnections) > 1000 {
		a.slowConnections = a.slowConnections[1:]
	}

	a.log.Warn("Slow connection detected: client=%s, duration=%v", clientIP, duration)
}

func (a *ConnectionAnalyzer) DetectConnectionLeak(connections []*TrackedConnection) {
	a.mu.Lock()
	defer a.mu.Unlock()

	now := time.Now()
	leakByIP := make(map[string]*LeakCandidate)

	for _, conn := range connections {
		conn.mu.Lock()
		duration := now.Sub(conn.StartTime)
		conn.mu.Unlock()

		if duration > a.cfg.LeakDetectionThreshold {
			if leakByIP[conn.ClientIP] == nil {
				leakByIP[conn.ClientIP] = &LeakCandidate{
					ClientIP:  conn.ClientIP,
					StartTime: conn.StartTime,
					Duration:  duration,
				}
			}
			leakByIP[conn.ClientIP].ConnectionCount++
			if duration > leakByIP[conn.ClientIP].Duration {
				leakByIP[conn.ClientIP].Duration = duration
				leakByIP[conn.ClientIP].StartTime = conn.StartTime
			}
		}
	}

	a.leakCandidates = a.leakCandidates[:0]
	for _, leak := range leakByIP {
		a.leakCandidates = append(a.leakCandidates, *leak)
		a.log.Warn("Potential connection leak: client=%s, count=%d, longest_duration=%v",
			leak.ClientIP, leak.ConnectionCount, leak.Duration)
	}
}

func (a *ConnectionAnalyzer) checkConnectionStorm() {
	history := a.connCountHistory["total"]
	if len(history) < 10 {
		return
	}

	recent := history[len(history)-10:]
	rate := float64(recent[len(recent)-1].Count-recent[0].Count) / recent[len(recent)-1].Time.Sub(recent[0].Time).Seconds()

	isStorm := rate > 50.0

	if a.useDynamicBaseline {
		a.baselineManager.RecordSample(baseline.ThresholdConnectionRate, rate)
		isStorm = a.baselineManager.IsAnomaly(baseline.ThresholdConnectionRate, rate)
	}

	if a.preWarmEngine != nil {
		a.preWarmEngine.RecordRate(rate)
	}

	if isStorm {
		if !a.wasStorm {
			if a.scalingPool != nil {
				a.scalingPool.NotifyStormDetected(rate)
			}
			a.wasStorm = true
		}

		alert := StormAlert{
			Timestamp:   time.Now(),
			Description: fmt.Sprintf("High connection rate detected (dynamic baseline): %.2f conn/s", rate),
			Severity:    "warning",
		}
		a.stormAlerts = append(a.stormAlerts, alert)

		if len(a.stormAlerts) > 100 {
			a.stormAlerts = a.stormAlerts[1:]
		}

		a.log.Warn("Connection storm alert: rate=%.2f conn/s (dynamic baseline)", rate)
	} else if a.wasStorm {
		if a.scalingPool != nil {
			a.scalingPool.NotifyStormEnded()
		}
		a.wasStorm = false
	}
}

func (a *ConnectionAnalyzer) startStatsCollector() {
	ticker := time.NewTicker(a.cfg.StatsInterval)
	defer ticker.Stop()

	for range ticker.C {
		a.collectStats()
	}
}

func (a *ConnectionAnalyzer) collectStats() {
	a.mu.Lock()
	defer a.mu.Unlock()

	for clientIP := range a.connCountHistory {
		history := a.connCountHistory[clientIP]
		if len(history) > 360 {
			a.connCountHistory[clientIP] = history[len(history)-360:]
		}
	}
}

func (a *ConnectionAnalyzer) GetSlowConnections() []SlowConnectionRecord {
	a.mu.RLock()
	defer a.mu.RUnlock()
	result := make([]SlowConnectionRecord, len(a.slowConnections))
	copy(result, a.slowConnections)
	return result
}

func (a *ConnectionAnalyzer) GetLeakCandidates() []LeakCandidate {
	a.mu.RLock()
	defer a.mu.RUnlock()
	result := make([]LeakCandidate, len(a.leakCandidates))
	copy(result, a.leakCandidates)
	return result
}

func (a *ConnectionAnalyzer) GetStormAlerts() []StormAlert {
	a.mu.RLock()
	defer a.mu.RUnlock()
	result := make([]StormAlert, len(a.stormAlerts))
	copy(result, a.stormAlerts)
	return result
}

func (a *ConnectionAnalyzer) GetConnectionTrend() map[string]interface{} {
	a.mu.RLock()
	defer a.mu.RUnlock()

	history := a.connCountHistory["total"]
	trend := make([]map[string]interface{}, 0, len(history))

	for _, tp := range history {
		trend = append(trend, map[string]interface{}{
			"timestamp": tp.Time,
			"count":     tp.Count,
		})
	}

	return map[string]interface{}{
		"trend": trend,
		"total": len(history),
	}
}

func (a *ConnectionAnalyzer) GetStats() map[string]interface{} {
	a.mu.RLock()
	defer a.mu.RUnlock()

	return map[string]interface{}{
		"slow_connection_count":   len(a.slowConnections),
		"leak_candidate_count":    len(a.leakCandidates),
		"storm_alert_count":       len(a.stormAlerts),
		"connection_history_size": len(a.connectionHistory),
	}
}
