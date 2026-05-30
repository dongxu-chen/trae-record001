package config

import (
	"fmt"
	"os"
	"time"

	"gopkg.in/yaml.v3"
)

type KafkaConfig struct {
	Brokers []string      `yaml:"brokers"`
	Timeout time.Duration `yaml:"timeout"`
}

type KubernetesConfig struct {
	InCluster      bool   `yaml:"inCluster"`
	KubeConfigPath string `yaml:"kubeConfigPath"`
}

type PrometheusConfig struct {
	ListenAddress  string        `yaml:"listenAddress"`
	ScrapeInterval time.Duration `yaml:"scrapeInterval"`
	MaxHistorySize int           `yaml:"maxHistorySize"`
}

type AutoscalerConfig struct {
	ConsumerGroupID             string        `yaml:"consumerGroupID"`
	K8sDeployment               string        `yaml:"k8sDeployment"`
	K8sNamespace                string        `yaml:"k8sNamespace"`
	K8sResourceType             string        `yaml:"k8sResourceType"`
	MinReplicas                 int32         `yaml:"minReplicas"`
	MaxReplicas                 int32         `yaml:"maxReplicas"`
	ScaleUpThreshold            int64         `yaml:"scaleUpThreshold"`
	ScaleDownThreshold          int64         `yaml:"scaleDownThreshold"`
	ScaleUpIncrement            int32         `yaml:"scaleUpIncrement"`
	ScaleDownDecrement          int32         `yaml:"scaleDownDecrement"`
	CooldownPeriod              time.Duration `yaml:"cooldownPeriod"`
	PredictionWindow            time.Duration `yaml:"predictionWindow"`
	UsePrediction               bool          `yaml:"usePrediction"`
	TargetLag                   int64         `yaml:"targetLag"`
	Mode                        string        `yaml:"mode"`
	EnablePartitionRebalance    bool          `yaml:"enablePartitionRebalance"`
	EnableRollingScale          bool          `yaml:"enableRollingScale"`
	RollingScaleInterval        time.Duration `yaml:"rollingScaleInterval"`
	MessageProcessingLatency    time.Duration `yaml:"messageProcessingLatency"`
	EnableScaleDownAfterLagClear bool         `yaml:"enableScaleDownAfterLagClear"`
	ScaleDownAfterLagDelay      time.Duration `yaml:"scaleDownAfterLagDelay"`
	EnableSelfHealing           bool          `yaml:"enableSelfHealing"`
	SelfHealingThreshold        int           `yaml:"selfHealingThreshold"`
	SelfHealingCooldown         time.Duration `yaml:"selfHealingCooldown"`
	EnableSlowPartitionDetection bool         `yaml:"enableSlowPartitionDetection"`
	SlowPartitionThreshold      time.Duration `yaml:"slowPartitionThreshold"`
}

type RebalancerConfig struct {
	Enabled               bool              `yaml:"enabled"`
	Strategy              string            `yaml:"strategy"`
	RebalanceInterval     time.Duration     `yaml:"rebalanceInterval"`
	DryRun                bool              `yaml:"dryRun"`
	EnableUnevenDetection bool              `yaml:"enableUnevenDetection"`
	UnevenThresholdRatio  float64           `yaml:"unevenThresholdRatio"`
	MinPartitionCount     int               `yaml:"minPartitionCount"`
	MaxConcurrentMoves    int               `yaml:"maxConcurrentMoves"`
	KeyPrefixDelimiter    string            `yaml:"keyPrefixDelimiter"`
}

type LogConfig struct {
	Level  string `yaml:"level"`
	Format string `yaml:"format"`
}

type AppConfig struct {
	Kafka       KafkaConfig        `yaml:"kafka"`
	Kubernetes  KubernetesConfig   `yaml:"kubernetes"`
	Prometheus  PrometheusConfig   `yaml:"prometheus"`
	Autoscalers []AutoscalerConfig `yaml:"autoscalers"`
	Rebalancer  RebalancerConfig   `yaml:"rebalancer"`
	Log         LogConfig          `yaml:"log"`
}

func LoadConfig(path string) (*AppConfig, error) {
	data, err := os.ReadFile(path)
	if err != nil {
		return nil, fmt.Errorf("failed to read config file: %w", err)
	}

	var config AppConfig
	if err := yaml.Unmarshal(data, &config); err != nil {
		return nil, fmt.Errorf("failed to parse config file: %w", err)
	}

	if err := config.validate(); err != nil {
		return nil, fmt.Errorf("config validation failed: %w", err)
	}

	config.setDefaults()

	return &config, nil
}

