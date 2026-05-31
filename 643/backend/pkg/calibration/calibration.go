package calibration

import (
	"capacity-planner/pkg/models"
	"math"
)

func getEnvironmentFactors() map[string]models.EnvironmentNormalization {
	return map[string]models.EnvironmentNormalization{
		"dev": {
			EnvType:      "dev",
			CPUFactor:    1.5,
			MemoryFactor: 1.3,
			NetworkFactor: 1.2,
			Description:  "开发环境",
		},
		"staging": {
			EnvType:      "staging",
			CPUFactor:    1.2,
			MemoryFactor: 1.15,
			NetworkFactor: 1.1,
			Description:  "预发环境",
		},
		"production": {
			EnvType:      "production",
			CPUFactor:    1.0,
			MemoryFactor: 1.0,
			NetworkFactor: 1.0,
			Description:  "生产环境",
		},
		"performance": {
			EnvType:      "performance",
			CPUFactor:    1.1,
			MemoryFactor: 1.05,
			NetworkFactor: 1.05,
			Description:  "性能测试环境",
		},
	}
}

func NormalizeEnvironmentData(
	data []models.LoadTestData,
	sourceEnv string,
	targetEnv string,
) []models.LoadTestData {
	factors := getEnvironmentFactors()
	sourceFactor, sourceExists := factors[sourceEnv]
	targetFactor, targetExists := factors[targetEnv]

	if !sourceExists || !targetExists || sourceEnv == targetEnv {
		return data
	}

	normalized := make([]models.LoadTestData, len(data))
	for i, d := range data {
		normalized[i] = models.LoadTestData{
			ServiceID:       d.ServiceID,
			ConcurrentUsers: d.ConcurrentUsers,
			Throughput:      d.Throughput * (sourceFactor.CPUFactor / targetFactor.CPUFactor),
			AvgLatencyMs:    d.AvgLatencyMs * (targetFactor.CPUFactor / sourceFactor.CPUFactor),
			P99LatencyMs:    d.P99LatencyMs * (targetFactor.CPUFactor / sourceFactor.CPUFactor),
			CPUUsage:        d.CPUUsage * (targetFactor.CPUFactor / sourceFactor.CPUFactor),
			MemoryUsage:     d.MemoryUsage * (targetFactor.MemoryFactor / sourceFactor.MemoryFactor),
			ErrorRate:       d.ErrorRate,
			Environment:     targetEnv,
			InstanceType:    d.InstanceType,
			TestDurationSec: d.TestDurationSec,
		}
	}

	return normalized
}

func CalculateEnvironmentFactor(sourceEnv string, targetEnv string) float64 {
	factors := getEnvironmentFactors()
	sourceFactor, sourceExists := factors[sourceEnv]
	targetFactor, targetExists := factors[targetEnv]

	if !sourceExists || !targetExists {
		return 1.0
	}

	avgFactor := (sourceFactor.CPUFactor + sourceFactor.MemoryFactor + sourceFactor.NetworkFactor) / 3.0
	avgTargetFactor := (targetFactor.CPUFactor + targetFactor.MemoryFactor + targetFactor.NetworkFactor) / 3.0

	return avgTargetFactor / avgFactor
}

