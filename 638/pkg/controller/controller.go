package controller

import (
	"fmt"
	"sync"
	"time"

	"github.com/k8s-autoscaler/pkg/benefit"
	"github.com/k8s-autoscaler/pkg/cost"
	"github.com/k8s-autoscaler/pkg/linkage"
	"github.com/k8s-autoscaler/pkg/metrics"
	"github.com/k8s-autoscaler/pkg/predictor"
	"github.com/k8s-autoscaler/pkg/recommender"
	"github.com/k8s-autoscaler/pkg/scaler"
	"github.com/k8s-autoscaler/pkg/tuner"
)

type AutotuneResult struct {
	Namespace           string                          `json:"namespace"`
	Deployment          string                          `json:"deployment"`
	CurrentReplicas     int32                           `json:"currentReplicas"`
	RecommendedReplicas int32                           `json:"recommendedReplicas"`
	HPARecommendation   recommender.HPARecommendation   `json:"hpaRecommendation"`
	ScaleDecision       scaler.ScaleDecision            `json:"scaleDecision"`
	CostAnalysis        cost.CostAnalysis               `json:"costAnalysis"`
	CostBenefit         benefit.CostBenefitResult       `json:"costBenefit"`
	PendingLinkages     []linkage.LinkageDecision       `json:"pendingLinkages"`
	TuningResult        tuner.TuningResult              `json:"tuningResult"`
	Timestamp           time.Time                       `json:"timestamp"`
}

type ControllerConfig struct {
	ReconcileInterval      time.Duration
	MetricsWindow          time.Duration
	PredictiveLookAhead    time.Duration
	EnablePredictive       bool
	EnableCostOptimization bool
	EnableAutoTuning       bool
	EnableLinkage          bool
	EnableCostBenefit      bool
	DryRun                 bool
}

type MetricsCollector interface {
	CollectWorkloadMetrics(namespace, deployment string) (*metrics.WorkloadMetrics, error)
	GetHistoricalMetrics(namespace, deployment string, duration time.Duration) ([]metrics.MetricPoint, error)
}

type watchEntry struct {
	Namespace  string
	Deployment string
	PrevReplicas int32
	PrevMetrics  *metrics.WorkloadMetrics
}

type Controller struct {
	config           ControllerConfig
	collector        MetricsCollector
	predictor        *predictor.PredictionEngine
	recommender      *recommender.HPARecommender
	scaler           *scaler.PredictiveScaler
	costOptimizer    *cost.CostOptimizer
	autoTuner        *tuner.AutoTuner
	linkageGraph     *linkage.LinkageGraph
	costBenefit      *benefit.CostBenefitAnalyzer
	results          map[string]*AutotuneResult
	previousReplicas map[string]int32
	previousMetrics  map[string]*metrics.WorkloadMetrics
	mu               sync.RWMutex
	stopCh           chan struct{}
	watchList        map[string]watchEntry
	watchMu          sync.RWMutex
}

func NewController(
	config ControllerConfig,
	collector MetricsCollector,
	pred *predictor.PredictionEngine,
	rec *recommender.HPARecommender,
	sc *scaler.PredictiveScaler,
	co *cost.CostOptimizer,
	at *tuner.AutoTuner,
	lg *linkage.LinkageGraph,
	cb *benefit.CostBenefitAnalyzer,
) *Controller {
	return &Controller{
		config:           config,
		collector:        collector,
		predictor:        pred,
		recommender:      rec,
		scaler:           sc,
		costOptimizer:    co,
		autoTuner:        at,
		linkageGraph:     lg,
		costBenefit:      cb,
		results:          make(map[string]*AutotuneResult),
		previousReplicas: make(map[string]int32),
		previousMetrics:  make(map[string]*metrics.WorkloadMetrics),
		stopCh:           make(chan struct{}),
		watchList:        make(map[string]watchEntry),
	}
}

func (c *Controller) Start() error {
	go c.runLoop()
	return nil
}

func (c *Controller) Stop() {
	close(c.stopCh)
}

