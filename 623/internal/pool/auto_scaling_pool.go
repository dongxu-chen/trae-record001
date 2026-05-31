package pool

import (
	"db-guardian/internal/config"
	"db-guardian/pkg/logger"
	"fmt"
	"net"
	"sync"
	"sync/atomic"
	"time"
)

type AutoScalingPool struct {
	cfg             config.ProxyConfig
	limiterCfg      config.LimiterConfig
	log             *logger.Logger

	baseMaxConns    int
	currentMaxConns int
	activeConns     int64

	warmConns       map[uint64]*WarmConnection
	warmConnIDGen   uint64
	warmMu          sync.RWMutex

	scalingHistory  []ScalingEvent
	scalingMu       sync.RWMutex

	isStorm         bool
	stormStartTime  time.Time
	stormPeakRate   float64

	usageHistory    []UsageSnapshot
	usageMu         sync.RWMutex

	stopChan        chan struct{}
	wg              sync.WaitGroup
}

type WarmConnection struct {
	ID         uint64
	Conn       net.Conn
	CreatedAt  time.Time
	LastUsed   time.Time
	IsLeased   bool
	LeaseCount int64
}

type ScalingEvent struct {
	Timestamp    time.Time
	EventType    string
	OldCapacity  int
	NewCapacity  int
	Reason       string
	ActiveConns  int64
	Rate         float64
}

type UsageSnapshot struct {
	Timestamp     time.Time
	ActiveConns   int64
	MaxConns      int
	UsageRatio    float64
	ConnectionRate float64
}

func NewAutoScalingPool(cfg config.ProxyConfig, limiterCfg config.LimiterConfig, log *logger.Logger) *AutoScalingPool {
	pool := &AutoScalingPool{
		cfg:             cfg,
		limiterCfg:      limiterCfg,
		log:             log,
		baseMaxConns:    limiterCfg.MaxTotalConnections,
		currentMaxConns: limiterCfg.MaxTotalConnections,
		warmConns:       make(map[uint64]*WarmConnection),
		scalingHistory:  make([]ScalingEvent, 0),
		usageHistory:    make([]UsageSnapshot, 0),
		stopChan:        make(chan struct{}),
	}

	pool.wg.Add(2)
	go pool.monitorUsage()
	go pool.autoScaleLoop()

	return pool
}

func (p *AutoScalingPool) IncrementActive() {
	atomic.AddInt64(&p.activeConns, 1)
}

func (p *AutoScalingPool) DecrementActive() {
	atomic.AddInt64(&p.activeConns, -1)
}

func (p *AutoScalingPool) GetActiveConns() int64 {
	return atomic.LoadInt64(&p.activeConns)
}

func (p *AutoScalingPool) GetCurrentMax() int {
	p.scalingMu.RLock()
	defer p.scalingMu.RUnlock()
	return p.currentMaxConns
}

func (p *AutoScalingPool) GetBaseMax() int {
	return p.baseMaxConns
}

func (p *AutoScalingPool) IsInStorm() bool {
	p.scalingMu.RLock()
	defer p.scalingMu.RUnlock()
	return p.isStorm
}

func (p *AutoScalingPool) NotifyStormDetected(rate float64) {
	p.scalingMu.Lock()
	defer p.scalingMu.Unlock()

	if !p.isStorm {
		p.isStorm = true
		p.stormStartTime = time.Now()
		p.stormPeakRate = rate

		newCapacity := int(float64(p.baseMaxConns) * 1.5)
		p.recordScalingEvent("storm_scale_up", p.currentMaxConns, newCapacity,
			fmt.Sprintf("Storm detected, rate=%.2f conn/s", rate))
		p.currentMaxConns = newCapacity

		p.log.Warn("Storm detected, scaling up: %d -> %d, rate=%.2f conn/s",
			p.baseMaxConns, newCapacity, rate)
	}

	if rate > p.stormPeakRate {
		p.stormPeakRate = rate
	}
}

func (p *AutoScalingPool) NotifyStormEnded() {
	p.scalingMu.Lock()
	defer p.scalingMu.Unlock()

	if p.isStorm {
		duration := time.Since(p.stormStartTime)
		p.isStorm = false

		p.recordScalingEvent("storm_scale_down", p.currentMaxConns, p.baseMaxConns,
			fmt.Sprintf("Storm ended after %v, peak rate=%.2f", duration, p.stormPeakRate))
		p.currentMaxConns = p.baseMaxConns

		p.log.Info("Storm ended, scaling down: %d -> %d, duration=%v, peak_rate=%.2f",
			p.currentMaxConns, p.baseMaxConns, duration, p.stormPeakRate)
	}
}

