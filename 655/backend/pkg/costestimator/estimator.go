package costestimator

import (
	"fmt"
	"math"
	"sync"
	"time"

	"github.com/google/uuid"

	"servicemesh-gateway/pkg/models"
)

var defaultCostConfigs = map[string]*models.CostConfig{
	"aws": {
		CloudProvider: "aws",
		Currency:      "USD",
		IntraAZRate: map[string]float64{
			"us-east-1": 0.01,
			"us-west-2": 0.01,
			"eu-west-1": 0.011,
			"ap-northeast-1": 0.012,
			"cn-north-1": 0.008,
		},
		CrossAZRate: map[string]float64{
			"us-east-1": 0.02,
			"us-west-2": 0.02,
			"eu-west-1": 0.022,
			"ap-northeast-1": 0.024,
			"cn-north-1": 0.016,
		},
	},
	"azure": {
		CloudProvider: "azure",
		Currency:      "USD",
		IntraAZRate: map[string]float64{
			"eastus":   0.008,
			"westus":   0.008,
			"westeurope": 0.009,
			"japaneast": 0.010,
			"chinaeast": 0.007,
		},
		CrossAZRate: map[string]float64{
			"eastus":   0.018,
			"westus":   0.018,
			"westeurope": 0.020,
			"japaneast": 0.022,
			"chinaeast": 0.015,
		},
	},
	"aliyun": {
		CloudProvider: "aliyun",
		Currency:      "CNY",
		IntraAZRate: map[string]float64{
			"cn-beijing":  0.008,
			"cn-shanghai": 0.008,
			"cn-shenzhen": 0.008,
			"cn-hangzhou": 0.008,
		},
		CrossAZRate: map[string]float64{
			"cn-beijing":  0.015,
			"cn-shanghai": 0.015,
			"cn-shenzhen": 0.015,
			"cn-hangzhou": 0.015,
		},
	},
}

type CostEstimator struct {
	configs map[string]*models.CostConfig
	mu      sync.RWMutex
}

func NewCostEstimator() *CostEstimator {
	return &CostEstimator{
		configs: defaultCostConfigs,
	}
}

func (ce *CostEstimator) Estimate(req *models.CostEstimateRequest) (*models.CostEstimateResult, error) {
	if req.CloudProvider == "" {
		req.CloudProvider = "aws"
	}
	if req.Region == "" {
		req.Region = "us-east-1"
	}
	if req.CrossAZRatio <= 0 {
		req.CrossAZRatio = 0.3
	}
	if req.TrafficGB <= 0 {
		return nil, fmt.Errorf("trafficGB must be greater than 0")
	}

	ce.mu.RLock()
	config, exists := ce.configs[req.CloudProvider]
	ce.mu.RUnlock()

	if !exists {
		return nil, fmt.Errorf("unsupported cloud provider: %s", req.CloudProvider)
	}

	intraAZRate := config.IntraAZRate[req.Region]
	crossAZRate := config.CrossAZRate[req.Region]

	if intraAZRate == 0 {
		intraAZRate = config.IntraAZRate["us-east-1"]
	}
	if crossAZRate == 0 {
		crossAZRate = config.CrossAZRate["us-east-1"]
	}

	crossAZTraffic := req.TrafficGB * req.CrossAZRatio
	intraAZTraffic := req.TrafficGB * (1 - req.CrossAZRatio)

	crossAZCost := crossAZTraffic * crossAZRate
	intraAZCost := intraAZTraffic * intraAZRate

	totalCost := intraAZCost + crossAZCost

	days := math.Max(1, math.Ceil(req.EndDate.Sub(req.StartDate).Hours()/24))
	avgDailyTrafficGB := req.TrafficGB / days
	estimatedRequests := int64(avgDailyTrafficGB * 1024 * 1024 / 2)

	result := &models.CostEstimateResult{
		ID:                uuid.New().String(),
		TotalCost:         roundTo(totalCost, 4),
		IntraAZCost:       roundTo(intraAZCost, 4),
		CrossAZCost:       roundTo(crossAZCost, 4),
		IntraAZTrafficGB:  roundTo(intraAZTraffic, 4),
		CrossAZTrafficGB:  roundTo(crossAZTraffic, 4),
		CostPerGBIntraAZ:  intraAZRate,
		CostPerGBCrossAZ:  crossAZRate,
		EstimatedRequests: estimatedRequests,
		AvgRequestSizeKB:  2.0,
		Currency:          config.Currency,
		Region:            req.Region,
		CloudProvider:     req.CloudProvider,
		GeneratedAt:       time.Now(),
		Breakdown: []models.CostBreakdownItem{
			{
				Name:        "Intra-AZ Traffic",
				Description: fmt.Sprintf("Traffic within same AZ: %.2f GB", intraAZTraffic),
				Amount:      roundTo(intraAZCost, 4),
				Percentage:  totalCost > 0 ? roundTo(intraAZCost/totalCost*100, 2) : 0,
			},
			{
				Name:        "Cross-AZ Traffic",
				Description: fmt.Sprintf("Traffic across AZs: %.2f GB", crossAZTraffic),
				Amount:      roundTo(crossAZCost, 4),
				Percentage:  totalCost > 0 ? roundTo(crossAZCost/totalCost*100, 2) : 0,
			},
		},
	}

	return result, nil
}

