package config

import (
	"fmt"
	"os"
	"time"

	"gopkg.in/yaml.v3"

	"autoscaler/internal/types"
	"autoscaler/pkg/cloud"
	"autoscaler/pkg/controller"
	"autoscaler/pkg/monitor"
	"autoscaler/pkg/predict"
	"autoscaler/pkg/strategy"
)

type Config struct {
	Autoscaler  AutoscalerConfig  `yaml:"autoscaler"`
	Prometheus  PrometheusConfig  `yaml:"prometheus"`
	Prediction  PredictionConfig  `yaml:"prediction"`
	Strategy    StrategyConfig    `yaml:"strategy"`
	Cloud       CloudConfig       `yaml:"cloud"`
	Logging     LoggingConfig     `yaml:"logging"`
}

type AutoscalerConfig struct {
	GroupID                string            `yaml:"group_id"`
	ScalingType            string            `yaml:"scaling_type"`
	DeploymentStrategy     string            `yaml:"deployment_strategy"`
	Interval               string            `yaml:"interval"`
	InstanceIDs            []string          `yaml:"instance_ids"`
	MonitorMetrics         []string          `yaml:"monitor_metrics"`
	EnablePrediction       bool              `yaml:"enable_prediction"`
	EnableErrorCorrection  bool              `yaml:"enable_error_correction"`
	DryRun                 bool              `yaml:"dry_run"`
	DryRunMode             string            `yaml:"dry_run_mode"`
	ServiceName            string            `yaml:"service_name"`
	ServiceLevel           string            `yaml:"service_level"`
	BlueGreenTimeout       string            `yaml:"bluegreen_timeout"`
	EnableCostOptimization bool              `yaml:"enable_cost_optimization"`
	HistoryEnabled         bool              `yaml:"history_enabled"`
	HistoryStoragePath     string            `yaml:"history_storage_path"`
}

type PrometheusConfig struct {
	Address  string `yaml:"address"`
	Timeout  string `yaml:"timeout"`
	Step     string `yaml:"step"`
	Lookback string `yaml:"lookback"`
}

type PredictionConfig struct {
	Method       string                `yaml:"method"`
	WindowSize   int                   `yaml:"window_size"`
	Horizon      int                   `yaml:"horizon"`
	Alpha        float64               `yaml:"alpha"`
	Differencing int                   `yaml:"differencing"`
	AROrder      int                   `yaml:"ar_order"`
	MAOrder      int                   `yaml:"ma_order"`
	ErrorFeedback ErrorFeedbackConfig  `yaml:"error_feedback"`
}

type ErrorFeedbackConfig struct {
	Enabled        bool    `yaml:"enabled"`
	WindowSize     int     `yaml:"window_size"`
	MinSamples     int     `yaml:"min_samples"`
	MaxCorrection  float64 `yaml:"max_correction"`
	UpdateInterval string  `yaml:"update_interval"`
	Alpha          float64 `yaml:"alpha"`
}

type StrategyConfig struct {
	UsePrediction      bool                `yaml:"use_prediction"`
	UseErrorCorrection bool                `yaml:"use_error_correction"`
	CooldownKey        string              `yaml:"cooldown_key"`
	DefaultServiceLevel string             `yaml:"default_service_level"`
	ServiceCooldowns   ServiceCooldownsConfig `yaml:"service_cooldowns"`
	Policies           []PolicyConfig      `yaml:"policies"`
	CostOptimization   bool                `yaml:"cost_optimization"`
	CostConfig         CostConfig          `yaml:"cost_config"`
}

type CostConfig struct {
	Enabled              bool    `yaml:"enabled"`
	ReservedInstanceRatio float64 `yaml:"reserved_instance_ratio"`
	MaxOnDemandInstances int     `yaml:"max_ondemand_instances"`
	SpotInstanceEnabled  bool    `yaml:"spot_instance_enabled"`
	SpotMaxPrice         float64 `yaml:"spot_max_price"`
	CostThreshold        float64 `yaml:"cost_threshold"`
	OptimizationInterval string  `yaml:"optimization_interval"`
}

type ServiceCooldownsConfig struct {
	Critical string `yaml:"critical"`
	High     string `yaml:"high"`
	Medium   string `yaml:"medium"`
	Low      string `yaml:"low"`
}

type PolicyConfig struct {
	MetricType     string  `yaml:"metric_type"`
	TargetValue    float64 `yaml:"target_value"`
	Tolerance      float64 `yaml:"tolerance"`
	StepSize       int     `yaml:"step_size"`
	CooldownPeriod string  `yaml:"cooldown_period"`
	MaxInstances   int     `yaml:"max_instances"`
	MinInstances   int     `yaml:"min_instances"`
	MaxSize        string  `yaml:"max_size"`
	MinSize        string  `yaml:"min_size"`
	ServiceLevel   string  `yaml:"service_level"`
}

type CloudConfig struct {
	Provider   string              `yaml:"provider"`
	Region     string              `yaml:"region"`
	AccessKey  string              `yaml:"access_key"`
	SecretKey  string              `yaml:"secret_key"`
	AssumeRole string              `yaml:"assume_role"`
	FlavorMap  map[string][]string `yaml:"flavor_map"`
}