func (p *AutoScalingPool) ScaleUp(factor float64, reason string) {
	p.scalingMu.Lock()
	defer p.scalingMu.Unlock()

	oldCapacity := p.currentMaxConns
	newCapacity := int(float64(p.currentMaxConns) * factor)

	maxAllowed := p.baseMaxConns * 3
	if newCapacity > maxAllowed {
		newCapacity = maxAllowed
	}

	if newCapacity != oldCapacity {
		p.recordScalingEvent("manual_scale_up", oldCapacity, newCapacity, reason)
		p.currentMaxConns = newCapacity
		p.log.Info("Manual scale up: %d -> %d, reason=%s", oldCapacity, newCapacity, reason)
	}
}

func (p *AutoScalingPool) ScaleDown(factor float64, reason string) {
	p.scalingMu.Lock()
	defer p.scalingMu.Unlock()

	oldCapacity := p.currentMaxConns
	newCapacity := int(float64(p.currentMaxConns) * factor)

	if newCapacity < p.baseMaxConns {
		newCapacity = p.baseMaxConns
	}

	if newCapacity != oldCapacity {
		p.recordScalingEvent("scale_down", oldCapacity, newCapacity, reason)
		p.currentMaxConns = newCapacity
		p.log.Info("Scale down: %d -> %d, reason=%s", oldCapacity, newCapacity, reason)
	}
}

func (p *AutoScalingPool) recordScalingEvent(eventType string, oldCap, newCap int, reason string) {
	event := ScalingEvent{
		Timestamp:   time.Now(),
		EventType:   eventType,
		OldCapacity: oldCap,
		NewCapacity: newCap,
		Reason:      reason,
		ActiveConns: atomic.LoadInt64(&p.activeConns),
	}
	p.scalingHistory = append(p.scalingHistory, event)

	if len(p.scalingHistory) > 500 {
		p.scalingHistory = p.scalingHistory[1:]
	}
}

func (p *AutoScalingPool) monitorUsage() {
	defer p.wg.Done()

	ticker := time.NewTicker(5 * time.Second)
	defer ticker.Stop()

	for {
		select {
		case <-ticker.C:
			p.recordUsageSnapshot()
		case <-p.stopChan:
			return
		}
	}
}

func (p *AutoScalingPool) recordUsageSnapshot() {
	active := atomic.LoadInt64(&p.activeConns)
	maxConns := p.GetCurrentMax()

	var ratio float64
	if maxConns > 0 {
		ratio = float64(active) / float64(maxConns)
	}

	p.usageMu.Lock()
	snapshot := UsageSnapshot{
		Timestamp:   time.Now(),
		ActiveConns: active,
		MaxConns:    maxConns,
		UsageRatio:  ratio,
	}
	p.usageHistory = append(p.usageHistory, snapshot)

	if len(p.usageHistory) > 720 {
		p.usageHistory = p.usageHistory[1:]
	}
	p.usageMu.Unlock()
}

func (p *AutoScalingPool) autoScaleLoop() {
	defer p.wg.Done()

	ticker := time.NewTicker(30 * time.Second)
	defer ticker.Stop()

	for {
		select {
		case <-ticker.C:
			p.evaluateScaling()
		case <-p.stopChan:
			return
		}
	}
}

func (p *AutoScalingPool) evaluateScaling() {
	p.usageMu.RLock()
	defer p.usageMu.RUnlock()

	if len(p.usageHistory) < 6 {
		return
	}

	recent := p.usageHistory[len(p.usageHistory)-6:]
	avgRatio := 0.0
	for _, s := range recent {
		avgRatio += s.UsageRatio
	}
	avgRatio /= float64(len(recent))

	p.scalingMu.Lock()
	defer p.scalingMu.Unlock()

	if !p.isStorm {
		if avgRatio > 0.85 {
			newCap := int(float64(p.currentMaxConns) * 1.2)
			maxAllowed := p.baseMaxConns * 2
			if newCap > maxAllowed {
				newCap = maxAllowed
			}
			if newCap > p.currentMaxConns {
				p.recordScalingEvent("auto_scale_up", p.currentMaxConns, newCap,
					fmt.Sprintf("High usage avg=%.2f%%", avgRatio*100))
				p.currentMaxConns = newCap
				p.log.Info("Auto scale up: %d -> %d (usage=%.1f%%)", p.currentMaxConns, newCap, avgRatio*100)
			}
		} else if avgRatio < 0.3 && p.currentMaxConns > p.baseMaxConns {
			newCap := int(float64(p.currentMaxConns) * 0.8)
			if newCap < p.baseMaxConns {
				newCap = p.baseMaxConns
			}
			if newCap < p.currentMaxConns {
				p.recordScalingEvent("auto_scale_down", p.currentMaxConns, newCap,
					fmt.Sprintf("Low usage avg=%.2f%%", avgRatio*100))
				p.currentMaxConns = newCap
				p.log.Info("Auto scale down: %d -> %d (usage=%.1f%%)", p.currentMaxConns, newCap, avgRatio*100)
			}
		}
	}
}

