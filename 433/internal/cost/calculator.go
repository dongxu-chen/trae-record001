package cost

import (
	"context"
	"fmt"
	"math"
	"sort"
	"time"

	"k8s-cost-allocation/internal/config"
	"k8s-cost-allocation/internal/k8sclient"
	"k8s-cost-allocation/internal/promclient"
)

type CostBreakdown struct {
	CPU      float64 `json:"cpu"`
	Memory   float64 `json:"memory"`
	Storage  float64 `json:"storage"`
	Network  float64 `json:"network"`
	Total    float64 `json:"total"`
}

type NamespaceCost struct {
	Namespace      string            `json:"namespace"`
	Labels         map[string]string `json:"labels"`
	Cost           CostBreakdown     `json:"cost"`
	ResourceUsage  ResourceUsage     `json:"resourceUsage"`
	CustomFactor   float64           `json:"customFactor"`
}

type ProjectCost struct {
	ProjectName string                 `json:"projectName"`
	Namespaces  []string               `json:"namespaces"`
	Cost        CostBreakdown          `json:"cost"`
}

type LabelCost struct {
	LabelKey   string                 `json:"labelKey"`
	LabelValue string                 `json:"labelValue"`
	Namespaces []string               `json:"namespaces"`
	Cost       CostBreakdown          `json:"cost"`
}

type ResourceUsage struct {
	CPUCores           float64 `json:"cpuCores"`
	MemoryGB           float64 `json:"memoryGB"`
	StorageUsedGB      float64 `json:"storageUsedGB"`
	StorageCapacityGB  float64 `json:"storageCapacityGB"`
	NetworkInternalRX  float64 `json:"networkInternalRxGB"`
	NetworkInternalTX  float64 `json:"networkInternalTxGB"`
	NetworkExternalRX  float64 `json:"networkExternalRxGB"`
	NetworkExternalTX  float64 `json:"networkExternalTxGB"`
	CPURequestCores    float64 `json:"cpuRequestCores"`
	MemoryRequestGB    float64 `json:"memoryRequestGB"`
}

type ResourceContention struct {
	Namespace          string  `json:"namespace"`
	CPUThrottledTime   float64 `json:"cpuThrottledTime"`
	MemoryOOMCount     int     `json:"memoryOOMCount"`
	ContentionScore    float64 `json:"contentionScore"`
	RecommendedCPU     float64 `json:"recommendedCPU"`
	RecommendedMemory  float64 `json:"recommendedMemory"`
	ContentionLevel    string  `json:"contentionLevel"`
}

type IdleResource struct {
	Namespace     string  `json:"namespace"`
	ResourceType  string  `json:"resourceType"`
	Requested     float64 `json:"requested"`
	Used          float64 `json:"used"`
	IdleAmount    float64 `json:"idleAmount"`
	IdleCost      float64 `json:"idleCost"`
	Utilization   float64 `json:"utilization"`
}

type CostPrediction struct {
	Namespace        string  `json:"namespace"`
	CurrentCost      float64 `json:"currentCost"`
	PredictedCost30D float64 `json:"predictedCost30D"`
	PredictedCost90D float64 `json:"predictedCost90D"`
	GrowthRate       float64 `json:"growthRate"`
}

type OptimizationSuggestion struct {
	Namespace      string  `json:"namespace"`
	Type           string  `json:"type"`
	Description    string  `json:"description"`
	EstimatedSavings float64 `json:"estimatedSavings"`
	Severity       string  `json:"severity"`
}

type Calculator struct {
	cfg          config.CostConfig
	budgetCfg    config.BudgetConfig
	pricingCfg   config.PricingConfig
	k8sClient    *k8sclient.Client
	promClient   *promclient.Client
	budgetMgr    *BudgetManager
}

