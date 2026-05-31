package circuitbreaker

import (
	"context"
	"fmt"
	"sync"
	"time"

	"github.com/zeromicro/go-zero/core/breaker"
	"github.com/zeromicro/go-zero/core/logx"
)

const (
	defaultErrorThreshold = 0.5
	defaultSleepWindow    = 10 * time.Second
	defaultBucketCount    = 10
	defaultStatInterval   = time.Second
)

type MirrorCircuitBreaker struct {
	breakers    map[string]*mirrorBreaker
	mu          sync.RWMutex
	config      BreakerConfig
	metricsChan chan MetricEvent
}

type mirrorBreaker struct {
	name         string
	breaker      breaker.Breaker
	errorCount   int64
	successCount int64
	lastOpenTime time.Time
	state        string
}

type BreakerConfig struct {
	ErrorThreshold float64
	SleepWindow    time.Duration
	BucketCount    int
	StatInterval   time.Duration
}

type MetricEvent struct {
	ServiceName   string
	EventType     string
	Timestamp     time.Time
	CurrentState  string
	ErrorRate     float64
}

type BreakerStatus struct {
	Name          string
	State         string
	ErrorRate     float64
	LastOpenTime  time.Time
	SuccessCount  int64
	ErrorCount    int64
}

func NewMirrorCircuitBreaker(config BreakerConfig) *MirrorCircuitBreaker {
	if config.ErrorThreshold == 0 {
		config.ErrorThreshold = defaultErrorThreshold
	}
	if config.SleepWindow == 0 {
		config.SleepWindow = defaultSleepWindow
	}
	if config.BucketCount == 0 {
		config.BucketCount = defaultBucketCount
	}
	if config.StatInterval == 0 {
		config.StatInterval = defaultStatInterval
	}

	return &MirrorCircuitBreaker{
		breakers:    make(map[string]*mirrorBreaker),
		config:      config,
		metricsChan: make(chan MetricEvent, 1000),
	}
}

func (mcb *MirrorCircuitBreaker) getOrCreateBreaker(serviceName string) *mirrorBreaker {
	mcb.mu.RLock()
	b, exists := mcb.breakers[serviceName]
	mcb.mu.RUnlock()

	if exists {
		return b
	}

	mcb.mu.Lock()
	defer mcb.mu.Unlock()

	if b, exists = mcb.breakers[serviceName]; exists {
		return b
	}

	b = &mirrorBreaker{
		name:  serviceName,
		state: "closed",
		breaker: breaker.NewBreaker(breaker.Options{
			Name:         serviceName,
			ErrorPercent: int(mcb.config.ErrorThreshold * 100),
			Duration:     mcb.config.SleepWindow,
			Buckets:      mcb.config.BucketCount,
		}),
	}

	mcb.breakers[serviceName] = b
	return b
}

func (mcb *MirrorCircuitBreaker) Allow(serviceName string) (func(bool), bool) {
	b := mcb.getOrCreateBreaker(serviceName)

	markPromise, err := b.breaker.Allow()
	if err != nil {
		mcb.updateState(b, "open")
		mcb.emitMetric(serviceName, "rejected", b.state, 0)
		return nil, false
	}

	return func(success bool) {
		markPromise(success)
		if success {
			b.successCount++
		} else {
			b.errorCount++
		}
		mcb.checkAndUpdateState(b)
		mcb.emitMetric(serviceName, "request", b.state, mcb.calculateErrorRate(b))
	}, true
}

func (mcb *MirrorCircuitBreaker) Do(serviceName string, fn func() error) error {
	b := mcb.getOrCreateBreaker(serviceName)

	err := b.breaker.Do(func() error {
		if err := fn(); err != nil {
			b.errorCount++
			return err
		}
		b.successCount++
		return nil
	})

	if err == breaker.ErrServiceUnavailable {
		mcb.updateState(b, "open")
		mcb.emitMetric(serviceName, "rejected", b.state, mcb.calculateErrorRate(b))
		return fmt.Errorf("circuit breaker open for service %s, will retry after %s",
			serviceName, mcb.config.SleepWindow)
	}

	mcb.checkAndUpdateState(b)
	mcb.emitMetric(serviceName, "request", b.state, mcb.calculateErrorRate(b))

	return err
}

