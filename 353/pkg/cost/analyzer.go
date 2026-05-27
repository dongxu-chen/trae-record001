package cost

import (
	"context"
	"encoding/json"
	"fmt"
	"math"
	"os"
	"path/filepath"
	"sync"
	"time"
)

type CloudProvider string

const (
	ProviderAWS     CloudProvider = "aws"
	ProviderAliyun  CloudProvider = "aliyun"
	ProviderTencent CloudProvider = "tencent"
)

type ResourceType string

const (
	ResourceTypeCompute  ResourceType = "compute"
	ResourceTypeStorage  ResourceType = "storage"
	ResourceTypeDatabase ResourceType = "database"
	ResourceTypeNetwork  ResourceType = "network"
)

type CostItem struct {
	ResourceType    ResourceType `json:"resource_type"`
	ResourceID      string       `json:"resource_id"`
	ResourceName    string       `json:"resource_name"`
	InstanceType    string       `json:"instance_type"`
	Region          string       `json:"region"`
	MonthlyCost     float64      `json:"monthly_cost"`
	MonthlyCostUSD  float64      `json:"monthly_cost_usd"`
	HourlyCost      float64      `json:"hourly_cost"`
	StorageGB       float64      `json:"storage_gb"`
	DataTransferGB  float64      `json:"data_transfer_gb"`
	Description     string       `json:"description"`
	Currency        string       `json:"currency"`
}

type MigrationCost struct {
	DataTransferCost float64 `json:"data_transfer_cost"`
	DataTransferUSD  float64 `json:"data_transfer_usd"`
	SnapshotCost     float64 `json:"snapshot_cost"`
	SnapshotUSD      float64 `json:"snapshot_usd"`
	ConversionCost   float64 `json:"conversion_cost"`
	ConversionUSD    float64 `json:"conversion_usd"`
	TotalMigration   float64 `json:"total_migration"`
	TotalMigrationUSD float64 `json:"total_migration_usd"`
}

type CostComparison struct {
	SourceProvider     CloudProvider `json:"source_provider"`
	SourceRegion       string        `json:"source_region"`
	SourceTotalMonthly float64       `json:"source_total_monthly"`
	SourceTotalUSD     float64       `json:"source_total_usd"`
	SourceItems        []*CostItem   `json:"source_items"`

	DestProvider       CloudProvider `json:"dest_provider"`
	DestRegion         string        `json:"dest_region"`
	DestTotalMonthly   float64       `json:"dest_total_monthly"`
	DestTotalUSD       float64       `json:"dest_total_usd"`
	DestItems          []*CostItem   `json:"dest_items"`

	MigrationCost      *MigrationCost `json:"migration_cost"`

	MonthlySavings     float64 `json:"monthly_savings"`
	MonthlySavingsUSD  float64 `json:"monthly_savings_usd"`
	SavingsPercentage  float64 `json:"savings_percentage"`
	ROIMonths          float64 `json:"roi_months"`

	Currency           string  `json:"currency"`
	ExchangeRate       float64 `json:"exchange_rate"`

	GeneratedAt        int64   `json:"generated_at"`
}

type InstancePricing struct {
	InstanceType string  `json:"instance_type"`
	HourlyRate   float64 `json:"hourly_rate"`
	MonthlyRate  float64 `json:"monthly_rate"`
	Region       string  `json:"region"`
	Provider     string  `json:"provider"`
}

type StoragePricing struct {
	StorageType string  `json:"storage_type"`
	GBPerMonth  float64 `json:"gb_per_month"`
	Region      string  `json:"region"`
	Provider    string  `json:"provider"`
}

type CostAnalyzer struct {
	instancePrices map[string]map[string]*InstancePricing
	storagePrices  map[string]map[string]*StoragePricing
	exchangeRates  map[string]float64
	cacheDir       string
	mu             sync.RWMutex
}

