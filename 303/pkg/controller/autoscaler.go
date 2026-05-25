package controller

import (
	"context"
	"fmt"
	"sync"
	"time"

	"autoscaler/internal/types"
	"autoscaler/pkg/cloud"
	"autoscaler/pkg/history"
	"autoscaler/pkg/monitor"
	"autoscaler/pkg/predict"
	"autoscaler/pkg/strategy"
	"github.com/google/uuid"
	"go.uber.org/zap"
)

type AutoscalerConfig struct {
	GroupID               string
	ScalingType           types.ScalingType
	DeploymentStrategy    types.DeploymentStrategy
	Interval              time.Duration
	InstanceIDs           []string
	MonitorMetrics        []types.MetricType
	EnablePrediction      bool
	EnableErrorCorrection bool
	DryRun                bool
	DryRunMode            types.DryRunMode
	ServiceName           string
	ServiceLevel          types.ServiceLevel
	BlueGreenTimeout      time.Duration
	ErrorFeedbackConfig   types.ErrorFeedbackConfig
	CostConfig            *types.CostConfig
	EnableCostOptimization bool
	HistoryEnabled        bool
	HistoryStoragePath    string
}

type Autoscaler struct {
	config         AutoscalerConfig
	monitor        *monitor.PrometheusClient
	predictor      *predict.Predictor
	strategy       *strategy.StrategyEngine
	cloud          cloud.CloudProvider
	history        *history.HistoryRecorder
	logger         *zap.Logger
	stopCh         chan struct{}
	costStopCh     chan struct{}
	running        bool
	mu             sync.Mutex
	lastAction     *types.ScalingAction
	lastDryRun     *types.DryRunResult
	actionHistory  []*types.ScalingAction
	deployment     *types.BlueGreenDeployment
	previousPredicted map[types.MetricType]float64
}

func NewAutoscaler(
	config AutoscalerConfig,
	monitorClient *monitor.PrometheusClient,
	predictor *predict.Predictor,
	strategyEngine *strategy.StrategyEngine,
	cloudProvider cloud.CloudProvider,
	logger *zap.Logger,
) *Autoscaler {
	if config.Interval == 0 {
		config.Interval = 5 * time.Minute
	}
	if config.DeploymentStrategy == "" {
		config.DeploymentStrategy = types.DeploymentBlueGreen
	}
	if config.ServiceLevel == "" {
		config.ServiceLevel = types.ServiceLevelMedium
	}
	if config.BlueGreenTimeout == 0 {
		config.BlueGreenTimeout = 10 * time.Minute
	}
	if config.DryRunMode == "" {
		config.DryRunMode = types.DryRunOff
	}

	histRecorder := history.NewHistoryRecorder(history.HistoryConfig{
		Enabled:     config.HistoryEnabled,
		StoragePath: config.HistoryStoragePath,
		MaxRecords:  10000,
	}, logger)

	return &Autoscaler{
		config:            config,
		monitor:           monitorClient,
		predictor:         predictor,
		strategy:          strategyEngine,
		cloud:             cloudProvider,
		history:           histRecorder,
		logger:            logger,
		stopCh:            make(chan struct{}),
		costStopCh:        make(chan struct{}),
		actionHistory:     make([]*types.ScalingAction, 0, 100),
		previousPredicted: make(map[types.MetricType]float64),
	}
}

func (a *Autoscaler) Start(ctx context.Context) error {
	a.mu.Lock()
	if a.running {
		a.mu.Unlock()
		return nil
	}
	a.running = true
	a.mu.Unlock()

	a.logger.Info("starting autoscaler",
		zap.String("group_id", a.config.GroupID),
		zap.String("scaling_type", string(a.config.ScalingType)),
		zap.String("deployment_strategy", string(a.config.DeploymentStrategy)),
		zap.String("service", a.config.ServiceName),
		zap.String("service_level", string(a.config.ServiceLevel)),
		zap.Duration("interval", a.config.Interval),
		zap.Bool("dry_run", a.config.DryRun),
		zap.Bool("enable_prediction", a.config.EnablePrediction),
		zap.Bool("enable_error_correction", a.config.EnableErrorCorrection),
	)

	go a.run(ctx)

	if a.config.EnableCostOptimization && a.config.CostConfig != nil {
		go a.runCostOptimization(ctx)
	}

	return nil
}

