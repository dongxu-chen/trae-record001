package autoscaler

import (
	"context"
	"fmt"
	"sort"
	"sync"
	"time"

	"github.com/sirupsen/logrus"

	kafkaclient "kafka-autoscaler/pkg/kafka"
	k8sclient "kafka-autoscaler/pkg/kubernetes"
	"kafka-autoscaler/pkg/predictor"
	promclient "kafka-autoscaler/pkg/prometheus"
)

type ScalingMode string

const (
	ModeOff        ScalingMode = "off"
	ModeObservation ScalingMode = "observation"
	ModeAuto       ScalingMode = "auto"
)

type ScalerConfig struct {
	ConsumerGroupID             string
	K8sDeployment               string
	K8sNamespace                string
	K8sResourceType             string
	MinReplicas                 int32
	MaxReplicas                 int32
	ScaleUpThreshold            int64
	ScaleDownThreshold          int64
	ScaleUpIncrement            int32
	ScaleDownDecrement          int32
	CooldownPeriod              time.Duration
	PredictionWindow            time.Duration
	UsePrediction               bool
	TargetLag                   int64
	Mode                        ScalingMode
	EnablePartitionRebalance    bool
	EnableRollingScale          bool
	RollingScaleInterval        time.Duration
	MessageProcessingLatency    time.Duration
	EnableScaleDownAfterLagClear bool
	ScaleDownAfterLagDelay      time.Duration
	EnableSelfHealing           bool
	SelfHealingThreshold        int
	SelfHealingCooldown         time.Duration
	EnableSlowPartitionDetection bool
	SlowPartitionThreshold      time.Duration
}

type ScaleDownState struct {
	InProgress      bool
	StartLag        int64
	StartTime       time.Time
	TargetReplicas  int32
	CurrentStep     int
}

type SlowPartitionInfo struct {
	Topic          string
	Partition      int32
	Lag            int64
	AvgLag         float64
	ConsumerID     string
	ProcessingRate float64
	IsSlow         bool
	AnomalyScore   float64
}

type BacklogAnalysis struct {
	Timestamp            time.Time
	TotalLag             int64
	SlowPartitions       []*SlowPartitionInfo
	TopLagPartitions     []*SlowPartitionInfo
	AverageProcessingRate float64
	ArrivalRate          float64
	RootCause            string
	Severity             string
}

type SelfHealingAction struct {
	Timestamp      time.Time
	ActionType     string
	Reason         string
	PodName        string
	Success        bool
}

type ScalingState string

const (
	StateIdle         ScalingState = "idle"
	StateScalingUp    ScalingState = "scaling_up"
	StateScalingDown  ScalingState = "scaling_down"
	StateWaitingStable ScalingState = "waiting_stable"
)

type AutoScaler struct {
	kafkaClient           *kafkaclient.Client
	k8sClient             *k8sclient.Client
	promCollector         *promclient.Collector
	predictor             *predictor.Predictor
	config                *ScalerConfig
	logger                *logrus.Logger
	ctx                   context.Context
	cancel                context.CancelFunc
	wg                    sync.WaitGroup
	mu                    sync.RWMutex
	lastScaleTime         time.Time
	scalingInProgress     bool
	scalingState          ScalingState
	targetReplicas        int32
	lastRollingScaleTime  time.Time
	lagBeforeScale        int64
	stableCheckCount      int
	scaleDownState        ScaleDownState
	lagClearedTime        time.Time
	consecutiveErrorCount int
	lastSelfHealingTime   time.Time
	healingActions        []*SelfHealingAction
	lastAnalysis          *BacklogAnalysis
}

type ScaleEvent struct {
	Timestamp      time.Time
	Action         string
	FromReplicas   int32
	ToReplicas     int32
	Reason         string
	CurrentLag     int64
	PredictedLag   int64
}

func NewAutoScaler(
	kafkaClient *kafkaclient.Client,
	k8sClient *k8sclient.Client,
	promCollector *promclient.Collector,
	predictor *predictor.Predictor,
	config *ScalerConfig,
	logger *logrus.Logger,
) *AutoScaler {
	ctx, cancel := context.WithCancel(context.Background())

	return &AutoScaler{
		kafkaClient:   kafkaClient,
		k8sClient:     k8sClient,
		promCollector: promCollector,
		predictor:     predictor,
		config:        config,
		logger:        logger,
		ctx:           ctx,
		cancel:        cancel,
	}
}

