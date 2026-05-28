package weight

import (
	"context"
	"cross-cloud-lb/pkg/model"
	"math"
	"sort"
	"sync"
	"time"

	"go.uber.org/zap"
)

type WeightAdjuster interface {
	Start(ctx context.Context)
	Stop()
	UpdateClusterMetrics(metrics *model.ClusterMetrics)
	GetClusterWeight(clusterID string) int
	RegisterCallback(callback func(clusterID string, newWeight int))
}

type WeightAdjusterImpl struct {
	config      model.WeightAdjustmentConfig
	clusters    map[string]*clusterWeightState
	mu          sync.RWMutex
	ticker      *time.Ticker
	logger      *zap.Logger
	callbacks   []func(string, int)
}

type clusterWeightState struct {
	clusterID       string
	currentWeight   int
	minWeight       int
	maxWeight       int
	metrics         *model.ClusterMetrics
	metricsHistory  []*model.ClusterMetrics
}

const maxMetricsHistory = 10

func NewWeightAdjuster(config model.WeightAdjustmentConfig, logger *zap.Logger) *WeightAdjusterImpl {
	return &WeightAdjusterImpl{
		config:   config,
		clusters: make(map[string]*clusterWeightState),
		logger:   logger,
	}
}

func (wa *WeightAdjusterImpl) Start(ctx context.Context) {
	if !wa.config.Enabled {
		wa.logger.Info("Dynamic weight adjustment is disabled")
		return
	}

	wa.ticker = time.NewTicker(wa.config.AdjustInterval)
	go wa.run(ctx)
}

func (wa *WeightAdjusterImpl) Stop() {
	if wa.ticker != nil {
		wa.ticker.Stop()
	}
}

func (wa *WeightAdjusterImpl) AddCluster(cluster *model.Cluster) {
	wa.mu.Lock()
	defer wa.mu.Unlock()

	state := &clusterWeightState{
		clusterID:      cluster.ID,
		currentWeight:  cluster.Weight,
		minWeight:      cluster.MinWeight,
		maxWeight:      cluster.MaxWeight,
		metricsHistory: make([]*model.ClusterMetrics, 0, maxMetricsHistory),
	}

	if state.minWeight == 0 {
		state.minWeight = 1
	}
	if state.maxWeight == 0 {
		state.maxWeight = 100
	}

	wa.clusters[cluster.ID] = state
}

func (wa *WeightAdjusterImpl) RemoveCluster(clusterID string) {
	wa.mu.Lock()
	defer wa.mu.Unlock()
	delete(wa.clusters, clusterID)
}

func (wa *WeightAdjusterImpl) UpdateClusterMetrics(metrics *model.ClusterMetrics) {
	wa.mu.Lock()
	defer wa.mu.Unlock()

	state, exists := wa.clusters[metrics.ClusterID]
	if !exists {
		return
	}

	state.metrics = metrics
	state.metricsHistory = append(state.metricsHistory, metrics)
	if len(state.metricsHistory) > maxMetricsHistory {
		state.metricsHistory = state.metricsHistory[1:]
	}
}

func (wa *WeightAdjusterImpl) GetClusterWeight(clusterID string) int {
	wa.mu.RLock()
	defer wa.mu.RUnlock()

	if state, exists := wa.clusters[clusterID]; exists {
		return state.currentWeight
	}
	return 1
}

func (wa *WeightAdjusterImpl) RegisterCallback(callback func(clusterID string, newWeight int)) {
	wa.callbacks = append(wa.callbacks, callback)
}

func (wa *WeightAdjusterImpl) run(ctx context.Context) {
	for {
		select {
		case <-ctx.Done():
			return
		case <-wa.ticker.C:
			wa.adjustWeights()
		}
	}
}

func (wa *WeightAdjusterImpl) adjustWeights() {
	wa.mu.Lock()
	defer wa.mu.Unlock()

	if len(wa.clusters) < 2 {
		return
	}

	avgResponseTimes := make(map[string]int64)
	errorRates := make(map[string]float64)

	for clusterID, state := range wa.clusters {
		avgRT, errRate := wa.calculateAggregateMetrics(state)
		avgResponseTimes[clusterID] = avgRT
		errorRates[clusterID] = errRate
	}

	relativeScores := wa.calculateRelativeScores(avgResponseTimes, errorRates)

	for clusterID, score := range relativeScores {
		state := wa.clusters[clusterID]
		newWeight := wa.calculateNewWeight(state, score)

		if newWeight != state.currentWeight {
			wa.logger.Info("Adjusting cluster weight",
				zap.String("cluster_id", clusterID),
				zap.Int("old_weight", state.currentWeight),
				zap.Int("new_weight", newWeight),
				zap.Float64("score", score))

			state.currentWeight = newWeight
			wa.notifyCallbacks(clusterID, newWeight)
		}
	}
}

