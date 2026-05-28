package adjuster

import (
	"context"
	"fmt"
	"math"
	"time"

	corev1 "k8s.io/api/core/v1"
	"k8s.io/apimachinery/pkg/api/resource"
	metav1 "k8s.io/apimachinery/pkg/apis/meta/v1"
	"k8s.io/client-go/kubernetes"
	"k8s.io/client-go/rest"
	"k8s.io/client-go/tools/clientcmd"

	"container-autoscaler/pkg/config"
	"container-autoscaler/pkg/types"
	"container-autoscaler/pkg/utils"
)

type KubernetesAdjuster struct {
	client       kubernetes.Interface
	config       config.KubernetesConfig
	scalingConfig config.ScalingConfig
	logger       *utils.Logger
	cooldowns    map[string]time.Time
}

func NewKubernetesAdjuster(
	kubeCfg config.KubernetesConfig,
	scalingCfg config.ScalingConfig,
	logger *utils.Logger,
) (*KubernetesAdjuster, error) {
	var config *rest.Config
	var err error

	if kubeCfg.KubeconfigPath != "" {
		config, err = clientcmd.BuildConfigFromFlags("", kubeCfg.KubeconfigPath)
	} else {
		config, err = rest.InClusterConfig()
	}
	if err != nil {
		return nil, fmt.Errorf("building kubernetes config: %w", err)
	}

	client, err := kubernetes.NewForConfig(config)
	if err != nil {
		return nil, fmt.Errorf("creating kubernetes client: %w", err)
	}

	return &KubernetesAdjuster{
		client:        client,
		config:        kubeCfg,
		scalingConfig: scalingCfg,
		logger:        logger,
		cooldowns:     make(map[string]time.Time),
	}, nil
}

func (a *KubernetesAdjuster) GetPodResources(
	ctx context.Context,
	namespace string,
	podName string,
	containerName string,
) (*types.ResourceMetrics, error) {
	pod, err := a.client.CoreV1().Pods(namespace).Get(ctx, podName, metav1.GetOptions{})
	if err != nil {
		return nil, fmt.Errorf("getting pod %s/%s: %w", namespace, podName, err)
	}

	for _, container := range pod.Spec.Containers {
		if container.Name == containerName {
			metrics := &types.ResourceMetrics{
				PodName:       podName,
				Namespace:     namespace,
				ContainerName: containerName,
			}

			if container.Resources.Limits != nil {
				if cpuLimit, ok := container.Resources.Limits[corev1.ResourceCPU]; ok {
					metrics.CPULimit = float64(cpuLimit.MilliValue())
				}
				if memLimit, ok := container.Resources.Limits[corev1.ResourceMemory]; ok {
					metrics.MemoryLimit = float64(memLimit.Value()) / (1024 * 1024)
				}
			}

			if container.Resources.Requests != nil {
				if cpuReq, ok := container.Resources.Requests[corev1.ResourceCPU]; ok {
					metrics.CPURequest = float64(cpuReq.MilliValue())
				}
				if memReq, ok := container.Resources.Requests[corev1.ResourceMemory]; ok {
					metrics.MemoryRequest = float64(memReq.Value()) / (1024 * 1024)
				}
			}

			return metrics, nil
		}
	}

	return nil, fmt.Errorf("container %s not found in pod %s/%s", containerName, namespace, podName)
}

func (a *KubernetesAdjuster) GetPod(
	ctx context.Context,
	namespace string,
	podName string,
) (*corev1.Pod, error) {
	pod, err := a.client.CoreV1().Pods(namespace).Get(ctx, podName, metav1.GetOptions{})
	if err != nil {
		return nil, fmt.Errorf("getting pod %s/%s: %w", namespace, podName, err)
	}
	return pod, nil
}