func (a *AutoScaler) Start() error {
	if a.config.Mode == ModeOff {
		a.logger.Info("Auto-scaler is disabled")
		return nil
	}

	a.wg.Add(1)
	go a.run()

	a.logger.Infof("Auto-scaler started for consumer group: %s, mode: %s", a.config.ConsumerGroupID, a.config.Mode)
	return nil
}

func (a *AutoScaler) Stop() {
	a.logger.Info("Stopping auto-scaler...")
	a.cancel()
	a.wg.Wait()
	a.logger.Info("Auto-scaler stopped")
}

func (a *AutoScaler) run() {
	defer a.wg.Done()

	ticker := time.NewTicker(30 * time.Second)
	defer ticker.Stop()

	for {
		select {
		case <-a.ctx.Done():
			return
		case <-ticker.C:
			a.reconcile()
		}
	}
}

func (a *AutoScaler) reconcile() {
	a.mu.Lock()
	if a.scalingInProgress {
		if a.config.EnableRollingScale {
			a.continueRollingScaling()
			a.mu.Unlock()
			return
		}
		a.mu.Unlock()
		a.logger.Debug("Scaling already in progress, skipping")
		return
	}

	if !a.lastScaleTime.IsZero() && time.Since(a.lastScaleTime) < a.config.CooldownPeriod {
		a.mu.Unlock()
		a.logger.Debug("Within cooldown period, skipping")
		return
	}
	a.mu.Unlock()

	totalLag, err := a.kafkaClient.GetTotalLag(a.config.ConsumerGroupID)
	if err != nil {
		a.logger.Errorf("Failed to get consumer group lag: %v", err)
		return
	}

	memberCount, err := a.kafkaClient.GetConsumerGroupMembers(a.config.ConsumerGroupID)
	if err != nil {
		a.logger.Errorf("Failed to get consumer group members: %v", err)
		return
	}

	a.promCollector.RecordConsumerGroupTotalLag(a.config.ConsumerGroupID, totalLag)
	a.promCollector.RecordConsumerGroupMembers(a.config.ConsumerGroupID, memberCount)
	a.promCollector.RecordLagThreshold(a.config.ConsumerGroupID, "scale_up", float64(a.config.ScaleUpThreshold))
	a.promCollector.RecordLagThreshold(a.config.ConsumerGroupID, "scale_down", float64(a.config.ScaleDownThreshold))

	lagHistory := a.promCollector.GetLagHistory(a.config.ConsumerGroupID)
	lagDataPoints := make([]predictor.LagDataPoint, len(lagHistory))
	for i, record := range lagHistory {
		lagDataPoints[i] = predictor.LagDataPoint{
			Timestamp: record.Timestamp,
			Lag:       record.Lag,
		}
	}

	var predictedLag int64
	var processingRate float64
	if a.config.UsePrediction && len(lagDataPoints) >= 5 {
		pred := a.predictor.PredictEnsembleWithProcessingTime(lagDataPoints, a.config.PredictionWindow, a.config.MessageProcessingLatency)
		if pred != nil {
			predictedLag = pred.PredictedLag
			processingRate = pred.ProcessingRate
			a.promCollector.RecordPredictedLag(a.config.ConsumerGroupID, fmt.Sprintf("%dm", int(a.config.PredictionWindow.Minutes())), predictedLag)
			a.logger.Infof("Predicted lag in %v: %d (trend: %s, confidence: %.2f, rate: %.2f msg/s)",
				a.config.PredictionWindow, predictedLag, pred.Trend, pred.Confidence, processingRate)
		}
	}

	scaler, err := a.k8sClient.GetScaler(a.config.K8sResourceType)
	if err != nil {
		a.logger.Errorf("Failed to get scaler: %v", err)
		return
	}

	currentReplicas, err := scaler.GetReplicas(a.ctx, a.config.K8sDeployment, a.config.K8sNamespace)
	if err != nil {
		a.logger.Errorf("Failed to get current replicas: %v", err)
		return
	}

	a.promCollector.RecordScalerReplicas(a.config.K8sDeployment, a.config.K8sNamespace, currentReplicas)

	a.logger.Infof("Consumer group %s: total_lag=%d, members=%d, predicted_lag=%d, replicas=%d, processing_rate=%.2f msg/s",
		a.config.ConsumerGroupID, totalLag, memberCount, predictedLag, currentReplicas, processingRate)

	desiredReplicas := a.calculateDesiredReplicas(totalLag, predictedLag, currentReplicas, memberCount, processingRate)

	if a.config.EnableScaleDownAfterLagClear {
		desiredReplicas = a.checkAndScaleDownAfterLagClear(totalLag, currentReplicas, desiredReplicas)
	}

	if desiredReplicas != currentReplicas {
		a.triggerScaling(currentReplicas, desiredReplicas, totalLag, predictedLag, scaler)
	}

	if a.config.EnableSlowPartitionDetection {
		a.analyzeBacklogCauses(totalLag)
	}

	if a.config.EnableSelfHealing {
		a.checkAndPerformSelfHealing(totalLag, currentReplicas, memberCount)
	}

	if a.config.EnablePartitionRebalance {
		a.checkAndTriggerRebalance(totalLag)
	}
}