func NewCalculator(cfg config.CostConfig, budgetCfg config.BudgetConfig, pricingCfg config.PricingConfig, k8sClient *k8sclient.Client, promClient *promclient.Client) *Calculator {
	budgetMgr := NewBudgetManager(budgetCfg, pricingCfg)
	return &Calculator{
		cfg:        cfg,
		budgetCfg:  budgetCfg,
		pricingCfg: pricingCfg,
		k8sClient:  k8sClient,
		promClient: promClient,
		budgetMgr:  budgetMgr,
	}
}

func (c *Calculator) GetBudgetManager() *BudgetManager {
	return c.budgetMgr
}

func (c *Calculator) CalculateNamespaceCosts(ctx context.Context, duration time.Duration) ([]NamespaceCost, error) {
	namespaces, err := c.k8sClient.GetNamespaces(ctx)
	if err != nil {
		return nil, err
	}

	allPods, err := c.k8sClient.GetAllPods(ctx)
	if err != nil {
		return nil, err
	}

	allPVCs, err := c.k8sClient.GetAllPVCs(ctx)
	if err != nil {
		return nil, err
	}

	metrics, err := c.promClient.GetAllNamespacesMetrics(ctx, duration)
	if err != nil {
		return nil, err
	}

	hours := duration.Hours()

	podMap := make(map[string][]k8sclient.PodInfo)
	for _, pod := range allPods {
		podMap[pod.Namespace] = append(podMap[pod.Namespace], pod)
	}

	pvcMap := make(map[string][]k8sclient.PVCInfo)
	for _, pvc := range allPVCs {
		pvcMap[pvc.Namespace] = append(pvcMap[pvc.Namespace], pvc)
	}

	metricsMap := make(map[string]promclient.NamespaceMetrics)
	for _, m := range metrics {
		metricsMap[m.Namespace] = m
	}

	var results []NamespaceCost
	for _, ns := range namespaces {
		nsPods := podMap[ns.Name]
		nsPVCs := pvcMap[ns.Name]
		nsMetrics := metricsMap[ns.Name]

		var cpuRequest, memoryRequest, storageCapacity float64
		for _, pod := range nsPods {
			cpuRequest += pod.CPURequest
			memoryRequest += pod.MemoryRequest
		}
		for _, pvc := range nsPVCs {
			storageCapacity += pvc.CapacityGB
		}

		cpuUsage := nsMetrics.CPUUsage
		memoryUsage := nsMetrics.MemoryUsage
		storageUsed := nsMetrics.StorageUsage

		internalRX := (nsMetrics.NetworkRX - nsMetrics.ExternalRX) * hours * 3600
		internalTX := (nsMetrics.NetworkTX - nsMetrics.ExternalTX) * hours * 3600
		externalRX := nsMetrics.ExternalRX * hours * 3600
		externalTX := nsMetrics.ExternalTX * hours * 3600
		externalNetworkTotal := externalRX + externalTX

		if internalRX < 0 {
			internalRX = 0
		}
		if internalTX < 0 {
			internalTX = 0
		}

		customFactor := 1.0
		if env, ok := ns.Labels["environment"]; ok {
			if factor, exists := c.cfg.CustomFactors[env]; exists {
				customFactor = factor
			}
		}

		cost := CostBreakdown{
			CPU:     cpuUsage * c.cfg.CPUPerCoreHour * hours * customFactor,
			Memory:  memoryUsage * c.cfg.MemoryPerGBHour * hours * customFactor,
			Storage: storageUsed * c.cfg.StoragePerGBHour * hours * customFactor,
			Network: externalNetworkTotal * c.cfg.NetworkPerGB * customFactor,
		}
		cost.Total = cost.CPU + cost.Memory + cost.Storage + cost.Network

		results = append(results, NamespaceCost{
			Namespace:    ns.Name,
			Labels:       ns.Labels,
			Cost:         cost,
			CustomFactor: customFactor,
			ResourceUsage: ResourceUsage{
				CPUCores:          cpuUsage,
				MemoryGB:          memoryUsage,
				StorageUsedGB:     storageUsed,
				StorageCapacityGB: storageCapacity,
				NetworkInternalRX: internalRX,
				NetworkInternalTX: internalTX,
				NetworkExternalRX: externalRX,
				NetworkExternalTX: externalTX,
				CPURequestCores:   cpuRequest,
				MemoryRequestGB:   memoryRequest,
			},
		})
	}

	return results, nil
}