func (a *Autoscaler) Stop() {
	a.mu.Lock()
	defer a.mu.Unlock()

	if !a.running {
		return
	}

	a.running = false
	close(a.stopCh)
	close(a.costStopCh)
	if a.history != nil {
		a.history.Close()
	}
	a.logger.Info("autoscaler stopped")
}

func (a *Autoscaler) run(ctx context.Context) {
	ticker := time.NewTicker(a.config.Interval)
	defer ticker.Stop()

	if err := a.DoScaling(ctx); err != nil {
		a.logger.Error("initial scaling failed", zap.Error(err))
	}

	for {
		select {
		case <-ctx.Done():
			a.logger.Info("context cancelled, stopping autoscaler")
			return
		case <-a.stopCh:
			return
		case <-ticker.C:
			if err := a.DoScaling(ctx); err != nil {
				a.logger.Error("scaling cycle failed", zap.Error(err))
			}
		}
	}
}

func (a *Autoscaler) DoScaling(ctx context.Context) error {
	a.logger.Debug("starting scaling cycle")

	group, err := a.cloud.GetInstanceGroup(ctx, a.config.GroupID)
	if err != nil {
		return fmt.Errorf("failed to get instance group: %w", err)
	}

	a.logger.Info("current instance group state",
		zap.Int("desired", group.Desired),
		zap.Int("min", group.MinSize),
		zap.Int("max", group.MaxSize),
		zap.Int("instances", len(group.Instances)),
		zap.Int("reserved", group.ReservedCount),
		zap.Int("ondemand", group.OnDemandCount),
		zap.Int("spot", group.SpotCount),
		zap.Float64("hourly_cost", group.TotalHourlyCost),
		zap.String("version", group.Version),
	)

	metrics, err := a.collectMetrics(ctx, group)
	if err != nil {
		return fmt.Errorf("failed to collect metrics: %w", err)
	}

	for _, metric := range metrics {
		a.logger.Info("metric collected",
			zap.String("type", string(metric.MetricType)),
			zap.Float64("current", metric.Current),
			zap.Int("data_points", len(metric.Values)),
		)
	}

	if a.config.EnableErrorCorrection {
		a.recordPredictionErrors(metrics)
		a.predictor.UpdateCorrections()
	}

	if a.config.EnablePrediction {
		for _, metric := range metrics {
			prediction, err := a.predictor.Predict(metric)
			if err != nil {
				a.logger.Warn("prediction failed",
					zap.String("metric", string(metric.MetricType)),
					zap.Error(err),
				)
				continue
			}
			metric.Predicted = prediction
			a.previousPredicted[metric.MetricType] = prediction

			a.logger.Info("prediction result",
				zap.String("metric", string(metric.MetricType)),
				zap.Float64("current", metric.Current),
				zap.Float64("predicted", prediction),
				zap.Float64("corrected", metric.Corrected),
			)
		}
	}

	action, err := a.strategy.Evaluate(metrics, group, a.config.ScalingType, a.config.ServiceName, a.config.ServiceLevel)
	if err != nil {
		return fmt.Errorf("strategy evaluation failed: %w", err)
	}

	a.lastAction = action
	a.recordAction(action)

	metricSnapshot := make(map[types.MetricType]types.MetricData)
	for _, m := range metrics {
		metricSnapshot[m.MetricType] = *m
	}

	historyID := ""
	if a.config.HistoryEnabled && a.history != nil {
		historyID = uuid.New().String()
	}

	a.logger.Info("scaling decision",
		zap.String("type", string(action.Type)),
		zap.String("direction", string(action.Direction)),
		zap.Int("step", action.Step),
		zap.String("reason", action.Reason),
		zap.String("service", action.ServiceName),
		zap.String("level", string(action.ServiceLevel)),
		zap.String("charge_type", string(action.ChargeType)),
		zap.Float64("cost_estimate", action.CostEstimate),
	)

	var result := "success"
	var execErr error
	startTime := time.Now()

	if action.Direction == types.NoScale {
		a.logger.Info("no scaling needed")
		result = "no_action"
	} else if a.config.DryRun || a.config.DryRunMode != types.DryRunOff {
		dryRunResult, err := a.executeDryRun(ctx, action, group)
		if err != nil {
			a.logger.Error("dry run failed", zap.Error(err))
			result = "dry_run_failed"
			execErr = err
		} else {
			a.lastDryRun = dryRunResult
			a.logger.Info("dry run completed",
				zap.String("mode", string(dryRunResult.Mode)),
				zap.Bool("validation_pass", dryRunResult.ValidationPass),
				zap.String("risk_level", dryRunResult.RiskLevel),
			)
			result = "dry_run"
		}
	} else {
		if execErr = a.executeAction(ctx, action)
		if execErr != nil {
			result = "failed"
			a.logger.Error("scaling execution failed", zap.Error(execErr))
		} else {
			a.strategy.RecordScaling(action)
		}
	}

	duration := time.Since(startTime)

	if a.config.HistoryEnabled && a.history != nil {
		record := &types.ScalingHistoryRecord{
			ID:            historyID,
			Timestamp:     time.Now(),
			ServiceName:   a.config.ServiceName,
			ServiceLevel:  a.config.ServiceLevel,
			Action:        *action,
			MetricSnapshot: metricSnapshot,
			Result:        result,
			Error: func() string {
				if execErr != nil {
					return execErr.Error()
				}
				return ""
			}(),
			Duration:      duration,
			CostChange:    action.CostEstimate,
			InstanceCount: group.Desired,
		}
		if len(group.Instances) > 0 {
			record.AvgFlavor = group.Instances[0].Flavor
		}

		if err := a.history.Record(record); err != nil {
			a.logger.Warn("failed to record scaling history", zap.Error(err))
		}
	}

	return execErr
}