func (a *AutoScaler) calculateDesiredReplicas(currentLag, predictedLag int64, currentReplicas int32, memberCount int, processingRate float64) int32 {
	effectiveLag := currentLag
	if a.config.UsePrediction && predictedLag > currentLag {
		effectiveLag = predictedLag
	}

	if effectiveLag >= a.config.ScaleUpThreshold {
		if currentReplicas < a.config.MaxReplicas {
			var newReplicas int32
			if processingRate > 0 {
				estimatedReplicas := a.estimateRequiredReplicas(effectiveLag, processingRate, currentReplicas)
				if estimatedReplicas > currentReplicas {
					newReplicas = estimatedReplicas
				} else {
					newReplicas = currentReplicas + a.config.ScaleUpIncrement
				}
			} else {
				newReplicas = currentReplicas + a.config.ScaleUpIncrement
			}

			if newReplicas > a.config.MaxReplicas {
				newReplicas = a.config.MaxReplicas
			}
			a.logger.Infof("Scale up condition met: lag=%d >= threshold=%d, processing_rate=%.2f, new_replicas=%d",
				effectiveLag, a.config.ScaleUpThreshold, processingRate, newReplicas)
			return newReplicas
		} else {
			a.logger.Infof("Scale up condition met but already at max replicas: %d", a.config.MaxReplicas)
		}
	}

	if currentLag <= a.config.ScaleDownThreshold {
		if currentReplicas > a.config.MinReplicas {
			newReplicas := currentReplicas - a.config.ScaleDownDecrement
			if newReplicas < a.config.MinReplicas {
				newReplicas = a.config.MinReplicas
			}
			a.logger.Infof("Scale down condition met: lag=%d <= threshold=%d, decrement=%d, new_replicas=%d",
				currentLag, a.config.ScaleDownThreshold, a.config.ScaleDownDecrement, newReplicas)
			return newReplicas
		}
	}

	return currentReplicas
}

func (a *AutoScaler) estimateRequiredReplicas(totalLag int64, processingRate float64, currentReplicas int32) int32 {
	if processingRate <= 0 {
		return currentReplicas
	}

	perReplicaRate := processingRate / float64(currentReplicas)
	if perReplicaRate <= 0 {
		return currentReplicas
	}

	targetProcessTime := a.config.MessageProcessingLatency.Seconds()
	if targetProcessTime <= 0 {
		targetProcessTime = 60
	}

	requiredRate := float64(totalLag) / targetProcessTime
	requiredReplicas := int32(requiredRate / perReplicaRate)

	if requiredReplicas < currentReplicas {
		requiredReplicas = currentReplicas
	}

	requiredReplicas = requiredReplicas + 1

	a.logger.Debugf("Estimated replicas: total_lag=%d, per_replica_rate=%.2f msg/s, target_time=%.0fs, required=%d",
		totalLag, perReplicaRate, targetProcessTime, requiredReplicas)

	return requiredReplicas
}