type LoggingConfig struct {
	Level  string `yaml:"level"`
	Format string `yaml:"format"`
}

func LoadConfig(path string) (*Config, error) {
	data, err := os.ReadFile(path)
	if err != nil {
		return nil, fmt.Errorf("failed to read config file: %w", err)
	}

	var config Config
	if err := yaml.Unmarshal(data, &config); err != nil {
		return nil, fmt.Errorf("failed to parse config file: %w", err)
	}

	if err := config.Validate(); err != nil {
		return nil, fmt.Errorf("invalid config: %w", err)
	}

	return &config, nil
}

func (c *Config) Validate() error {
	if c.Autoscaler.GroupID == "" {
		return fmt.Errorf("autoscaler.group_id is required")
	}

	if c.Autoscaler.ScalingType == "" {
		c.Autoscaler.ScalingType = "horizontal"
	}

	if c.Autoscaler.ScalingType != "horizontal" && c.Autoscaler.ScalingType != "vertical" {
		return fmt.Errorf("autoscaler.scaling_type must be 'horizontal' or 'vertical'")
	}

	if c.Autoscaler.DeploymentStrategy == "" {
		c.Autoscaler.DeploymentStrategy = "bluegreen"
	}

	if c.Autoscaler.ServiceLevel == "" {
		c.Autoscaler.ServiceLevel = "medium"
	}

	if len(c.Autoscaler.MonitorMetrics) == 0 {
		c.Autoscaler.MonitorMetrics = []string{"cpu", "memory"}
	}

	if c.Prometheus.Address == "" {
		c.Prometheus.Address = "http://localhost:9090"
	}

	if c.Cloud.Provider == "" {
		c.Cloud.Provider = "mock"
	}

	return nil
}

func (c *Config) GetAutoscalerConfig() (controller.AutoscalerConfig, error) {
	interval, err := time.ParseDuration(c.Autoscaler.Interval)
	if err != nil {
		interval = 5 * time.Minute
	}

	bgTimeout, err := time.ParseDuration(c.Autoscaler.BlueGreenTimeout)
	if err != nil {
		bgTimeout = 10 * time.Minute
	}

	metrics := make([]types.MetricType, len(c.Autoscaler.MonitorMetrics))
	for i, m := range c.Autoscaler.MonitorMetrics {
		metrics[i] = types.MetricType(m)
	}

	errorFeedbackConfig := types.ErrorFeedbackConfig{
		Enabled:        c.Prediction.ErrorFeedback.Enabled,
		WindowSize:     c.Prediction.ErrorFeedback.WindowSize,
		MinSamples:     c.Prediction.ErrorFeedback.MinSamples,
		MaxCorrection:  c.Prediction.ErrorFeedback.MaxCorrection,
		Alpha:          c.Prediction.ErrorFeedback.Alpha,
	}

	if c.Prediction.ErrorFeedback.UpdateInterval != "" {
		errorFeedbackConfig.UpdateInterval, _ = time.ParseDuration(c.Prediction.ErrorFeedback.UpdateInterval)
	}

	costConfig := c.getCostConfig()

	dryRunMode := types.DryRunMode(c.Autoscaler.DryRunMode)
	if dryRunMode == "" {
		dryRunMode = types.DryRunOff
	}

	return controller.AutoscalerConfig{
		GroupID:                c.Autoscaler.GroupID,
		ScalingType:            types.ScalingType(c.Autoscaler.ScalingType),
		DeploymentStrategy:     types.DeploymentStrategy(c.Autoscaler.DeploymentStrategy),
		Interval:               interval,
		InstanceIDs:            c.Autoscaler.InstanceIDs,
		MonitorMetrics:         metrics,
		EnablePrediction:       c.Autoscaler.EnablePrediction,
		EnableErrorCorrection:  c.Autoscaler.EnableErrorCorrection,
		DryRun:                 c.Autoscaler.DryRun,
		DryRunMode:             dryRunMode,
		ServiceName:            c.Autoscaler.ServiceName,
		ServiceLevel:           types.ServiceLevel(c.Autoscaler.ServiceLevel),
		BlueGreenTimeout:       bgTimeout,
		ErrorFeedbackConfig:    errorFeedbackConfig,
		CostConfig:             costConfig,
		EnableCostOptimization: c.Autoscaler.EnableCostOptimization,
		HistoryEnabled:         c.Autoscaler.HistoryEnabled,
		HistoryStoragePath:     c.Autoscaler.HistoryStoragePath,
	}, nil
}

func (c *Config) getCostConfig() *types.CostConfig {
	optInterval, _ := time.ParseDuration(c.Strategy.CostConfig.OptimizationInterval)
	if optInterval == 0 {
		optInterval = 1 * time.Hour
	}

	return &types.CostConfig{
		Enabled:              c.Strategy.CostConfig.Enabled,
		ReservedInstanceRatio: c.Strategy.CostConfig.ReservedInstanceRatio,
		MaxOnDemandInstances: c.Strategy.CostConfig.MaxOnDemandInstances,
		SpotInstanceEnabled:  c.Strategy.CostConfig.SpotInstanceEnabled,
		SpotMaxPrice:         c.Strategy.CostConfig.SpotMaxPrice,
		CostThreshold:        c.Strategy.CostConfig.CostThreshold,
		OptimizationInterval: optInterval,
	}
}