func (a *Autoscaler) recordPredictionErrors(metrics []*types.MetricData) {
	for _, metric := range metrics {
		prevPredicted, exists := a.previousPredicted[metric.MetricType]
		if !exists {
			continue
		}

		error := metric.Current - prevPredicted
		errorRatio := 0.0
		if metric.Current != 0 {
			errorRatio = error / metric.Current * 100
		}

		a.predictor.RecordError(metric.MetricType, prevPredicted, metric.Current)

		a.logger.Debug("prediction error recorded",
			zap.String("metric", string(metric.MetricType)),
			zap.Float64("predicted", prevPredicted),
			zap.Float64("actual", metric.Current),
			zap.Float64("error", error),
			zap.Float64("error_ratio", errorRatio),
		)
	}
}

func (a *Autoscaler) collectMetrics(ctx context.Context, group *types.InstanceGroup) ([]*types.MetricData, error) {
	instanceIDs := a.config.InstanceIDs
	if len(instanceIDs) == 0 && len(group.Instances) > 0 {
		instanceIDs = make([]string, len(group.Instances))
		for i, inst := range group.Instances {
			instanceIDs[i] = inst.ID
		}
	}

	metrics := make([]*types.MetricData, 0, len(a.config.MonitorMetrics))

	for _, metricType := range a.config.MonitorMetrics {
		var metric *types.MetricData
		var err error

		if a.config.ScalingType == types.HorizontalScaling && len(instanceIDs) > 1 {
			metric, err = a.monitor.GetAggregatedMetric(ctx, instanceIDs, metricType)
		} else {
			targetID := "aggregated"
			if len(instanceIDs) > 0 {
				targetID = instanceIDs[0]
			}
			switch metricType {
			case types.MetricCPU:
				metric, err = a.monitor.GetCPUUtilization(ctx, targetID)
			case types.MetricMemory:
				metric, err = a.monitor.GetMemoryUtilization(ctx, targetID)
			case types.MetricNetwork:
				metric, err = a.monitor.GetNetworkThroughput(ctx, targetID)
			default:
				return nil, fmt.Errorf("unsupported metric type: %s", metricType)
			}
		}

		if err != nil {
			a.logger.Warn("failed to collect metric",
				zap.String("type", string(metricType)),
				zap.Error(err),
			)
			continue
		}

		metrics = append(metrics, metric)
	}

	return metrics, nil
}