func (a *AutoScaler) continueRollingScaling() {
	if !a.config.EnableRollingScale {
		return
	}

	if a.scalingState == StateIdle {
		return
	}

	scaler, err := a.k8sClient.GetScaler(a.config.K8sResourceType)
	if err != nil {
		a.logger.Errorf("Failed to get scaler in rolling process: %v", err)
		return
	}

	currentReplicas, err := scaler.GetReplicas(a.ctx, a.config.K8sDeployment, a.config.K8sNamespace)
	if err != nil {
		a.logger.Errorf("Failed to get current replicas: %v", err)
		return
	}

	if a.scalingState == StateWaitingStable {
		a.checkStability(currentReplicas, scaler)
		return
	}

	if time.Since(a.lastRollingScaleTime) < a.config.RollingScaleInterval {
		return
	}

	if a.scalingState == StateScalingUp && currentReplicas < a.targetReplicas {
		nextReplicas := currentReplicas + 1
		if nextReplicas > a.targetReplicas {
			nextReplicas = a.targetReplicas
		}

		a.logger.Infof("Rolling scale up: %d -> %d (target: %d)", currentReplicas, nextReplicas, a.targetReplicas)

		if a.config.Mode != ModeObservation {
			if err := scaler.Scale(a.ctx, a.config.K8sDeployment, a.config.K8sNamespace, nextReplicas); err != nil {
				a.logger.Errorf("Failed to rolling scale up: %v", err)
				return
			}
			a.promCollector.RecordScalerAction("rolling_scale_up", a.config.ConsumerGroupID, a.config.K8sDeployment)
		}

		a.lastRollingScaleTime = time.Now()
		a.scalingState = StateWaitingStable
		a.stableCheckCount = 0
		a.lagBeforeScale, _ = a.kafkaClient.GetTotalLag(a.config.ConsumerGroupID)
		return
	}

	if a.scalingState == StateScalingDown && currentReplicas > a.targetReplicas {
		nextReplicas := currentReplicas - 1
		if nextReplicas < a.targetReplicas {
			nextReplicas = a.targetReplicas
		}

		a.logger.Infof("Rolling scale down: %d -> %d (target: %d)", currentReplicas, nextReplicas, a.targetReplicas)

		if a.config.Mode != ModeObservation {
			if err := scaler.Scale(a.ctx, a.config.K8sDeployment, a.config.K8sNamespace, nextReplicas); err != nil {
				a.logger.Errorf("Failed to rolling scale down: %v", err)
				return
			}
			a.promCollector.RecordScalerAction("rolling_scale_down", a.config.ConsumerGroupID, a.config.K8sDeployment)
		}

		a.lastRollingScaleTime = time.Now()
		a.scalingState = StateWaitingStable
		a.stableCheckCount = 0
		return
	}

	if (a.scalingState == StateScalingUp && currentReplicas >= a.targetReplicas) ||
		(a.scalingState == StateScalingDown && currentReplicas <= a.targetReplicas) {
		a.logger.Infof("Rolling scaling completed: current=%d, target=%d", currentReplicas, a.targetReplicas)
		a.scalingState = StateIdle
		a.scalingInProgress = false
		a.lastScaleTime = time.Now()
		a.promCollector.RecordScalerReplicas(a.config.K8sDeployment, a.config.K8sNamespace, currentReplicas)
	}
}

func (a *AutoScaler) checkStability(currentReplicas int32, scaler k8sclient.ScalableResource) {
	a.stableCheckCount++

	waitCtx, waitCancel := context.WithTimeout(a.ctx, 2*time.Minute)
	defer waitCancel()
	if err := scaler.WaitForReady(waitCtx, a.config.K8sDeployment, a.config.K8sNamespace, 2*time.Minute); err != nil {
		a.logger.Warnf("Deployment not yet ready: %v", err)
		if a.stableCheckCount > 5 {
			a.logger.Warn("Too many stability check failures, continuing")
			a.stableCheckCount = 0
			if a.targetReplicas > currentReplicas {
				a.scalingState = StateScalingUp
			} else {
				a.scalingState = StateScalingDown
			}
		}
		return
	}

	currentLag, err := a.kafkaClient.GetTotalLag(a.config.ConsumerGroupID)
	if err != nil {
		a.logger.Warnf("Failed to get lag for stability check: %v", err)
	}

	lagChange := float64(currentLag - a.lagBeforeScale)
	if a.lagBeforeScale > 0 {
		lagChangePercent := lagChange / float64(a.lagBeforeScale)
		a.logger.Infof("Stability check #%d: replicas=%d ready, lag_before=%d, lag_current=%d, change=%.1f%%",
			a.stableCheckCount, currentReplicas, a.lagBeforeScale, currentLag, lagChangePercent*100)
	}

	a.stableCheckCount = 0
	if a.targetReplicas > currentReplicas {
		a.scalingState = StateScalingUp
	} else {
		a.scalingState = StateScalingDown
	}

	a.promCollector.RecordScalerReplicas(a.config.K8sDeployment, a.config.K8sNamespace, currentReplicas)
}

