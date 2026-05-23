package cloud

import (
	"context"
	"fmt"
	"time"

	"github.com/cloud-autoscaler/pkg/config"
)

type Instance struct {
	ID                string    `json:"id"`
	Name              string    `json:"name"`
	Status            string    `json:"status"`
	Region            string    `json:"region"`
	InstanceType      string    `json:"instance_type"`
	PrivateIP         string    `json:"private_ip"`
	PublicIP          string    `json:"public_ip"`
	CreationTime      time.Time `json:"creation_time"`
	CPUUtilization    float64   `json:"cpu_utilization"`
	MemoryUtilization float64   `json:"memory_utilization"`
	Provider          string    `json:"provider"`
}

type ProviderConfig struct {
	Provider       string
	Region         string
	Credentials    config.CredentialsConfig
	Infrastructure config.InfrastructureConfig
	ScalingGroupID string
}

type Provider interface {
	GetName() string
	GetInstances(ctx context.Context) ([]Instance, error)
	GetInstanceCount(ctx context.Context) (int, error)
	ScaleUp(ctx context.Context, count int) error
	ScaleDown(ctx context.Context, count int) error
	GetMetrics(ctx context.Context) (cpu, memory float64, err error)
}

type ProviderFactory func(cfg ProviderConfig) (Provider, error)

var providers = make(map[string]ProviderFactory)

func RegisterProvider(name string, factory ProviderFactory) {
	providers[name] = factory
}

func NewProvider(cfg *config.Config) (Provider, error) {
	factory, exists := providers[cfg.Cloud.Provider]
	if !exists {
		return nil, fmt.Errorf("unsupported cloud provider: %s", cfg.Cloud.Provider)
	}

	providerCfg := ProviderConfig{
		Provider:       cfg.Cloud.Provider,
		Region:         cfg.Cloud.Credentials.Region,
		Credentials:    cfg.Cloud.Credentials,
		Infrastructure: cfg.Cloud.Infrastructure,
		ScalingGroupID: cfg.Cloud.ScalingGroup,
	}

	return factory(providerCfg)
}

func NewHybridProviderConfig(hp config.HybridProviderConfig) ProviderConfig {
	return ProviderConfig{
		Provider:       hp.Provider,
		Region:         hp.Credentials.Region,
		Credentials:    hp.Credentials,
		Infrastructure: hp.Infrastructure,
		ScalingGroupID: hp.ScalingGroup,
	}
}
