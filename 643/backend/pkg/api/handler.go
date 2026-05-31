package api

import (
	"capacity-planner/pkg/calibration"
	"capacity-planner/pkg/cost"
	"capacity-planner/pkg/dependency"
	"capacity-planner/pkg/forecast"
	"capacity-planner/pkg/models"
	"capacity-planner/pkg/queueing"
	"net/http"
	"time"

	"github.com/gin-gonic/gin"
)

type Handler struct{}

func NewHandler() *Handler {
	return &Handler{}
}

func (h *Handler) EvaluateCapacity(c *gin.Context) {
	var req models.EvaluationRequest
	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
		return
	}

	if req.ReservedInstanceRatio <= 0 {
		req.ReservedInstanceRatio = 0.7
	}
	if req.Environment == "" {
		req.Environment = "production"
	}
	if req.AvailabilityTarget <= 0 {
		req.AvailabilityTarget = 0.999
	}

	trafficForecasts := h.generateTrafficForecasts(req)

	targetEnv := req.Environment
	calibrationFactors := calibration.CalculateCalibrationFactors(
		req.LoadTestData,
		req.PerformanceData,
		targetEnv,
	)

	calibrationFactorList := make([]models.CalibrationFactor, 0)
	for _, f := range calibrationFactors {
		calibrationFactorList = append(calibrationFactorList, f)
	}

	peakTrafficMap := make(map[string]float64)
	for _, tf := range trafficForecasts {
		peakTrafficMap[tf.ServiceID] = forecast.CalculatePeakTraffic(tf, 1.2)
	}

	if req.IncludeDependencies {
		graph := dependency.BuildDependencyGraph(req.Services)
		entryTraffic := make(map[string]float64)
		for id, traffic := range peakTrafficMap {
			entryTraffic[id] = traffic
		}

		if req.UseTrafficMatrix {
			tpm := dependency.BuildTrafficPropagationMatrix(graph, req.Services)
			peakTrafficMap = dependency.CalculateTrafficWithMatrix(tpm, entryTraffic)
		} else {
			peakTrafficMap = dependency.CalculateTrafficPropagation(graph, entryTraffic)
		}
	}

	results, totalCost := dependency.CalculateTotalCapacityWithDependencies(
		req.Services,
		peakTrafficMap,
		req.ServerConfigs,
		req.TargetUtilization,
		req.MaxLatencyMs,
		req.UseTrafficMatrix,
	)

	costParams := cost.DefaultCostParameters()
	optimizedTotalCost := 0.0
	totalSavings := 0.0

	for i, result := range results {
		if factor, exists := calibrationFactors[result.ServiceID]; exists {
			results[i] = calibration.ApplyCalibration(result, factor)
		}

		hybridConfig := cost.CalculateHybridInstanceConfig(
			results[i].RecommendedServers,
			req.ReservedInstanceRatio,
		)

		results[i].ReservedInstances = hybridConfig.ReservedInstances
		results[i].OnDemandInstances = hybridConfig.OnDemandInstances

		optimizationResult := cost.CalculateHybridCost(
			results[i].ServerConfig,
			hybridConfig,
			costParams,
		)

		results[i].OptimizedMonthlyCost = optimizationResult.MonthlyCost
		results[i].CostSavings = optimizationResult.TotalMonthlySavings

		optimizedTotalCost += optimizationResult.MonthlyCost
		totalSavings += optimizationResult.TotalMonthlySavings

		results[i].Breakdown = cost.CalculateDetailedCost(
			results[i],
			float64(results[i].ServerConfig.MemoryGB)*2,
			1000.0,
			costParams,
			true,
		)
	}

	graph := dependency.BuildDependencyGraph(req.Services)
	sensitivities := dependency.CalculateSensitivity(
		graph,
		peakTrafficMap,
		models.ServerConfig{},
	)

	for i := range results {
		for _, s := range sensitivities {
			if s.ServiceID == results[i].ServiceID {
				results[i].SensitivityIndex = s.SensitivityIndex
				results[i].CriticalityScore = s.CriticalityScore
				break
			}
		}
	}

	dependencyResults := h.generateDependencyResults(req, peakTrafficMap, graph)

	response := models.EvaluationResponse{
		Results:            results,
		DependencyResults:  dependencyResults,
		TrafficForecasts:   trafficForecasts,
		CalibrationFactors: calibrationFactorList,
		TotalMonthlyCost:   totalCost,
		OptimizedTotalCost: optimizedTotalCost,
		TotalCostSavings:   totalSavings,
	}

	c.JSON(http.StatusOK, response)
}

