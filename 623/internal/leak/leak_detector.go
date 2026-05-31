package leak

import (
	"db-guardian/pkg/logger"
	"sync"
	"time"
)

type LeakDetector struct {
	connections     map[uint64]*LeakTrackedConnection
	leakRecords     []LeakRecord
	clientLeakStats map[string]*ClientLeakStats
	mu              sync.RWMutex
	log             *logger.Logger
	customThreshold time.Duration
}

type LeakTrackedConnection struct {
	ID            uint64
	ClientID      string
	ClientIP      string
	StartTime     time.Time
	EndTime       time.Time
	IsActive      bool
	QueryCount    int64
	LastQueryTime time.Time
	StackInfo     string
	AppName       string
	ProcessID     string
}

type LeakRecord struct {
	ID              uint64
	ClientID        string
	ClientIP        string
	DetectedTime    time.Time
	Duration        time.Duration
	QueryCount      int64
	IdleDuration    time.Duration
	SuspectedLeak   bool
	LeakSeverity    string
	StackInfo       string
	AppName         string
	ProcessID       string
}

type ClientLeakStats struct {
	ClientID       string
	TotalLeaks     int
	ActiveLeaks    int
	TotalDuration  time.Duration
	AvgDuration    time.Duration
	LastLeakTime   time.Time
	LeakPattern    string
}

func NewLeakDetector(log *logger.Logger) *LeakDetector {
	return &LeakDetector{
		connections:     make(map[uint64]*LeakTrackedConnection),
		leakRecords:     make([]LeakRecord, 0),
		clientLeakStats: make(map[string]*ClientLeakStats),
		log:             log,
		customThreshold: 30 * time.Minute,
	}
}

func (ld *LeakDetector) TrackConnection(id uint64, clientID, clientIP, appName, processID, stackInfo string) {
	ld.mu.Lock()
	defer ld.mu.Unlock()

	now := time.Now()
	ld.connections[id] = &LeakTrackedConnection{
		ID:            id,
		ClientID:      clientID,
		ClientIP:      clientIP,
		StartTime:     now,
		IsActive:      true,
		QueryCount:    0,
		LastQueryTime: now,
		StackInfo:     stackInfo,
		AppName:       appName,
		ProcessID:     processID,
	}
}

func (ld *LeakDetector) UpdateConnectionActivity(id uint64) {
	ld.mu.Lock()
	defer ld.mu.Unlock()

	if conn, exists := ld.connections[id]; exists {
		conn.QueryCount++
		conn.LastQueryTime = time.Now()
	}
}

func (ld *LeakDetector) CloseConnection(id uint64) {
	ld.mu.Lock()
	defer ld.mu.Unlock()

	if conn, exists := ld.connections[id]; exists {
		conn.IsActive = false
		conn.EndTime = time.Now()
		delete(ld.connections, id)
	}
}

func (ld *LeakDetector) SetThreshold(threshold time.Duration) {
	ld.mu.Lock()
	defer ld.mu.Unlock()
	ld.customThreshold = threshold
}

func (ld *LeakDetector) DetectLeaks() []LeakRecord {
	ld.mu.Lock()
	defer ld.mu.Unlock()

	now := time.Now()
	newLeaks := make([]LeakRecord, 0)

	for id, conn := range ld.connections {
		if !conn.IsActive {
			continue
		}

		duration := now.Sub(conn.StartTime)
		idleDuration := now.Sub(conn.LastQueryTime)

		leakThreshold := ld.calculateLeakThreshold(conn)
		isLeak := ld.analyzeLeakPattern(conn, duration, idleDuration)

		if isLeak && duration > leakThreshold {
			severity := ld.calculateSeverity(duration, idleDuration)

			record := LeakRecord{
				ID:            id,
				ClientID:      conn.ClientID,
				ClientIP:      conn.ClientIP,
				DetectedTime:  now,
				Duration:      duration,
				QueryCount:    conn.QueryCount,
				IdleDuration:  idleDuration,
				SuspectedLeak: true,
				LeakSeverity:  severity,
				StackInfo:     conn.StackInfo,
				AppName:       conn.AppName,
				ProcessID:     conn.ProcessID,
			}

			newLeaks = append(newLeaks, record)
			ld.leakRecords = append(ld.leakRecords, record)

			ld.updateClientStats(conn.ClientID, duration, severity)

			ld.log.Warn("Connection leak detected: id=%d, client=%s, duration=%v, idle=%v, severity=%s",
				id, conn.ClientID, duration, idleDuration, severity)
		}
	}

	return newLeaks
}

