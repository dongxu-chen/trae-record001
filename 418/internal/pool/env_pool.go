package pool

import (
	"context"
	"errors"
	"fmt"
	"sync"
	"time"
)

type EnvStatus string

const (
	EnvIdle    EnvStatus = "idle"
	EnvBusy    EnvStatus = "busy"
	EnvExpired EnvStatus = "expired"
	EnvEvicted EnvStatus = "evicted"
	EnvLeaked  EnvStatus = "leaked"
)

type RuntimeEnv struct {
	ID           string
	Function     string
	Runtime      string
	ContainerID  string
	Node         string
	CreatedAt    time.Time
	LastUsedAt   time.Time
	Status       EnvStatus
	UsedCount    uint64
	MaxAge       time.Duration
	IdleTimeout  time.Duration
	MaxUseCount  uint64
	MaxConns     int
	ActiveConns  int
	TotalConns   uint64
	Reclaimed    bool
}

type PoolConfig struct {
	MaxSize        int
	MinIdle        int
	IdleTimeout    time.Duration
	MaxAge         time.Duration
	MaxConnsPerEnv int
	MaxUsePerEnv   uint64
	ReclaimTimeout time.Duration
	SweepInterval  time.Duration
}

func DefaultPoolConfig() PoolConfig {
	return PoolConfig{
		MaxSize:        100,
		MinIdle:        2,
		IdleTimeout:    10 * time.Minute,
		MaxAge:         time.Hour,
		MaxConnsPerEnv: 10,
		MaxUsePerEnv:   1000,
		ReclaimTimeout: 30 * time.Second,
		SweepInterval:  30 * time.Second,
	}
}

type EnvPool struct {
	mu       sync.RWMutex
	envs     map[string]*RuntimeEnv
	idle     map[string]*RuntimeEnv
	busy     map[string]*RuntimeEnv
	config   PoolConfig
	metrics  *PoolMetrics
	wg       sync.WaitGroup
	stopCh   chan struct{}
	stopped  bool
}

type PoolMetrics struct {
	TotalCreated   uint64
	TotalEvicted   uint64
	TotalReclaimed uint64
	TotalTimeout   uint64
	TotalExhausted uint64
	TotalLeakDet   uint64
}

var (
	ErrPoolClosed    = errors.New("pool closed")
	ErrPoolExhausted = errors.New("pool exhausted (max size reached)")
	ErrEnvNotFound   = errors.New("env not found")
	ErrEnvExpired    = errors.New("env expired")
	ErrTooManyConns  = errors.New("too many active connections on env")
)

func NewEnvPool(config PoolConfig) *EnvPool {
	if config.MaxSize <= 0 {
		config = DefaultPoolConfig()
	}
	p := &EnvPool{
		envs:    make(map[string]*RuntimeEnv),
		idle:    make(map[string]*RuntimeEnv),
		busy:    make(map[string]*RuntimeEnv),
		config:  config,
		metrics: &PoolMetrics{},
		stopCh:  make(chan struct{}),
	}
	return p
}

func (p *EnvPool) Start(ctx context.Context) {
	p.wg.Add(1)
	go p.sweeper(ctx)
}

func (p *EnvPool) Stop() {
	p.mu.Lock()
	defer p.mu.Unlock()
	if p.stopped {
		return
	}
	p.stopped = true
	close(p.stopCh)
	p.wg.Wait()
}

func (p *EnvPool) sweeper(ctx context.Context) {
	defer p.wg.Done()
	t := time.NewTicker(p.config.SweepInterval)
	defer t.Stop()
	for {
		select {
		case <-ctx.Done():
			return
		case <-p.stopCh:
			return
		case <-t.C:
			p.sweep()
		}
	}
}

func (p *EnvPool) sweep() {
	p.mu.Lock()
	defer p.mu.Unlock()
	now := time.Now()
	for id, env := range p.idle {
		expired := (env.MaxAge > 0 && now.Sub(env.CreatedAt) > env.MaxAge) ||
			(env.IdleTimeout > 0 && now.Sub(env.LastUsedAt) > env.IdleTimeout) ||
			(env.MaxUseCount > 0 && env.UsedCount >= env.MaxUseCount)
		if expired {
			p.evictLocked(env, EnvExpired)
			delete(p.idle, id)
			delete(p.envs, id)
			p.metrics.TotalEvicted++
		}
	}
	for id, env := range p.busy {
		if p.config.ReclaimTimeout > 0 && now.Sub(env.LastUsedAt) > p.config.ReclaimTimeout {
			p.metrics.TotalLeakDet++
			env.Status = EnvLeaked
			env.Reclaimed = true
			env.ActiveConns = 0
			delete(p.busy, id)
			p.idle[id] = env
			env.Status = EnvIdle
			p.metrics.TotalReclaimed++
		}
	}
	for len(p.envs) > p.config.MaxSize {
		var victim *RuntimeEnv
		for _, v := range p.idle {
			if victim == nil || v.LastUsedAt.Before(victim.LastUsedAt) {
				victim = v
			}
		}
		if victim == nil {
			break
		}
		p.evictLocked(victim, EnvEvicted)
		delete(p.idle, victim.ID)
		delete(p.envs, victim.ID)
		p.metrics.TotalEvicted++
	}
}

func (p *EnvPool) evictLocked(env *RuntimeEnv, status EnvStatus) {
	env.Status = status
	env.ActiveConns = 0
}

