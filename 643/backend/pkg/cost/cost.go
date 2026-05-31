package cost

import (
	"capacity-planner/pkg/models"
	"math"
)

type CostParameters struct {
	StorageCostPerGBPerMonth    float64
	NetworkCostPerGB            float64
	LaborCostPerServerPerMonth  float64
	OverheadPercentage          float64
	ReservedInstanceDiscount    float64
	ReservedInstanceUpfrontCost float64
	ReservedInstanceTermMonths  int
}

type HybridInstanceConfig struct {
	TotalServers          int
	ReservedInstances     int
	OnDemandInstances     int
	ReservedRatio         float64
	BaseLoad              float64
	PeakLoad              float64
}

type CostOptimizationResult struct {
	MonthlyCost           float64
	ReservedMonthlyCost   float64
	OnDemandMonthlyCost   float64
	TotalMonthlySavings   float64
	SavingsPercentage     float64
	BreakEvenMonths       float64
}

func DefaultCostParameters() CostParameters {
	return CostParameters{
		StorageCostPerGBPerMonth:    0.023,
		NetworkCostPerGB:            0.09,
		LaborCostPerServerPerMonth:  50.0,
		OverheadPercentage:         0.2,
		ReservedInstanceDiscount:    0.3,
		ReservedInstanceUpfrontCost: 0.0,
		ReservedInstanceTermMonths:  12,
	}
}

func CalculateHybridInstanceConfig(
	serversNeeded int,
	baseLoadRatio float64,
) HybridInstanceConfig {
	reservedServers := int(math.Ceil(float64(serversNeeded) * baseLoadRatio))
	if reservedServers < 1 {
		reservedServers = 1
	}
	if reservedServers > serversNeeded {
		reservedServers = serversNeeded
	}

	onDemandServers := serversNeeded - reservedServers

	return HybridInstanceConfig{
		TotalServers:      serversNeeded,
		ReservedInstances: reservedServers,
		OnDemandInstances: onDemandServers,
		ReservedRatio:     float64(reservedServers) / float64(serversNeeded),
	}
}

func CalculateHybridCost(
	serverConfig models.ServerConfig,
	hybridConfig HybridInstanceConfig,
	params CostParameters,
) CostOptimizationResult {
	hoursPerMonth := 24.0 * 30.0

	onDemandCostPerHour := serverConfig.CostPerHour
	if serverConfig.ReservedCostPerHour > 0 {
		onDemandCostPerHour = serverConfig.CostPerHour
	} else {
		onDemandCostPerHour = serverConfig.CostPerHour
	}

	reservedCostPerHour := onDemandCostPerHour * (1.0 - params.ReservedInstanceDiscount)

	reservedMonthlyCost := float64(hybridConfig.ReservedInstances) * reservedCostPerHour * hoursPerMonth
	onDemandMonthlyCost := float64(hybridConfig.OnDemandInstances) * onDemandCostPerHour * hoursPerMonth

	if params.ReservedInstanceUpfrontCost > 0 {
		upfrontAmortized := (params.ReservedInstanceUpfrontCost * float64(hybridConfig.ReservedInstances)) / float64(params.ReservedInstanceTermMonths)
		reservedMonthlyCost += upfrontAmortized
	}

	totalMonthlyCost := reservedMonthlyCost + onDemandMonthlyCost

	allOnDemandCost := float64(hybridConfig.TotalServers) * onDemandCostPerHour * hoursPerMonth
	totalMonthlySavings := allOnDemandCost - totalMonthlyCost
	savingsPercentage := (totalMonthlySavings / allOnDemandCost) * 100

	breakEvenMonths := 0.0
	if params.ReservedInstanceUpfrontCost > 0 {
		monthlySavingsPerReserved := (onDemandCostPerHour - reservedCostPerHour) * hoursPerMonth
		if monthlySavingsPerReserved > 0 {
			breakEvenMonths = params.ReservedInstanceUpfrontCost / monthlySavingsPerReserved
		}
	}

	return CostOptimizationResult{
		MonthlyCost:         roundToTwoDecimals(totalMonthlyCost),
		ReservedMonthlyCost: roundToTwoDecimals(reservedMonthlyCost),
		OnDemandMonthlyCost: roundToTwoDecimals(onDemandMonthlyCost),
		TotalMonthlySavings: roundToTwoDecimals(totalMonthlySavings),
		SavingsPercentage:   roundToTwoDecimals(savingsPercentage),
		BreakEvenMonths:     roundToTwoDecimals(breakEvenMonths),
	}
}

