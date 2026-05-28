package cost

import (
	"cross-cloud-lb/pkg/model"
	"sync"
	"time"

	"go.uber.org/zap"
)

type CostManager interface {
	GetClusterCost(clusterID string) (float64, bool)
	UpdateClusterCost(clusterID string, cost float64)
	GetCostAdjustedWeight(clusterID string, baseWeight int) int
	CalculateCostScore(clusterID string) float64
	RefreshPricing()
}

type CostManagerImpl struct {
	clusters  map[string]*clusterCostState
	mu        sync.RWMutex
	logger    *zap.Logger
	config    model.CostConfig
	pricing   map[model.CloudProvider]map[string]float64
}

type clusterCostState struct {
	clusterID       string
	currentCost     float64
	historicalCosts []float64
	lastUpdated     time.Time
}

type CloudPricing struct {
	ComputeCostPerHour float64
	NetworkCostPerGB   float64
	StorageCostPerGB   float64
	LoadBalancerCost   float64
}

var defaultPricing = map[model.CloudProvider]map[string]CloudPricing{
	model.AWS: {
		"us-east-1": {
			ComputeCostPerHour: 0.05,
			NetworkCostPerGB:   0.02,
			StorageCostPerGB:   0.023,
			LoadBalancerCost:   0.025,
		},
		"us-west-2": {
			ComputeCostPerHour: 0.052,
			NetworkCostPerGB:   0.02,
			StorageCostPerGB:   0.023,
			LoadBalancerCost:   0.025,
		},
	},
	model.Azure: {
		"eastus": {
			ComputeCostPerHour: 0.046,
			NetworkCostPerGB:   0.018,
			StorageCostPerGB:   0.018,
			LoadBalancerCost:   0.02,
		},
		"westus": {
			ComputeCostPerHour: 0.048,
			NetworkCostPerGB:   0.018,
			StorageCostPerGB:   0.018,
			LoadBalancerCost:   0.02,
		},
	},
	model.GCP: {
		"us-central1": {
			ComputeCostPerHour: 0.047,
			NetworkCostPerGB:   0.019,
			StorageCostPerGB:   0.020,
			LoadBalancerCost:   0.018,
		},
		"us-east1": {
			ComputeCostPerHour: 0.049,
			NetworkCostPerGB:   0.019,
			StorageCostPerGB:   0.020,
			LoadBalancerCost:   0.018,
		},
	},
}

func NewCostManager(config model.CostConfig, logger *zap.Logger) *CostManagerImpl {
	cm := &CostManagerImpl{
		clusters: make(map[string]*clusterCostState),
		logger:   logger,
		config:   config,
		pricing:  make(map[model.CloudProvider]map[string]float64),
	}

	return cm
}

func (cm *CostManagerImpl) RegisterCluster(cluster *model.Cluster) {
	cm.mu.Lock()
	defer cm.mu.Unlock()

	cost := cm.calculateBaseCost(cluster.Provider, cluster.Region)
	cm.clusters[cluster.ID] = &clusterCostState{
		clusterID:       cluster.ID,
		currentCost:     cost,
		historicalCosts: make([]float64, 0, 30),
		lastUpdated:     time.Now(),
	}

	cm.logger.Info("Registered cluster for cost management",
		zap.String("cluster_id", cluster.ID),
		zap.String("provider", string(cluster.Provider)),
		zap.String("region", cluster.Region),
		zap.Float64("base_cost", cost))
}

func (cm *CostManagerImpl) UnregisterCluster(clusterID string) {
	cm.mu.Lock()
	defer cm.mu.Unlock()
	delete(cm.clusters, clusterID)
}

func (cm *CostManagerImpl) GetClusterCost(clusterID string) (float64, bool) {
	cm.mu.RLock()
	defer cm.mu.RUnlock()

	state, exists := cm.clusters[clusterID]
	if !exists {
		return 0, false
	}
	return state.currentCost, true
}

func (cm *CostManagerImpl) UpdateClusterCost(clusterID string, cost float64) {
	cm.mu.Lock()
	defer cm.mu.Unlock()

	state, exists := cm.clusters[clusterID]
	if !exists {
		return
	}

	state.historicalCosts = append(state.historicalCosts, state.currentCost)
	if len(state.historicalCosts) > 30 {
		state.historicalCosts = state.historicalCosts[1:]
	}

	state.currentCost = cost
	state.lastUpdated = time.Now()
}

