package config

import (
	"os"

	"gopkg.in/yaml.v3"
)

type Config struct {
	Server     ServerConfig     `yaml:"server"`
	Kubernetes KubernetesConfig `yaml:"kubernetes"`
	Prometheus PrometheusConfig `yaml:"prometheus"`
	Cost       CostConfig       `yaml:"cost"`
	Budgets    BudgetConfig     `yaml:"budgets"`
	Pricing    PricingConfig    `yaml:"pricing"`
	Cloud      CloudConfig      `yaml:"cloud"`
}

type ServerConfig struct {
	Port string `yaml:"port"`
}

type KubernetesConfig struct {
	Kubeconfig string `yaml:"kubeconfig"`
	InCluster  bool   `yaml:"inCluster"`
}

type PrometheusConfig struct {
	Address string `yaml:"address"`
}

type CostConfig struct {
	CPUPerCoreHour      float64            `yaml:"cpuPerCoreHour"`
	MemoryPerGBHour     float64            `yaml:"memoryPerGBHour"`
	StoragePerGBHour    float64            `yaml:"storagePerGBHour"`
	NetworkPerGB        float64            `yaml:"networkPerGB"`
	IdleThreshold       float64            `yaml:"idleThreshold"`
	CustomFactors       map[string]float64 `yaml:"customFactors"`
}

type BudgetConfig struct {
	DefaultMonthlyBudget float64            `yaml:"defaultMonthlyBudget"`
	Namespaces           map[string]float64 `yaml:"namespaces"`
	AlertThreshold       float64            `yaml:"alertThreshold"`
	CriticalThreshold    float64            `yaml:"criticalThreshold"`
}

type PricingConfig struct {
	OnDemand OnDemandPricing `yaml:"onDemand"`
	Reserved ReservedPricing `yaml:"reserved"`
	Spot     SpotPricing     `yaml:"spot"`
}

type OnDemandPricing struct {
	CPUPerCoreHour  float64 `yaml:"cpuPerCoreHour"`
	MemoryPerGBHour float64 `yaml:"memoryPerGBHour"`
}

type ReservedPricing struct {
	CPUPerCoreHour      float64 `yaml:"cpuPerCoreHour"`
	MemoryPerGBHour     float64 `yaml:"memoryPerGBHour"`
	UpfrontFeePerCore   float64 `yaml:"upfrontFeePerCore"`
	UpfrontFeePerGB     float64 `yaml:"upfrontFeePerGB"`
	ContractTermMonths  int     `yaml:"contractTermMonths"`
}

type SpotPricing struct {
	CPUPerCoreHour          float64 `yaml:"cpuPerCoreHour"`
	MemoryPerGBHour         float64 `yaml:"memoryPerGBHour"`
	DiscountThreshold       float64 `yaml:"discountThreshold"`
	InterruptionRiskThreshold float64 `yaml:"interruptionRiskThreshold"`
}

type CloudConfig struct {
	Provider string    `yaml:"provider"`
	Region   string    `yaml:"region"`
	AWS      AWSConfig `yaml:"aws"`
}

type AWSConfig struct {
	AccessKey string `yaml:"accessKey"`
	SecretKey string `yaml:"secretKey"`
}

func LoadConfig(path string) (*Config, error) {
	data, err := os.ReadFile(path)
	if err != nil {
		return nil, err
	}

	var cfg Config
	if err := yaml.Unmarshal(data, &cfg); err != nil {
		return nil, err
	}

	return &cfg, nil
}
