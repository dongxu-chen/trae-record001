package cloud

import (
	"context"
	"fmt"
	"sync"

	"github.com/cloud-autoscaler/pkg/config"
)

type HybridProvider struct {
	cfg         *config.HybridConfig
	providers   map[string]Provider
	weights     map[string]int
	totalWeight int
	mu          sync.Mutex
}

func init() {
	RegisterProvider("hybrid", NewHybridProvider)
}

func NewHybridProvider(cfg ProviderConfig) (Provider, error) {
	return nil, fmt.Errorf("hybrid provider must be created via NewHybridProviderFromConfig")
}

func NewHybridProviderFromConfig(cfg *config.Config) (Provider, error) {
	if !cfg.Hybrid.Enabled {
		return nil, fmt.Errorf("hybrid mode is not enabled")
	}

	providers := make(map[string]Provider)
	weights := make(map[string]int)
	totalWeight := 0

	for _, hp := range cfg.Hybrid.Providers {
		providerCfg := NewHybridProviderConfig(hp)
		provider, err := NewProviderFromConfig(providerCfg)
		if err != nil {
			return nil, fmt.Errorf("failed to create provider %s: %w", hp.Name, err)
		}

		providers[hp.Name] = provider
		weights[hp.Name] = hp.Weight
		totalWeight += hp.Weight
	}

	return &HybridProvider{
		cfg:         &cfg.Hybrid,
		providers:   providers,
		weights:     weights,
		totalWeight: totalWeight,
	}, nil
}

func NewProviderFromConfig(cfg ProviderConfig) (Provider, error) {
	factory, exists := providers[cfg.Provider]
	if !exists {
		return nil, fmt.Errorf("unsupported cloud provider: %s", cfg.Provider)
	}
	return factory(cfg)
}

func (p *HybridProvider) GetName() string {
	return "hybrid"
}

func (p *HybridProvider) GetInstances(ctx context.Context) ([]Instance, error) {
	p.mu.Lock()
	defer p.mu.Unlock()

	var allInstances []Instance
	var wg sync.WaitGroup
	var mu sync.Mutex
	errChan := make(chan error, len(p.providers))

	for name, provider := range p.providers {
		wg.Add(1)
		go func(name string, provider Provider) {
			defer wg.Done()
			instances, err := provider.GetInstances(ctx)
			if err != nil {
				errChan <- fmt.Errorf("provider %s: %w", name, err)
				return
			}
			mu.Lock()
			allInstances = append(allInstances, instances...)
			mu.Unlock()
		}(name, provider)
	}

	wg.Wait()
	close(errChan)

	if len(errChan) > 0 {
		return allInstances, <-errChan
	}

	return allInstances, nil
}

func (p *HybridProvider) GetInstanceCount(ctx context.Context) (int, error) {
	instances, err := p.GetInstances(ctx)
	if err != nil {
		return 0, err
	}
	return len(instances), nil
}

func (p *HybridProvider) ScaleUp(ctx context.Context, count int) error {
	p.mu.Lock()
	defer p.mu.Unlock()

	distribution := p.distributeInstances(count)

	var wg sync.WaitGroup
	errChan := make(chan error, len(distribution))

	for name, num := range distribution {
		if num <= 0 {
			continue
		}
		wg.Add(1)
		go func(name string, num int) {
			defer wg.Done()
			provider := p.providers[name]
			if err := provider.ScaleUp(ctx, num); err != nil {
				errChan <- fmt.Errorf("provider %s: %w", name, err)
			}
		}(name, num)
	}

	wg.Wait()
	close(errChan)

	if len(errChan) > 0 {
		return <-errChan
	}

	return nil
}

func (p *HybridProvider) ScaleDown(ctx context.Context, count int) error {
	p.mu.Lock()
	defer p.mu.Unlock()

	distribution := p.distributeInstances(count)

	var wg sync.WaitGroup
	errChan := make(chan error, len(distribution))

	for name, num := range distribution {
		if num <= 0 {
			continue
		}
		wg.Add(1)
		go func(name string, num int) {
			defer wg.Done()
			provider := p.providers[name]
			if err := provider.ScaleDown(ctx, num); err != nil {
				errChan <- fmt.Errorf("provider %s: %w", name, err)
			}
		}(name, num)
	}

	wg.Wait()
	close(errChan)

	if len(errChan) > 0 {
		return <-errChan
	}

	return nil
}

func (p *HybridProvider) GetMetrics(ctx context.Context) (cpu, memory float64, err error) {
	return 0, 0, fmt.Errorf("metrics should be retrieved via Prometheus")
}

func (p *HybridProvider) distributeInstances(count int) map[string]int {
	distribution := make(map[string]int)
	remaining := count

	switch p.cfg.Allocation.Strategy {
	case "weighted":
		for name, weight := range p.weights {
			alloc := (count * weight) / p.totalWeight
			distribution[name] = alloc
			remaining -= alloc
		}
		if remaining > 0 {
			for name := range p.providers {
				if remaining <= 0 {
					break
				}
				distribution[name]++
				remaining--
			}
		}
	default:
		perProvider := count / len(p.providers)
		remaining = count % len(p.providers)
		for name := range p.providers {
			distribution[name] = perProvider
			if remaining > 0 {
				distribution[name]++
				remaining--
			}
		}
	}

	return distribution
}