func (c *AppConfig) validate() error {
	if len(c.Kafka.Brokers) == 0 {
		return fmt.Errorf("kafka brokers are required")
	}

	if len(c.Autoscalers) == 0 {
		return fmt.Errorf("at least one autoscaler configuration is required")
	}

	for i, scaler := range c.Autoscalers {
		if scaler.ConsumerGroupID == "" {
			return fmt.Errorf("autoscaler[%d]: consumerGroupID is required", i)
		}
		if scaler.K8sDeployment == "" {
			return fmt.Errorf("autoscaler[%d]: k8sDeployment is required", i)
		}
		if scaler.MinReplicas < 0 {
			return fmt.Errorf("autoscaler[%d]: minReplicas cannot be negative", i)
		}
		if scaler.MaxReplicas < scaler.MinReplicas {
			return fmt.Errorf("autoscaler[%d]: maxReplicas must be >= minReplicas", i)
		}
		if scaler.ScaleUpThreshold <= 0 {
			return fmt.Errorf("autoscaler[%d]: scaleUpThreshold must be positive", i)
		}
		if scaler.ScaleDownThreshold < 0 {
			return fmt.Errorf("autoscaler[%d]: scaleDownThreshold cannot be negative", i)
		}
		if scaler.ScaleUpThreshold <= scaler.ScaleDownThreshold {
			return fmt.Errorf("autoscaler[%d]: scaleUpThreshold must be > scaleDownThreshold", i)
		}
	}

	return nil
}

func (c *AppConfig) setDefaults() {
	if c.Kafka.Timeout == 0 {
		c.Kafka.Timeout = 30 * time.Second
	}

	if c.Prometheus.ListenAddress == "" {
		c.Prometheus.ListenAddress = ":9090"
	}
	if c.Prometheus.ScrapeInterval == 0 {
		c.Prometheus.ScrapeInterval = 30 * time.Second
	}
	if c.Prometheus.MaxHistorySize == 0 {
		c.Prometheus.MaxHistorySize = 1000
	}

	for i := range c.Autoscalers {
		if c.Autoscalers[i].K8sNamespace == "" {
			c.Autoscalers[i].K8sNamespace = "default"
		}
		if c.Autoscalers[i].K8sResourceType == "" {
			c.Autoscalers[i].K8sResourceType = "deployment"
		}
		if c.Autoscalers[i].MinReplicas == 0 {
			c.Autoscalers[i].MinReplicas = 1
		}
		if c.Autoscalers[i].ScaleUpIncrement == 0 {
			c.Autoscalers[i].ScaleUpIncrement = 1
		}
		if c.Autoscalers[i].ScaleDownDecrement == 0 {
			c.Autoscalers[i].ScaleDownDecrement = 1
		}
		if c.Autoscalers[i].CooldownPeriod == 0 {
			c.Autoscalers[i].CooldownPeriod = 5 * time.Minute
		}
		if c.Autoscalers[i].PredictionWindow == 0 {
			c.Autoscalers[i].PredictionWindow = 5 * time.Minute
		}
		if c.Autoscalers[i].Mode == "" {
			c.Autoscalers[i].Mode = "observation"
		}
		if c.Autoscalers[i].RollingScaleInterval == 0 {
			c.Autoscalers[i].RollingScaleInterval = 2 * time.Minute
		}
		if c.Autoscalers[i].MessageProcessingLatency == 0 {
			c.Autoscalers[i].MessageProcessingLatency = 100 * time.Millisecond
		}
		if c.Autoscalers[i].ScaleDownAfterLagDelay == 0 {
			c.Autoscalers[i].ScaleDownAfterLagDelay = 10 * time.Minute
		}
		if c.Autoscalers[i].SelfHealingThreshold == 0 {
			c.Autoscalers[i].SelfHealingThreshold = 3
		}
		if c.Autoscalers[i].SelfHealingCooldown == 0 {
			c.Autoscalers[i].SelfHealingCooldown = 30 * time.Minute
		}
		if c.Autoscalers[i].SlowPartitionThreshold == 0 {
			c.Autoscalers[i].SlowPartitionThreshold = 2 * time.Minute
		}
	}

	if c.Rebalancer.Strategy == "" {
		c.Rebalancer.Strategy = "sticky"
	}
	if c.Rebalancer.RebalanceInterval == 0 {
		c.Rebalancer.RebalanceInterval = 15 * time.Minute
	}
	if c.Rebalancer.UnevenThresholdRatio == 0 {
		c.Rebalancer.UnevenThresholdRatio = 2.0
	}
	if c.Rebalancer.MinPartitionCount == 0 {
		c.Rebalancer.MinPartitionCount = 5
	}
	if c.Rebalancer.MaxConcurrentMoves == 0 {
		c.Rebalancer.MaxConcurrentMoves = 3
	}
	if c.Rebalancer.KeyPrefixDelimiter == "" {
		c.Rebalancer.KeyPrefixDelimiter = ":"
	}

	if c.Log.Level == "" {
		c.Log.Level = "info"
	}
	if c.Log.Format == "" {
		c.Log.Format = "json"
	}
}

func (c *AppConfig) Save(path string) error {
	data, err := yaml.Marshal(c)
	if err != nil {
		return fmt.Errorf("failed to marshal config: %w", err)
	}

	if err := os.WriteFile(path, data, 0644); err != nil {
		return fmt.Errorf("failed to write config file: %w", err)
	}

	return nil
}