func (c *Controller) runLoop() {
	ticker := time.NewTicker(c.config.ReconcileInterval)
	defer ticker.Stop()

	for {
		select {
		case <-c.stopCh:
			return
		case <-ticker.C:
			c.reconcileAll()
		}
	}
}

func (c *Controller) reconcileAll() {
	c.watchMu.RLock()
	entries := make([]watchEntry, 0, len(c.watchList))
	for _, entry := range c.watchList {
		entries = append(entries, entry)
	}
	c.watchMu.RUnlock()

	for _, entry := range entries {
		c.Reconcile(entry.Namespace, entry.Deployment)
	}
}

func convertMetricPoints(points []metrics.MetricPoint) []predictor.TimeSeriesPoint {
	result := make([]predictor.TimeSeriesPoint, len(points))
	for i, p := range points {
		result[i] = predictor.TimeSeriesPoint{
			Timestamp: p.Timestamp,
			Value:     p.Value,
		}
	}
	return result
}

func (c *Controller) applyTunedParams() {
	if !c.config.EnableAutoTuning || c.autoTuner == nil {
		return
	}
	params := c.autoTuner.GetParams()

	scalerCfg := c.scaler.Config()
	scalerCfg.ScaleUpThreshold = params.ScaleUpThreshold
	scalerCfg.ScaleDownThreshold = params.ScaleDownThreshold

	recConfig := c.recommender.Config()
	recConfig.CompositeTarget = params.CompositeTarget
	recConfig.MaxScaleUpRatio = params.MaxScaleUpRatio
	if params.FusionWeights != nil {
		if recConfig.FusionWeights == nil {
			recConfig.FusionWeights = make(map[recommender.MetricType]float64)
		}
		for k, v := range params.FusionWeights {
			recConfig.FusionWeights[recommender.MetricType(k)] = v
		}
	}
}

