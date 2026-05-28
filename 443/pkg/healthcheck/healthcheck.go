package healthcheck

import (
	"context"
	"cross-cloud-lb/pkg/cloud"
	"cross-cloud-lb/pkg/model"
	"sync"
	"time"

	"go.uber.org/zap"
)

type HealthChecker interface {
	Start(ctx context.Context)
	Stop()
	RegisterCluster(cluster *model.Cluster)
	UnregisterCluster(clusterID string)
	AddBackend(backend *model.Backend)
	RemoveBackend(backendID string)
	GetClusterHealth(clusterID string) (bool, *model.ClusterMetrics)
	GetBackendStatus(backendID string) (bool, int64)
	RegisterCallback(callback func(clusterID string, healthy bool))
}

type HealthCheckerImpl struct {
	config     model.HealthCheckConfig
	clusters   map[string]*clusterHealthState
	backends   map[string]*backendState
	providers  map[model.CloudProvider]cloud.Provider
	mu         sync.RWMutex
	callbacks  []func(string, bool)
	ticker     *time.Ticker
	logger     *zap.Logger
}

type clusterHealthState struct {
	cluster           *model.Cluster
	healthy           bool
	metrics           *model.ClusterMetrics
	consecutiveFails  uint32
	consecutivePasses uint32
	lastCheck         time.Time
}

type backendState struct {
	backend           *model.Backend
	consecutiveFails  uint32
	consecutivePasses uint32
	lastResponseTime  int64
}

func NewHealthChecker(
	config model.HealthCheckConfig,
	providers map[model.CloudProvider]cloud.Provider,
	logger *zap.Logger,
) *HealthCheckerImpl {
	return &HealthCheckerImpl{
		config:    config,
		clusters:  make(map[string]*clusterHealthState),
		backends:  make(map[string]*backendState),
		providers: providers,
		logger:    logger,
	}
}

func (hc *HealthCheckerImpl) Start(ctx context.Context) {
	hc.ticker = time.NewTicker(hc.config.Interval)
	go hc.run(ctx)
}

func (hc *HealthCheckerImpl) Stop() {
	if hc.ticker != nil {
		hc.ticker.Stop()
	}
}

func (hc *HealthCheckerImpl) RegisterCluster(cluster *model.Cluster) {
	hc.mu.Lock()
	defer hc.mu.Unlock()

	hc.clusters[cluster.ID] = &clusterHealthState{
		cluster: cluster,
		healthy: cluster.Healthy,
		metrics: &model.ClusterMetrics{
			ClusterID: cluster.ID,
		},
		lastCheck: time.Now(),
	}
}

func (hc *HealthCheckerImpl) UnregisterCluster(clusterID string) {
	hc.mu.Lock()
	defer hc.mu.Unlock()
	delete(hc.clusters, clusterID)
}

func (hc *HealthCheckerImpl) AddBackend(backend *model.Backend) {
	hc.mu.Lock()
	defer hc.mu.Unlock()
	hc.backends[backend.ID] = &backendState{
		backend:          backend,
		lastResponseTime: -1,
	}
}

func (hc *HealthCheckerImpl) RemoveBackend(backendID string) {
	hc.mu.Lock()
	defer hc.mu.Unlock()
	delete(hc.backends, backendID)
}

func (hc *HealthCheckerImpl) GetClusterHealth(clusterID string) (bool, *model.ClusterMetrics) {
	hc.mu.RLock()
	defer hc.mu.RUnlock()

	if state, exists := hc.clusters[clusterID]; exists {
		return state.healthy, state.metrics
	}
	return false, nil
}

func (hc *HealthCheckerImpl) GetBackendStatus(backendID string) (bool, int64) {
	hc.mu.RLock()
	defer hc.mu.RUnlock()

	if state, exists := hc.backends[backendID]; exists {
		return state.backend.Healthy, state.lastResponseTime
	}
	return false, -1
}

func (hc *HealthCheckerImpl) RegisterCallback(callback func(clusterID string, healthy bool)) {
	hc.callbacks = append(hc.callbacks, callback)
}