func (h *Handler) generateTrafficForecasts(req models.EvaluationRequest) []models.TrafficForecast {
	forecasts := make([]models.TrafficForecast, 0)

	serviceHistoricalData := make(map[string][]models.TrafficData)
	for _, data := range req.PerformanceData {
		trafficData := models.TrafficData{
			Timestamp:      data.Timestamp,
			RequestsPerSec: data.RequestsPerSec,
		}
		serviceHistoricalData[data.ServiceID] = append(serviceHistoricalData[data.ServiceID], trafficData)
	}

	for _, svc := range req.Services {
		historical := serviceHistoricalData[svc.ID]
		if len(historical) == 0 {
			historical = h.generateSampleData(svc.ID)
		}
		tf := forecast.ForecastTraffic(svc.ID, historical, req.ForecastPeriodDays)
		forecasts = append(forecasts, tf)
	}

	return forecasts
}

func (h *Handler) generateSampleData(serviceID string) []models.TrafficData {
	data := make([]models.TrafficData, 30)
	baseTraffic := 100.0

	for i := 0; i < 30; i++ {
		dayFactor := 1.0
		if i%7 < 2 {
			dayFactor = 0.7
		}
		growth := 1.0 + float64(i)*0.01
		requests := baseTraffic * dayFactor * growth

		data[i] = models.TrafficData{
			Timestamp:      time.Now().AddDate(0, 0, i-30),
			RequestsPerSec: requests,
		}
	}

	return data
}

func (h *Handler) generateDependencyResults(
	req models.EvaluationRequest,
	peakTrafficMap map[string]float64,
	graph map[string]*dependency.ServiceNode,
) []models.DependencyResult {
	results := make([]models.DependencyResult, 0)

	for _, svc := range req.Services {
		if len(svc.Dependencies) == 0 {
			continue
		}

		dr := dependency.AnalyzeDependencies(
			req.Services,
			svc.ID,
			peakTrafficMap[svc.ID],
			models.ServerConfig{},
			req.TargetUtilization,
			req.MaxLatencyMs,
		)

		criticalPath := dependency.FindCriticalPath(
			graph,
			svc.ID,
			peakTrafficMap,
			models.ServerConfig{},
		)

		chainImpacts := dependency.AnalyzeChainImpact(
			graph,
			svc.ID,
			peakTrafficMap[svc.ID],
		)

		chainImpactData := make([]models.ChainImpactData, len(chainImpacts))
		for i, ci := range chainImpacts {
			chainImpactData[i] = models.ChainImpactData{
				Chain:        ci.Chain,
				ImpactFactor: ci.ImpactFactor,
				TrafficRatio: ci.TrafficRatio,
			}
		}

		dr.CriticalPath = criticalPath
		dr.ChainImpacts = chainImpactData

		results = append(results, dr)
	}

	return results
}

func (h *Handler) GetServerConfigs(c *gin.Context) {
	configs := []models.ServerConfig{
		{
			ID:                  "t2-micro",
			Name:                "T2 Micro",
			CPUCores:            1,
			MemoryGB:            1,
			CostPerHour:         0.0116,
			ReservedCostPerHour: 0.0081,
			MaxRequestsPerSec:   50,
		},
		{
			ID:                  "t2-small",
			Name:                "T2 Small",
			CPUCores:            1,
			MemoryGB:            2,
			CostPerHour:         0.023,
			ReservedCostPerHour: 0.0161,
			MaxRequestsPerSec:   100,
		},
		{
			ID:                  "t2-medium",
			Name:                "T2 Medium",
			CPUCores:            2,
			MemoryGB:            4,
			CostPerHour:         0.0464,
			ReservedCostPerHour: 0.0325,
			MaxRequestsPerSec:   200,
		},
		{
			ID:                  "t2-large",
			Name:                "T2 Large",
			CPUCores:            2,
			MemoryGB:            8,
			CostPerHour:         0.0928,
			ReservedCostPerHour: 0.065,
			MaxRequestsPerSec:   400,
		},
		{
			ID:                  "c5-xlarge",
			Name:                "C5 XLarge",
			CPUCores:            4,
			MemoryGB:            8,
			CostPerHour:         0.17,
			ReservedCostPerHour: 0.119,
			MaxRequestsPerSec:   800,
		},
		{
			ID:                  "m5-2xlarge",
			Name:                "M5 2XLarge",
			CPUCores:            8,
			MemoryGB:            32,
			CostPerHour:         0.384,
			ReservedCostPerHour: 0.269,
			MaxRequestsPerSec:   1600,
		},
	}

	c.JSON(http.StatusOK, configs)
}