func (a *Autoscaler) executeAction(ctx context.Context, action *types.ScalingAction) error {
	switch action.Type {
	case types.HorizontalScaling:
		return a.executeHorizontalScaling(ctx, action)
	case types.VerticalScaling:
		return a.executeVerticalScaling(ctx, action)
	default:
		return fmt.Errorf("unsupported scaling type: %s", action.Type)
	}
}

func (a *Autoscaler) executeHorizontalScaling(ctx context.Context, action *types.ScalingAction) error {
	switch action.Direction {
	case types.ScaleUp:
		a.logger.Info("executing horizontal scale up",
			zap.String("group_id", action.InstanceID),
			zap.Int("step", action.Step),
		)
		return a.cloud.ScaleUp(ctx, action)
	case types.ScaleDown:
		a.logger.Info("executing horizontal scale down",
			zap.String("group_id", action.InstanceID),
			zap.Int("step", action.Step),
		)
		return a.cloud.ScaleDown(ctx, action)
	default:
		return fmt.Errorf("invalid scaling direction: %s", action.Direction)
	}
}

func (a *Autoscaler) executeVerticalScaling(ctx context.Context, action *types.ScalingAction) error {
	group, err := a.cloud.GetInstanceGroup(ctx, a.config.GroupID)
	if err != nil {
		return fmt.Errorf("failed to get instance group: %w", err)
	}
	if len(group.Instances) == 0 {
		return fmt.Errorf("no instances in group")
	}

	currentFlavor := group.Instances[0].Flavor
	newSize, err := a.cloud.GetNextFlavor(ctx, currentFlavor, action.Direction)
	if err != nil {
		return fmt.Errorf("failed to get next flavor: %w", err)
	}

	a.logger.Info("executing vertical scaling",
		zap.String("group_id", a.config.GroupID),
		zap.String("old_flavor", currentFlavor),
		zap.String("new_flavor", newSize),
		zap.String("deployment_strategy", string(a.config.DeploymentStrategy)),
	)

	switch a.config.DeploymentStrategy {
	case types.DeploymentBlueGreen:
		return a.executeBlueGreenScaling(ctx, group, newSize, action.Direction)
	case types.DeploymentRolling:
		return a.executeRollingScaling(ctx, group, newSize, action)
	default:
		return a.executeInPlaceScaling(ctx, group.Instances[0].ID, newSize)
	}
}

func (a *Autoscaler) executeBlueGreenScaling(ctx context.Context, group *types.InstanceGroup, newFlavor string, direction types.ScalingDirection) error {
	a.logger.Info("starting blue-green deployment",
		zap.String("group_id", group.ID),
		zap.String("new_flavor", newFlavor),
		zap.Int("instance_count", len(group.Instances)),
	)

	deployment, err := a.cloud.BlueGreenPrepare(ctx, group.ID, newFlavor, len(group.Instances))
	if err != nil {
		return fmt.Errorf("failed to prepare blue-green deployment: %w", err)
	}

	a.deployment = deployment

	a.logger.Info("blue-green deployment prepared, waiting for green instances to be ready",
		zap.String("deployment_id", deployment.ID),
	)

	err = a.cloud.BlueGreenWaitReady(ctx, deployment, a.config.BlueGreenTimeout)
	if err != nil {
		a.logger.Error("green instances failed to become ready, rolling back",
			zap.String("deployment_id", deployment.ID),
			zap.Error(err),
		)
		if rollbackErr := a.cloud.BlueGreenRollback(ctx, deployment); rollbackErr != nil {
			a.logger.Error("rollback failed", zap.Error(rollbackErr))
		}
		return fmt.Errorf("blue-green deployment failed: %w", err)
	}

	a.logger.Info("green instances ready, switching traffic",
		zap.String("deployment_id", deployment.ID),
	)

	err = a.cloud.BlueGreenSwitchTraffic(ctx, deployment, 100)
	if err != nil {
		a.logger.Error("traffic switch failed, rolling back",
			zap.String("deployment_id", deployment.ID),
			zap.Error(err),
		)
		if rollbackErr := a.cloud.BlueGreenRollback(ctx, deployment); rollbackErr != nil {
			a.logger.Error("rollback failed", zap.Error(rollbackErr))
		}
		return fmt.Errorf("traffic switch failed: %w", err)
	}

	a.logger.Info("traffic switched, completing deployment",
		zap.String("deployment_id", deployment.ID),
	)

	err = a.cloud.BlueGreenComplete(ctx, deployment)
	if err != nil {
		return fmt.Errorf("failed to complete blue-green deployment: %w", err)
	}

	a.logger.Info("blue-green deployment completed successfully",
		zap.String("deployment_id", deployment.ID),
		zap.String("new_flavor", newFlavor),
	)

	return nil
}