func (c *Controller) Reconcile(namespace, deployment string) (*AutotuneResult, error) {
	c.applyTunedParams()

	wm, err := c.collector.CollectWorkloadMetrics(namespace, deployment)
	if err != nil {
		return nil, fmt.Errorf("failed to collect metrics: %w", err)
	}

	key := namespace + "/" + deployment
	c.mu.RLock()
	prevReplicas := c.previousReplicas[key]
	prevMetrics := c.previousMetrics[key]
	c.mu.RUnlock()

	if c.config.EnableLinkage && c.linkageGraph != nil && prevReplicas > 0 && prevReplicas != wm.Replicas {
		c.linkageGraph.OnSourceScaled(namespace, deployment, prevReplicas, wm.Replicas, time.Now())
	}

	hpaRec := c.recommender.Recommend(namespace, deployment, wm.Replicas, *wm)

	recommendedReplicas := hpaRec.TargetReplicas

	var scaleDecision scaler.ScaleDecision
	if c.config.EnablePredictive {
		historical, histErr := c.collector.GetHistoricalMetrics(namespace, deployment, c.config.MetricsWindow)
		if histErr != nil {
			historical = nil
		}
		tsPoints := convertMetricPoints(historical)
		scaleDecision = c.scaler.Evaluate(namespace, deployment, wm.Replicas, tsPoints, *wm)
		if scaleDecision.Confidence > 0.7 {
			recommendedReplicas = scaleDecision.DesiredReplicas
		}
	}

	var costAnalysis cost.CostAnalysis
	if c.config.EnableCostOptimization {
		costAnalysis = c.costOptimizer.AnalyzeWorkload(namespace, deployment, *wm, recommendedReplicas)
	}

	slaViolations := len(costAnalysis.SLAViolations)

	if c.config.EnableAutoTuning && c.autoTuner != nil {
		params := c.autoTuner.GetParams()
		avgCPU := wm.AggCPU / float64(wm.Replicas)
		avgQPS := wm.AggQPS / float64(wm.Replicas)
		costChange := 0.0
		if wm.Replicas > 0 {
			costChange = float64(recommendedReplicas - wm.Replicas) / float64(wm.Replicas) * 100
		}
		sample := tuner.TuningSample{
			Timestamp:         time.Now(),
			ParamsBefore:      params,
			CurrentReplicas:   wm.Replicas,
			DesiredReplicas:   recommendedReplicas,
			AvgCPU:            avgCPU,
			AvgQPS:            avgQPS,
			AvgLatency:        wm.AggLatency,
			SLAViolations:     slaViolations,
			CostChangePercent: costChange,
		}
		c.autoTuner.RecordSample(sample)
	}

	var cbResult benefit.CostBenefitResult
	if c.config.EnableCostBenefit && c.costBenefit != nil {
		if recommendedReplicas != wm.Replicas {
			action := "scale_up"
			if recommendedReplicas < wm.Replicas {
				action = "scale_down"
			}
			sa := benefit.ScaleAction{
				Service:   deployment,
				Namespace: namespace,
				OldReplicas: wm.Replicas,
				NewReplicas: recommendedReplicas,
				Action:    action,
				Timestamp: time.Now(),
			}
			if prevMetrics != nil {
				cbResult = c.costBenefit.Analyze(sa, *prevMetrics, *wm, 0, slaViolations)
			} else {
				cbResult = c.costBenefit.EstimateBenefit(namespace, deployment, recommendedReplicas, *wm)
			}
		}
	}

	var pendingLinkages []linkage.LinkageDecision
	if c.config.EnableLinkage && c.linkageGraph != nil {
		pendingLinkages = c.linkageGraph.GetPendingDecisions(namespace, deployment, time.Now())
		for _, ld := range pendingLinkages {
			recommendedReplicas += ld.TargetRecommendedChange
			if recommendedReplicas < 1 {
				recommendedReplicas = 1
			}
		}
	}

	var tuningResult tuner.TuningResult
	if c.config.EnableAutoTuning && c.autoTuner != nil {
		tuningResult = c.autoTuner.GetTuningResult()
	}

	result := &AutotuneResult{
		Namespace:           namespace,
		Deployment:          deployment,
		CurrentReplicas:     wm.Replicas,
		RecommendedReplicas: recommendedReplicas,
		HPARecommendation:   hpaRec,
		ScaleDecision:       scaleDecision,
		CostAnalysis:        costAnalysis,
		CostBenefit:         cbResult,
		PendingLinkages:     pendingLinkages,
		TuningResult:        tuningResult,
		Timestamp:           time.Now(),
	}

	c.mu.Lock()
	c.results[key] = result
	c.previousReplicas[key] = wm.Replicas
	c.previousMetrics[key] = wm
	c.mu.Unlock()

	c.watchMu.Lock()
	if we, ok := c.watchList[key]; ok {
		we.PrevReplicas = wm.Replicas
		we.PrevMetrics = wm
		c.watchList[key] = we
	}
	c.watchMu.Unlock()

	return result, nil
}

func (c *Controller) GetResult(namespace, deployment string) (*AutotuneResult, bool) {
	key := namespace + "/" + deployment
	c.mu.RLock()
	defer c.mu.RUnlock()
	result, ok := c.results[key]
	return result, ok
}

func (c *Controller) GetAllResults() map[string]*AutotuneResult {
	c.mu.RLock()
	defer c.mu.RUnlock()
	copy := make(map[string]*AutotuneResult, len(c.results))
	for k, v := range c.results {
		copy[k] = v
	}
	return copy
}

func (c *Controller) ApplyScaling(namespace, deployment string, replicas int32) error {
	if c.config.DryRun {
		fmt.Printf("[DRY-RUN] Would scale %s/%s to %d replicas\n", namespace, deployment, replicas)
		return nil
	}
	fmt.Printf("Scaling %s/%s to %d replicas\n", namespace, deployment, replicas)
	return nil
}

func (c *Controller) WatchDeployment(namespace, deployment string) {
	key := namespace + "/" + deployment
	c.watchMu.Lock()
	defer c.watchMu.Unlock()
	c.watchList[key] = watchEntry{Namespace: namespace, Deployment: deployment}
}

func (c *Controller) UnwatchDeployment(namespace, deployment string) {
	key := namespace + "/" + deployment
	c.watchMu.Lock()
	defer c.watchMu.Unlock()
	delete(c.watchList, key)
}

