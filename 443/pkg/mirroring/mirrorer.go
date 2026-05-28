package mirroring

import (
	"bytes"
	"cross-cloud-lb/pkg/model"
	"fmt"
	"io"
	"math/rand"
	"net/http"
	"sync"
	"sync/atomic"
	"time"

	"go.uber.org/zap"
)

type TrafficMirrorer interface {
	ShouldMirror() bool
	MirrorRequest(req *http.Request) error
	SetTargetCluster(clusterID string, endpoints []string)
	UpdateConfig(config model.TrafficMirroringConfig)
	RecordMetrics(responseTime int64, statusCode int, success bool)
	IsCircuitOpen() bool
	AdjustMirrorRatio(loadPressure float64)
	GetEffectivePercent() float64
}

type TrafficMirrorerImpl struct {
	config       model.TrafficMirroringConfig
	targetEndpoints []string
	mu           sync.RWMutex
	logger       *zap.Logger
	httpClient   *http.Client

	circuitOpen         atomic.Bool
	consecutiveFailures int64
	totalRequests       int64
	failedRequests      int64
	avgResponseTime     atomic.Int64
	effectivePercent    float64

	lastOpenTime       time.Time
	lastHalfOpenTime   time.Time
	recoveryCount      int32

	metricsWindow []metricsSample
	metricsMu     sync.RWMutex
}

type metricsSample struct {
	responseTime int64
	statusCode   int
	timestamp    time.Time
}

const metricsWindowSize = 100

func NewTrafficMirrorer(config model.TrafficMirroringConfig, logger *zap.Logger) *TrafficMirrorerImpl {
	initialPercent := config.Percent
	if initialPercent == 0 && config.BasePercent > 0 {
		initialPercent = config.BasePercent
	}

	tm := &TrafficMirrorerImpl{
		config:          config,
		logger:          logger,
		effectivePercent: initialPercent,
		metricsWindow:   make([]metricsSample, 0, metricsWindowSize),
		httpClient: &http.Client{
			Timeout: 5 * time.Second,
			Transport: &http.Transport{
				MaxIdleConns:        100,
				IdleConnTimeout:     30 * time.Second,
				TLSHandshakeTimeout: 2 * time.Second,
			},
		},
	}

	if config.Enabled {
		go tm.startMetricsCollector()
	}

	return tm
}

func (tm *TrafficMirrorerImpl) ShouldMirror() bool {
	tm.mu.RLock()
	defer tm.mu.RUnlock()

	if !tm.config.Enabled || len(tm.targetEndpoints) == 0 {
		return false
	}

	if tm.circuitOpen.Load() {
		return false
	}

	return rand.Float64()*100 < tm.effectivePercent
}

func (tm *TrafficMirrorerImpl) MirrorRequest(req *http.Request) error {
	tm.mu.RLock()
	if !tm.config.Enabled || len(tm.targetEndpoints) == 0 {
		tm.mu.RUnlock()
		return nil
	}

	if tm.circuitOpen.Load() {
		tm.mu.RUnlock()
		return fmt.Errorf("mirroring circuit is open")
	}

	targets := make([]string, len(tm.targetEndpoints))
	copy(targets, tm.targetEndpoints)
	tm.mu.RUnlock()

	for _, target := range targets {
		go func(targetEndpoint string) {
			start := time.Now()
			err := tm.sendMirroredRequest(req, targetEndpoint)
			duration := time.Since(start).Milliseconds()

			if err != nil {
				tm.RecordMetrics(duration, http.StatusInternalServerError, false)
				tm.logger.Debug("Failed to send mirrored request",
					zap.String("target", targetEndpoint),
					zap.Error(err))
			} else {
				tm.RecordMetrics(duration, http.StatusOK, true)
			}
		}(target)
	}

	return nil
}