func (cm *CostManagerImpl) GetCostAdjustedWeight(clusterID string, baseWeight int) int {
	if !cm.config.Enabled {
		return baseWeight
	}

	cm.mu.RLock()
	defer cm.mu.RUnlock()

	state, exists := cm.clusters[clusterID]
	if !exists {
		return baseWeight
	}

	allCosts := make([]float64, 0, len(cm.clusters))
	for _, s := range cm.clusters {
		allCosts = append(allCosts, s.currentCost)
	}

	if len(allCosts) == 0 {
		return baseWeight
	}

	minCost := allCosts[0]
	maxCost := allCosts[0]
	for _, c := range allCosts {
		if c < minCost {
			minCost = c
		}
		if c > maxCost {
			maxCost = c
		}
	}

	if maxCost == minCost {
		return baseWeight
	}

	costFactor := 1.0 - (state.currentCost-minCost)/(maxCost-minCost)
	costFactor = 0.5 + costFactor*0.5

	weightInfluence := cm.config.WeightInfluence
	if weightInfluence == 0 {
		weightInfluence = 0.3
	}

	adjustment := 1.0 + (costFactor-0.5)*2*weightInfluence
	adjustedWeight := float64(baseWeight) * adjustment

	return int(adjustedWeight + 0.5)
}

func (cm *CostManagerImpl) CalculateCostScore(clusterID string) float64 {
	cm.mu.RLock()
	defer cm.mu.RUnlock()

	state, exists := cm.clusters[clusterID]
	if !exists {
		return 0.5
	}

	allCosts := make([]float64, 0, len(cm.clusters))
	for _, s := range cm.clusters {
		allCosts = append(allCosts, s.currentCost)
	}

	if len(allCosts) <= 1 {
		return 0.5
	}

	minCost := allCosts[0]
	maxCost := allCosts[0]
	for _, c := range allCosts {
		if c < minCost {
			minCost = c
		}
		if c > maxCost {
			maxCost = c
		}
	}

	if maxCost == minCost {
		return 0.5
	}

	score := 1.0 - (state.currentCost-minCost)/(maxCost-minCost)
	return score
}

func (cm *CostManagerImpl) calculateBaseCost(provider model.CloudProvider, region string) float64 {
	providerPricing, providerExists := defaultPricing[provider]
	if !providerExists {
		return 1.0
	}

	regionPricing, regionExists := providerPricing[region]
	if !regionExists {
		for _, rp := range providerPricing {
			regionPricing = rp
			break
		}
	}

	computeWeight := 0.4
	networkWeight := 0.35
	storageWeight := 0.15
	lbWeight := 0.10

	totalCost := regionPricing.ComputeCostPerHour*computeWeight +
		regionPricing.NetworkCostPerGB*networkWeight*100 +
		regionPricing.StorageCostPerGB*storageWeight*100 +
		regionPricing.LoadBalancerCost*lbWeight

	return totalCost
}

func (cm *CostManagerImpl) RefreshPricing() {
	cm.logger.Debug("Refreshing cloud pricing information")
}

func (cm *CostManagerImpl) GetAllClusterCosts() map[string]float64 {
	cm.mu.RLock()
	defer cm.mu.RUnlock()

	result := make(map[string]float64)
	for clusterID, state := range cm.clusters {
		result[clusterID] = state.currentCost
	}
	return result
}

func (cm *CostManagerImpl) GetMostCostEffectiveCluster() (string, float64) {
	cm.mu.RLock()
	defer cm.mu.RUnlock()

	var bestCluster string
	minCost := 1e9

	for clusterID, state := range cm.clusters {
		if state.currentCost < minCost {
			minCost = state.currentCost
			bestCluster = clusterID
		}
	}

	return bestCluster, minCost
}

func (cm *CostManagerImpl) GetSortedClustersByCost() []string {
	cm.mu.RLock()
	defer cm.mu.RUnlock()

	type clusterCost struct {
		clusterID string
		cost      float64
	}

	costs := make([]clusterCost, 0, len(cm.clusters))
	for clusterID, state := range cm.clusters {
		costs = append(costs, clusterCost{clusterID, state.currentCost})
	}

	for i := 0; i < len(costs); i++ {
		for j := i + 1; j < len(costs); j++ {
			if costs[i].cost > costs[j].cost {
				costs[i], costs[j] = costs[j], costs[i]
			}
		}
	}

	result := make([]string, len(costs))
	for i, c := range costs {
		result[i] = c.clusterID
	}

	return result
}