var defaultAWSPricing = map[string]map[string]*InstancePricing{
	"us-east-1": {
		"t2.micro": {InstanceType: "t2.micro", HourlyRate: 0.0116, MonthlyRate: 8.47},
		"t2.small": {InstanceType: "t2.small", HourlyRate: 0.023, MonthlyRate: 16.79},
		"t2.medium": {InstanceType: "t2.medium", HourlyRate: 0.0464, MonthlyRate: 33.87},
		"t2.large": {InstanceType: "t2.large", HourlyRate: 0.0928, MonthlyRate: 67.74},
		"m5.large": {InstanceType: "m5.large", HourlyRate: 0.096, MonthlyRate: 70.08},
		"m5.xlarge": {InstanceType: "m5.xlarge", HourlyRate: 0.192, MonthlyRate: 140.16},
		"c5.large": {InstanceType: "c5.large", HourlyRate: 0.085, MonthlyRate: 62.05},
		"r5.large": {InstanceType: "r5.large", HourlyRate: 0.126, MonthlyRate: 91.98},
	},
}

var defaultAliyunPricing = map[string]map[string]*InstancePricing{
	"cn-hangzhou": {
		"ecs.t5-lc2m1.nano": {InstanceType: "ecs.t5-lc2m1.nano", HourlyRate: 0.014, MonthlyRate: 10.22},
		"ecs.t5-lc1m1.small": {InstanceType: "ecs.t5-lc1m1.small", HourlyRate: 0.028, MonthlyRate: 20.44},
		"ecs.t5-lc1m2.large": {InstanceType: "ecs.t5-lc1m2.large", HourlyRate: 0.112, MonthlyRate: 81.76},
		"ecs.g6.large": {InstanceType: "ecs.g6.large", HourlyRate: 0.12, MonthlyRate: 87.6},
		"ecs.g6.xlarge": {InstanceType: "ecs.g6.xlarge", HourlyRate: 0.24, MonthlyRate: 175.2},
		"ecs.c6.large": {InstanceType: "ecs.c6.large", HourlyRate: 0.105, MonthlyRate: 76.65},
		"ecs.r6.large": {InstanceType: "ecs.r6.large", HourlyRate: 0.156, MonthlyRate: 113.88},
	},
}

var defaultTencentPricing = map[string]map[string]*InstancePricing{
	"ap-guangzhou": {
		"S2.SMALL1": {InstanceType: "S2.SMALL1", HourlyRate: 0.018, MonthlyRate: 13.14},
		"S2.SMALL2": {InstanceType: "S2.SMALL2", HourlyRate: 0.036, MonthlyRate: 26.28},
		"S2.MEDIUM4": {InstanceType: "S2.MEDIUM4", HourlyRate: 0.072, MonthlyRate: 52.56},
		"S4.SMALL2": {InstanceType: "S4.SMALL2", HourlyRate: 0.03, MonthlyRate: 21.9},
		"S4.MEDIUM4": {InstanceType: "S4.MEDIUM4", HourlyRate: 0.06, MonthlyRate: 43.8},
		"M4.LARGE8": {InstanceType: "M4.LARGE8", HourlyRate: 0.144, MonthlyRate: 105.12},
		"C4.LARGE4": {InstanceType: "C4.LARGE4", HourlyRate: 0.096, MonthlyRate: 70.08},
	},
}

var defaultStoragePricing = map[string]map[string]float64{
	"aws-us-east-1": {
		"gp2": 0.10,
		"gp3": 0.08,
		"s3":  0.023,
		"snapshot": 0.05,
	},
	"aliyun-cn-hangzhou": {
		"cloud_efficiency": 0.07,
		"cloud_ssd": 0.12,
		"oss":  0.025,
		"snapshot": 0.06,
	},
	"tencent-ap-guangzhou": {
		"CLOUD_PREMIUM": 0.08,
		"CLOUD_SSD": 0.13,
		"cos":  0.024,
		"snapshot": 0.055,
	},
}