func (tm *TrafficMirrorerImpl) sendMirroredRequest(originalReq *http.Request, targetEndpoint string) error {
	mirroredReq, err := tm.cloneRequest(originalReq, targetEndpoint)
	if err != nil {
		return fmt.Errorf("failed to clone request: %w", err)
	}

	mirroredReq.Header.Set("X-Mirrored-From", "cross-cloud-lb")
	mirroredReq.Header.Set("X-Original-Host", originalReq.Host)
	mirroredReq.Header.Set("X-Mirror-Timestamp", fmt.Sprintf("%d", time.Now().UnixNano()))

	resp, err := tm.httpClient.Do(mirroredReq)
	if err != nil {
		return fmt.Errorf("mirrored request failed: %w", err)
	}
	defer resp.Body.Close()

	io.Copy(io.Discard, resp.Body)

	if resp.StatusCode >= 500 {
		return fmt.Errorf("mirrored request failed with status: %d", resp.StatusCode)
	}

	return nil
}

func (tm *TrafficMirrorerImpl) cloneRequest(req *http.Request, targetEndpoint string) (*http.Request, error) {
	var bodyBytes []byte
	if req.Body != nil {
		var err error
		bodyBytes, err = io.ReadAll(req.Body)
		if err != nil {
			return nil, err
		}
		req.Body = io.NopCloser(bytes.NewBuffer(bodyBytes))
	}

	newURL := *req.URL
	newURL.Scheme = "http"
	newURL.Host = targetEndpoint

	mirroredReq, err := http.NewRequest(req.Method, newURL.String(), bytes.NewBuffer(bodyBytes))
	if err != nil {
		return nil, err
	}

	for name, values := range req.Header {
		for _, value := range values {
			mirroredReq.Header.Add(name, value)
		}
	}

	mirroredReq.Host = targetEndpoint

	if req.Close {
		mirroredReq.Close = true
	}

	return mirroredReq, nil
}

func (tm *TrafficMirrorerImpl) RecordMetrics(responseTime int64, statusCode int, success bool) {
	tm.metricsMu.Lock()
	tm.metricsWindow = append(tm.metricsWindow, metricsSample{
		responseTime: responseTime,
		statusCode:   statusCode,
		timestamp:    time.Now(),
	})
	if len(tm.metricsWindow) > metricsWindowSize {
		tm.metricsWindow = tm.metricsWindow[1:]
	}
	tm.metricsMu.Unlock()

	atomic.AddInt64(&tm.totalRequests, 1)
	if !success || statusCode >= 500 {
		atomic.AddInt64(&tm.consecutiveFailures, 1)
		atomic.AddInt64(&tm.failedRequests, 1)
	} else {
		atomic.StoreInt64(&tm.consecutiveFailures, 0)
	}

	currentAvg := tm.avgResponseTime.Load()
	newAvg := (currentAvg*9 + responseTime) / 10
	tm.avgResponseTime.Store(newAvg)

	tm.checkCircuitBreaker()
}

