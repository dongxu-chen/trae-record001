package queueing

import (
	"capacity-planner/pkg/models"
	"math"
)

type MMCResult struct {
	ArrivalRate       float64
	ServiceRate       float64
	Servers           int
	Utilization       float64
	ProbEmpty         float64
	AvgQueueLength    float64
	AvgSystemLength   float64
	AvgWaitTime       float64
	AvgSystemTime     float64
	ProbWait          float64
}

func CalculateMMC(arrivalRate, serviceRate float64, servers int) MMCResult {
	if servers <= 0 {
		servers = 1
	}
	if serviceRate <= 0 {
		serviceRate = 1
	}

	rho := arrivalRate / (float64(servers) * serviceRate)

	if rho >= 1.0 {
		return MMCResult{
			ArrivalRate:     arrivalRate,
			ServiceRate:     serviceRate,
			Servers:         servers,
			Utilization:     1.0,
			AvgQueueLength:  math.Inf(1),
			AvgSystemLength: math.Inf(1),
			AvgWaitTime:     math.Inf(1),
			AvgSystemTime:   math.Inf(1),
			ProbWait:        1.0,
		}
	}

	p0 := calculateP0(arrivalRate, serviceRate, servers)

	term1 := math.Pow(arrivalRate/serviceRate, float64(servers))
	term2 := servers * serviceRate
	term3 := 1.0 / (math.Pow(1.0-rho, 2))
	lq := (term1 * rho * p0) / (float64(factorial(servers-1)) * term3)
	if math.IsNaN(lq) || lq < 0 {
		lq = 0
	}

	l := lq + arrivalRate/serviceRate

	wq := lq / arrivalRate
	if arrivalRate == 0 {
		wq = 0
	}

	w := wq + 1.0/serviceRate

	probWait := calculateErlangC(arrivalRate, serviceRate, servers)

	return MMCResult{
		ArrivalRate:       arrivalRate,
		ServiceRate:       serviceRate,
		Servers:           servers,
		Utilization:       rho,
		ProbEmpty:         p0,
		AvgQueueLength:    lq,
		AvgSystemLength:   l,
		AvgWaitTime:       wq,
		AvgSystemTime:     w,
		ProbWait:          probWait,
	}
}

func calculateP0(arrivalRate, serviceRate float64, servers int) float64 {
	sum := 0.0
	a := arrivalRate / serviceRate

	for k := 0; k < servers; k++ {
		sum += math.Pow(a, float64(k)) / float64(factorial(k))
	}

	term := math.Pow(a, float64(servers)) / float64(factorial(servers))
	term = term / (1.0 - a/float64(servers))

	return 1.0 / (sum + term)
}

func calculateErlangC(arrivalRate, serviceRate float64, servers int) float64 {
	a := arrivalRate / serviceRate
	rho := a / float64(servers)

	if rho >= 1.0 {
		return 1.0
	}

	num := math.Pow(a, float64(servers)) / float64(factorial(servers))
	num = num / (1.0 - rho)

	denom := 0.0
	for k := 0; k < servers; k++ {
		denom += math.Pow(a, float64(k)) / float64(factorial(k))
	}
	denom += num

	return num / denom
}

func factorial(n int) int {
	if n <= 1 {
		return 1
	}
	result := 1
	for i := 2; i <= n; i++ {
		result *= i
	}
	return result
}

func FindMinServers(arrivalRate, serviceRate, maxLatency float64, targetUtilization float64) int {
	if arrivalRate <= 0 {
		return 1
	}

	minServers := int(math.Ceil(arrivalRate / serviceRate))
	if minServers < 1 {
		minServers = 1
	}

	for servers := minServers; servers <= 1000; servers++ {
		result := CalculateMMC(arrivalRate, serviceRate, servers)

		latencyOK := maxLatency <= 0 || result.AvgSystemTime*1000 <= maxLatency
		utilizationOK := targetUtilization <= 0 || result.Utilization <= targetUtilization

		if latencyOK && utilizationOK {
			return servers
		}
	}

	return 1000
}

func CalculateCapacity(
	serviceID string,
	peakTraffic float64,
	serverConfig models.ServerConfig,
	targetUtilization float64,
	maxLatency float64,
) models.CapacityResult {
	arrivalRate := peakTraffic
	serviceRate := serverConfig.MaxRequestsPerSec

	requiredServers := FindMinServers(arrivalRate, serviceRate, maxLatency, targetUtilization)

	recommendedServers := requiredServers
	if recommendedServers < 2 {
		recommendedServers = 2
	}

	mmcResult := CalculateMMC(arrivalRate, serviceRate, recommendedServers)

	estimatedCPU := mmcResult.Utilization * 100
	estimatedMemory := math.Min(mmcResult.Utilization*1.1, 1.0) * 100
	estimatedLatency := mmcResult.AvgSystemTime * 1000

	hoursPerMonth := 24.0 * 30.0
	monthlyCost := float64(recommendedServers) * serverConfig.CostPerHour * hoursPerMonth

	breakdown := models.CostBreakdown{
		ComputeCost: monthlyCost * 0.7,
		StorageCost: monthlyCost * 0.15,
		NetworkCost: monthlyCost * 0.1,
		LaborCost:   monthlyCost * 0.05,
		TotalCost:   monthlyCost,
	}

	return models.CapacityResult{
		ServiceID:           serviceID,
		ServerConfig:        serverConfig,
		RequiredServers:     requiredServers,
		RecommendedServers:  recommendedServers,
		EstimatedCPUUsage:   estimatedCPU,
		EstimatedMemoryUsage: estimatedMemory,
		EstimatedLatencyMs:  estimatedLatency,
		QueueLength:         mmcResult.AvgQueueLength,
		Utilization:         mmcResult.Utilization,
		MonthlyCost:         monthlyCost,
		Breakdown:           breakdown,
	}
}

func OptimizeServerConfig(
	peakTraffic float64,
	serverConfigs []models.ServerConfig,
	targetUtilization float64,
	maxLatency float64,
) (models.ServerConfig, models.CapacityResult) {
	if len(serverConfigs) == 0 {
		defaultConfig := models.ServerConfig{
			ID:               "default",
			Name:             "Default",
			CPUCores:         4,
			MemoryGB:         8,
			CostPerHour:      0.5,
			MaxRequestsPerSec: 100,
		}
		return defaultConfig, CalculateCapacity("default", peakTraffic, defaultConfig, targetUtilization, maxLatency)
	}

	bestCost := math.Inf(1)
	bestConfig := serverConfigs[0]
	bestResult := models.CapacityResult{}

	for _, config := range serverConfigs {
		result := CalculateCapacity("opt", peakTraffic, config, targetUtilization, maxLatency)

		if result.MonthlyCost < bestCost && result.RequiredServers > 0 {
			bestCost = result.MonthlyCost
			bestConfig = config
			bestResult = result
		}
	}

	return bestConfig, bestResult
}