var defaultDataTransferPricing = map[string]float64{
	"aws":     0.09,
	"aliyun":  0.07,
	"tencent": 0.08,
}

func NewCostAnalyzer(cacheDir string) (*CostAnalyzer, error) {
	if err := os.MkdirAll(cacheDir, 0755); err != nil {
		return nil, fmt.Errorf("failed to create cost cache directory: %w", err)
	}

	ca := &CostAnalyzer{
		instancePrices: make(map[string]map[string]*InstancePricing),
		storagePrices:  make(map[string]map[string]*StoragePricing),
		exchangeRates: map[string]float64{
			"CNY": 7.2,
			"USD": 1.0,
		},
		cacheDir: cacheDir,
	}

	ca.loadDefaultPricing()

	return ca, nil
}

func (ca *CostAnalyzer) loadDefaultPricing() {
	for region, prices := range defaultAWSPricing {
		key := fmt.Sprintf("aws-%s", region)
		ca.instancePrices[key] = prices
	}

	for region, prices := range defaultAliyunPricing {
		key := fmt.Sprintf("aliyun-%s", region)
		ca.instancePrices[key] = prices
	}

	for region, prices := range defaultTencentPricing {
		key := fmt.Sprintf("tencent-%s", region)
		ca.instancePrices[key] = prices
	}
}

func (ca *CostAnalyzer) AnalyzeCostComparison(
	ctx context.Context,
	sourceProvider, sourceRegion string,
	destProvider, destRegion string,
	sourceResources, destResources []*CostItem,
	dataTransferGB float64,
) (*CostComparison, error) {

	comparison := &CostComparison{
		SourceProvider: CloudProvider(sourceProvider),
		SourceRegion:   sourceRegion,
		SourceItems:    sourceResources,
		DestProvider:   CloudProvider(destProvider),
		DestRegion:     destRegion,
		DestItems:      destResources,
		Currency:       "USD",
		ExchangeRate:   1.0,
		GeneratedAt:    time.Now().Unix(),
	}

	for _, item := range sourceResources {
		comparison.SourceTotalMonthly += item.MonthlyCost
		comparison.SourceTotalUSD += item.MonthlyCostUSD
	}

	for _, item := range destResources {
		comparison.DestTotalMonthly += item.MonthlyCost
		comparison.DestTotalUSD += item.MonthlyCostUSD
	}

	comparison.MigrationCost = ca.calculateMigrationCost(
		sourceProvider, destProvider, dataTransferGB,
		sourceResources, destResources,
	)

	comparison.MonthlySavings = comparison.SourceTotalMonthly - comparison.DestTotalMonthly
	comparison.MonthlySavingsUSD = comparison.SourceTotalUSD - comparison.DestTotalUSD

	if comparison.SourceTotalMonthly > 0 {
		comparison.SavingsPercentage = (comparison.MonthlySavings / comparison.SourceTotalMonthly) * 100
	}

	if comparison.MonthlySavings > 0 {
		comparison.ROIMonths = comparison.MigrationCost.TotalMigration / comparison.MonthlySavings
	} else {
		comparison.ROIMonths = math.Inf(1)
	}

	return comparison, nil
}

func (ca *CostAnalyzer) calculateMigrationCost(
	sourceProvider, destProvider string,
	dataTransferGB float64,
	sourceResources, destResources []*CostItem,
) *MigrationCost {

	mc := &MigrationCost{}

	sourceRate, _ := defaultDataTransferPricing[sourceProvider]
	destRate, _ := defaultDataTransferPricing[destProvider]
	avgRate := (sourceRate + destRate) / 2
	mc.DataTransferCost = dataTransferGB * avgRate
	mc.DataTransferUSD = mc.DataTransferCost

	var totalSnapshotGB float64
	for _, res := range sourceResources {
		totalSnapshotGB += res.StorageGB
	}

	snapshotRate := ca.getSnapshotRate(sourceProvider)
	mc.SnapshotCost = totalSnapshotGB * snapshotRate
	mc.SnapshotUSD = mc.SnapshotCost

	mc.ConversionCost = 50.0
	mc.ConversionUSD = 50.0

	mc.TotalMigration = mc.DataTransferCost + mc.SnapshotCost + mc.ConversionCost
	mc.TotalMigrationUSD = mc.TotalMigration

	return mc
}