func (c *Calculator) DetectResourceContention(ctx context.Context, duration time.Duration, namespaceCosts []NamespaceCost) ([]ResourceContention, error) {
	contentionMetrics, err := c.promClient.GetAllNamespacesContention(ctx, duration)
	if err != nil {
		return nil, err
	}

	contentionMap := make(map[string]promclient.ContentionMetrics)
	for _, cm := range contentionMetrics {
		contentionMap[cm.Namespace] = cm
	}

	nsCostMap := make(map[string]NamespaceCost)
	for _, nc := range namespaceCosts {
		nsCostMap[nc.Namespace] = nc
	}

	var results []ResourceContention
	for namespace, cm := range contentionMap {
		nc := nsCostMap[namespace]

		var contentionScore float64
		throttlingRatio := 0.0
		if nc.ResourceUsage.CPUCores > 0 {
			throttlingRatio = cm.CPUThrottledTime / (nc.ResourceUsage.CPUCores * duration.Hours() * 3600)
		}

		contentionScore = throttlingRatio*0.6 + float64(cm.MemoryOOMCount)*0.1
		if contentionScore > 1.0 {
			contentionScore = 1.0
		}

		contentionLevel := "low"
		if contentionScore >= 0.5 {
			contentionLevel = "high"
		} else if contentionScore >= 0.2 {
			contentionLevel = "medium"
		}

		recommendedCPU := nc.ResourceUsage.CPURequestCores
		recommendedMemory := nc.ResourceUsage.MemoryRequestGB

		if contentionLevel != "low" {
			recommendedCPU = nc.ResourceUsage.CPUCores * 1.5
			if recommendedCPU < nc.ResourceUsage.CPURequestCores {
				recommendedCPU = nc.ResourceUsage.CPURequestCores * 1.2
			}

			recommendedMemory = nc.ResourceUsage.MemoryGB * 1.5
			if recommendedMemory < nc.ResourceUsage.MemoryRequestGB {
				recommendedMemory = nc.ResourceUsage.MemoryRequestGB * 1.2
			}
		}

		results = append(results, ResourceContention{
			Namespace:         namespace,
			CPUThrottledTime:  cm.CPUThrottledTime,
			MemoryOOMCount:    cm.MemoryOOMCount,
			ContentionScore:   contentionScore,
			RecommendedCPU:    recommendedCPU,
			RecommendedMemory: recommendedMemory,
			ContentionLevel:   contentionLevel,
		})
	}

	sort.Slice(results, func(i, j int) bool {
		return results[i].ContentionScore > results[j].ContentionScore
	})

	return results, nil
}

func (c *Calculator) CalculateProjectCosts(ctx context.Context, namespaceCosts []NamespaceCost, projectLabel string) []ProjectCost {
	projectMap := make(map[string]*ProjectCost)

	for _, nc := range namespaceCosts {
		project := nc.Labels[projectLabel]
		if project == "" {
			project = "unknown"
		}

		if _, exists := projectMap[project]; !exists {
			projectMap[project] = &ProjectCost{
				ProjectName: project,
			}
		}

		pc := projectMap[project]
		pc.Namespaces = append(pc.Namespaces, nc.Namespace)
		pc.Cost.CPU += nc.Cost.CPU
		pc.Cost.Memory += nc.Cost.Memory
		pc.Cost.Storage += nc.Cost.Storage
		pc.Cost.Network += nc.Cost.Network
		pc.Cost.Total += nc.Cost.Total
	}

	var results []ProjectCost
	for _, pc := range projectMap {
		results = append(results, *pc)
	}

	sort.Slice(results, func(i, j int) bool {
		return results[i].Cost.Total > results[j].Cost.Total
	})

	return results
}