func (a *KubernetesAdjuster) AdjustResources(
	ctx context.Context,
	action types.AdjustmentAction,
) (*types.AdjustmentResult, error) {
	key := fmt.Sprintf("%s/%s/%s", action.Namespace, action.PodName, action.ContainerName)

	if cooldown, exists := a.cooldowns[key]; exists {
		if time.Since(cooldown) < a.scalingConfig.CooldownPeriod {
			a.logger.Debug("Skipping adjustment for %s: in cooldown period", key)
			return &types.AdjustmentResult{
				Success: true,
				Action:  action,
				Applied: false,
				Message: fmt.Sprintf("Cooldown active, next adjustment allowed at %s",
					cooldown.Add(a.scalingConfig.CooldownPeriod).Format(time.RFC3339)),
			}, nil
		}
	}

	if action.DryRun {
		a.logger.Info("[DRY RUN] Would adjust %s/%s/%s %s: %.0fm -> %.0fm (request: %.0fm -> %.0fm)",
			action.Namespace, action.PodName, action.ContainerName,
			action.ResourceType, action.OldLimit, action.NewLimit,
			action.OldRequest, action.NewRequest)

		return &types.AdjustmentResult{
			Success: true,
			Action:  action,
			Applied: false,
			Message: fmt.Sprintf("Dry run: %s limit %.0f -> %.0f, request %.0f -> %.0f",
				action.ResourceType, action.OldLimit, action.NewLimit,
				action.OldRequest, action.NewRequest),
		}, nil
	}

	pod, err := a.client.CoreV1().Pods(action.Namespace).Get(ctx, action.PodName, metav1.GetOptions{})
	if err != nil {
		return nil, fmt.Errorf("getting pod: %w", err)
	}

	updated := false
	for i, container := range pod.Spec.Containers {
		if container.Name == action.ContainerName {
			if pod.Spec.Containers[i].Resources.Limits == nil {
				pod.Spec.Containers[i].Resources.Limits = make(corev1.ResourceList)
			}
			if pod.Spec.Containers[i].Resources.Requests == nil {
				pod.Spec.Containers[i].Resources.Requests = make(corev1.ResourceList)
			}

			switch action.ResourceType {
			case corev1.ResourceCPU:
				pod.Spec.Containers[i].Resources.Limits[corev1.ResourceCPU] = *resource.NewMilliQuantity(
					int64(action.NewLimit), resource.DecimalSI,
				)
				pod.Spec.Containers[i].Resources.Requests[corev1.ResourceCPU] = *resource.NewMilliQuantity(
					int64(action.NewRequest), resource.DecimalSI,
				)
			case corev1.ResourceMemory:
				pod.Spec.Containers[i].Resources.Limits[corev1.ResourceMemory] = *resource.NewQuantity(
					int64(action.NewLimit*1024*1024), resource.BinarySI,
				)
				pod.Spec.Containers[i].Resources.Requests[corev1.ResourceMemory] = *resource.NewQuantity(
					int64(action.NewRequest*1024*1024), resource.BinarySI,
				)
			}

			updated = true
			break
		}
	}

	if !updated {
		return nil, fmt.Errorf("container %s not found in pod", action.ContainerName)
	}

	_, err = a.client.CoreV1().Pods(action.Namespace).Update(ctx, pod, metav1.UpdateOptions{})
	if err != nil {
		return nil, fmt.Errorf("updating pod: %w", err)
	}

	a.cooldowns[key] = time.Now()

	a.logger.Info("Successfully adjusted %s/%s/%s %s: %.0f -> %.0f",
		action.Namespace, action.PodName, action.ContainerName,
		action.ResourceType, action.OldLimit, action.NewLimit)

	return &types.AdjustmentResult{
		Success: true,
		Action:  action,
		Applied: true,
		Message: fmt.Sprintf("Successfully adjusted %s resources", action.ResourceType),
		AppliedAt: time.Now(),
	}, nil
}

func (a *KubernetesAdjuster) GetPodsInNamespace(
	ctx context.Context,
	namespace string,
) ([]corev1.Pod, error) {
	pods, err := a.client.CoreV1().Pods(namespace).List(ctx, metav1.ListOptions{})
	if err != nil {
		return nil, fmt.Errorf("listing pods: %w", err)
	}
	return pods.Items, nil
}

func (a *KubernetesAdjuster) ValidateAction(action types.AdjustmentAction) error {
	if action.NewLimit <= 0 {
		return fmt.Errorf("new limit must be positive")
	}

	if action.NewRequest > action.NewLimit {
		return fmt.Errorf("request cannot exceed limit")
	}

	changePercent := 0.0
	if action.OldLimit > 0 {
		changePercent = (action.NewLimit - action.OldLimit) / action.OldLimit
	}

	if math.Abs(changePercent) > a.scalingConfig.MaxAdjustmentPercent {
		return fmt.Errorf("adjustment %.2f%% exceeds maximum allowed %.2f%%",
			changePercent*100, a.scalingConfig.MaxAdjustmentPercent*100)
	}

	return nil
}

func (a *KubernetesAdjuster) ShouldAdjust(
	recommendation types.Recommendation,
	currentLimit float64,
	minConfidence float64,
) bool {
	if recommendation.Confidence < minConfidence {
		a.logger.Debug("Confidence %.2f below threshold %.2f", recommendation.Confidence, minConfidence)
		return false
	}

	changeRatio := math.Abs(recommendation.ProposedLimit-currentLimit) / currentLimit
	if changeRatio < 0.05 {
		a.logger.Debug("Change ratio %.4f too small to warrant adjustment", changeRatio)
		return false
	}

	return true
}

type BacktestConfig struct {
	Namespace     string
	PodName       string
	ContainerName string
	ResourceType  corev1.ResourceName
	DaysToSimulate int
	StepMinutes   int
	CooldownMinutes int
}

