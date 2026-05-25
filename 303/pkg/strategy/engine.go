package strategy

import (
	"context"
	"fmt"
	"sync"
	"time"

	"autoscaler/internal/types"
	"go.uber.org/zap"
)

type StrategyEngineConfig struct {
	Policies            []types.ScalingPolicy
	UsePrediction       bool
	UseErrorCorrection  bool
	CooldownKey         string
	ServiceCooldowns    types.ServiceCooldownConfig
	DefaultServiceLevel types.ServiceLevel
	CostConfig          *types.CostConfig
	CostOptimization    bool
}

type StrategyEngine struct {
	config       StrategyEngineConfig
	lastScaling  map[string]time.Time
	cooldownLock sync.RWMutex
	errorState   *types.ErrorFeedbackState
	logger       *zap.Logger
}

func NewStrategyEngine(config StrategyEngineConfig, logger *zap.Logger) *StrategyEngine {
	if config.Policies == nil {
		config.Policies = make([]types.ScalingPolicy, 0)
	}

	if config.DefaultServiceLevel == "" {
		config.DefaultServiceLevel = types.ServiceLevelMedium
	}

	return &StrategyEngine{
		config:     config,
		lastScaling: make(map[string]time.Time),
		errorState: &types.ErrorFeedbackState{
			Errors:      make([]types.PredictionError, 0),
			Corrections: make(map[types.MetricType]float64),
		},
		logger: logger,
	}
}

func (s *StrategyEngine) AddPolicy(policy types.ScalingPolicy) {
	s.config.Policies = append(s.config.Policies, policy)
}

func (s *StrategyEngine) SetErrorFeedbackState(state *types.ErrorFeedbackState) {
	if state != nil {
		s.errorState = state
	}
}

func (s *StrategyEngine) Evaluate(
	metrics []*types.MetricData,
	instanceGroup *types.InstanceGroup,
	scalingType types.ScalingType,
	serviceName string,
	serviceLevel types.ServiceLevel,
) (*types.ScalingAction, error) {
	if serviceLevel == "" {
		serviceLevel = s.config.DefaultServiceLevel
	}

	if len(metrics) == 0 {
		return &types.ScalingAction{
			Type:         scalingType,
			Direction:    types.NoScale,
			Reason:       "no metrics available",
			Timestamp:    time.Now(),
			ServiceName:  serviceName,
			ServiceLevel: serviceLevel,
		}, nil
	}

	var bestAction *types.ScalingAction
	strongestDeviation := 0.0

	for _, policy := range s.config.Policies {
		metric := s.findMetric(metrics, policy.MetricType)
		if metric == nil {
			continue
		}

		if s.config.UseErrorCorrection {
			metric.Corrected = s.applyErrorCorrection(metric)
			s.logger.Debug("applied error correction",
				zap.String("metric", string(metric.MetricType)),
				zap.Float64("predicted", metric.Predicted),
				zap.Float64("corrected", metric.Corrected),
			)
		}

		action, deviation := s.evaluatePolicy(metric, policy, instanceGroup, scalingType)
		if action == nil {
			continue
		}

		action.ServiceName = serviceName
		action.ServiceLevel = serviceLevel

		if action.Direction != types.NoScale {
			cooldownPeriod := s.getServiceCooldown(serviceLevel, policy.CooldownPeriod)
			if s.isInCooldown(action.InstanceID, cooldownPeriod, serviceName) {
				s.logger.Debug("skipping scaling due to cooldown",
					zap.String("instance_id", action.InstanceID),
					zap.String("service", serviceName),
					zap.String("level", string(serviceLevel)),
					zap.Duration("cooldown", cooldownPeriod),
				)
				continue
			}
		}

		absDeviation := deviation
		if absDeviation < 0 {
			absDeviation = -absDeviation
		}

		if absDeviation > strongestDeviation {
			strongestDeviation = absDeviation
			bestAction = action
		}
	}

	if bestAction == nil {
		return &types.ScalingAction{
			Type:         scalingType,
			Direction:    types.NoScale,
			Reason:       "all metrics within tolerance",
			Timestamp:    time.Now(),
			ServiceName:  serviceName,
			ServiceLevel: serviceLevel,
		}, nil
	}

	return bestAction, nil
}