func (p *EnvPool) Put(env *RuntimeEnv) error {
	p.mu.Lock()
	defer p.mu.Unlock()
	if p.stopped {
		return ErrPoolClosed
	}
	if env.MaxConns <= 0 {
		env.MaxConns = p.config.MaxConnsPerEnv
	}
	if env.MaxAge <= 0 {
		env.MaxAge = p.config.MaxAge
	}
	if env.IdleTimeout <= 0 {
		env.IdleTimeout = p.config.IdleTimeout
	}
	if env.MaxUseCount <= 0 {
		env.MaxUseCount = p.config.MaxUsePerEnv
	}
	if len(p.envs) >= p.config.MaxSize {
		p.metrics.TotalExhausted++
		return ErrPoolExhausted
	}
	if _, exists := p.envs[env.ID]; exists {
		return fmt.Errorf("env %s already exists", env.ID)
	}
	env.CreatedAt = time.Now()
	env.LastUsedAt = env.CreatedAt
	env.Status = EnvIdle
	p.envs[env.ID] = env
	p.idle[env.ID] = env
	p.metrics.TotalCreated++
	return nil
}

func (p *EnvPool) Get(function string) (*RuntimeEnv, error) {
	p.mu.Lock()
	defer p.mu.Unlock()
	if p.stopped {
		return nil, ErrPoolClosed
	}
	var best *RuntimeEnv
	for _, env := range p.idle {
		if env.Function != function {
			continue
		}
		if env.ActiveConns >= env.MaxConns {
			continue
		}
		if best == nil || env.UsedCount < best.UsedCount {
			best = env
		}
	}
	if best == nil {
		return nil, ErrEnvNotFound
	}
	if p.isExpiredLocked(best) {
		delete(p.idle, best.ID)
		delete(p.envs, best.ID)
		p.evictLocked(best, EnvExpired)
		p.metrics.TotalTimeout++
		return nil, ErrEnvExpired
	}
	best.ActiveConns++
	best.TotalConns++
	if best.ActiveConns >= best.MaxConns {
		delete(p.idle, best.ID)
		p.busy[best.ID] = best
		best.Status = EnvBusy
	}
	best.LastUsedAt = time.Now()
	best.UsedCount++
	return best, nil
}

func (p *EnvPool) Release(id string) error {
	p.mu.Lock()
	defer p.mu.Unlock()
	env, ok := p.envs[id]
	if !ok {
		return ErrEnvNotFound
	}
	if env.ActiveConns > 0 {
		env.ActiveConns--
	}
	if env.Status == EnvBusy && env.ActiveConns < env.MaxConns {
		delete(p.busy, id)
		p.idle[id] = env
		env.Status = EnvIdle
	}
	env.LastUsedAt = time.Now()
	return nil
}

func (p *EnvPool) isExpiredLocked(env *RuntimeEnv) bool {
	now := time.Now()
	if env.MaxAge > 0 && now.Sub(env.CreatedAt) > env.MaxAge {
		return true
	}
	if env.IdleTimeout > 0 && now.Sub(env.LastUsedAt) > env.IdleTimeout {
		return true
	}
	if env.MaxUseCount > 0 && env.UsedCount >= env.MaxUseCount {
		return true
	}
	return false
}

func (p *EnvPool) Remove(id string) error {
	p.mu.Lock()
	defer p.mu.Unlock()
	env, ok := p.envs[id]
	if !ok {
		return ErrEnvNotFound
	}
	delete(p.envs, id)
	delete(p.idle, id)
	delete(p.busy, id)
	p.evictLocked(env, EnvEvicted)
	p.metrics.TotalEvicted++
	return nil
}

func (p *EnvPool) Stats() PoolStats {
	p.mu.RLock()
	defer p.mu.RUnlock()
	return PoolStats{
		Total:     len(p.envs),
		Idle:      len(p.idle),
		Busy:      len(p.busy),
		MaxSize:   p.config.MaxSize,
		MinIdle:   p.config.MinIdle,
		Created:   p.metrics.TotalCreated,
		Evicted:   p.metrics.TotalEvicted,
		Reclaimed: p.metrics.TotalReclaimed,
		Timeout:   p.metrics.TotalTimeout,
		Exhausted: p.metrics.TotalExhausted,
		Leaks:     p.metrics.TotalLeakDet,
	}
}

type PoolStats struct {
	Total     int    `json:"total"`
	Idle      int    `json:"idle"`
	Busy      int    `json:"busy"`
	MaxSize   int    `json:"max_size"`
	MinIdle   int    `json:"min_idle"`
	Created   uint64 `json:"created"`
	Evicted   uint64 `json:"evicted"`
	Reclaimed uint64 `json:"reclaimed"`
	Timeout   uint64 `json:"timeout"`
	Exhausted uint64 `json:"exhausted"`
	Leaks     uint64 `json:"leaks"`
}

func (p *EnvPool) ListIdle() []*RuntimeEnv {
	p.mu.RLock()
	defer p.mu.RUnlock()
	out := make([]*RuntimeEnv, 0, len(p.idle))
	for _, v := range p.idle {
		out = append(out, v)
	}
	return out
}

func (p *EnvPool) ListBusy() []*RuntimeEnv {
	p.mu.RLock()
	defer p.mu.RUnlock()
	out := make([]*RuntimeEnv, 0, len(p.busy))
	for _, v := range p.busy {
		out = append(out, v)
	}
	return out
}

func NewEnv(id, function, runtime, containerID, node string) *RuntimeEnv {
	return &RuntimeEnv{
		ID:          id,
		Function:    function,
		Runtime:     runtime,
		ContainerID: containerID,
		Node:        node,
		Status:      EnvIdle,
	}
}