func (a *AutoScaler) triggerScaling(currentReplicas, desiredReplicas int32, currentLag, predictedLag int64, scaler k8sclient.ScalableResource) {
	a.mu.Lock()
	defer a.mu.Unlock()

	action := "scale_up"
	scalingState := StateScalingUp
	if desiredReplicas < currentReplicas {
		action = "scale_down"
		scalingState = StateScalingDown
	}

	reason := fmt.Sprintf("Current lag: %d, Threshold: %d", currentLag, a.config.ScaleUpThreshold)
	if predictedLag > 0 {
		reason = fmt.Sprintf("Current lag: %d, Predicted lag: %d, Threshold: %d", currentLag, predictedLag, a.config.ScaleUpThreshold)
	}

	a.logger.Infof("Triggering %s: %d -> %d (reason: %s, rolling: %v)",
		action, currentReplicas, desiredReplicas, reason, a.config.EnableRollingScale)
	a.promCollector.RecordScalerEvent(action, a.config.ConsumerGroupID)
	a.promCollector.RecordScalerAction(action, a.config.ConsumerGroupID, a.config.K8sDeployment)

	if a.config.Mode == ModeObservation {
		a.logger.Infof("Observation mode: would have scaled to %d replicas", desiredReplicas)
		return
	}

	if a.config.EnableRollingScale {
		a.targetReplicas = desiredReplicas
		a.scalingState = scalingState
		a.scalingInProgress = true
		a.lastRollingScaleTime = time.Time{}
		a.lagBeforeScale = currentLag
		a.stableCheckCount = 0
		a.logger.Infof("Rolling scaling initiated: current=%d, target=%d", currentReplicas, desiredReplicas)
		return
	}

	if err := scaler.Scale(a.ctx, a.config.K8sDeployment, a.config.K8sNamespace, desiredReplicas); err != nil {
		a.logger.Errorf("Failed to scale deployment: %v", err)
		return
	}

	waitCtx, waitCancel := context.WithTimeout(a.ctx, 5*time.Minute)
	defer waitCancel()

	if err := scaler.WaitForReady(waitCtx, a.config.K8sDeployment, a.config.K8sNamespace, 5*time.Minute); err != nil {
		a.logger.Warnf("Failed to wait for deployment ready: %v", err)
	}

	a.lastScaleTime = time.Now()
	a.promCollector.RecordScalerReplicas(a.config.K8sDeployment, a.config.K8sNamespace, desiredReplicas)
	a.logger.Infof("Successfully scaled to %d replicas", desiredReplicas)
}

func (a *AutoScaler) checkAndScaleDownAfterLagClear(totalLag int64, currentReplicas int32, desiredReplicas int32) int32 {
	a.mu.Lock()
	defer a.mu.Unlock()

	if totalLag <= a.config.ScaleDownThreshold {
		if a.lagClearedTime.IsZero() {
			a.lagClearedTime = time.Now()
			a.logger.Infof("Lag cleared below threshold, starting scale-down delay timer: %v", a.config.ScaleDownAfterLagDelay)
		} else if time.Since(a.lagClearedTime) >= a.config.ScaleDownAfterLagDelay {
			if !a.scaleDownState.InProgress && currentReplicas > a.config.MinReplicas {
				targetReplicas := currentReplicas - a.config.ScaleDownDecrement
				if targetReplicas < a.config.MinReplicas {
					targetReplicas = a.config.MinReplicas
				}

				a.scaleDownState = ScaleDownState{
					InProgress:     true,
					StartLag:       totalLag,
					StartTime:      time.Now(),
					TargetReplicas: targetReplicas,
					CurrentStep:    0,
				}

				a.logger.Infof("Scale-down after lag clear triggered: %d -> %d (lag below threshold for %v)",
					currentReplicas, targetReplicas, a.config.ScaleDownAfterLagDelay)

				return targetReplicas
			}
		}
	} else {
		if !a.lagClearedTime.IsZero() {
			a.logger.Infof("Lag increased again, resetting scale-down timer")
			a.lagClearedTime = time.Time{}
			a.scaleDownState.InProgress = false
		}
	}

	return desiredReplicas
}