func (hc *HealthCheckerImpl) run(ctx context.Context) {
	for {
		select {
		case <-ctx.Done():
			return
		case <-hc.ticker.C:
			hc.checkAllClusters()
		}
	}
}

func (hc *HealthCheckerImpl) checkAllClusters() {
	hc.mu.RLock()
	clusters := make([]*clusterHealthState, 0, len(hc.clusters))
	for _, state := range hc.clusters {
		clusters = append(clusters, state)
	}
	hc.mu.RUnlock()

	var wg sync.WaitGroup
	for _, state := range clusters {
		wg.Add(1)
		go func(s *clusterHealthState) {
			defer wg.Done()
			hc.checkCluster(s)
		}(state)
	}
	wg.Wait()
}

func (hc *HealthCheckerImpl) checkCluster(state *clusterHealthState) {
	ctx, cancel := context.WithTimeout(context.Background(), hc.config.Timeout)
	defer cancel()

	provider, exists := hc.providers[state.cluster.Provider]
	if !exists {
		hc.logger.Warn("No provider found for cluster",
			zap.String("cluster_id", state.cluster.ID),
			zap.String("provider", string(state.cluster.Provider)))
		return
	}

	start := time.Now()
	healthy, err := provider.CheckClusterHealth(ctx, state.cluster.ID)
	responseTime := time.Since(start).Milliseconds()

	hc.mu.Lock()
	defer hc.mu.Unlock()

	state.lastCheck = time.Now()
	state.metrics.AvgResponseTime = responseTime

	if err != nil {
		hc.logger.Warn("Cloud provider health check failed",
			zap.String("cluster_id", state.cluster.ID),
			zap.Error(err))
		hc.handleHealthCheckResult(state, false)
		return
	}

	hc.logger.Debug("Cloud LB health check result",
		zap.String("cluster_id", state.cluster.ID),
		zap.Bool("healthy", healthy),
		zap.Int64("response_time_ms", responseTime))

	hc.handleHealthCheckResult(state, healthy)
}

func (hc *HealthCheckerImpl) handleHealthCheckResult(state *clusterHealthState, healthy bool) {
	if healthy {
		state.consecutivePasses++
		state.consecutiveFails = 0

		if state.consecutivePasses >= hc.config.HealthyThreshold && !state.healthy {
			hc.logger.Info("Cluster health recovered, using cloud LB health check",
				zap.String("cluster_id", state.cluster.ID),
				zap.Uint32("consecutive_passes", state.consecutivePasses))

			state.healthy = true
			state.cluster.Healthy = true
			hc.notifyCallbacks(state.cluster.ID, true)
		}
	} else {
		state.consecutiveFails++
		state.consecutivePasses = 0

		if state.consecutiveFails >= hc.config.UnhealthyThreshold && state.healthy {
			hc.logger.Warn("Cluster health degraded, detected via cloud LB",
				zap.String("cluster_id", state.cluster.ID),
				zap.Uint32("consecutive_failures", state.consecutiveFails))

			state.healthy = false
			state.cluster.Healthy = false
			hc.notifyCallbacks(state.cluster.ID, false)
		}
	}
}

func (hc *HealthCheckerImpl) notifyCallbacks(clusterID string, healthy bool) {
	for _, callback := range hc.callbacks {
		go callback(clusterID, healthy)
	}
}

func (hc *HealthCheckerImpl) UpdateClusterMetrics(clusterID string, metrics *model.ClusterMetrics) {
	hc.mu.Lock()
	defer hc.mu.Unlock()

	if state, exists := hc.clusters[clusterID]; exists {
		state.metrics = metrics
	}
}

func (hc *HealthCheckerImpl) GetAllClusterHealth() map[string]bool {
	hc.mu.RLock()
	defer hc.mu.RUnlock()

	result := make(map[string]bool)
	for clusterID, state := range hc.clusters {
		result[clusterID] = state.healthy
	}
	return result
}