func (p *AutoScalingPool) PreWarmConnections(count int) int {
	p.warmMu.Lock()
	defer p.warmMu.Unlock()

	created := 0
	backendAddr := fmt.Sprintf("%s:%d", p.cfg.TargetDBHost, p.cfg.TargetDBPort)

	for i := 0; i < count; i++ {
		conn, err := net.DialTimeout("tcp", backendAddr, 5*time.Second)
		if err != nil {
			p.log.Warn("Pre-warm connection failed: %v", err)
			continue
		}

		id := atomic.AddUint64(&p.warmConnIDGen, 1)
		now := time.Now()
		p.warmConns[id] = &WarmConnection{
			ID:        id,
			Conn:      conn,
			CreatedAt: now,
			LastUsed:  now,
			IsLeased:  false,
		}
		created++
	}

	if created > 0 {
		p.log.Info("Pre-warmed %d connections (pool=%d)", created, len(p.warmConns))
	}

	return created
}

func (p *AutoScalingPool) LeaseWarmConnection() (net.Conn, uint64, bool) {
	p.warmMu.Lock()
	defer p.warmMu.Unlock()

	for id, wc := range p.warmConns {
		if !wc.IsLeased {
			wc.IsLeased = true
			wc.LastUsed = time.Now()
			wc.LeaseCount++
			return wc.Conn, id, true
		}
	}

	return nil, 0, false
}

func (p *AutoScalingPool) ReturnWarmConnection(id uint64) {
	p.warmMu.Lock()
	defer p.warmMu.Unlock()

	if wc, exists := p.warmConns[id]; exists {
		wc.IsLeased = false
		wc.LastUsed = time.Now()
	}
}

func (p *AutoScalingPool) RemoveWarmConnection(id uint64) {
	p.warmMu.Lock()
	defer p.warmMu.Unlock()

	if wc, exists := p.warmConns[id]; exists {
		wc.Conn.Close()
		delete(p.warmConns, id)
	}
}

func (p *AutoScalingPool) GetWarmPoolSize() int {
	p.warmMu.RLock()
	defer p.warmMu.RUnlock()
	return len(p.warmConns)
}

func (p *AutoScalingPool) GetAvailableWarmCount() int {
	p.warmMu.RLock()
	defer p.warmMu.RUnlock()

	count := 0
	for _, wc := range p.warmConns {
		if !wc.IsLeased {
			count++
		}
	}
	return count
}

func (p *AutoScalingPool) cleanupExpiredWarmConnections() {
	p.warmMu.Lock()
	defer p.warmMu.Unlock()

	now := time.Now()
	expired := 0

	for id, wc := range p.warmConns {
		if !wc.IsLeased && now.Sub(wc.LastUsed) > 5*time.Minute {
			wc.Conn.Close()
			delete(p.warmConns, id)
			expired++
		}
	}

	if expired > 0 {
		p.log.Debug("Cleaned up %d expired warm connections", expired)
	}
}

func (p *AutoScalingPool) GetScalingHistory() []ScalingEvent {
	p.scalingMu.RLock()
	defer p.scalingMu.RUnlock()

	result := make([]ScalingEvent, len(p.scalingHistory))
	copy(result, p.scalingHistory)
	return result
}

func (p *AutoScalingPool) GetUsageHistory() []UsageSnapshot {
	p.usageMu.RLock()
	defer p.usageMu.RUnlock()

	result := make([]UsageSnapshot, len(p.usageHistory))
	copy(result, p.usageHistory)
	return result
}

func (p *AutoScalingPool) GetStats() map[string]interface{} {
	p.scalingMu.RLock()
	isStorm := p.isStorm
	stormStart := p.stormStartTime
	stormPeak := p.stormPeakRate
	currentMax := p.currentMaxConns
	p.scalingMu.RUnlock()

	p.warmMu.RLock()
	warmTotal := len(p.warmConns)
	warmAvailable := 0
	for _, wc := range p.warmConns {
		if !wc.IsLeased {
			warmAvailable++
		}
	}
	p.warmMu.RUnlock()

	active := atomic.LoadInt64(&p.activeConns)
	usageRatio := 0.0
	if currentMax > 0 {
		usageRatio = float64(active) / float64(currentMax)
	}

	return map[string]interface{}{
		"active_connections":  active,
		"base_max_connections": p.baseMaxConns,
		"current_max_connections": currentMax,
		"usage_ratio":         usageRatio,
		"is_storm":            isStorm,
		"storm_start_time":    stormStart,
		"storm_peak_rate":     stormPeak,
		"warm_pool_total":     warmTotal,
		"warm_pool_available": warmAvailable,
		"scaling_events":      len(p.scalingHistory),
	}
}

func (p *AutoScalingPool) Stop() {
	close(p.stopChan)
	p.wg.Wait()

	p.warmMu.Lock()
	for _, wc := range p.warmConns {
		wc.Conn.Close()
	}
	p.warmConns = make(map[uint64]*WarmConnection)
	p.warmMu.Unlock()
}