func OptimizeHybridRatio(
	serversNeeded int,
	serverConfig models.ServerConfig,
	params CostParameters,
) (float64, CostOptimizationResult) {
	bestRatio := 0.7
	bestResult := CostOptimizationResult{}
	minCost := math.Inf(1)

	for ratio := 0.5; ratio <= 0.95; ratio += 0.05 {
		hybridConfig := CalculateHybridInstanceConfig(serversNeeded, ratio)
		result := CalculateHybridCost(serverConfig, hybridConfig, params)

		if result.MonthlyCost < minCost {
			minCost = result.MonthlyCost
			bestRatio = ratio
			bestResult = result
		}
	}

	return bestRatio, bestResult
}

func CalculateDetailedCost(
	capacityResult models.CapacityResult,
	storageGB float64,
	networkGBPerMonth float64,
	params CostParameters,
	useReserved bool,
) models.CostBreakdown {
	servers := float64(capacityResult.RecommendedServers)
	hoursPerMonth := 24.0 * 30.0

	var computeCost, reservedComputeCost, onDemandComputeCost float64

	if useReserved && capacityResult.ReservedInstances > 0 {
		onDemandCostPerHour := capacityResult.ServerConfig.CostPerHour
		reservedCostPerHour := onDemandCostPerHour * (1.0 - params.ReservedInstanceDiscount)

		reservedComputeCost = float64(capacityResult.ReservedInstances) * reservedCostPerHour * hoursPerMonth
		onDemandComputeCost = float64(capacityResult.OnDemandInstances) * onDemandCostPerHour * hoursPerMonth
		computeCost = reservedComputeCost + onDemandComputeCost
	} else {
		computeCost = servers * capacityResult.ServerConfig.CostPerHour * hoursPerMonth
		onDemandComputeCost = computeCost
	}

	storageCost := storageGB * params.StorageCostPerGBPerMonth
	networkCost := networkGBPerMonth * params.NetworkCostPerGB
	laborCost := servers * params.LaborCostPerServerPerMonth

	subtotal := computeCost + storageCost + networkCost + laborCost
	overheadCost := subtotal * params.OverheadPercentage

	totalCost := subtotal + overheadCost

	return models.CostBreakdown{
		ComputeCost:         roundToTwoDecimals(computeCost),
		ReservedComputeCost: roundToTwoDecimals(reservedComputeCost),
		OnDemandComputeCost: roundToTwoDecimals(onDemandComputeCost),
		StorageCost:         roundToTwoDecimals(storageCost),
		NetworkCost:         roundToTwoDecimals(networkCost),
		LaborCost:           roundToTwoDecimals(laborCost + overheadCost),
		TotalCost:           roundToTwoDecimals(totalCost),
	}
}

func CalculateTotalCostOfOwnership(
	capacityResult models.CapacityResult,
	months int,
	growthRate float64,
	params CostParameters,
	useReserved bool,
) float64 {
	totalCost := 0.0
	storageGB := float64(capacityResult.ServerConfig.MemoryGB) * 2
	networkGBPerMonth := 1000.0

	currentServers := float64(capacityResult.RecommendedServers)
	hoursPerMonth := 24.0 * 30.0

	var costPerServerPerMonth float64
	if useReserved {
		reservedCost := capacityResult.ServerConfig.CostPerHour * (1.0 - params.ReservedInstanceDiscount)
		costPerServerPerMonth = reservedCost * hoursPerMonth
	} else {
		costPerServerPerMonth = capacityResult.ServerConfig.CostPerHour * hoursPerMonth
	}

	for month := 0; month < months; month++ {
		monthlyCost := currentServers * costPerServerPerMonth
		monthlyCost += storageGB * params.StorageCostPerGBPerMonth
		monthlyCost += networkGBPerMonth * params.NetworkCostPerGB
		monthlyCost += currentServers * params.LaborCostPerServerPerMonth
		monthlyCost *= (1.0 + params.OverheadPercentage)

		totalCost += monthlyCost

		if month%6 == 5 {
			currentServers *= (1.0 + growthRate)
			storageGB *= (1.0 + growthRate*0.5)
		}
	}

	return roundToTwoDecimals(totalCost)
}