func CalculateCalibrationFactors(
	loadTestData []models.LoadTestData,
	historicalData []models.PerformanceData,
	targetEnv string,
) map[string]models.CalibrationFactor {
	calibrationMap := make(map[string]models.CalibrationFactor)

	serviceLoadTests := make(map[string][]models.LoadTestData)
	for _, data := range loadTestData {
		sourceEnv := data.Environment
		if sourceEnv == "" {
			sourceEnv = "staging"
		}
		normalizedData := NormalizeEnvironmentData([]models.LoadTestData{data}, sourceEnv, targetEnv)
		serviceLoadTests[data.ServiceID] = append(serviceLoadTests[data.ServiceID], normalizedData[0])
	}

	serviceHistorical := make(map[string][]models.PerformanceData)
	for _, data := range historicalData {
		serviceHistorical[data.ServiceID] = append(serviceHistorical[data.ServiceID], data)
	}

	for serviceID := range serviceLoadTests {
		loadTests := serviceLoadTests[serviceID]
		historical := serviceHistorical[serviceID]

		var cpuCorrection, memoryCorrection, latencyCorrection, throughputCorrection float64
		var normalizationScore float64

		if len(loadTests) > 0 && len(historical) > 0 {
			avgLoadTestCPU := averageLoadTestCPU(loadTests)
			avgHistoricalCPU := averageHistoricalCPU(historical)

			avgLoadTestMemory := averageLoadTestMemory(loadTests)
			avgHistoricalMemory := averageHistoricalMemory(historical)

			avgLoadTestLatency := averageLoadTestLatency(loadTests)
			avgHistoricalLatency := averageHistoricalLatency(historical)

			avgLoadTestThroughput := averageLoadTestThroughput(loadTests)
			avgHistoricalThroughput := averageHistoricalThroughput(historical)

			cpuCorrection = 1.0
			if avgLoadTestCPU > 0 && avgHistoricalCPU > 0 {
				cpuCorrection = avgHistoricalCPU / avgLoadTestCPU
			}

			memoryCorrection = 1.0
			if avgLoadTestMemory > 0 && avgHistoricalMemory > 0 {
				memoryCorrection = avgHistoricalMemory / avgLoadTestMemory
			}

			latencyCorrection = 1.0
			if avgLoadTestLatency > 0 && avgHistoricalLatency > 0 {
				latencyCorrection = avgHistoricalLatency / avgLoadTestLatency
			}

			throughputCorrection = 1.0
			if avgHistoricalThroughput > 0 && avgLoadTestThroughput > 0 {
				throughputCorrection = avgHistoricalThroughput / avgLoadTestThroughput
			}

			normalizationScore = calculateNormalizationScore(
				cpuCorrection,
				memoryCorrection,
				latencyCorrection,
				throughputCorrection,
			)
		} else {
			cpuCorrection = 1.2
			memoryCorrection = 1.15
			latencyCorrection = 1.25
			throughputCorrection = 0.9
			normalizationScore = 0.7
		}

		cpuCorrection = clamp(cpuCorrection, 0.5, 2.5)
		memoryCorrection = clamp(memoryCorrection, 0.5, 2.5)
		latencyCorrection = clamp(latencyCorrection, 0.5, 3.0)
		throughputCorrection = clamp(throughputCorrection, 0.5, 1.5)

		environmentFactor := CalculateEnvironmentFactor("staging", targetEnv)

		calibrationMap[serviceID] = models.CalibrationFactor{
			ServiceID:           serviceID,
			CPUCorrection:       cpuCorrection,
			MemoryCorrection:    memoryCorrection,
			LatencyCorrection:   latencyCorrection,
			ThroughputCorrection: throughputCorrection,
			EnvironmentFactor:   environmentFactor,
			NormalizationScore:  normalizationScore,
		}
	}

	return calibrationMap
}

func calculateNormalizationScore(factors ...float64) float64 {
	if len(factors) == 0 {
		return 0
	}

	variance := 0.0
	mean := 0.0
	for _, f := range factors {
		mean += f
	}
	mean /= float64(len(factors))

	for _, f := range factors {
		variance += math.Pow(f-mean, 2)
	}
	variance /= float64(len(factors))

	stdDev := math.Sqrt(variance)
	score := 1.0 / (1.0 + stdDev)

	return score
}

func averageLoadTestCPU(data []models.LoadTestData) float64 {
	if len(data) == 0 {
		return 0
	}
	sum := 0.0
	for _, d := range data {
		sum += d.CPUUsage
	}
	return sum / float64(len(data))
}

func averageHistoricalCPU(data []models.PerformanceData) float64 {
	if len(data) == 0 {
		return 0
	}
	sum := 0.0
	for _, d := range data {
		sum += d.CPUUsage
	}
	return sum / float64(len(data))
}

func averageLoadTestMemory(data []models.LoadTestData) float64 {
	if len(data) == 0 {
		return 0
	}
	sum := 0.0
	for _, d := range data {
		sum += d.MemoryUsage
	}
	return sum / float64(len(data))
}

func averageHistoricalMemory(data []models.PerformanceData) float64 {
	if len(data) == 0 {
		return 0
	}
	sum := 0.0
	for _, d := range data {
		sum += d.MemoryUsage
	}
	return sum / float64(len(data))
}

func averageLoadTestLatency(data []models.LoadTestData) float64 {
	if len(data) == 0 {
		return 0
	}
	sum := 0.0
	for _, d := range data {
		sum += d.AvgLatencyMs
	}
	return sum / float64(len(data))
}