func (wa *WeightAdjusterImpl) calculateAggregateMetrics(state *clusterWeightState) (int64, float64) {
	if len(state.metricsHistory) == 0 {
		return 100, 0.0
	}

	var totalRT int64
	var totalErrRate float64
	count := 0

	for _, metrics := range state.metricsHistory {
		if metrics != nil {
			totalRT += metrics.AvgResponseTime
			totalErrRate += metrics.ErrorRate
			count++
		}
	}

	if count == 0 {
		return 100, 0.0
	}

	return totalRT / int64(count), totalErrRate / float64(count)
}

func (wa *WeightAdjusterImpl) calculateRelativeScores(
	avgResponseTimes map[string]int64,
	errorRates map[string]float64,
) map[string]float64 {
	if len(avgResponseTimes) == 0 {
		return nil
	}

	var minRT int64 = math.MaxInt64
	var maxRT int64 = 0
	var maxErrRate float64 = 0

	for _, rt := range avgResponseTimes {
		if rt < minRT {
			minRT = rt
		}
		if rt > maxRT {
			maxRT = rt
		}
	}

	for _, er := range errorRates {
		if er > maxErrRate {
			maxErrRate = er
		}
	}

	scores := make(map[string]float64)
	for clusterID, rt := range avgResponseTimes {
		rtScore := wa.normalizeRT(rt, minRT, maxRT)
		errScore := wa.normalizeErrorRate(errorRates[clusterID], maxErrRate)

		score := rtScore*wa.config.ResponseTimeWeight + errScore*wa.config.ErrorRateWeight
		scores[clusterID] = score
	}

	return scores
}

func (wa *WeightAdjusterImpl) normalizeRT(rt, minRT, maxRT int64) float64 {
	if maxRT == minRT {
		return 1.0
	}
	return 1.0 - float64(rt-minRT)/float64(maxRT-minRT)
}

func (wa *WeightAdjusterImpl) normalizeErrorRate(errRate, maxErrRate float64) float64 {
	if maxErrRate == 0 {
		return 1.0
	}
	return 1.0 - errRate/maxErrRate
}

func (wa *WeightAdjusterImpl) calculateNewWeight(state *clusterWeightState, score float64) int {
	stepSize := wa.config.StepSize
	if stepSize == 0 {
		stepSize = 5
	}

	targetWeight := int(float64(state.maxWeight) * score)

	if targetWeight > state.currentWeight+stepSize {
		targetWeight = state.currentWeight + stepSize
	} else if targetWeight < state.currentWeight-stepSize {
		targetWeight = state.currentWeight - stepSize
	}

	if targetWeight < state.minWeight {
		targetWeight = state.minWeight
	}
	if targetWeight > state.maxWeight {
		targetWeight = state.maxWeight
	}

	return targetWeight
}

func (wa *WeightAdjusterImpl) notifyCallbacks(clusterID string, newWeight int) {
	for _, callback := range wa.callbacks {
		go callback(clusterID, newWeight)
	}
}

func (wa *WeightAdjusterImpl) GetAllWeights() map[string]int {
	wa.mu.RLock()
	defer wa.mu.RUnlock()

	weights := make(map[string]int)
	for clusterID, state := range wa.clusters {
		weights[clusterID] = state.currentWeight
	}
	return weights
}

func (wa *WeightAdjusterImpl) GetSortedClustersByWeight() []string {
	wa.mu.RLock()
	defer wa.mu.RUnlock()

	type clusterWeight struct {
		clusterID string
		weight    int
	}

	cws := make([]clusterWeight, 0, len(wa.clusters))
	for clusterID, state := range wa.clusters {
		cws = append(cws, clusterWeight{clusterID, state.currentWeight})
	}

	sort.Slice(cws, func(i, j int) bool {
		return cws[i].weight > cws[j].weight
	})

	result := make([]string, len(cws))
	for i, cw := range cws {
		result[i] = cw.clusterID
	}

	return result
}