func (a *KubernetesAdjuster) RunBacktest(
	ctx context.Context,
	ts types.TimeSeriesData,
	cfg BacktestConfig,
	initialLimit float64,
	initialRequest float64,
	recommender func(usageHistory []float64, currentLimit float64) (float64, float64, string),
) *types.BacktestResult {
	if len(ts.Values) < 24 {
		a.logger.Warning("Insufficient data for backtest: %d points (need at least 24)", len(ts.Values))
		return nil
	}

	result := &types.BacktestResult{
		PodName:       cfg.PodName,
		Namespace:     cfg.Namespace,
		ContainerName: cfg.ContainerName,
		ResourceType:  cfg.ResourceType,
		StartDate:     ts.Timestamps[0],
		EndDate:       ts.Timestamps[len(ts.Timestamps)-1],
		Actions:       make([]types.BacktestAction, 0),
		Points:        make([]types.BacktestPoint, 0),
	}

	windowSize := 24
	currentLimit := initialLimit
	currentRequest := initialRequest
	lastAdjustmentIdx := -1

	originalWaste := 0.0
	simulatedWaste := 0.0
	contentionCount := 0
	peakOverage := 0.0
	totalEfficiency := 0.0
	efficiencyCount := 0

	for i := windowSize; i < len(ts.Values); i++ {
		history := ts.Values[i-windowSize : i]

		recommendedLimit, recommendedRequest, reason := recommender(history, currentLimit)

		cooldownSteps := cfg.CooldownMinutes / cfg.StepMinutes
		if cooldownSteps < 1 {
			cooldownSteps = 1
		}

		shouldAdjust := false
		if lastAdjustmentIdx == -1 || (i-lastAdjustmentIdx) >= cooldownSteps {
			changeRatio := math.Abs(recommendedLimit-currentLimit) / currentLimit
			if changeRatio > 0.05 {
				shouldAdjust = true
			}
		}

		if shouldAdjust && i < len(ts.Timestamps) {
			action := types.BacktestAction{
				Timestamp:    ts.Timestamps[i],
				ResourceType: cfg.ResourceType,
				OldLimit:     currentLimit,
				NewLimit:     recommendedLimit,
				OldRequest:   currentRequest,
				NewRequest:   recommendedRequest,
				Reason:       reason,
				Confidence:   0.7,
			}
			result.Actions = append(result.Actions, action)
			currentLimit = recommendedLimit
			currentRequest = recommendedRequest
			lastAdjustmentIdx = i
		}

		actualUsage := ts.Values[i]

		originalLimit := initialLimit
		origEfficiency := 0.0
		if originalLimit > 0 {
			origEfficiency = actualUsage / originalLimit
		}

		simEfficiency := 0.0
		if currentLimit > 0 {
			simEfficiency = actualUsage / currentLimit
		}

		origWaste := 0.0
		if originalLimit > actualUsage {
			origWaste = originalLimit - actualUsage
		}
		originalWaste += origWaste

		simWaste := 0.0
		if currentLimit > actualUsage {
			simWaste = currentLimit - actualUsage
		}
		simulatedWaste += simWaste

		contentionRisk := 0.0
		if actualUsage > currentLimit*0.95 {
			contentionRisk = (actualUsage - currentLimit*0.95) / currentLimit
		}
		if actualUsage > currentLimit {
			contentionCount++
			overage := actualUsage - currentLimit
			if overage > peakOverage {
				peakOverage = overage
			}
		}

		point := types.BacktestPoint{
			Timestamp:      ts.Timestamps[i],
			ActualUsage:    actualUsage,
			Recommended:    recommendedLimit,
			OriginalLimit:  initialLimit,
			SimulatedLimit: currentLimit,
			EfficiencyGain: simEfficiency - origEfficiency,
			WasteAvoided:   origWaste - simWaste,
			ContentionRisk: contentionRisk,
		}
		result.Points = append(result.Points, point)

		if simEfficiency > 0 && simEfficiency <= 1.0 {
			totalEfficiency += simEfficiency
			efficiencyCount++
		}
	}

	result.OriginalWaste = originalWaste
	result.SimulatedWaste = simulatedWaste
	result.WasteSaved = originalWaste - simulatedWaste
	if efficiencyCount > 0 {
		result.AvgEfficiency = totalEfficiency / float64(efficiencyCount)
	}
	result.ContentionCount = contentionCount
	result.PeakOverage = peakOverage

	if result.WasteSaved > 0 && result.OriginalWaste > 0 {
		savingsPct := result.WasteSaved / result.OriginalWaste * 100
		result.Recommendation = fmt.Sprintf(
			"Backtest shows %.1f%% waste reduction (%.0f -> %.0f units saved). Avg efficiency: %.1f%%. Contentions: %d.",
			savingsPct, result.WasteSaved, result.OriginalWaste,
			result.AvgEfficiency*100, contentionCount,
		)
	} else {
		result.Recommendation = fmt.Sprintf(
			"Backtest complete. Avg efficiency: %.1f%%. Contentions: %d. Peak overage: %.2f.",
			result.AvgEfficiency*100, contentionCount, peakOverage,
		)
	}

	return result
}

func mathAbs(x float64) float64 {
	if x < 0 {
		return -x
	}
	return x
}