func (a *AutoScaler) analyzeBacklogCauses(totalLag int64) {
	a.mu.Lock()
	defer a.mu.Unlock()

	lagData, err := a.kafkaClient.GetConsumerGroupLag(a.config.ConsumerGroupID)
	if err != nil {
		a.logger.Errorf("Failed to get lag data for analysis: %v", err)
		return
	}

	partitionInfos := make([]*SlowPartitionInfo, 0, len(lagData))
	var totalProcessingRate float64

	for _, lag := range lagData {
		processingRate := a.calculatePartitionProcessingRate(lag)
		avgLag := a.calculatePartitionAverageLag(lag.Topic, lag.Partition)

		anomalyScore := 0.0
		if avgLag > 0 {
			anomalyScore = float64(lag.Lag) / avgLag
		}

		isSlow := false
		if a.config.SlowPartitionThreshold > 0 {
			expectedLag := float64(a.config.MessageProcessingLatency.Milliseconds()) * processingRate
			if float64(lag.Lag) > expectedLag*2 || anomalyScore > 3.0 {
				isSlow = true
			}
		}

		partitionInfos = append(partitionInfos, &SlowPartitionInfo{
			Topic:          lag.Topic,
			Partition:      lag.Partition,
			Lag:            lag.Lag,
			AvgLag:         avgLag,
			ConsumerID:     lag.ConsumerID,
			ProcessingRate: processingRate,
			IsSlow:         isSlow,
			AnomalyScore:   anomalyScore,
		})

		totalProcessingRate += processingRate
	}

	sort.Slice(partitionInfos, func(i, j int) bool {
		return partitionInfos[i].Lag > partitionInfos[j].Lag
	})

	slowPartitions := make([]*SlowPartitionInfo, 0)
	for _, p := range partitionInfos {
		if p.IsSlow {
			slowPartitions = append(slowPartitions, p)
		}
	}

	topLagPartitions := partitionInfos
	if len(topLagPartitions) > 5 {
		topLagPartitions = topLagPartitions[:5]
	}

	avgProcessingRate := totalProcessingRate / float64(len(partitionInfos))

	rootCause := a.determineRootCause(slowPartitions, totalLag, avgProcessingRate)

	severity := "low"
	if totalLag > a.config.ScaleUpThreshold*2 {
		severity = "critical"
	} else if totalLag > a.config.ScaleUpThreshold {
		severity = "high"
	} else if totalLag > a.config.ScaleDownThreshold {
		severity = "medium"
	}

	analysis := &BacklogAnalysis{
		Timestamp:            time.Now(),
		TotalLag:             totalLag,
		SlowPartitions:       slowPartitions,
		TopLagPartitions:     topLagPartitions,
		AverageProcessingRate: avgProcessingRate,
		ArrivalRate:          avgProcessingRate + (avgProcessingRate * 0.1),
		RootCause:            rootCause,
		Severity:             severity,
	}

	a.lastAnalysis = analysis

	if len(slowPartitions) > 0 {
		a.logger.Warnf("Backlog analysis for %s: severity=%s, root_cause=%s, slow_partitions=%d",
			a.config.ConsumerGroupID, severity, rootCause, len(slowPartitions))

		for i, p := range slowPartitions {
			if i < 3 {
				a.logger.Warnf("  Slow partition #%d: %s-%d, lag=%d, anomaly_score=%.2f, consumer=%s",
					i+1, p.Topic, p.Partition, p.Lag, p.AnomalyScore, p.ConsumerID)
			}
		}
	}
}

func (a *AutoScaler) calculatePartitionProcessingRate(lag *kafkaclient.ConsumerGroupLag) float64 {
	if lag.EndOffset == 0 || lag.CurrentOffset == -1 {
		return 0
	}

	messagesProcessed := lag.EndOffset - lag.CurrentOffset
	if messagesProcessed < 0 {
		messagesProcessed = 0
	}

	return float64(messagesProcessed) / 30.0
}

func (a *AutoScaler) calculatePartitionAverageLag(topic string, partition int32) float64 {
	history := a.promCollector.GetLagHistory(a.config.ConsumerGroupID)
	if len(history) == 0 {
		return 0
	}

	var sum int64
	for _, record := range history {
		sum += record.Lag
	}

	return float64(sum) / float64(len(history))
}

func (a *AutoScaler) determineRootCause(slowPartitions []*SlowPartitionInfo, totalLag int64, avgProcessingRate float64) string {
	if len(slowPartitions) == 0 {
		if totalLag > a.config.ScaleUpThreshold {
			return "insufficient_consumers"
		}
		return "normal"
	}

	allSameConsumer := true
	consumerID := ""
	for _, p := range slowPartitions {
		if consumerID == "" {
			consumerID = p.ConsumerID
		} else if p.ConsumerID != consumerID {
			allSameConsumer = false
			break
		}
	}

	if allSameConsumer && consumerID != "" {
		return "stuck_consumer"
	}

	highAnomalyCount := 0
	for _, p := range slowPartitions {
		if p.AnomalyScore > 5.0 {
			highAnomalyCount++
		}
	}

	if highAnomalyCount > 0 {
		return "slow_message_types"
	}

	if avgProcessingRate < 1.0 {
		return "processing_blocked"
	}

	return "high_volume_traffic"
}