func (ld *LeakDetector) calculateLeakThreshold(conn *LeakTrackedConnection) time.Duration {
	baseThreshold := ld.customThreshold

	if conn.QueryCount == 0 {
		return baseThreshold / 2
	}

	if conn.QueryCount < 5 {
		return baseThreshold * 2
	}

	return baseThreshold
}

func (ld *LeakDetector) analyzeLeakPattern(conn *LeakTrackedConnection, duration, idleDuration time.Duration) bool {
	if idleDuration > 10*time.Minute && conn.QueryCount > 0 {
		queryRate := float64(conn.QueryCount) / duration.Hours()
		if queryRate < 1.0 {
			return true
		}
	}

	if idleDuration > duration*0.8 && duration > 5*time.Minute {
		return true
	}

	return false
}

func (ld *LeakDetector) calculateSeverity(duration, idleDuration time.Duration) string {
	idleRatio := float64(idleDuration) / float64(duration)

	if duration > 2*time.Hour && idleRatio > 0.9 {
		return "critical"
	}

	if duration > time.Hour && idleRatio > 0.7 {
		return "high"
	}

	if duration > 30*time.Minute && idleRatio > 0.5 {
		return "medium"
	}

	return "low"
}

func (ld *LeakDetector) updateClientStats(clientID string, duration time.Duration, severity string) {
	if _, exists := ld.clientLeakStats[clientID]; !exists {
		ld.clientLeakStats[clientID] = &ClientLeakStats{
			ClientID: clientID,
		}
	}

	stats := ld.clientLeakStats[clientID]
	stats.TotalLeaks++
	stats.ActiveLeaks++
	stats.TotalDuration += duration
	stats.AvgDuration = stats.TotalDuration / time.Duration(stats.TotalLeaks)
	stats.LastLeakTime = time.Now()
	stats.LeakPattern = severity
}

func (ld *LeakDetector) GetLeakRecords() []LeakRecord {
	ld.mu.RLock()
	defer ld.mu.RUnlock()

	result := make([]LeakRecord, len(ld.leakRecords))
	copy(result, ld.leakRecords)
	return result
}

func (ld *LeakDetector) GetActiveLeakConnections() []LeakTrackedConnection {
	ld.mu.RLock()
	defer ld.mu.RUnlock()

	result := make([]LeakTrackedConnection, 0)
	for _, conn := range ld.connections {
		if conn.IsActive {
			result = append(result, *conn)
		}
	}
	return result
}

func (ld *LeakDetector) GetClientLeakStats() map[string]*ClientLeakStats {
	ld.mu.RLock()
	defer ld.mu.RUnlock()

	result := make(map[string]*ClientLeakStats)
	for k, v := range ld.clientLeakStats {
		result[k] = v
	}
	return result
}

func (ld *LeakDetector) GetStats() map[string]interface{} {
	ld.mu.RLock()
	defer ld.mu.RUnlock()

	activeLeakCount := 0
	trackedCount := 0
	for _, conn := range ld.connections {
		if conn.IsActive {
			trackedCount++
			duration := time.Since(conn.StartTime)
			idleDuration := time.Since(conn.LastQueryTime)
			if ld.analyzeLeakPattern(conn, duration, idleDuration) && duration > ld.customThreshold/2 {
				activeLeakCount++
			}
		}
	}

	return map[string]interface{}{
		"tracked_connections":   trackedCount,
		"total_leak_records":    len(ld.leakRecords),
		"active_leak_suspects":  activeLeakCount,
		"affected_clients":      len(ld.clientLeakStats),
		"leak_threshold":        ld.customThreshold.String(),
	}
}

func (ld *LeakDetector) ForceCloseLeakConnection(id uint64) bool {
	ld.mu.Lock()
	defer ld.mu.Unlock()

	if conn, exists := ld.connections[id]; exists {
		conn.IsActive = false
		conn.EndTime = time.Now()
		delete(ld.connections, id)
		return true
	}
	return false
}

func (ld *LeakDetector) GetTopLeakClients(limit int) []ClientLeakStats {
	ld.mu.RLock()
	defer ld.mu.RUnlock()

	result := make([]ClientLeakStats, 0, len(ld.clientLeakStats))
	for _, v := range ld.clientLeakStats {
		result = append(result, *v)
	}

	for i := 0; i < len(result); i++ {
		for j := i + 1; j < len(result); j++ {
			if result[j].TotalLeaks > result[i].TotalLeaks {
				result[i], result[j] = result[j], result[i]
			}
		}
	}

	if limit > 0 && limit < len(result) {
		result = result[:limit]
	}

	return result
}