func (s *StrategyEngine) applyErrorCorrection(metric *types.MetricData) float64 {
	if metric.Predicted <= 0 {
		return metric.Current
	}

	correction := s.errorState.GetCorrection(metric.MetricType, types.ErrorFeedbackConfig{
		Enabled:       s.config.UseErrorCorrection,
		MaxCorrection: 20.0,
	})

	corrected := metric.Predicted + correction
	if corrected < 0 {
		corrected = 0
	}

	return corrected
}

func (s *StrategyEngine) evaluatePolicy(
	metric *types.MetricData,
	policy types.ScalingPolicy,
	instanceGroup *types.InstanceGroup,
	scalingType types.ScalingType,
) (*types.ScalingAction, float64) {
	currentValue := metric.Current
	if s.config.UsePrediction && metric.Predicted > 0 {
		currentValue = metric.Predicted
		if s.config.UseErrorCorrection && metric.Corrected > 0 {
			currentValue = metric.Corrected
		}
		s.logger.Debug("using predicted/corrected value for evaluation",
			zap.Float64("current", metric.Current),
			zap.Float64("predicted", metric.Predicted),
			zap.Float64("corrected", metric.Corrected),
		)
	}

	target := policy.TargetValue
	tolerance := policy.Tolerance
	if tolerance <= 0 {
		tolerance = 5.0
	}

	upperBound := target + tolerance
	lowerBound := target - tolerance

	deviation := currentValue - target
	relativeDeviation := deviation / target * 100

	var direction types.ScalingDirection
	var step int

	switch {
	case currentValue > upperBound:
		direction = types.ScaleUp
		step = s.calculateStep(deviation, target, policy.StepSize)
	case currentValue < lowerBound:
		direction = types.ScaleDown
		step = s.calculateStep(-deviation, target, policy.StepSize)
	default:
		direction = types.NoScale
		step = 0
	}

	instanceID := metric.InstanceID
	if scalingType == types.HorizontalScaling {
		instanceID = instanceGroup.ID
		if direction == types.ScaleUp && instanceGroup.Desired >= policy.MaxInstances {
			s.logger.Debug("cannot scale up, already at max instances",
				zap.Int("current", instanceGroup.Desired),
				zap.Int("max", policy.MaxInstances),
			)
			return &types.ScalingAction{
				Type:      scalingType,
				Direction: types.NoScale,
				Reason:    "already at max instances",
				Timestamp: time.Now(),
			}, 0
		}
		if direction == types.ScaleDown && instanceGroup.Desired <= policy.MinInstances {
			s.logger.Debug("cannot scale down, already at min instances",
				zap.Int("current", instanceGroup.Desired),
				zap.Int("min", policy.MinInstances),
			)
			return &types.ScalingAction{
				Type:      scalingType,
				Direction: types.NoScale,
				Reason:    "already at min instances",
				Timestamp: time.Now(),
			}, 0
		}
	}

	if direction != types.NoScale {
		step = s.adjustStep(step, instanceGroup, policy, scalingType, direction)
	}

	costEstimate := 0.0
	chargeType := types.ChargeTypeOnDemand

	if s.config.CostOptimization && s.config.CostConfig != nil {
		chargeType, costEstimate = s.calculateCostEstimate(instanceGroup, direction, step, policy)
	}

	reason := fmt.Sprintf("metric %s: current=%.2f, target=%.2f, deviation=%.2f%%",
		policy.MetricType, currentValue, target, relativeDeviation)

	return &types.ScalingAction{
		Type:         scalingType,
		Direction:    direction,
		InstanceID:   instanceID,
		Step:         step,
		Reason:       reason,
		Timestamp:    time.Now(),
		ChargeType:   chargeType,
		CostEstimate: costEstimate,
	}, deviation
}

func (s *StrategyEngine) calculateStep(deviation, target float64, baseStep int) int {
	if baseStep <= 0 {
		baseStep = 1
	}

	ratio := deviation / target
	step := int(ratio * float64(baseStep) * 2)

	if step < 1 {
		step = 1
	}
	if step > baseStep*2 {
		step = baseStep * 2
	}

	return step
}

func (s *StrategyEngine) adjustStep(
	step int,
	instanceGroup *types.InstanceGroup,
	policy types.ScalingPolicy,
	scalingType types.ScalingType,
	direction types.ScalingDirection,
) int {
	if scalingType == types.HorizontalScaling {
		if direction == types.ScaleUp {
			maxAdd := policy.MaxInstances - instanceGroup.Desired
			if step > maxAdd {
				step = maxAdd
			}
		} else if direction == types.ScaleDown {
			maxRemove := instanceGroup.Desired - policy.MinInstances
			if step > maxRemove {
				step = maxRemove
			}
		}
	}

	return step
}