func (a *AutoScaler) checkAndPerformSelfHealing(totalLag int64, currentReplicas int32, memberCount int) {
	a.mu.Lock()
	defer a.mu.Unlock()

	if !a.lastSelfHealingTime.IsZero() && time.Since(a.lastSelfHealingTime) < a.config.SelfHealingCooldown {
		return
	}

	if a.lastAnalysis != nil && a.lastAnalysis.RootCause == "stuck_consumer" {
		a.consecutiveErrorCount++

		if a.consecutiveErrorCount >= a.config.SelfHealingThreshold {
			a.logger.Warnf("Self-healing triggered: stuck consumer detected for %d consecutive checks",
				a.consecutiveErrorCount)

			if err := a.performSelfHealing("restart_stuck_consumer", "Stuck consumer detected"); err != nil {
				a.logger.Errorf("Self-healing failed: %v", err)
			} else {
				a.consecutiveErrorCount = 0
				a.lastSelfHealingTime = time.Now()
			}
		}
		return
	}

	if totalLag > a.config.ScaleUpThreshold*3 && memberCount < int(currentReplicas) {
		a.consecutiveErrorCount++

		if a.consecutiveErrorCount >= a.config.SelfHealingThreshold {
			a.logger.Warnf("Self-healing triggered: consumer group membership inconsistency (members=%d, replicas=%d)",
				memberCount, currentReplicas)

			if err := a.performSelfHealing("restart_all", "Consumer group membership inconsistency"); err != nil {
				a.logger.Errorf("Self-healing failed: %v", err)
			} else {
				a.consecutiveErrorCount = 0
				a.lastSelfHealingTime = time.Now()
			}
		}
		return
	}

	a.consecutiveErrorCount = 0
}

func (a *AutoScaler) performSelfHealing(actionType, reason string) error {
	a.logger.Infof("Performing self-healing action: %s, reason: %s", actionType, reason)

	action := &SelfHealingAction{
		Timestamp:  time.Now(),
		ActionType: actionType,
		Reason:     reason,
		Success:    false,
	}

	switch actionType {
	case "restart_stuck_consumer":
		if a.lastAnalysis != nil && len(a.lastAnalysis.SlowPartitions) > 0 {
			consumerID := a.lastAnalysis.SlowPartitions[0].ConsumerID
			action.PodName = consumerID
			a.logger.Infof("Would restart stuck consumer pod: %s", consumerID)
		}

	case "restart_all":
		action.PodName = "all"
		if a.config.Mode == ModeAuto {
			if err := a.k8sClient.RestartDeployment(a.ctx, a.config.K8sDeployment, a.config.K8sNamespace); err != nil {
				action.Success = false
				a.healingActions = append(a.healingActions, action)
				return fmt.Errorf("failed to restart deployment: %w", err)
			}
			action.Success = true
			a.logger.Infof("Successfully restarted deployment %s/%s", a.config.K8sNamespace, a.config.K8sDeployment)
		} else {
			a.logger.Infof("Observation mode: would restart deployment %s/%s", a.config.K8sNamespace, a.config.K8sDeployment)
			action.Success = true
		}

	default:
		return fmt.Errorf("unknown self-healing action: %s", actionType)
	}

	if len(a.healingActions) > 100 {
		a.healingActions = a.healingActions[1:]
	}
	a.healingActions = append(a.healingActions, action)

	a.promCollector.RecordScalerEvent("self_healing_"+actionType, a.config.ConsumerGroupID)

	return nil
}

func (a *AutoScaler) checkAndTriggerRebalance(totalLag int64) {
	topicPartitions, err := a.kafkaClient.GetConsumerGroupLag(a.config.ConsumerGroupID)
	if err != nil {
		a.logger.Errorf("Failed to get consumer group lag details: %v", err)
		return
	}

	partitionLagMap := make(map[string]map[int32]int64)
	for _, tp := range topicPartitions {
		if _, ok := partitionLagMap[tp.Topic]; !ok {
			partitionLagMap[tp.Topic] = make(map[int32]int64)
		}
		partitionLagMap[tp.Topic][tp.Partition] = tp.Lag
	}

	for topic, partitionLags := range partitionLagMap {
		if a.isRebalanceNeeded(partitionLags) {
			a.logger.Infof("Partition rebalance needed for topic %s due to uneven lag distribution", topic)
		}
	}
}

func (a *AutoScaler) isRebalanceNeeded(partitionLags map[int32]int64) bool {
	if len(partitionLags) < 2 {
		return false
	}

	var total int64
	var maxLag int64
	var minLag int64 = -1

	for _, lag := range partitionLags {
		total += lag
		if lag > maxLag {
			maxLag = lag
		}
		if minLag == -1 || lag < minLag {
			minLag = lag
		}
	}

	avgLag := float64(total) / float64(len(partitionLags))

	if avgLag > 0 && maxLag > int64(2*avgLag) {
		return true
	}

	return false
}

