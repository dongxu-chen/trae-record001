package failover

import (
	"context"
	"cross-cloud-lb/pkg/model"
	"sync"
	"time"

	"go.uber.org/zap"
)

type FailoverManager interface {
	Start(ctx context.Context)
	Stop()
	RegisterCluster(cluster *model.Cluster)
	UnregisterCluster(clusterID string)
	UpdateClusterHealth(clusterID string, healthy bool)
	GetActiveClusters() []string
	GetFailoverTarget(failedClusterID string) (string, bool)
	IsClusterInFailover(clusterID string) bool
	RegisterCallback(callback func(clusterID string, failedOver bool))
}

type FailoverManagerImpl struct {
	config       model.FailoverConfig
	clusters     map[string]*clusterFailoverState
	mu           sync.RWMutex
	ticker       *time.Ticker
	logger       *zap.Logger
	callbacks    []func(string, bool)
}

type clusterFailoverState struct {
	clusterID         string
	healthy           bool
	consecutiveFails  uint32
	consecutivePasses uint32
	inFailover        bool
	failoverStartTime time.Time
	lastHealthCheck   time.Time
	provider          model.CloudProvider
	region            string
}

func NewFailoverManager(config model.FailoverConfig, logger *zap.Logger) *FailoverManagerImpl {
	return &FailoverManagerImpl{
		config:   config,
		clusters: make(map[string]*clusterFailoverState),
		logger:   logger,
	}
}

func (fm *FailoverManagerImpl) Start(ctx context.Context) {
	if !fm.config.Enabled {
		fm.logger.Info("Cross-cloud failover is disabled")
		return
	}

	fm.ticker = time.NewTicker(fm.config.CheckInterval)
	go fm.run(ctx)
}

func (fm *FailoverManagerImpl) Stop() {
	if fm.ticker != nil {
		fm.ticker.Stop()
	}
}

func (fm *FailoverManagerImpl) RegisterCluster(cluster *model.Cluster) {
	fm.mu.Lock()
	defer fm.mu.Unlock()

	fm.clusters[cluster.ID] = &clusterFailoverState{
		clusterID:       cluster.ID,
		healthy:         cluster.Healthy,
		inFailover:      false,
		provider:        cluster.Provider,
		region:          cluster.Region,
		lastHealthCheck: time.Now(),
	}
}

func (fm *FailoverManagerImpl) UnregisterCluster(clusterID string) {
	fm.mu.Lock()
	defer fm.mu.Unlock()
	delete(fm.clusters, clusterID)
}

func (fm *FailoverManagerImpl) UpdateClusterHealth(clusterID string, healthy bool) {
	fm.mu.Lock()
	defer fm.mu.Unlock()

	state, exists := fm.clusters[clusterID]
	if !exists {
		return
	}

	state.lastHealthCheck = time.Now()

	if healthy {
		state.consecutivePasses++
		state.consecutiveFails = 0

		if state.inFailover && state.consecutivePasses >= fm.config.RecoveryThreshold {
			fm.logger.Info("Cluster recovered from failover",
				zap.String("cluster_id", clusterID),
				zap.Duration("failover_duration", time.Since(state.failoverStartTime)))
			
			state.inFailover = false
			state.healthy = true
			fm.notifyCallbacks(clusterID, false)
		} else if !state.inFailover {
			state.healthy = true
		}
	} else {
		state.consecutiveFails++
		state.consecutivePasses = 0

		if !state.inFailover && state.consecutiveFails >= fm.config.FailoverThreshold {
			fm.logger.Warn("Cluster entering failover state",
				zap.String("cluster_id", clusterID),
				zap.Uint32("consecutive_failures", state.consecutiveFails))
			
			state.inFailover = true
			state.healthy = false
			state.failoverStartTime = time.Now()
			fm.notifyCallbacks(clusterID, true)
		} else if !state.inFailover {
			state.healthy = false
		}
	}
}