func (mcb *MirrorCircuitBreaker) DoWithAcceptable(serviceName string, fn func() error,
	acceptable func(err error) bool) error {
	b := mcb.getOrCreateBreaker(serviceName)

	err := b.breaker.DoWithAcceptable(fn, func(err error) bool {
		if acceptable != nil && acceptable(err) {
			return true
		}
		return err == nil
	})

	if err == breaker.ErrServiceUnavailable {
		mcb.updateState(b, "open")
		return fmt.Errorf("circuit breaker open for service %s", serviceName)
	}

	return err
}

func (mcb *MirrorCircuitBreaker) DoCtx(ctx context.Context, serviceName string,
	fn func(ctx context.Context) error) error {
	b := mcb.getOrCreateBreaker(serviceName)

	err := b.breaker.DoCtx(ctx, fn)

	if err == breaker.ErrServiceUnavailable {
		mcb.updateState(b, "open")
		return fmt.Errorf("circuit breaker open for service %s", serviceName)
	}

	return err
}

func (mcb *MirrorCircuitBreaker) updateState(b *mirrorBreaker, state string) {
	mcb.mu.Lock()
	defer mcb.mu.Unlock()

	if state == "open" && b.state != "open" {
		b.lastOpenTime = time.Now()
		logx.Warnf("Circuit breaker opened for service: %s", b.name)
	} else if state == "closed" && b.state != "closed" {
		logx.Infof("Circuit breaker closed for service: %s", b.name)
	}

	b.state = state
}

func (mcb *MirrorCircuitBreaker) checkAndUpdateState(b *mirrorBreaker) {
	errorRate := mcb.calculateErrorRate(b)

	if errorRate >= mcb.config.ErrorThreshold && b.state == "closed" {
		mcb.updateState(b, "open")
	} else if b.state == "open" && time.Since(b.lastOpenTime) > mcb.config.SleepWindow {
		mcb.updateState(b, "half-open")
	}
}

func (mcb *MirrorCircuitBreaker) calculateErrorRate(b *mirrorBreaker) float64 {
	total := b.successCount + b.errorCount
	if total == 0 {
		return 0
	}
	return float64(b.errorCount) / float64(total)
}

func (mcb *MirrorCircuitBreaker) emitMetric(serviceName, eventType, state string, errorRate float64) {
	select {
	case mcb.metricsChan <- MetricEvent{
		ServiceName:  serviceName,
		EventType:    eventType,
		Timestamp:    time.Now(),
		CurrentState: state,
		ErrorRate:    errorRate,
	}:
	default:
	}
}

func (mcb *MirrorCircuitBreaker) GetMetricsChan() <-chan MetricEvent {
	return mcb.metricsChan
}

func (mcb *MirrorCircuitBreaker) GetStatus(serviceName string) *BreakerStatus {
	mcb.mu.RLock()
	defer mcb.mu.RUnlock()

	b, exists := mcb.breakers[serviceName]
	if !exists {
		return nil
	}

	return &BreakerStatus{
		Name:         b.name,
		State:        b.state,
		ErrorRate:    mcb.calculateErrorRate(b),
		LastOpenTime: b.lastOpenTime,
		SuccessCount: b.successCount,
		ErrorCount:   b.errorCount,
	}
}

func (mcb *MirrorCircuitBreaker) GetAllStatuses() []*BreakerStatus {
	mcb.mu.RLock()
	defer mcb.mu.RUnlock()

	statuses := make([]*BreakerStatus, 0, len(mcb.breakers))
	for _, b := range mcb.breakers {
		statuses = append(statuses, &BreakerStatus{
			Name:         b.name,
			State:        b.state,
			ErrorRate:    mcb.calculateErrorRate(b),
			LastOpenTime: b.lastOpenTime,
			SuccessCount: b.successCount,
			ErrorCount:   b.errorCount,
		})
	}

	return statuses
}

func (mcb *MirrorCircuitBreaker) Reset(serviceName string) {
	mcb.mu.Lock()
	defer mcb.mu.Unlock()

	if b, exists := mcb.breakers[serviceName]; exists {
		b.successCount = 0
		b.errorCount = 0
		b.state = "closed"
		b.lastOpenTime = time.Time{}
	}
}

func (mcb *MirrorCircuitBreaker) ResetAll() {
	mcb.mu.Lock()
	defer mcb.mu.Unlock()

	for _, b := range mcb.breakers {
		b.successCount = 0
		b.errorCount = 0
		b.state = "closed"
		b.lastOpenTime = time.Time{}
	}
}