func (a *AutoScaler) GetStatus() map[string]interface{} {
	a.mu.RLock()
	defer a.mu.RUnlock()

	status := map[string]interface{}{
		"consumer_group":              a.config.ConsumerGroupID,
		"mode":                        a.config.Mode,
		"deployment":                  a.config.K8sDeployment,
		"namespace":                   a.config.K8sNamespace,
		"min_replicas":                a.config.MinReplicas,
		"max_replicas":                a.config.MaxReplicas,
		"scale_up_threshold":          a.config.ScaleUpThreshold,
		"scale_down_threshold":        a.config.ScaleDownThreshold,
		"cooldown_period":             a.config.CooldownPeriod.String(),
		"last_scale_time":             a.lastScaleTime,
		"scaling_in_progress":         a.scalingInProgress,
		"use_prediction":              a.config.UsePrediction,
		"enable_rolling_scale":        a.config.EnableRollingScale,
		"scaling_state":               a.scalingState,
		"target_replicas":             a.targetReplicas,
		"processing_latency":          a.config.MessageProcessingLatency.String(),
		"enable_scale_down_after_lag": a.config.EnableScaleDownAfterLagClear,
		"enable_self_healing":         a.config.EnableSelfHealing,
		"enable_slow_detection":       a.config.EnableSlowPartitionDetection,
		"consecutive_error_count":     a.consecutiveErrorCount,
		"last_self_healing_time":      a.lastSelfHealingTime,
		"healing_actions_count":       len(a.healingActions),
	}

	if a.lastAnalysis != nil {
		status["last_analysis"] = map[string]interface{}{
			"timestamp":   a.lastAnalysis.Timestamp,
			"total_lag":   a.lastAnalysis.TotalLag,
			"root_cause":  a.lastAnalysis.RootCause,
			"severity":    a.lastAnalysis.Severity,
			"slow_partitions": len(a.lastAnalysis.SlowPartitions),
		}
	}

	return status
}

func (a *AutoScaler) ForceScale(ctx context.Context, replicas int32) error {
	a.mu.Lock()
	defer a.mu.Unlock()

	if replicas < a.config.MinReplicas {
		return fmt.Errorf("replicas %d is below minimum %d", replicas, a.config.MinReplicas)
	}
	if replicas > a.config.MaxReplicas {
		return fmt.Errorf("replicas %d is above maximum %d", replicas, a.config.MaxReplicas)
	}

	scaler, err := a.k8sClient.GetScaler(a.config.K8sResourceType)
	if err != nil {
		return err
	}

	currentReplicas, err := scaler.GetReplicas(ctx, a.config.K8sDeployment, a.config.K8sNamespace)
	if err != nil {
		return err
	}

	if currentReplicas == replicas {
		return nil
	}

	action := "scale_up"
	if replicas < currentReplicas {
		action = "scale_down"
	}

	a.promCollector.RecordScalerEvent("manual_"+action, a.config.ConsumerGroupID)
	a.promCollector.RecordScalerAction("manual_"+action, a.config.ConsumerGroupID, a.config.K8sDeployment)

	return scaler.Scale(ctx, a.config.K8sDeployment, a.config.K8sNamespace, replicas)
}

func (a *AutoScaler) UpdateConfig(newConfig *ScalerConfig) {
	a.mu.Lock()
	defer a.mu.Unlock()

	if newConfig.Mode != "" {
		a.config.Mode = newConfig.Mode
	}
	if newConfig.MinReplicas > 0 {
		a.config.MinReplicas = newConfig.MinReplicas
	}
	if newConfig.MaxReplicas > 0 {
		a.config.MaxReplicas = newConfig.MaxReplicas
	}
	if newConfig.ScaleUpThreshold > 0 {
		a.config.ScaleUpThreshold = newConfig.ScaleUpThreshold
	}
	if newConfig.ScaleDownThreshold >= 0 {
		a.config.ScaleDownThreshold = newConfig.ScaleDownThreshold
	}

	a.logger.Infof("Config updated: mode=%s, min=%d, max=%d, scale_up=%d, scale_down=%d",
		a.config.Mode, a.config.MinReplicas, a.config.MaxReplicas,
		a.config.ScaleUpThreshold, a.config.ScaleDownThreshold)
}