func (ca *CostAnalyzer) getSnapshotRate(provider string) float64 {
	key := fmt.Sprintf("%s", provider)
	switch key {
	case "aws":
		return 0.05
	case "aliyun":
		return 0.06
	case "tencent":
		return 0.055
	default:
		return 0.05
	}
}

func (ca *CostAnalyzer) GetComputeCost(provider, region, instanceType string, hours float64) (*CostItem, error) {
	ca.mu.RLock()
	defer ca.mu.RUnlock()

	key := fmt.Sprintf("%s-%s", provider, region)
	prices, ok := ca.instancePrices[key]
	if !ok {
		return ca.estimateComputeCost(provider, region, instanceType, hours)
	}

	pricing, ok := prices[instanceType]
	if !ok {
		return ca.estimateComputeCost(provider, region, instanceType, hours)
	}

	monthlyHours := 730.0
	if hours > 0 {
		monthlyHours = hours
	}

	return &CostItem{
		ResourceType:   ResourceTypeCompute,
		InstanceType:   instanceType,
		Region:         region,
		HourlyCost:     pricing.HourlyRate,
		MonthlyCost:    pricing.MonthlyRate,
		MonthlyCostUSD: pricing.MonthlyRate,
		Description:    fmt.Sprintf("%s %s compute instance", provider, instanceType),
		Currency:       "USD",
	}, nil
}

func (ca *CostAnalyzer) estimateComputeCost(provider, region, instanceType string, hours float64) (*CostItem, error) {
	baseRate := 0.1
	switch provider {
	case "aliyun":
		baseRate = 0.08
	case "tencent":
		baseRate = 0.085
	}

	monthlyHours := 730.0
	if hours > 0 {
		monthlyHours = hours
	}

	return &CostItem{
		ResourceType:   ResourceTypeCompute,
		InstanceType:   instanceType,
		Region:         region,
		HourlyCost:     baseRate,
		MonthlyCost:    baseRate * monthlyHours,
		MonthlyCostUSD: baseRate * monthlyHours,
		Description:    fmt.Sprintf("Estimated %s %s compute instance", provider, instanceType),
		Currency:       "USD",
	}, nil
}

func (ca *CostAnalyzer) GetStorageCost(provider, region, storageType string, storageGB float64) (*CostItem, error) {
	key := fmt.Sprintf("%s-%s", provider, region)
	prices, ok := defaultStoragePricing[key]
	if !ok {
		prices = defaultStoragePricing["aws-us-east-1"]
	}

	rate, ok := prices[storageType]
	if !ok {
		rate = 0.10
	}

	monthlyCost := storageGB * rate

	return &CostItem{
		ResourceType:   ResourceTypeStorage,
		Region:         region,
		StorageGB:      storageGB,
		MonthlyCost:    monthlyCost,
		MonthlyCostUSD: monthlyCost,
		Description:    fmt.Sprintf("%.2f GB %s storage", storageGB, storageType),
		Currency:       "USD",
	}, nil
}

