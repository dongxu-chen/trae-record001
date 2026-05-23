package config

import (
	"fmt"
	"os"
	"time"

	"gopkg.in/yaml.v2"
)

const (
	MinMetricsInterval = 5 * time.Second
	MaxMetricsInterval = 60 * time.Second
)

type Config struct {
	Prometheus PrometheusConfig `yaml:"prometheus"`
	Scaling    ScalingConfig    `yaml:"scaling"`
	Cloud      CloudConfig      `yaml:"cloud"`
	Hybrid     HybridConfig     `yaml:"hybrid,omitempty"`
	Prediction PredictionConfig `yaml:"prediction"`
	History    HistoryConfig    `yaml:"history"`
	Cost       CostConfig       `yaml:"cost"`
}

type PrometheusConfig struct {
	Address  string        `yaml:"address"`
	Query    string        `yaml:"query"`
	Interval time.Duration `yaml:"interval"`
	Timeout  time.Duration `yaml:"timeout"`
	CPUQuery string        `yaml:"cpu_query,omitempty"`
	MemQuery string        `yaml:"mem_query,omitempty"`
}

type ScalingConfig struct {
	TargetCPUUtilization    float64       `yaml:"target_cpu_utilization"`
	TargetMemoryUtilization float64       `yaml:"target_memory_utilization"`
	MinInstances            int           `yaml:"min_instances"`
	MaxInstances            int           `yaml:"max_instances"`
	CooldownPeriod          time.Duration `yaml:"cooldown_period"`
	ScaleUpThreshold        float64       `yaml:"scale_up_threshold"`
	ScaleDownThreshold      float64       `yaml:"scale_down_threshold"`
	SlidingWindowSize       int           `yaml:"sliding_window_size"`
	Mode                    string        `yaml:"mode"`
}

type PredictionConfig struct {
	Enabled            bool   `yaml:"enabled"`
	Mode               string `yaml:"mode"`
	HistorySize        int    `yaml:"history_size"`
	PredictionSteps    int    `yaml:"prediction_steps"`
	MinConfidence      float64 `yaml:"min_confidence"`
	LeadTimeMinutes    int    `yaml:"lead_time_minutes"`
}

type HistoryConfig struct {
	Enabled     bool   `yaml:"enabled"`
	FilePath    string `yaml:"file_path"`
	MaxRecords  int    `yaml:"max_records"`
}

type CostConfig struct {
	Enabled              bool    `yaml:"enabled"`
	IdleThreshold        float64 `yaml:"idle_threshold"`
	UnderutilThreshold   float64 `yaml:"underutil_threshold"`
	OptimizationEnabled  bool    `yaml:"optimization_enabled"`
}

type CloudConfig struct {
	Provider       string                 `yaml:"provider"`
	InstanceGroup  string                 `yaml:"instance_group"`
	Credentials    CredentialsConfig      `yaml:"credentials"`
	Infrastructure InfrastructureConfig   `yaml:"infrastructure"`
	ScalingGroup   string                 `yaml:"scaling_group_id,omitempty"`
}

type CredentialsConfig struct {
	AccessKeyID     string `yaml:"access_key_id,omitempty"`
	AccessKeySecret string `yaml:"access_key_secret,omitempty"`
	SecretID        string `yaml:"secret_id,omitempty"`
	SecretKey       string `yaml:"secret_key,omitempty"`
	Region          string `yaml:"region"`
}

type InfrastructureConfig struct {
	ImageID         string `yaml:"image_id"`
	InstanceType    string `yaml:"instance_type"`
	SecurityGroupID string `yaml:"security_group_id"`
	SubnetID        string `yaml:"subnet_id"`
	KeyID           string `yaml:"key_id,omitempty"`
	UserData        string `yaml:"user_data,omitempty"`
}

type HybridConfig struct {
	Enabled    bool                   `yaml:"enabled"`
	Providers  []HybridProviderConfig `yaml:"providers"`
	Allocation HybridAllocation       `yaml:"allocation"`
}

type HybridProviderConfig struct {
	Name           string                 `yaml:"name"`
	Provider       string                 `yaml:"provider"`
	Weight         int                    `yaml:"weight"`
	Credentials    CredentialsConfig      `yaml:"credentials"`
	Infrastructure InfrastructureConfig   `yaml:"infrastructure"`
	ScalingGroup   string                 `yaml:"scaling_group_id,omitempty"`
}

type HybridAllocation struct {
	Strategy string `yaml:"strategy"`
}

func Load(path string) (*Config, error) {
	data, err := os.ReadFile(path)
	if err != nil {
		return nil, fmt.Errorf("failed to read config file: %w", err)
	}

	var cfg Config
	if err := yaml.Unmarshal(data, &cfg); err != nil {
		return nil, fmt.Errorf("failed to parse config: %w", err)
	}

	if err := cfg.Validate(); err != nil {
		return nil, fmt.Errorf("invalid config: %w", err)
	}

	return &cfg, nil
}

func (c *Config) Validate() error {
	if c.Prometheus.Address == "" {
		return fmt.Errorf("prometheus address is required")
	}

	if c.Prometheus.Interval < MinMetricsInterval {
		return fmt.Errorf("metrics interval must be at least %v", MinMetricsInterval)
	}
	if c.Prometheus.Interval > MaxMetricsInterval {
		return fmt.Errorf("metrics interval must be at most %v", MaxMetricsInterval)
	}

	if c.Scaling.SlidingWindowSize <= 0 {
		return fmt.Errorf("sliding_window_size must be > 0")
	}

	if c.Scaling.MinInstances < 0 {
		return fmt.Errorf("min_instances must be >= 0")
	}
	if c.Scaling.MaxInstances < c.Scaling.MinInstances {
		return fmt.Errorf("max_instances must be >= min_instances")
	}
	if c.Cloud.Provider == "" {
		return fmt.Errorf("cloud provider is required")
	}
	if c.Cloud.InstanceGroup == "" {
		return fmt.Errorf("instance_group name is required")
	}
	return nil
}