func (c *Calculator) CalculateLabelCosts(ctx context.Context, namespaceCosts []NamespaceCost, labelKey string) []LabelCost {
	labelMap := make(map[string]*LabelCost)

	for _, nc := range namespaceCosts {
		labelValue := nc.Labels[labelKey]
		if labelValue == "" {
			continue
		}

		key := labelValue
		if _, exists := labelMap[key]; !exists {
			labelMap[key] = &LabelCost{
				LabelKey:   labelKey,
				LabelValue: labelValue,
			}
		}

		lc := labelMap[key]
		lc.Namespaces = append(lc.Namespaces, nc.Namespace)
		lc.Cost.CPU += nc.Cost.CPU
		lc.Cost.Memory += nc.Cost.Memory
		lc.Cost.Storage += nc.Cost.Storage
		lc.Cost.Network += nc.Cost.Network
		lc.Cost.Total += nc.Cost.Total
	}

	var results []LabelCost
	for _, lc := range labelMap {
		results = append(results, *lc)
	}

	sort.Slice(results, func(i, j int) bool {
		return results[i].Cost.Total > results[j].Cost.Total
	})

	return results
}

func (c *Calculator) DetectIdleResources(ctx context.Context, namespaceCosts []NamespaceCost) []IdleResource {
	var idleResources []IdleResource

	for _, nc := range namespaceCosts {
		if nc.ResourceUsage.CPURequestCores > 0 {
			cpuUtilization := nc.ResourceUsage.CPUCores / nc.ResourceUsage.CPURequestCores
			if cpuUtilization < c.cfg.IdleThreshold && nc.ResourceUsage.CPURequestCores > 0.1 {
				idleCPU := nc.ResourceUsage.CPURequestCores - nc.ResourceUsage.CPUCores
				idleResources = append(idleResources, IdleResource{
					Namespace:    nc.Namespace,
					ResourceType: "CPU",
					Requested:    nc.ResourceUsage.CPURequestCores,
					Used:         nc.ResourceUsage.CPUCores,
					IdleAmount:   idleCPU,
					IdleCost:     idleCPU * c.cfg.CPUPerCoreHour * 24 * 30,
					Utilization:  cpuUtilization,
				})
			}
		}

		if nc.ResourceUsage.MemoryRequestGB > 0 {
			memoryUtilization := nc.ResourceUsage.MemoryGB / nc.ResourceUsage.MemoryRequestGB
			if memoryUtilization < c.cfg.IdleThreshold && nc.ResourceUsage.MemoryRequestGB > 0.1 {
				idleMemory := nc.ResourceUsage.MemoryRequestGB - nc.ResourceUsage.MemoryGB
				idleResources = append(idleResources, IdleResource{
					Namespace:    nc.Namespace,
					ResourceType: "Memory",
					Requested:    nc.ResourceUsage.MemoryRequestGB,
					Used:         nc.ResourceUsage.MemoryGB,
					IdleAmount:   idleMemory,
					IdleCost:     idleMemory * c.cfg.MemoryPerGBHour * 24 * 30,
					Utilization:  memoryUtilization,
				})
			}
		}
	}

	sort.Slice(idleResources, func(i, j int) bool {
		return idleResources[i].IdleCost > idleResources[j].IdleCost
	})

	return idleResources
}

