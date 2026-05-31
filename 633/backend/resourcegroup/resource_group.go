package resourcegroup

import (
	"sync"
	"time"

	"clickhouse-rate-limiter/config"
	"clickhouse-rate-limiter/limiter"
)

type ResourceGroup struct {
	Name           string
	Config         config.ResourceGroupConfig
	RateLimiter    *limiter.RateLimiter
	ActiveQueries  int64
	QueuedQueries  int64
	TotalQueries   int64
	RejectedQueries int64
	mu             sync.RWMutex
}

type ResourceGroupManager struct {
	groups map[string]*ResourceGroup
	mu     sync.RWMutex
}

func NewResourceGroupManager(defaultCfg config.LimiterConfig, groups []config.ResourceGroupConfig) *ResourceGroupManager {
	mgr := &ResourceGroupManager{
		groups: make(map[string]*ResourceGroup),
	}

	mgr.groups["default"] = &ResourceGroup{
		Name: "default",
		Config: config.ResourceGroupConfig{
			Name:           "default",
			Weight:         100,
			MaxConcurrency: 10,
			MaxQueueSize:   1000,
			Limiter:        defaultCfg,
		},
		RateLimiter: limiter.NewRateLimiter(defaultCfg),
	}

	for _, cfg := range groups {
		mgr.groups[cfg.Name] = &ResourceGroup{
			Name:        cfg.Name,
			Config:      cfg,
			RateLimiter: limiter.NewRateLimiter(cfg.Limiter),
		}
	}

	go mgr.cleanupMetricsLoop()

	return mgr
}

func (mgr *ResourceGroupManager) GetGroup(name string) *ResourceGroup {
	mgr.mu.RLock()
	defer mgr.mu.RUnlock()

	if group, exists := mgr.groups[name]; exists {
		return group
	}
	return mgr.groups["default"]
}

func (mgr *ResourceGroupManager) GetAllGroups() []*ResourceGroup {
	mgr.mu.RLock()
	defer mgr.mu.RUnlock()

	groups := make([]*ResourceGroup, 0, len(mgr.groups))
	for _, g := range mgr.groups {
		groups = append(groups, g)
	}
	return groups
}

func (mgr *ResourceGroupManager) AddGroup(cfg config.ResourceGroupConfig, defaultLimiter config.LimiterConfig) *ResourceGroup {
	mgr.mu.Lock()
	defer mgr.mu.Unlock()

	group := &ResourceGroup{
		Name:        cfg.Name,
		Config:      cfg,
		RateLimiter: limiter.NewRateLimiter(cfg.Limiter),
	}
	mgr.groups[cfg.Name] = group
	return group
}

func (mgr *ResourceGroupManager) RemoveGroup(name string) bool {
	mgr.mu.Lock()
	defer mgr.mu.Unlock()

	if name == "default" {
		return false
	}
	if _, exists := mgr.groups[name]; exists {
		delete(mgr.groups, name)
		return true
	}
	return false
}

func (rg *ResourceGroup) Allow(userID string, scanRows, memoryBytes int64) *limiter.LimitStatus {
	rg.mu.RLock()
	active := rg.ActiveQueries
	queued := rg.QueuedQueries
	rg.mu.RUnlock()

	if active >= rg.Config.MaxConcurrency {
		return &limiter.LimitStatus{
			Allowed: false,
			Reason:  "concurrency_limit_exceeded",
		}
	}

	if queued >= rg.Config.MaxQueueSize {
		return &limiter.LimitStatus{
			Allowed: false,
			Reason:  "resource_group_queue_full",
		}
	}

	return rg.RateLimiter.Allow(userID, scanRows, memoryBytes)
}

func (rg *ResourceGroup) IncrementActive() {
	rg.mu.Lock()
	defer rg.mu.Unlock()
	rg.ActiveQueries++
	rg.TotalQueries++
}

func (rg *ResourceGroup) DecrementActive() {
	rg.mu.Lock()
	defer rg.mu.Unlock()
	if rg.ActiveQueries > 0 {
		rg.ActiveQueries--
	}
}

func (rg *ResourceGroup) IncrementQueued() {
	rg.mu.Lock()
	defer rg.mu.Unlock()
	rg.QueuedQueries++
}

func (rg *ResourceGroup) DecrementQueued() {
	rg.mu.Lock()
	defer rg.mu.Unlock()
	if rg.QueuedQueries > 0 {
		rg.QueuedQueries--
	}
}

func (rg *ResourceGroup) IncrementRejected() {
	rg.mu.Lock()
	defer rg.mu.Unlock()
	rg.RejectedQueries++
}

func (rg *ResourceGroup) GetMetrics() map[string]interface{} {
	rg.mu.RLock()
	defer rg.mu.RUnlock()

	limiterMetrics := rg.RateLimiter.GetCircuitBreakerDetail()

	return map[string]interface{}{
		"name":              rg.Name,
		"weight":            rg.Config.Weight,
		"max_concurrency":   rg.Config.MaxConcurrency,
		"max_queue_size":    rg.Config.MaxQueueSize,
		"active_queries":    rg.ActiveQueries,
		"queued_queries":    rg.QueuedQueries,
		"total_queries":     rg.TotalQueries,
		"rejected_queries":  rg.RejectedQueries,
		"circuit_breaker":   limiterMetrics,
		"limiter_config": map[string]interface{}{
			"global_rate":     rg.Config.Limiter.GlobalRate,
			"max_scan_rows":   rg.Config.Limiter.MaxScanRows,
			"max_memory":      rg.Config.Limiter.MaxMemoryBytes,
		},
	}
}

func (rg *ResourceGroup) RecordSuccess() {
	rg.RateLimiter.RecordSuccess()
}

func (rg *ResourceGroup) RecordFailure() {
	rg.RateLimiter.RecordFailure()
}

func (mgr *ResourceGroupManager) cleanupMetricsLoop() {
	ticker := time.NewTicker(5 * time.Minute)
	defer ticker.Stop()

	for range ticker.C {
		mgr.mu.Lock()
		for _, rg := range mgr.groups {
			rg.mu.Lock()
			rg.TotalQueries = 0
			rg.RejectedQueries = 0
			rg.mu.Unlock()
		}
		mgr.mu.Unlock()
	}
}