func (tm *TrafficMirrorerImpl) checkCircuitBreaker() {
	tm.mu.Lock()
	defer tm.mu.Unlock()

	if !tm.config.CircuitBreaker.Enabled {
		return
	}

	consecutiveFails := atomic.LoadInt64(&tm.consecutiveFailures)
	total := atomic.LoadInt64(&tm.totalRequests)
	failed := atomic.LoadInt64(&tm.failedRequests)
	avgRT := tm.avgResponseTime.Load()

	openDuration := tm.config.CircuitBreaker.OpenDuration
	if openDuration == 0 {
		openDuration = 30 * time.Second
	}

	if tm.circuitOpen.Load() {
		if time.Since(tm.lastOpenTime) > openDuration {
			if time.Since(tm.lastHalfOpenTime) > 5*time.Second {
				tm.logger.Info("Mirroring circuit entering half-open state")
				tm.circuitOpen.Store(false)
				tm.lastHalfOpenTime = time.Now()
				tm.recoveryCount = 0
				atomic.StoreInt64(&tm.consecutiveFailures, 0)
			}
		}
		return
	}

	var errorRate float64
	if total > 0 {
		errorRate = float64(failed) / float64(total)
	}

	var shouldOpen bool
	var reason string

	failureThreshold := tm.config.CircuitBreaker.FailureThreshold
	if failureThreshold == 0 {
		failureThreshold = 10
	}
	errorRateThreshold := tm.config.CircuitBreaker.ErrorRateThreshold
	if errorRateThreshold == 0 {
		errorRateThreshold = 0.20
	}
	slowResponseThreshold := tm.config.CircuitBreaker.SlowResponseThreshold
	if slowResponseThreshold == 0 {
		slowResponseThreshold = 2000
	}

	if consecutiveFails >= failureThreshold {
		shouldOpen = true
		reason = fmt.Sprintf("consecutive failures: %d", consecutiveFails)
	} else if total >= 50 && errorRate >= errorRateThreshold {
		shouldOpen = true
		reason = fmt.Sprintf("error rate: %.2f%%", errorRate*100)
	} else if avgRT > slowResponseThreshold && total >= 20 {
		shouldOpen = true
		reason = fmt.Sprintf("slow response: %dms", avgRT)
	}

	if shouldOpen {
		tm.logger.Warn("Mirroring circuit opened",
			zap.String("reason", reason),
			zap.Float64("error_rate", errorRate),
			zap.Int64("avg_response_time_ms", avgRT),
			zap.Int64("consecutive_failures", consecutiveFails))

		tm.circuitOpen.Store(true)
		tm.lastOpenTime = time.Now()
	}

	halfOpenMaxRequests := tm.config.CircuitBreaker.HalfOpenMaxRequests
	if halfOpenMaxRequests == 0 {
		halfOpenMaxRequests = 5
	}

	if tm.recoveryCount > 0 && tm.recoveryCount >= halfOpenMaxRequests {
		if failed == 0 {
			tm.logger.Info("Mirroring circuit recovered and closed")
			tm.recoveryCount = 0
			atomic.StoreInt64(&tm.totalRequests, 0)
			atomic.StoreInt64(&tm.failedRequests, 0)
		}
	}
}

func (tm *TrafficMirrorerImpl) IsCircuitOpen() bool {
	return tm.circuitOpen.Load()
}

func (tm *TrafficMirrorerImpl) AdjustMirrorRatio(loadPressure float64) {
	tm.mu.Lock()
	defer tm.mu.Unlock()

	basePercent := tm.config.BasePercent
	if basePercent == 0 {
		basePercent = tm.config.Percent
	}

	minPercent := tm.config.MinPercent
	maxPercent := tm.config.MaxPercent
	if minPercent == 0 {
		minPercent = 1.0
	}
	if maxPercent == 0 {
		maxPercent = 50.0
	}

	var adjustedPercent float64
	switch {
	case loadPressure < 0.3:
		adjustedPercent = basePercent * 1.2
	case loadPressure < 0.5:
		adjustedPercent = basePercent
	case loadPressure < 0.7:
		adjustedPercent = basePercent * 0.7
	case loadPressure < 0.85:
		adjustedPercent = basePercent * 0.4
	default:
		adjustedPercent = basePercent * 0.1
	}

	if adjustedPercent > maxPercent {
		adjustedPercent = maxPercent
	}
	if adjustedPercent < minPercent {
		adjustedPercent = minPercent
	}

	if adjustedPercent != tm.effectivePercent {
		tm.logger.Info("Adjusted mirroring ratio",
			zap.Float64("load_pressure", loadPressure),
			zap.Float64("base_percent", basePercent),
			zap.Float64("min_percent", minPercent),
			zap.Float64("max_percent", maxPercent),
			zap.Float64("effective_percent", adjustedPercent))
		tm.effectivePercent = adjustedPercent
	}
}

func (tm *TrafficMirrorerImpl) GetEffectivePercent() float64 {
	tm.mu.RLock()
	defer tm.mu.RUnlock()
	return tm.effectivePercent
}