func (a *Autoscaler) executeRollingScaling(ctx context.Context, group *types.InstanceGroup, newFlavor string, action *types.ScalingAction) error {
	a.logger.Info("starting rolling update",
		zap.String("group_id", group.ID),
		zap.String("new_flavor", newFlavor),
	)

	for _, inst := range group.Instances {
		a.logger.Info("updating instance",
			zap.String("instance_id", inst.ID),
			zap.String("old_flavor", inst.Flavor),
			zap.String("new_flavor", newFlavor),
		)

		err := a.cloud.ScaleVertical(ctx, &types.ScalingAction{
			Type:       action.Type,
			Direction:  action.Direction,
			InstanceID: inst.ID,
			Step:       action.Step,
			Reason:     action.Reason,
			Timestamp:  action.Timestamp,
		}, newFlavor)

		if err != nil {
			a.logger.Error("failed to update instance, continuing with next",
				zap.String("instance_id", inst.ID),
				zap.Error(err),
			)
			continue
		}

		time.Sleep(30 * time.Second)
	}

	a.logger.Info("rolling update completed",
		zap.String("group_id", group.ID),
		zap.String("new_flavor", newFlavor),
	)

	return nil
}

func (a *Autoscaler) executeInPlaceScaling(ctx context.Context, instanceID string, newFlavor string) error {
	a.logger.Info("executing in-place vertical scaling",
		zap.String("instance_id", instanceID),
		zap.String("new_flavor", newFlavor),
	)

	return a.cloud.ScaleVertical(ctx, &types.ScalingAction{
		Type:       types.VerticalScaling,
		Direction:  types.ScaleUp,
		InstanceID: instanceID,
		Step:       1,
		Reason:     "in-place vertical scaling",
		Timestamp:  time.Now(),
	}, newFlavor)
}

func (a *Autoscaler) recordAction(action *types.ScalingAction) {
	a.mu.Lock()
	defer a.mu.Unlock()

	a.actionHistory = append(a.actionHistory, action)
	if len(a.actionHistory) > 100 {
		a.actionHistory = a.actionHistory[1:]
	}
}

func (a *Autoscaler) GetLastAction() *types.ScalingAction {
	a.mu.Lock()
	defer a.mu.Unlock()
	return a.lastAction
}

func (a *Autoscaler) GetActionHistory() []*types.ScalingAction {
	a.mu.Lock()
	defer a.mu.Unlock()
	history := make([]*types.ScalingAction, len(a.actionHistory))
	copy(history, a.actionHistory)
	return history
}

func (a *Autoscaler) IsRunning() bool {
	a.mu.Lock()
	defer a.mu.Unlock()
	return a.running
}

func (a *Autoscaler) GetConfig() AutoscalerConfig {
	return a.config
}

func (a *Autoscaler) GetDeployment() *types.BlueGreenDeployment {
	a.mu.Lock()
	defer a.mu.Unlock()
	return a.deployment
}