func (ce *CostEstimator) GetSupportedCloudProviders() []string {
	ce.mu.RLock()
	defer ce.mu.RUnlock()

	providers := make([]string, 0, len(ce.configs))
	for p := range ce.configs {
		providers = append(providers, p)
	}
	return providers
}

func (ce *CostEstimator) GetSupportedRegions(cloudProvider string) []string {
	ce.mu.RLock()
	defer ce.mu.RUnlock()

	config, exists := ce.configs[cloudProvider]
	if !exists {
		return nil
	}

	regions := make([]string, 0, len(config.IntraAZRate))
	for r := range config.IntraAZRate {
		regions = append(regions, r)
	}
	return regions
}

func (ce *CostEstimator) GetCostConfig(cloudProvider string) (*models.CostConfig, error) {
	ce.mu.RLock()
	defer ce.mu.RUnlock()

	config, exists := ce.configs[cloudProvider]
	if !exists {
		return nil, fmt.Errorf("unsupported cloud provider: %s", cloudProvider)
	}

	return config, nil
}

func (ce *CostEstimator) UpdateCostConfig(config *models.CostConfig) error {
	ce.mu.Lock()
	defer ce.mu.Unlock()

	if config.CloudProvider == "" {
		return fmt.Errorf("cloud provider cannot be empty")
	}

	ce.configs[config.CloudProvider] = config
	return nil
}

func (ce *CostEstimator) GenerateMonthlyReport(cloudProvider, region string, dailyTrafficGB []float64, crossAZRatio float64) (*models.CostEstimateResult, error) {
	totalTraffic := 0.0
	for _, d := range dailyTrafficGB {
		totalTraffic += d
	}

	avgTraffic := totalTraffic / float64(len(dailyTrafficGB))

	req := &models.CostEstimateRequest{
		TrafficGB:    totalTraffic,
		CrossAZRatio: crossAZRatio,
		Region:       region,
		CloudProvider: cloudProvider,
		StartDate:    time.Now().AddDate(0, 0, -len(dailyTrafficGB)),
		EndDate:      time.Now(),
	}

	result, err := ce.Estimate(req)
	if err != nil {
		return nil, err
	}

	dailyCost := result.TotalCost / float64(len(dailyTrafficGB))

	result.Breakdown = append(result.Breakdown,
		models.CostBreakdownItem{
			Name:        "Average Daily Cost",
			Description: fmt.Sprintf("Average daily cost based on %d days data", len(dailyTrafficGB)),
			Amount:      roundTo(dailyCost, 4),
			Percentage:  0,
		},
		models.CostBreakdownItem{
			Name:        "Projected Monthly Cost",
			Description: "Based on average daily traffic * 30 days",
			Amount:      roundTo(dailyCost*30, 4),
			Percentage:  0,
		},
	)

	return result, nil
}

func (ce *CostEstimator) CompareCloudProviders(regions []string, trafficGB float64, crossAZRatio float64) []*models.CostEstimateResult {
	results := make([]*models.CostEstimateResult, 0)

	for _, provider := range ce.GetSupportedCloudProviders() {
		for _, region := range ce.GetSupportedRegions(provider) {
			match := false
			for _, r := range regions {
				if r == region {
					match = true
					break
				}
			}
			if len(regions) > 0 && !match {
				continue
			}

			req := &models.CostEstimateRequest{
				TrafficGB:     trafficGB,
				CrossAZRatio:  crossAZRatio,
				Region:        region,
				CloudProvider: provider,
				StartDate:     time.Now().AddDate(0, 0, -30),
				EndDate:       time.Now(),
			}

			result, err := ce.Estimate(req)
			if err == nil {
				results = append(results, result)
			}
		}
	}

	return results
}

func roundTo(val float64, places int) float64 {
	shift := math.Pow(10, float64(places))
	return math.Round(val*shift) / shift
}