func (c *Calculator) PredictCosts(ctx context.Context, namespace string, duration time.Duration) (*CostPrediction, error) {
	end := time.Now()
	start := end.Add(-duration)
	step := 24 * time.Hour

	historical, err := c.promClient.GetHistoricalMetrics(ctx, namespace, start, end, step)
	if err != nil {
		return nil, err
	}

	cpuData := historical["cpu"]
	memoryData := historical["memory"]

	if len(cpuData) < 7 {
		return &CostPrediction{
			Namespace:        namespace,
			CurrentCost:      0,
			PredictedCost30D: 0,
			PredictedCost90D: 0,
			GrowthRate:       0,
		}, nil
	}

	var avgCPU, avgMemory float64
	for _, d := range cpuData {
		avgCPU += d.Value
	}
	for _, d := range memoryData {
		avgMemory += d.Value
	}
	avgCPU /= float64(len(cpuData))
	avgMemory /= float64(len(memoryData))

	var growthRate float64
	if len(cpuData) >= 14 {
		firstHalf := cpuData[:len(cpuData)/2]
		secondHalf := cpuData[len(cpuData)/2:]
		firstAvg := 0.0
		secondAvg := 0.0
		for _, d := range firstHalf {
			firstAvg += d.Value
		}
		for _, d := range secondHalf {
			secondAvg += d.Value
		}
		firstAvg /= float64(len(firstHalf))
		secondAvg /= float64(len(secondHalf))
		if firstAvg > 0 {
			growthRate = (secondAvg - firstAvg) / firstAvg
		}
	}

	dailyCost := (avgCPU*c.cfg.CPUPerCoreHour + avgMemory*c.cfg.MemoryPerGBHour) * 24
	currentMonthlyCost := dailyCost * 30
	predicted30D := currentMonthlyCost * (1 + growthRate)
	predicted90D := currentMonthlyCost * math.Pow(1+growthRate, 3)

	return &CostPrediction{
		Namespace:        namespace,
		CurrentCost:      currentMonthlyCost,
		PredictedCost30D: predicted30D,
		PredictedCost90D: predicted90D,
		GrowthRate:       growthRate,
	}, nil
}

func (c *Calculator) GetOptimizationSuggestions(ctx context.Context, idleResources []IdleResource, namespaceCosts []NamespaceCost, contentions []ResourceContention) []OptimizationSuggestion {
	var suggestions []OptimizationSuggestion

	for _, ir := range idleResources {
		severity := "low"
		if ir.IdleCost > 100 {
			severity = "high"
		} else if ir.IdleCost > 20 {
			severity = "medium"
		}

		suggestions = append(suggestions, OptimizationSuggestion{
			Namespace:        ir.Namespace,
			Type:             "resource-rightsizing",
			Description:      ir.ResourceType + " utilization is " + formatPercent(ir.Utilization) + ", consider reducing requests",
			EstimatedSavings: ir.IdleCost,
			Severity:         severity,
		})
	}

	for _, contention := range contentions {
		if contention.ContentionLevel == "low" {
			continue
		}

		description := fmt.Sprintf("Resource contention detected: CPU throttling detected, OOM events: %d", contention.MemoryOOMCount)
		if contention.ContentionLevel == "high" {
			description += " - HIGH contention level, immediate action recommended"
		}

		suggestions = append(suggestions, OptimizationSuggestion{
			Namespace:        contention.Namespace,
			Type:             "resource-contention",
			Description:      description,
			EstimatedSavings: 0,
			Severity:         contention.ContentionLevel,
		})
	}

	for _, nc := range namespaceCosts {
		if nc.CustomFactor != 1.0 {
			continue
		}
		if env, ok := nc.Labels["environment"]; ok {
			if env == "development" || env == "staging" {
				suggestions = append(suggestions, OptimizationSuggestion{
					Namespace:        nc.Namespace,
					Type:             "environment-tagging",
					Description:      "Namespace is tagged as " + env + " but not using custom cost factor",
					EstimatedSavings: nc.Cost.Total * 0.5,
					Severity:         "low",
				})
			}
		}
	}

	sort.Slice(suggestions, func(i, j int) bool {
		severityOrder := map[string]int{"high": 3, "medium": 2, "low": 1}
		if severityOrder[suggestions[i].Severity] != severityOrder[suggestions[j].Severity] {
			return severityOrder[suggestions[i].Severity] > severityOrder[suggestions[j].Severity]
		}
		return suggestions[i].EstimatedSavings > suggestions[j].EstimatedSavings
	})

	return suggestions
}

func formatPercent(v float64) string {
	return fmt.Sprintf("%.1f%%", v*100)
}
