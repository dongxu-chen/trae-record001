package prediction

import (
	"cross-cloud-lb/pkg/model"
	"math"
	"sync"
	"time"

	"go.uber.org/zap"
)

type TrafficPredictor interface {
	RecordTraffic(clusterID string, requests int64, bytesIn, bytesOut int64)
	PredictTraffic(clusterID string, horizon time.Duration) *TrafficPrediction
	GetPredictedWeights() map[string]int
	Start(ctx context.Context)
	Stop()
}

type TrafficPredictorImpl struct {
	clusters    map[string]*clusterTrafficState
	mu          sync.RWMutex
	logger      *zap.Logger
	config      model.PredictionConfig
	ticker      *time.Ticker
	lastWeights map[string]int
}

type clusterTrafficState struct {
	clusterID       string
	history         []TrafficSample
	predictions     []TrafficPrediction
	currentRequests int64
	currentBytesIn  int64
	currentBytesOut int64
	lastUpdate      time.Time
}

type TrafficSample struct {
	Timestamp   time.Time
	Requests    int64
	BytesIn     int64
	BytesOut    int64
	RequestRate float64
}

type TrafficPrediction struct {
	Timestamp          time.Time
	Horizon            time.Duration
	PredictedRequests  int64
	PredictedRequestRate float64
	PredictedBytesIn   int64
	PredictedBytesOut  int64
	Confidence         float64
}

const (
	maxHistorySamples = 168
	minHistorySamples = 12
)

func NewTrafficPredictor(config model.PredictionConfig, logger *zap.Logger) *TrafficPredictorImpl {
	return &TrafficPredictorImpl{
		clusters:    make(map[string]*clusterTrafficState),
		logger:      logger,
		config:      config,
		lastWeights: make(map[string]int),
	}
}

func (tp *TrafficPredictorImpl) RegisterCluster(clusterID string) {
	tp.mu.Lock()
	defer tp.mu.Unlock()

	tp.clusters[clusterID] = &clusterTrafficState{
		clusterID:   clusterID,
		history:     make([]TrafficSample, 0, maxHistorySamples),
		predictions: make([]TrafficPrediction, 0, 24),
		lastUpdate:  time.Now(),
	}
}

func (tp *TrafficPredictorImpl) UnregisterCluster(clusterID string) {
	tp.mu.Lock()
	defer tp.mu.Unlock()
	delete(tp.clusters, clusterID)
}

func (tp *TrafficPredictorImpl) RecordTraffic(clusterID string, requests int64, bytesIn, bytesOut int64) {
	tp.mu.Lock()
	defer tp.mu.Unlock()

	state, exists := tp.clusters[clusterID]
	if !exists {
		return
	}

	state.currentRequests += requests
	state.currentBytesIn += bytesIn
	state.currentBytesOut += bytesOut
}

func (tp *TrafficPredictorImpl) Start(ctx context.Context) {
	if !tp.config.Enabled {
		tp.logger.Info("Traffic prediction is disabled")
		return
	}

	interval := tp.config.PredictionInterval
	if interval == 0 {
		interval = 5 * time.Minute
	}

	tp.ticker = time.NewTicker(interval)
	go tp.run(ctx)
}

func (tp *TrafficPredictorImpl) Stop() {
	if tp.ticker != nil {
		tp.ticker.Stop()
	}
}

func (tp *TrafficPredictorImpl) run(ctx context.Context) {
	for {
		select {
		case <-ctx.Done():
			return
		case <-tp.ticker.C:
			tp.collectAndPredict()
		}
	}
}

func (tp *TrafficPredictorImpl) collectAndPredict() {
	tp.mu.Lock()
	defer tp.mu.Unlock()

	now := time.Now()
	interval := tp.config.PredictionInterval
	if interval == 0 {
		interval = 5 * time.Minute
	}

	for clusterID, state := range tp.clusters {
		requestRate := float64(state.currentRequests) / interval.Seconds()

		sample := TrafficSample{
			Timestamp:   now,
			Requests:    state.currentRequests,
			BytesIn:     state.currentBytesIn,
			BytesOut:    state.currentBytesOut,
			RequestRate: requestRate,
		}

		state.history = append(state.history, sample)
		if len(state.history) > maxHistorySamples {
			state.history = state.history[1:]
		}

		state.currentRequests = 0
		state.currentBytesIn = 0
		state.currentBytesOut = 0
		state.lastUpdate = now

		if len(state.history) >= minHistorySamples {
			prediction := tp.predictClusterTraffic(state)
			state.predictions = append(state.predictions, prediction)
			if len(state.predictions) > 24 {
				state.predictions = state.predictions[1:]
			}
		}
	}

	tp.updatePredictedWeights()
}