func (s *StrategyEngine) findMetric(metrics []*types.MetricData, metricType types.MetricType) *types.MetricData {
	for _, m := range metrics {
		if m.MetricType == metricType {
			return m
		}
	}
	return nil
}

func (s *StrategyEngine) getServiceCooldown(serviceLevel types.ServiceLevel, defaultCooldown time.Duration) time.Duration {
	switch serviceLevel {
	case types.ServiceLevelCritical:
		if s.config.ServiceCooldowns.Critical > 0 {
			return s.config.ServiceCooldowns.Critical
		}
		return defaultCooldown * 3
	case types.ServiceLevelHigh:
		if s.config.ServiceCooldowns.High > 0 {
			return s.config.ServiceCooldowns.High
		}
		return defaultCooldown * 2
	case types.ServiceLevelMedium:
		if s.config.ServiceCooldowns.Medium > 0 {
			return s.config.ServiceCooldowns.Medium
		}
		return defaultCooldown
	case types.ServiceLevelLow:
		if s.config.ServiceCooldowns.Low > 0 {
			return s.config.ServiceCooldowns.Low
		}
		return defaultCooldown / 2
	default:
		return defaultCooldown
	}
}

func (s *StrategyEngine) RecordScaling(action *types.ScalingAction) {
	s.cooldownLock.Lock()
	defer s.cooldownLock.Unlock()

	key := action.InstanceID
	if action.ServiceName != "" {
		key = action.ServiceName
	}
	if s.config.CooldownKey != "" {
		key = s.config.CooldownKey
	}

	s.lastScaling[key] = action.Timestamp
	s.logger.Info("recorded scaling action for cooldown",
		zap.String("key", key),
		zap.String("type", string(action.Type)),
		zap.String("direction", string(action.Direction)),
		zap.String("service", action.ServiceName),
		zap.String("level", string(action.ServiceLevel)),
		zap.Time("timestamp", action.Timestamp),
	)
}

func (s *StrategyEngine) isInCooldown(instanceID string, cooldownPeriod time.Duration, serviceName string) bool {
	if cooldownPeriod <= 0 {
		return false
	}

	s.cooldownLock.RLock()
	defer s.cooldownLock.RUnlock()

	key := instanceID
	if serviceName != "" {
		key = serviceName
	}
	if s.config.CooldownKey != "" {
		key = s.config.CooldownKey
	}

	lastTime, exists := s.lastScaling[key]
	if !exists {
		return false
	}

	elapsed := time.Since(lastTime)
	return elapsed < cooldownPeriod
}

func (s *StrategyEngine) GetCooldownRemaining(instanceID string, cooldownPeriod time.Duration, serviceName string) time.Duration {
	if cooldownPeriod <= 0 {
		return 0
	}

	s.cooldownLock.RLock()
	defer s.cooldownLock.RUnlock()

	key := instanceID
	if serviceName != "" {
		key = serviceName
	}
	if s.config.CooldownKey != "" {
		key = s.config.CooldownKey
	}

	lastTime, exists := s.lastScaling[key]
	if !exists {
		return 0
	}

	elapsed := time.Since(lastTime)
	if elapsed >= cooldownPeriod {
		return 0
	}

	return cooldownPeriod - elapsed
}

func (s *StrategyEngine) ClearCooldown(instanceID string) {
	s.cooldownLock.Lock()
	defer s.cooldownLock.Unlock()

	key := instanceID
	if s.config.CooldownKey != "" {
		key = s.config.CooldownKey
	}

	delete(s.lastScaling, key)
}

func (s *StrategyEngine) RecordPredictionError(metricType types.MetricType, predicted, actual float64) {
	error := actual - predicted
	errorRatio := 0.0
	if actual != 0 {
		errorRatio = error / actual * 100
	}

	err := types.PredictionError{
		MetricType: metricType,
		Timestamp:  time.Now(),
		Predicted:  predicted,
		Actual:     actual,
		Error:      error,
		ErrorRatio: errorRatio,
	}

	s.errorState.RecordError(err)

	s.logger.Debug("recorded prediction error",
		zap.String("metric", string(metricType)),
		zap.Float64("predicted", predicted),
		zap.Float64("actual", actual),
		zap.Float64("error", error),
		zap.Float64("error_ratio", errorRatio),
	)
}