func (fm *FailoverManagerImpl) GetActiveClusters() []string {
	fm.mu.RLock()
	defer fm.mu.RUnlock()

	activeClusters := make([]string, 0)
	for clusterID, state := range fm.clusters {
		if state.healthy && !state.inFailover {
			activeClusters = append(activeClusters, clusterID)
		}
	}
	return activeClusters
}

func (fm *FailoverManagerImpl) GetFailoverTarget(failedClusterID string) (string, bool) {
	fm.mu.RLock()
	defer fm.mu.RUnlock()

	failedState, exists := fm.clusters[failedClusterID]
	if !exists {
		return "", false
	}

	var bestTarget string
	bestScore := -1

	for clusterID, state := range fm.clusters {
		if clusterID == failedClusterID || !state.healthy || state.inFailover {
			continue
		}

		score := fm.calculateFailoverScore(failedState, state)
		if score > bestScore {
			bestScore = score
			bestTarget = clusterID
		}
	}

	if bestTarget == "" {
		return "", false
	}

	return bestTarget, true
}

func (fm *FailoverManagerImpl) calculateFailoverScore(failed, candidate *clusterFailoverState) int {
	score := 0

	if candidate.provider != failed.provider {
		score += 50
	}

	if candidate.region != failed.region {
		score += 30
	}

	score += int(candidate.consecutivePasses) * 2

	return score
}

func (fm *FailoverManagerImpl) IsClusterInFailover(clusterID string) bool {
	fm.mu.RLock()
	defer fm.mu.RUnlock()

	if state, exists := fm.clusters[clusterID]; exists {
		return state.inFailover
	}
	return false
}

func (fm *FailoverManagerImpl) RegisterCallback(callback func(clusterID string, failedOver bool)) {
	fm.callbacks = append(fm.callbacks, callback)
}

func (fm *FailoverManagerImpl) run(ctx context.Context) {
	for {
		select {
		case <-ctx.Done():
			return
		case <-fm.ticker.C:
			fm.checkStaleStates()
		}
	}
}

func (fm *FailoverManagerImpl) checkStaleStates() {
	fm.mu.Lock()
	defer fm.mu.Unlock()

	now := time.Now()
	timeout := fm.config.CheckInterval * 3

	for clusterID, state := range fm.clusters {
		if now.Sub(state.lastHealthCheck) > timeout {
			if state.healthy && !state.inFailover {
				fm.logger.Warn("Cluster health check timed out, marking as unhealthy",
					zap.String("cluster_id", clusterID))
				state.healthy = false
				state.consecutiveFails++
				
				if state.consecutiveFails >= fm.config.FailoverThreshold {
					state.inFailover = true
					state.failoverStartTime = now
					fm.notifyCallbacks(clusterID, true)
				}
			}
		}
	}
}

func (fm *FailoverManagerImpl) notifyCallbacks(clusterID string, failedOver bool) {
	for _, callback := range fm.callbacks {
		go callback(clusterID, failedOver)
	}
}

func (fm *FailoverManagerImpl) GetClusterState(clusterID string) (healthy, inFailover bool, exists bool) {
	fm.mu.RLock()
	defer fm.mu.RUnlock()

	state, ok := fm.clusters[clusterID]
	if !ok {
		return false, false, false
	}
	return state.healthy, state.inFailover, true
}

func (fm *FailoverManagerImpl) GetAllClusterStates() map[string]map[string]interface{} {
	fm.mu.RLock()
	defer fm.mu.RUnlock()

	result := make(map[string]map[string]interface{})
	for clusterID, state := range fm.clusters {
		result[clusterID] = map[string]interface{}{
			"healthy":           state.healthy,
			"in_failover":       state.inFailover,
			"consecutive_fails": state.consecutiveFails,
			"consecutive_passes": state.consecutivePasses,
			"provider":          state.provider,
			"region":            state.region,
		}
	}
	return result
}