func (a *Autoscaler) executeDryRun(ctx context.Context, action *types.ScalingAction, group *types.InstanceGroup) (*types.DryRunResult, error) {
	mode := a.config.DryRunMode
	if mode == types.DryRunOff {
		mode = types.DryRunSimulate
	}

	result := &types.DryRunResult{
		Mode:           mode,
		Timestamp:      time.Now(),
		OriginalAction: *action,
		Recommendations: make([]string, 0),
	}

	riskLevel := "low"
	validationPass := true
	expectedImpact := ""

	if action.Type == types.HorizontalScaling {
		if action.Direction == types.ScaleUp {
			newCount := group.Desired + action.Step
			if newCount > group.MaxSize {
				riskLevel = "high"
				validationPass = false
				result.Recommendations = append(result.Recommendations,
					fmt.Sprintf("Scale up would exceed max instances: %d > %d", newCount, group.MaxSize))
			}

			price := 0.10
			for _, inst := range group.Instances {
				if inst.Flavor == "ecs.large" {
					price = 0.20
				} else if inst.Flavor == "ecs.xlarge" {
					price = 0.40
				}
			}
			monthlyCost := price * float64(action.Step) * 24 * 30
			expectedImpact = fmt.Sprintf("Adding %d instances will increase monthly cost by ~$%.2f",
				action.Step, monthlyCost)

			if newCount > group.MaxSize*0.9 {
				riskLevel = "medium"
				result.Recommendations = append(result.Recommendations,
					"Approaching max instance limit, consider increasing max size")
			}
		} else if action.Direction == types.ScaleDown {
			newCount := group.Desired - action.Step
			if newCount < group.MinSize {
				riskLevel = "high"
				validationPass = false
				result.Recommendations = append(result.Recommendations,
					fmt.Sprintf("Scale down would go below min instances: %d < %d", newCount, group.MinSize))
			}

			if newCount <= group.MinSize+1 {
				riskLevel = "medium"
				result.Recommendations = append(result.Recommendations,
					"Approaching min instance limit, be cautious about further scale downs")
			}

			price := 0.10
			for _, inst := range group.Instances {
				if inst.Flavor == "ecs.large" {
					price = 0.20
				} else if inst.Flavor == "ecs.xlarge" {
					price = 0.40
				}
			}
			monthlySavings := price * float64(action.Step) * 24 * 30
			expectedImpact = fmt.Sprintf("Removing %d instances will reduce monthly cost by ~$%.2f",
				action.Step, monthlySavings)
		}
	} else if action.Type == types.VerticalScaling {
		currentFlavor := group.Instances[0].Flavor
		newFlavor, _ := a.cloud.GetNextFlavor(ctx, currentFlavor, action.Direction)
		expectedImpact = fmt.Sprintf("Vertical %s from %s to %s",
			action.Direction, currentFlavor, newFlavor)

		if action.Direction == types.ScaleUp {
			riskLevel = "medium"
			result.Recommendations = append(result.Recommendations,
				"Vertical scaling requires instance restart, expect brief downtime")
		}

		if a.config.DeploymentStrategy == types.DeploymentBlueGreen {
			result.Recommendations = append(result.Recommendations,
				"Blue-green deployment will be used, no downtime expected")
			riskLevel = "low"
		}
	}

	if mode == types.DryRunValidate {
		if group.ReservedCount+group.OnDemandCount+group.SpotCount != len(group.Instances) {
			validationPass = false
			result.Recommendations = append(result.Recommendations,
				"Instance count mismatch detected")
		}
	}

	if mode == types.DryRunReport {
		result.Recommendations = append(result.Recommendations,
			"Review predicted metrics and error correction before applying")
		result.Recommendations = append(result.Recommendations,
			fmt.Sprintf("Service level %s has cooldown period multiplier applied", a.config.ServiceLevel))
	}

	result.SimulatedResult = fmt.Sprintf("Would %s %d instances", action.Direction, action.Step)
	result.ExpectedImpact = expectedImpact
	result.RiskLevel = riskLevel
	result.ValidationPass = validationPass

	a.logger.Info("dry run analysis complete",
		zap.String("mode", string(mode)),
		zap.String("risk", riskLevel),
		zap.Bool("valid", validationPass),
		zap.String("impact", expectedImpact),
	)

	return result, nil
}

