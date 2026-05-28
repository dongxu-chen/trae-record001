package config

import (
	"cross-cloud-lb/pkg/model"
	"fmt"
	"strings"
	"time"

	"github.com/spf13/viper"
)

func LoadConfig(configPath string) (*model.LoadBalancerConfig, error) {
	v := viper.New()
	v.SetConfigFile(configPath)
	v.SetConfigType("yaml")
	v.AutomaticEnv()
	v.SetEnvKeyReplacer(strings.NewReplacer(".", "_"))

	if err := v.ReadInConfig(); err != nil {
		return nil, fmt.Errorf("failed to read config: %w", err)
	}

	config := &model.LoadBalancerConfig{}
	if err := v.Unmarshal(config); err != nil {
		return nil, fmt.Errorf("failed to unmarshal config: %w", err)
	}

	if err := validateConfig(config); err != nil {
		return nil, fmt.Errorf("invalid config: %w", err)
	}

	setDefaults(config)

	return config, nil
}

func validateConfig(config *model.LoadBalancerConfig) error {
	if config.Name == "" {
		return fmt.Errorf("load balancer name is required")
	}

	if len(config.Listeners) == 0 {
		return fmt.Errorf("at least one listener is required")
	}

	for i, listener := range config.Listeners {
		if listener.Port == 0 {
			return fmt.Errorf("listener %d: port is required", i)
		}
		if listener.Protocol == "" {
			listener.Protocol = "http"
		}
	}

	for i, cluster := range config.Clusters {
		if cluster.ID == "" {
			return fmt.Errorf("cluster %d: id is required", i)
		}
		if cluster.Provider == "" {
			return fmt.Errorf("cluster %d: provider is required", i)
		}
		if cluster.Weight <= 0 {
			cluster.Weight = 10
		}
	}

	return nil
}

func setDefaults(config *model.LoadBalancerConfig) {
	if config.HealthCheck.Type == "" {
		config.HealthCheck.Type = "cloud_provider"
	}
	if config.HealthCheck.Interval == 0 {
		config.HealthCheck.Interval = 15 * time.Second
	}
	if config.HealthCheck.Timeout == 0 {
		config.HealthCheck.Timeout = 5 * time.Second
	}
	if config.HealthCheck.UnhealthyThreshold == 0 {
		config.HealthCheck.UnhealthyThreshold = 3
	}
	if config.HealthCheck.HealthyThreshold == 0 {
		config.HealthCheck.HealthyThreshold = 2
	}
	if config.HealthCheck.Path == "" {
		config.HealthCheck.Path = "/health"
	}
	if config.HealthCheck.Protocol == "" {
		config.HealthCheck.Protocol = "http"
	}

	if config.SessionAffinity.HeaderName == "" {
		config.SessionAffinity.HeaderName = "X-Gateway-ID"
	}
	if config.SessionAffinity.TTL == 0 {
		config.SessionAffinity.TTL = 3600 * time.Second
	}
	if config.SessionAffinity.Type == "" {
		config.SessionAffinity.Type = "header"
	}

	if config.TrafficMirroring.BasePercent == 0 && config.TrafficMirroring.Percent > 0 {
		config.TrafficMirroring.BasePercent = config.TrafficMirroring.Percent
	}
	if config.TrafficMirroring.Percent == 0 && config.TrafficMirroring.BasePercent > 0 {
		config.TrafficMirroring.Percent = config.TrafficMirroring.BasePercent
	}
	if config.TrafficMirroring.MinPercent == 0 {
		config.TrafficMirroring.MinPercent = 1.0
	}
	if config.TrafficMirroring.MaxPercent == 0 {
		config.TrafficMirroring.MaxPercent = 50.0
	}
	if config.TrafficMirroring.CircuitBreaker.FailureThreshold == 0 {
		config.TrafficMirroring.CircuitBreaker.FailureThreshold = 10
	}
	if config.TrafficMirroring.CircuitBreaker.ErrorRateThreshold == 0 {
		config.TrafficMirroring.CircuitBreaker.ErrorRateThreshold = 0.20
	}
	if config.TrafficMirroring.CircuitBreaker.SlowResponseThreshold == 0 {
		config.TrafficMirroring.CircuitBreaker.SlowResponseThreshold = 2000
	}
	if config.TrafficMirroring.CircuitBreaker.OpenDuration == 0 {
		config.TrafficMirroring.CircuitBreaker.OpenDuration = 30 * time.Second
	}
	if config.TrafficMirroring.CircuitBreaker.HalfOpenMaxRequests == 0 {
		config.TrafficMirroring.CircuitBreaker.HalfOpenMaxRequests = 5
	}

	if config.WeightAdjustment.AdjustInterval == 0 {
		config.WeightAdjustment.AdjustInterval = 30 * time.Second
	}
	if config.WeightAdjustment.ResponseTimeWeight == 0 {
		config.WeightAdjustment.ResponseTimeWeight = 0.7
	}
	if config.WeightAdjustment.ErrorRateWeight == 0 {
		config.WeightAdjustment.ErrorRateWeight = 0.3
	}
	if config.WeightAdjustment.StepSize == 0 {
		config.WeightAdjustment.StepSize = 5
	}

	if config.Failover.FailoverThreshold == 0 {
		config.Failover.FailoverThreshold = 3
	}
	if config.Failover.RecoveryThreshold == 0 {
		config.Failover.RecoveryThreshold = 5
	}
	if config.Failover.CheckInterval == 0 {
		config.Failover.CheckInterval = 10 * time.Second
	}

	if config.Cost.WeightInfluence == 0 {
		config.Cost.WeightInfluence = 0.3
	}

	if config.Prediction.PredictionInterval == 0 {
		config.Prediction.PredictionInterval = 5 * time.Minute
	}
	if config.Prediction.PredictionHorizon == 0 {
		config.Prediction.PredictionHorizon = 30 * time.Minute
	}
	if config.Prediction.WeightInfluence == 0 {
		config.Prediction.WeightInfluence = 0.2
	}
	if config.Prediction.MinHistorySamples == 0 {
		config.Prediction.MinHistorySamples = 12
	}

	if config.Proximity.WeightInfluence == 0 {
		config.Proximity.WeightInfluence = 0.3
	}
	if config.Proximity.GeoIPProvider == "" {
		config.Proximity.GeoIPProvider = "local"
	}

	for _, cluster := range config.Clusters {
		if cluster.MinWeight == 0 {
			cluster.MinWeight = 1
		}
		if cluster.MaxWeight == 0 {
			cluster.MaxWeight = 100
		}
		if cluster.Status == "" {
			cluster.Status = model.ClusterActive
		}
	}
}

func LoadProviderConfigs(configPath string) ([]model.CloudProvider, error) {
	v := viper.New()
	v.SetConfigFile(configPath)
	v.SetConfigType("yaml")
	v.AutomaticEnv()

	if err := v.ReadInConfig(); err != nil {
		return nil, fmt.Errorf("failed to read provider config: %w", err)
	}

	var providers []model.CloudProvider
	if err := v.UnmarshalKey("providers", &providers); err != nil {
		return nil, fmt.Errorf("failed to unmarshal providers: %w", err)
	}

	return providers, nil
}