func (c *Controller) GetMetrics(namespace, deployment string) (*metrics.WorkloadMetrics, error) {
	return c.collector.CollectWorkloadMetrics(namespace, deployment)
}

func (c *Controller) GetRecommendation(namespace, deployment string) (*recommender.HPARecommendation, error) {
	result, ok := c.GetResult(namespace, deployment)
	if !ok {
		_, err := c.Reconcile(namespace, deployment)
		if err != nil {
			return nil, err
		}
		result, _ = c.GetResult(namespace, deployment)
	}
	if result == nil {
		return nil, fmt.Errorf("no recommendation available")
	}
	rec := result.HPARecommendation
	return &rec, nil
}

func (c *Controller) GetPrediction(namespace, deployment string) (*scaler.ScaleDecision, error) {
	result, ok := c.GetResult(namespace, deployment)
	if !ok {
		_, err := c.Reconcile(namespace, deployment)
		if err != nil {
			return nil, err
		}
		result, _ = c.GetResult(namespace, deployment)
	}
	if result == nil {
		return nil, fmt.Errorf("no prediction available")
	}
	sd := result.ScaleDecision
	return &sd, nil
}

func (c *Controller) GetCost(namespace, deployment string) (*cost.CostAnalysis, error) {
	result, ok := c.GetResult(namespace, deployment)
	if !ok {
		_, err := c.Reconcile(namespace, deployment)
		if err != nil {
			return nil, err
		}
		result, _ = c.GetResult(namespace, deployment)
	}
	if result == nil {
		return nil, fmt.Errorf("no cost analysis available")
	}
	ca := result.CostAnalysis
	return &ca, nil
}

func (c *Controller) GetAutotune(namespace, deployment string) (*AutotuneResult, error) {
	result, ok := c.GetResult(namespace, deployment)
	if !ok {
		return c.Reconcile(namespace, deployment)
	}
	return result, nil
}

func (c *Controller) Scale(namespace, deployment string, replicas int32) error {
	return c.ApplyScaling(namespace, deployment, replicas)
}

func (c *Controller) AddWatch(namespace, deployment string) error {
	c.WatchDeployment(namespace, deployment)
	return nil
}

func (c *Controller) RemoveWatch(namespace, deployment string) error {
	c.UnwatchDeployment(namespace, deployment)
	return nil
}

func (c *Controller) GetDashboard() (map[string]*AutotuneResult, error) {
	return c.GetAllResults(), nil
}

func (c *Controller) GetTuningResult() (tuner.TuningResult, error) {
	if c.autoTuner == nil {
		return tuner.TuningResult{}, fmt.Errorf("auto tuner not enabled")
	}
	return c.autoTuner.GetTuningResult(), nil
}

func (c *Controller) GetTuningHistory() ([]tuner.TuningSample, error) {
	if c.autoTuner == nil {
		return nil, fmt.Errorf("auto tuner not enabled")
	}
	return c.autoTuner.GetRollingWindow(), nil
}

func (c *Controller) GetLinkages() ([]linkage.ServiceDependency, error) {
	if c.linkageGraph == nil {
		return nil, fmt.Errorf("linkage not enabled")
	}
	return c.linkageGraph.GetDependencies(), nil
}

func (c *Controller) AddLinkage(dep linkage.ServiceDependency) error {
	if c.linkageGraph == nil {
		return fmt.Errorf("linkage not enabled")
	}
	c.linkageGraph.AddDependency(dep)
	return nil
}

func (c *Controller) GetPendingLinkages() ([]linkage.LinkageDecision, error) {
	if c.linkageGraph == nil {
		return nil, fmt.Errorf("linkage not enabled")
	}
	return c.linkageGraph.GetAllPending(), nil
}

func (c *Controller) GetCostBenefitHistory() ([]benefit.CostBenefitResult, error) {
	if c.costBenefit == nil {
		return nil, fmt.Errorf("cost benefit analyzer not enabled")
	}
	return c.costBenefit.GetHistory(), nil
}