func (a *Autoscaler) runCostOptimization(ctx context.Context) {
	interval := a.config.CostConfig.OptimizationInterval
	if interval == 0 {
		interval = 1 * time.Hour
	}

	ticker := time.NewTicker(interval)
	defer ticker.Stop()

	a.logger.Info("starting cost optimization routine",
		zap.Duration("interval", interval),
		zap.Float64("reserved_ratio", a.config.CostConfig.ReservedInstanceRatio),
	)

	for {
		select {
		case <-ctx.Done():
			return
		case <-a.costStopCh:
			return
		case <-ticker.C:
			if err := a.doCostOptimization(ctx); err != nil {
				a.logger.Error("cost optimization failed", zap.Error(err))
			}
		}
	}
}

func (a *Autoscaler) doCostOptimization(ctx context.Context) error {
	a.logger.Debug("starting cost optimization cycle")

	group, err := a.cloud.GetInstanceGroup(ctx, a.config.GroupID)
	if err != nil {
		return fmt.Errorf("failed to get instance group: %w", err)
	}

	reservedRatio := float64(group.ReservedCount) / float64(len(group.Instances))
	a.logger.Info("current cost state",
		zap.Int("total", len(group.Instances)),
		zap.Int("reserved", group.ReservedCount),
		zap.Int("ondemand", group.OnDemandCount),
		zap.Int("spot", group.SpotCount),
		zap.Float64("reserved_ratio", reservedRatio),
		zap.Float64("hourly_cost", group.TotalHourlyCost),
		zap.Float64("monthly_cost_estimate", group.TotalHourlyCost*24*30),
	)

	costActions, err := a.cloud.CalculateCostOptimization(ctx, group)
	if err != nil {
		return fmt.Errorf("failed to calculate cost optimization: %w", err)
	}

	validActions := a.strategy.EvaluateCostOptimization(ctx, group, costActions)

	if len(validActions) == 0 {
		a.logger.Info("no cost optimization actions needed")
		return nil
	}

	a.logger.Info("executing cost optimization actions",
		zap.Int("action_count", len(validActions)),
	)

	for _, act := range validActions {
		if a.config.DryRun || a.config.DryRunMode != types.DryRunOff {
			a.logger.Info("dry run: skipping cost optimization action",
				zap.String("type", act.Type),
				zap.String("instance_id", act.InstanceID),
				zap.Float64("savings", act.CostSavings),
			)
			continue
		}

		if act.Type == "convert_to_reserved" {
			if err := a.cloud.ConvertChargeType(ctx, act.InstanceID, types.ChargeTypeReserved); err != nil {
				a.logger.Error("failed to convert to reserved",
					zap.String("instance_id", act.InstanceID),
					zap.Error(err),
				)
				continue
			}
			a.logger.Info("converted instance to reserved",
				zap.String("instance_id", act.InstanceID),
				zap.Float64("monthly_savings", act.CostSavings),
			)
		}
	}

	totalSavings := 0.0
	for _, act := range validActions {
		totalSavings += act.CostSavings
	}
	a.logger.Info("cost optimization completed",
		zap.Float64("total_monthly_savings", totalSavings),
	)

	return nil
}

func (a *Autoscaler) GetLastDryRun() *types.DryRunResult {
	a.mu.Lock()
	defer a.mu.Unlock()
	return a.lastDryRun
}

func (a *Autoscaler) RunReplay(ctx context.Context, config types.HistoryReplayConfig) (*types.ReplayResult, error) {
	if a.history == nil {
		return nil, fmt.Errorf("history recorder not initialized")
	}

	return a.history.Replay(ctx, config)
}

func (a *Autoscaler) GetHistoryRecords(startTime, endTime time.Time) ([]*types.ScalingHistoryRecord, error) {
	if a.history == nil {
		return nil, fmt.Errorf("history recorder not initialized")
	}

	return a.history.Query(startTime, endTime)
}

func (a *Autoscaler) GenerateVisualReport(ctx context.Context, config types.HistoryReplayConfig) (string, error) {
	if a.history == nil {
		return "", fmt.Errorf("history recorder not initialized")
	}

	return a.history.GenerateVisualReport(ctx, config)
}