func (c *Config) GetPrometheusConfig() monitor.PrometheusConfig {
	timeout, _ := time.ParseDuration(c.Prometheus.Timeout)
	step, _ := time.ParseDuration(c.Prometheus.Step)
	lookback, _ := time.ParseDuration(c.Prometheus.Lookback)

	return monitor.PrometheusConfig{
		Address:  c.Prometheus.Address,
		Timeout:  timeout,
		Step:     step,
		Lookback: lookback,
	}
}

func (c *Config) GetPredictorConfig() predict.PredictorConfig {
	errorFeedbackConfig := types.ErrorFeedbackConfig{
		Enabled:        c.Prediction.ErrorFeedback.Enabled,
		WindowSize:     c.Prediction.ErrorFeedback.WindowSize,
		MinSamples:     c.Prediction.ErrorFeedback.MinSamples,
		MaxCorrection:  c.Prediction.ErrorFeedback.MaxCorrection,
		Alpha:          c.Prediction.ErrorFeedback.Alpha,
	}

	if c.Prediction.ErrorFeedback.UpdateInterval != "" {
		errorFeedbackConfig.UpdateInterval, _ = time.ParseDuration(c.Prediction.ErrorFeedback.UpdateInterval)
	}

	return predict.PredictorConfig{
		Method:          predict.PredictionMethod(c.Prediction.Method),
		WindowSize:      c.Prediction.WindowSize,
		Horizon:         c.Prediction.Horizon,
		Alpha:           c.Prediction.Alpha,
		Differencing:    c.Prediction.Differencing,
		AROrder:         c.Prediction.AROrder,
		MAOrder:         c.Prediction.MAOrder,
		ErrorFeedback:   errorFeedbackConfig,
	}
}

func (c *Config) GetStrategyConfig() (strategy.StrategyEngineConfig, error) {
	policies := make([]types.ScalingPolicy, len(c.Strategy.Policies))
	for i, p := range c.Strategy.Policies {
		cooldown, err := time.ParseDuration(p.CooldownPeriod)
		if err != nil {
			cooldown = 10 * time.Minute
		}

		serviceLevel := types.ServiceLevel(p.ServiceLevel)
		if serviceLevel == "" {
			serviceLevel = types.ServiceLevelMedium
		}

		policies[i] = types.ScalingPolicy{
			MetricType:     types.MetricType(p.MetricType),
			TargetValue:    p.TargetValue,
			Tolerance:      p.Tolerance,
			StepSize:       p.StepSize,
			CooldownPeriod: cooldown,
			MaxInstances:   p.MaxInstances,
			MinInstances:   p.MinInstances,
			MaxSize:        p.MaxSize,
			MinSize:        p.MinSize,
			ServiceLevel:   serviceLevel,
		}
	}

	serviceCooldowns := types.ServiceCooldownConfig{}
	if c.Strategy.ServiceCooldowns.Critical != "" {
		serviceCooldowns.Critical, _ = time.ParseDuration(c.Strategy.ServiceCooldowns.Critical)
	}
	if c.Strategy.ServiceCooldowns.High != "" {
		serviceCooldowns.High, _ = time.ParseDuration(c.Strategy.ServiceCooldowns.High)
	}
	if c.Strategy.ServiceCooldowns.Medium != "" {
		serviceCooldowns.Medium, _ = time.ParseDuration(c.Strategy.ServiceCooldowns.Medium)
	}
	if c.Strategy.ServiceCooldowns.Low != "" {
		serviceCooldowns.Low, _ = time.ParseDuration(c.Strategy.ServiceCooldowns.Low)
	}

	costConfig := c.getCostConfig()

	return strategy.StrategyEngineConfig{
		Policies:            policies,
		UsePrediction:       c.Strategy.UsePrediction,
		UseErrorCorrection:  c.Strategy.UseErrorCorrection,
		CooldownKey:         c.Strategy.CooldownKey,
		DefaultServiceLevel: types.ServiceLevel(c.Strategy.DefaultServiceLevel),
		ServiceCooldowns:    serviceCooldowns,
		CostConfig:          costConfig,
		CostOptimization:    c.Strategy.CostOptimization,
	}, nil
}

func (c *Config) GetCloudConfig() cloud.ProviderConfig {
	costConfig := c.getCostConfig()
	priceList := make(map[string]cloud.FlavorPrice)

	return cloud.ProviderConfig{
		Type:       types.CloudProvider(c.Cloud.Provider),
		Region:     c.Cloud.Region,
		AccessKey:  c.Cloud.AccessKey,
		SecretKey:  c.Cloud.SecretKey,
		AssumeRole: c.Cloud.AssumeRole,
		FlavorMap:  c.Cloud.FlavorMap,
		CostConfig: costConfig,
		PriceList:  priceList,
	}
}