func (s *StrategyEngine) UpdateErrorCorrections(config types.ErrorFeedbackConfig) {
	s.errorState.UpdateCorrections(config)

	s.logger.Debug("updated error corrections",
		zap.Any("corrections", s.errorState.Corrections),
	)
}

func (s *StrategyEngine) calculateCostEstimate(
	group *types.InstanceGroup,
	direction types.ScalingDirection,
	step int,
	policy types.ScalingPolicy,
) (types.InstanceChargeType, float64) {
	if s.config.CostConfig == nil {
		return types.ChargeTypeOnDemand, 0
	}

	targetRatio := s.config.CostConfig.ReservedInstanceRatio
	if targetRatio <= 0 {
		targetRatio = 0.7
	}

	totalInstances := group.Desired
	if direction == types.ScaleUp {
		totalInstances += step
	} else if direction == types.ScaleDown {
		totalInstances -= step
	}

	if totalInstances < 0 {
		totalInstances = 0
	}

	targetReserved := int(float64(totalInstances) * targetRatio)
	needReserved := targetReserved - group.ReservedCount

	chargeType := types.ChargeTypeOnDemand
	costPerHour := 0.0

	if direction == types.ScaleUp && step > 0 {
		flavor := policy.MaxSize
		for _, inst := range group.Instances {
			if inst.Flavor != "" {
				flavor = inst.Flavor
				break
			}
		}

		reservedPrice := 0.03
		onDemandPrice := 0.05
		spotPrice := 0.02

		if flavor == "ecs.medium" {
			reservedPrice = 0.06
			onDemandPrice = 0.10
			spotPrice = 0.04
		} else if flavor == "ecs.large" {
			reservedPrice = 0.12
			onDemandPrice = 0.20
			spotPrice = 0.08
		}

		for i := 0; i < step; i++ {
			if needReserved > 0 {
				chargeType = types.ChargeTypeReserved
				costPerHour += reservedPrice
				needReserved--
			} else if s.config.CostConfig.SpotInstanceEnabled {
				chargeType = types.ChargeTypeSpot
				costPerHour += spotPrice
			} else {
				chargeType = types.ChargeTypeOnDemand
				costPerHour += onDemandPrice
			}
		}

		s.logger.Debug("calculated cost estimate for scaling",
			zap.String("direction", string(direction)),
			zap.Int("step", step),
			zap.String("charge_type", string(chargeType)),
			zap.Float64("cost_per_hour", costPerHour),
		)
	} else if direction == types.ScaleDown && step > 0 {
		flavor := policy.MaxSize
		for _, inst := range group.Instances {
			if inst.Flavor != "" {
				flavor = inst.Flavor
				break
			}
		}

		onDemandPrice := 0.05
		if flavor == "ecs.medium" {
			onDemandPrice = 0.10
		} else if flavor == "ecs.large" {
			onDemandPrice = 0.20
		}

		costPerHour = -float64(step) * onDemandPrice
	}

	return chargeType, costPerHour
}

func (s *StrategyEngine) EvaluateCostOptimization(
	ctx context.Context,
	group *types.InstanceGroup,
	costActions []types.CostOptimizationAction,
) []types.CostOptimizationAction {
	if !s.config.CostOptimization || s.config.CostConfig == nil {
		return nil
	}

	validActions := make([]types.CostOptimizationAction, 0)
	costThreshold := s.config.CostConfig.CostThreshold
	if costThreshold <= 0 {
		costThreshold = 10.0
	}

	for _, action := range costActions {
		if action.CostSavings >= costThreshold {
			validActions = append(validActions, action)
			s.logger.Info("cost optimization action approved",
				zap.String("type", action.Type),
				zap.String("instance_id", action.InstanceID),
				zap.Float64("monthly_savings", action.CostSavings),
				zap.String("reason", action.Reason),
			)
		} else {
			s.logger.Debug("cost optimization action skipped",
				zap.String("type", action.Type),
				zap.String("instance_id", action.InstanceID),
				zap.Float64("savings_below_threshold", costThreshold-action.CostSavings),
			)
		}
	}

	return validActions
}