func (h *Handler) ForecastTraffic(c *gin.Context) {
	var req struct {
		ServiceID      string              `json:"serviceId"`
		HistoricalData []models.TrafficData `json:"historicalData"`
		ForecastDays   int                 `json:"forecastDays"`
	}

	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
		return
	}

	if req.ForecastDays <= 0 {
		req.ForecastDays = 30
	}

	result := forecast.ForecastTraffic(req.ServiceID, req.HistoricalData, req.ForecastDays)
	c.JSON(http.StatusOK, result)
}

func (h *Handler) CalculateQueueing(c *gin.Context) {
	var req struct {
		ArrivalRate float64 `json:"arrivalRate"`
		ServiceRate float64 `json:"serviceRate"`
		Servers     int     `json:"servers"`
	}

	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
		return
	}

	result := queueing.CalculateMMC(req.ArrivalRate, req.ServiceRate, req.Servers)
	c.JSON(http.StatusOK, result)
}

func (h *Handler) CalculateHybridCost(c *gin.Context) {
	var req struct {
		ServerConfig    models.ServerConfig `json:"serverConfig"`
		ServersNeeded   int                 `json:"serversNeeded"`
		ReservedRatio   float64             `json:"reservedRatio"`
	}

	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
		return
	}

	if req.ReservedRatio <= 0 {
		req.ReservedRatio = 0.7
	}

	costParams := cost.DefaultCostParameters()
	hybridConfig := cost.CalculateHybridInstanceConfig(req.ServersNeeded, req.ReservedRatio)
	result := cost.CalculateHybridCost(req.ServerConfig, hybridConfig, costParams)

	c.JSON(http.StatusOK, gin.H{
		"hybridConfig": hybridConfig,
		"costResult":   result,
	})
}

func (h *Handler) GetEnvironmentFactors(c *gin.Context) {
	factors := map[string]interface{}{
		"dev": map[string]interface{}{
			"cpuFactor":    1.5,
			"memoryFactor": 1.3,
			"networkFactor": 1.2,
			"description":  "开发环境 - 资源通常较少",
		},
		"staging": map[string]interface{}{
			"cpuFactor":    1.2,
			"memoryFactor": 1.15,
			"networkFactor": 1.1,
			"description":  "预发环境 - 接近生产",
		},
		"production": map[string]interface{}{
			"cpuFactor":    1.0,
			"memoryFactor": 1.0,
			"networkFactor": 1.0,
			"description":  "生产环境 - 基准",
		},
		"performance": map[string]interface{}{
			"cpuFactor":    1.1,
			"memoryFactor": 1.05,
			"networkFactor": 1.05,
			"description":  "性能测试环境",
		},
	}

	c.JSON(http.StatusOK, factors)
}

func (h *Handler) GetSensitivityAnalysis(c *gin.Context) {
	var req struct {
		Services       []models.Service     `json:"services"`
		PeakTrafficMap map[string]float64   `json:"peakTrafficMap"`
		ServerConfig   models.ServerConfig  `json:"serverConfig"`
	}

	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
		return
	}

	graph := dependency.BuildDependencyGraph(req.Services)
	results := dependency.CalculateSensitivity(graph, req.PeakTrafficMap, req.ServerConfig)

	c.JSON(http.StatusOK, results)
}