func (tp *TrafficPredictorImpl) predictClusterTraffic(state *clusterTrafficState) TrafficPrediction {
	horizon := tp.config.PredictionHorizon
	if horizon == 0 {
		horizon = 30 * time.Minute
	}

	avgRate, trend, seasonality := tp.analyzeTrendAndSeasonality(state.history)

	predictedRate := avgRate + trend*horizon.Hours()
	if predictedRate < 0 {
		predictedRate = 0
	}

	predictedRequests := int64(predictedRate * horizon.Seconds())
	confidence := tp.calculateConfidence(state.history)

	return TrafficPrediction{
		Timestamp:            time.Now(),
		Horizon:              horizon,
		PredictedRequests:    predictedRequests,
		PredictedRequestRate: predictedRate,
		Confidence:           confidence,
	}
}

func (tp *TrafficPredictorImpl) analyzeTrendAndSeasonality(history []TrafficSample) (avgRate, trend, seasonality float64) {
	if len(history) == 0 {
		return 0, 0, 0
	}

	var totalRate float64
	for _, sample := range history {
		totalRate += sample.RequestRate
	}
	avgRate = totalRate / float64(len(history))

	if len(history) >= 2 {
		firstHalf := 0.0
		secondHalf := 0.0
		half := len(history) / 2

		for i := 0; i < half; i++ {
			firstHalf += history[i].RequestRate
		}
		for i := half; i < len(history); i++ {
			secondHalf += history[i].RequestRate
		}

		firstHalfAvg := firstHalf / float64(half)
		secondHalfAvg := secondHalf / float64(len(history)-half)

		trend = (secondHalfAvg - firstHalfAvg) / float64(half)
	}

	seasonality = 1.0

	return avgRate, trend, seasonality
}

func (tp *TrafficPredictorImpl) calculateConfidence(history []TrafficSample) float64 {
	if len(history) < minHistorySamples {
		return 0.5
	}

	variance := 0.0
	var avg float64

	for _, sample := range history {
		avg += sample.RequestRate
	}
	avg /= float64(len(history))

	for _, sample := range history {
		diff := sample.RequestRate - avg
		variance += diff * diff
	}
	variance /= float64(len(history))

	stdDev := math.Sqrt(variance)
	coeffOfVariation := stdDev / (avg + 1e-9)

	confidence := 1.0 - math.Min(coeffOfVariation, 1.0)
	confidence = confidence*0.6 + 0.4

	sampleFactor := math.Min(float64(len(history))/float64(maxHistorySamples), 1.0)
	confidence *= 0.5 + sampleFactor*0.5

	return confidence
}

func (tp *TrafficPredictorImpl) PredictTraffic(clusterID string, horizon time.Duration) *TrafficPrediction {
	tp.mu.RLock()
	defer tp.mu.RUnlock()

	state, exists := tp.clusters[clusterID]
	if !exists {
		return nil
	}

	if len(state.predictions) == 0 {
		return nil
	}

	latest := state.predictions[len(state.predictions)-1]
	return &latest
}

func (tp *TrafficPredictorImpl) updatePredictedWeights() {
	if !tp.config.AdjustWeights {
		return
	}

	totalPredictedRate := 0.0
	predictedRates := make(map[string]float64)

	for clusterID, state := range tp.clusters {
		if len(state.predictions) > 0 {
			rate := state.predictions[len(state.predictions)-1].PredictedRequestRate
			predictedRates[clusterID] = rate
			totalPredictedRate += rate
		}
	}

	if totalPredictedRate == 0 {
		return
	}

	influence := tp.config.WeightInfluence
	if influence == 0 {
		influence = 0.2
	}

	for clusterID, rate := range predictedRates {
		ratio := rate / totalPredictedRate
		baseWeight := 100.0 / float64(len(predictedRates))
		predictedWeight := baseWeight + (ratio*100-baseWeight)*influence

		if predictedWeight < 5 {
			predictedWeight = 5
		}
		if predictedWeight > 50 {
			predictedWeight = 50
		}

		tp.lastWeights[clusterID] = int(predictedWeight + 0.5)
	}

	tp.logger.Debug("Updated predicted weights",
		zap.Any("weights", tp.lastWeights))
}

func (tp *TrafficPredictorImpl) GetPredictedWeights() map[string]int {
	tp.mu.RLock()
	defer tp.mu.RUnlock()

	weights := make(map[string]int)
	for k, v := range tp.lastWeights {
		weights[k] = v
	}
	return weights
}

func (tp *TrafficPredictorImpl) GetPredictedWeight(clusterID string) (int, bool) {
	tp.mu.RLock()
	defer tp.mu.RUnlock()

	w, exists := tp.lastWeights[clusterID]
	return w, exists
}

func (tp *TrafficPredictorImpl) GetTrafficHistory(clusterID string) []TrafficSample {
	tp.mu.RLock()
	defer tp.mu.RUnlock()

	state, exists := tp.clusters[clusterID]
	if !exists {
		return nil
	}

	history := make([]TrafficSample, len(state.history))
	copy(history, state.history)
	return history
}