func averageHistoricalLatency(data []models.PerformanceData) float64 {
	if len(data) == 0 {
		return 0
	}
	sum := 0.0
	for _, d := range data {
		sum += d.AvgLatencyMs
	}
	return sum / float64(len(data))
}

func averageLoadTestThroughput(data []models.LoadTestData) float64 {
	if len(data) == 0 {
		return 0
	}
	sum := 0.0
	for _, d := range data {
		sum += d.Throughput
	}
	return sum / float64(len(data))
}

func averageHistoricalThroughput(data []models.PerformanceData) float64 {
	if len(data) == 0 {
		return 0
	}
	sum := 0.0
	for _, d := range data {
		sum += d.RequestsPerSec
	}
	return sum / float64(len(data))
}

func clamp(value, min, max float64) float64 {
	return math.Max(min, math.Min(max, value))
}

func ApplyCalibration(
	result models.CapacityResult,
	factor models.CalibrationFactor,
) models.CapacityResult {
	result.EstimatedCPUUsage *= factor.CPUCorrection * factor.EnvironmentFactor
	result.EstimatedMemoryUsage *= factor.MemoryCorrection * factor.EnvironmentFactor
	result.EstimatedLatencyMs *= factor.LatencyCorrection * factor.EnvironmentFactor
	result.Utilization *= factor.CPUCorrection

	result.EstimatedCPUUsage = math.Min(result.EstimatedCPUUsage, 100)
	result.EstimatedMemoryUsage = math.Min(result.EstimatedMemoryUsage, 100)

	if result.EstimatedCPUUsage > 90 || result.EstimatedMemoryUsage > 90 {
		additionalServers := 0
		if result.EstimatedCPUUsage > 90 {
			additionalServers = int(math.Ceil(result.EstimatedCPUUsage / 70))
		}
		if result.EstimatedMemoryUsage > 90 {
			memServers := int(math.Ceil(result.EstimatedMemoryUsage / 70))
			if memServers > additionalServers {
				additionalServers = memServers
			}
		}
		if additionalServers > result.RecommendedServers {
			oldServers := result.RecommendedServers
			result.RecommendedServers = additionalServers
			result.RequiredServers = additionalServers

			costRatio := float64(additionalServers) / float64(oldServers)
			result.MonthlyCost *= costRatio
			result.Breakdown.ComputeCost *= costRatio
			result.Breakdown.TotalCost *= costRatio
		}
	}

	return result
}

func EstimateMaxThroughput(loadTestData []models.LoadTestData, serviceID string, targetEnv string) float64 {
	serviceData := make([]models.LoadTestData, 0)
	for _, d := range loadTestData {
		if d.ServiceID == serviceID {
			serviceData = append(serviceData, d)
		}
	}

	if len(serviceData) == 0 {
		return 100
	}

	maxThroughput := 0.0
	for _, d := range serviceData {
		if d.ErrorRate < 0.05 && d.Throughput > maxThroughput {
			maxThroughput = d.Throughput
		}
	}

	if maxThroughput == 0 {
		for _, d := range serviceData {
			if d.Throughput > maxThroughput {
				maxThroughput = d.Throughput
			}
		}
	}

	envFactor := CalculateEnvironmentFactor("staging", targetEnv)
	adjustedThroughput := maxThroughput * 0.8 * envFactor

	return adjustedThroughput
}

func CalculateInstanceTypeCorrection(sourceInstance string, targetInstance string) float64 {
	instanceFactors := map[string]float64{
		"t2.micro":   0.5,
		"t2.small":   0.7,
		"t2.medium":  1.0,
		"t2.large":   1.5,
		"t2.xlarge":  2.5,
		"c5.large":   1.8,
		"c5.xlarge":  3.0,
		"c5.2xlarge": 5.5,
		"m5.large":   1.6,
		"m5.xlarge":  2.8,
		"m5.2xlarge": 5.0,
		"r5.large":   1.4,
		"r5.xlarge":  2.5,
	}

	sourceFactor, sourceExists := instanceFactors[sourceInstance]
	targetFactor, targetExists := instanceFactors[targetInstance]

	if !sourceExists || !targetExists {
		return 1.0
	}

	return targetFactor / sourceFactor
}