func (ca *CostAnalyzer) GetDatabaseCost(provider, region, instanceType string, storageGB float64) (*CostItem, error) {
	computeCost, _ := ca.GetComputeCost(provider, region, instanceType, 0)
	storageCost, _ := ca.GetStorageCost(provider, region, "ssd", storageGB)

	dbPremium := 1.5

	return &CostItem{
		ResourceType:   ResourceTypeDatabase,
		InstanceType:   instanceType,
		Region:         region,
		StorageGB:      storageGB,
		MonthlyCost:    (computeCost.MonthlyCost + storageCost.MonthlyCost) * dbPremium,
		MonthlyCostUSD: (computeCost.MonthlyCost + storageCost.MonthlyCost) * dbPremium,
		Description:    fmt.Sprintf("%s %s database with %.2f GB storage", provider, instanceType, storageGB),
		Currency:       "USD",
	}, nil
}

func (ca *CostAnalyzer) GenerateCostReport(comparison *CostComparison) string {
	report := `
========================================
迁移成本对比分析报告
========================================

生成时间: ` + time.Unix(comparison.GeneratedAt, 0).Format(time.RFC3339) + `

【源端成本分析】
云厂商: ` + string(comparison.SourceProvider) + `
区域: ` + comparison.SourceRegion + `
`
	for _, item := range comparison.SourceItems {
		report += fmt.Sprintf("  - [%s] %s (%s): $%.2f/月\n",
			item.ResourceType, item.ResourceName, item.InstanceType, item.MonthlyCostUSD)
	}
	report += fmt.Sprintf("  源端月总成本: $%.2f\n\n", comparison.SourceTotalUSD)

	report += `【目标端成本分析】
云厂商: ` + string(comparison.DestProvider) + `
区域: ` + comparison.DestRegion + `
`
	for _, item := range comparison.DestItems {
		report += fmt.Sprintf("  - [%s] %s (%s): $%.2f/月\n",
			item.ResourceType, item.ResourceName, item.InstanceType, item.MonthlyCostUSD)
	}
	report += fmt.Sprintf("  目标端月总成本: $%.2f\n\n", comparison.DestTotalUSD)

	report += `【迁移成本估算】
`
	if comparison.MigrationCost != nil {
		report += fmt.Sprintf("  - 数据传输费用: $%.2f\n", comparison.MigrationCost.DataTransferUSD)
		report += fmt.Sprintf("  - 快照费用: $%.2f\n", comparison.MigrationCost.SnapshotUSD)
		report += fmt.Sprintf("  - 转换费用: $%.2f\n", comparison.MigrationCost.ConversionUSD)
		report += fmt.Sprintf("  迁移总成本: $%.2f\n\n", comparison.MigrationCost.TotalMigrationUSD)
	}

	report += `【成本节约分析】
`
	if comparison.MonthlySavingsUSD > 0 {
		report += fmt.Sprintf("  月度节约: $%.2f (%.1f%%)\n", comparison.MonthlySavingsUSD, comparison.SavingsPercentage)
		if !math.IsInf(comparison.ROIMonths, 1) {
			report += fmt.Sprintf("  投资回收期: %.1f 个月\n", comparison.ROIMonths)
		} else {
			report += "  投资回收期: 无法计算（无节约）\n"
		}
	} else {
		report += fmt.Sprintf("  月度增加: $%.2f (%.1f%%)\n", -comparison.MonthlySavingsUSD, -comparison.SavingsPercentage)
		report += "  投资回收期: N/A\n"
	}

	return report
}

func (ca *CostAnalyzer) SaveComparison(comparison *CostComparison, filename string) error {
	data, err := json.MarshalIndent(comparison, "", "  ")
	if err != nil {
		return err
	}

	fullPath := filepath.Join(ca.cacheDir, filename)
	return os.WriteFile(fullPath, data, 0644)
}

func (ca *CostAnalyzer) LoadComparison(filename string) (*CostComparison, error) {
	fullPath := filepath.Join(ca.cacheDir, filename)
	data, err := os.ReadFile(fullPath)
	if err != nil {
		return nil, err
	}

	var comparison CostComparison
	if err := json.Unmarshal(data, &comparison); err != nil {
		return nil, err
	}

	return &comparison, nil
}