func (tm *TrafficMirrorerImpl) SetTargetCluster(clusterID string, endpoints []string) {
	tm.mu.Lock()
	defer tm.mu.Unlock()

	tm.config.TargetCluster = clusterID
	tm.targetEndpoints = endpoints

	atomic.StoreInt64(&tm.totalRequests, 0)
	atomic.StoreInt64(&tm.failedRequests, 0)
	atomic.StoreInt64(&tm.consecutiveFailures, 0)
	tm.avgResponseTime.Store(0)
	tm.circuitOpen.Store(false)
	tm.effectivePercent = tm.config.Percent

	tm.logger.Info("Mirroring target cluster updated",
		zap.String("cluster_id", clusterID),
		zap.Int("endpoint_count", len(endpoints)))
}

func (tm *TrafficMirrorerImpl) UpdateConfig(config model.TrafficMirroringConfig) {
	tm.mu.Lock()
	defer tm.mu.Unlock()
	tm.config = config
	tm.effectivePercent = config.Percent
}

func (tm *TrafficMirrorerImpl) GetConfig() model.TrafficMirroringConfig {
	tm.mu.RLock()
	defer tm.mu.RUnlock()
	return tm.config
}

func (tm *TrafficMirrorerImpl) GetTargetEndpoints() []string {
	tm.mu.RLock()
	defer tm.mu.RUnlock()
	endpoints := make([]string, len(tm.targetEndpoints))
	copy(endpoints, tm.targetEndpoints)
	return endpoints
}

func (tm *TrafficMirrorerImpl) AddTargetEndpoint(endpoint string) {
	tm.mu.Lock()
	defer tm.mu.Unlock()

	for _, e := range tm.targetEndpoints {
		if e == endpoint {
			return
		}
	}
	tm.targetEndpoints = append(tm.targetEndpoints, endpoint)
}

func (tm *TrafficMirrorerImpl) RemoveTargetEndpoint(endpoint string) {
	tm.mu.Lock()
	defer tm.mu.Unlock()

	for i, e := range tm.targetEndpoints {
		if e == endpoint {
			tm.targetEndpoints = append(tm.targetEndpoints[:i], tm.targetEndpoints[i+1:]...)
			return
		}
	}
}

func (tm *TrafficMirrorerImpl) startMetricsCollector() {
	ticker := time.NewTicker(30 * time.Second)
	defer ticker.Stop()

	for range ticker.C {
		tm.metricsMu.Lock()
		cutoff := time.Now().Add(-5 * time.Minute)
		validSamples := 0
		for _, sample := range tm.metricsWindow {
			if sample.timestamp.After(cutoff) {
				tm.metricsWindow[validSamples] = sample
				validSamples++
			}
		}
		tm.metricsWindow = tm.metricsWindow[:validSamples]
		tm.metricsMu.Unlock()

		total := atomic.LoadInt64(&tm.totalRequests)
		if total > 1000 {
			atomic.StoreInt64(&tm.totalRequests, total/2)
			atomic.StoreInt64(&tm.failedRequests, atomic.LoadInt64(&tm.failedRequests)/2)
		}
	}
}

func (tm *TrafficMirrorerImpl) GetStats() map[string]interface{} {
	tm.mu.RLock()
	defer tm.mu.RUnlock()

	return map[string]interface{}{
		"enabled":             tm.config.Enabled,
		"target_cluster":      tm.config.TargetCluster,
		"base_percent":        tm.config.Percent,
		"effective_percent":   tm.effectivePercent,
		"circuit_open":        tm.circuitOpen.Load(),
		"total_requests":      atomic.LoadInt64(&tm.totalRequests),
		"failed_requests":     atomic.LoadInt64(&tm.failedRequests),
		"consecutive_failures": atomic.LoadInt64(&tm.consecutiveFailures),
		"avg_response_time_ms": tm.avgResponseTime.Load(),
		"endpoint_count":      len(tm.targetEndpoints),
	}
}