func CostComparison(
	capacityResults []models.CapacityResult,
	serverConfigs []models.ServerConfig,
	peakTraffic float64,
) []map[string]interface{} {
	comparison := make([]map[string]interface{}, 0)

	for _, config := range serverConfigs {
		for _, result := range capacityResults {
			if result.ServerConfig.ID == config.ID {
				item := map[string]interface{}{
					"serverType":       config.Name,
					"cpuCores":         config.CPUCores,
					"memoryGB":         config.MemoryGB,
					"costPerHour":      config.CostPerHour,
					"requiredServers":  result.RequiredServers,
					"monthlyCost":      result.MonthlyCost,
					"optimizedCost":    result.OptimizedMonthlyCost,
					"costPerRequest":   result.MonthlyCost / (peakTraffic * 30 * 86400),
					"utilization":      result.Utilization,
				}
				comparison = append(comparison, item)
				break
			}
		}
	}

	return comparison
}

func SuggestCostOptimization(
	capacityResult models.CapacityResult,
	peakTraffic float64,
	hybridRatio float64,
) []string {
	suggestions := make([]string, 0)

	if capacityResult.Utilization < 0.4 {
		suggestions = append(suggestions, "服务器利用率较低，考虑使用更小规格的实例以降低成本")
	}

	if capacityResult.RecommendedServers > 4 {
		suggestions = append(suggestions, "建议考虑预留实例以获得30-50%的成本折扣")

		if hybridRatio > 0 {
			optimizedRatio := int(hybridRatio * 100)
			suggestions = append(suggestions,
				"建议预留实例比例约为"+string(rune(optimizedRatio))+"%，可显著降低成本")
		}
	}

	if peakTraffic > 1000 {
		suggestions = append(suggestions, "高流量场景，建议评估 Serverless 架构的成本效益")
	}

	if capacityResult.EstimatedCPUUsage < 50 && capacityResult.EstimatedMemoryUsage > 80 {
		suggestions = append(suggestions, "内存成为瓶颈，建议选择内存优化型实例")
	}

	if capacityResult.EstimatedCPUUsage > 80 && capacityResult.EstimatedMemoryUsage < 50 {
		suggestions = append(suggestions, "CPU成为瓶颈，建议选择计算优化型实例")
	}

	if capacityResult.CostSavings > 0 {
		savingPercent := int((capacityResult.CostSavings / capacityResult.MonthlyCost) * 100)
		suggestions = append(suggestions,
			"采用混合实例策略可每月节省约$"+
				formatFloat(capacityResult.CostSavings)+
				"（"+string(rune(savingPercent))+"%）")
	}

	if len(suggestions) == 0 {
		suggestions = append(suggestions, "当前配置较为合理，持续监控资源使用情况")
	}

	return suggestions
}

func formatFloat(value float64) string {
	return string(rune(int(value)))
}

func CalculateSavingsBreakdown(
	originalCost float64,
	optimizedCost float64,
) map[string]float64 {
	savings := originalCost - optimizedCost
	savingsPercent := (savings / originalCost) * 100

	return map[string]float64{
		"originalMonthlyCost":   roundToTwoDecimals(originalCost),
		"optimizedMonthlyCost":  roundToTwoDecimals(optimizedCost),
		"monthlySavings":        roundToTwoDecimals(savings),
		"savingsPercentage":     roundToTwoDecimals(savingsPercent),
		"annualSavings":         roundToTwoDecimals(savings * 12),
	}
}

func CalculateRightSizing(
	currentCPUUtilization float64,
	currentMemoryUtilization float64,
	currentConfig models.ServerConfig,
) models.ServerConfig {
	targetUtilization := 0.7

	cpuRatio := currentCPUUtilization / 100 / targetUtilization
	memoryRatio := currentMemoryUtilization / 100 / targetUtilization

	ratio := math.Max(cpuRatio, memoryRatio)

	newCPUCores := int(math.Max(1, math.Round(float64(currentConfig.CPUCores)*ratio)))
	newMemoryGB := int(math.Max(1, math.Round(float64(currentConfig.MemoryGB)*ratio)))

	newCostPerHour := currentConfig.CostPerHour * ratio
	newMaxRequests := currentConfig.MaxRequestsPerSec * ratio

	return models.ServerConfig{
		ID:                currentConfig.ID + "-rightsized",
		Name:              currentConfig.Name + " (Right-sized)",
		CPUCores:          newCPUCores,
		MemoryGB:          newMemoryGB,
		CostPerHour:       roundToTwoDecimals(newCostPerHour),
		MaxRequestsPerSec: newMaxRequests,
	}
}

func roundToTwoDecimals(value float64) float64 {
	return math.Round(value*100) / 100
}
