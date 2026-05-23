package metrics

import (
	"context"
	"fmt"
	"time"

	"github.com/prometheus/client_golang/api"
	v1 "github.com/prometheus/client_golang/api/prometheus/v1"
	"github.com/prometheus/common/model"
	"github.com/cloud-autoscaler/pkg/config"
)

const (
	DefaultCPUQuery    = `avg(100 - (rate(node_cpu_seconds_total{mode="idle"}[5m]) * 100))`
	DefaultMemoryQuery = `(1 - (node_memory_MemAvailable_bytes / node_memory_MemTotal_bytes)) * 100`
)

type PrometheusClient struct {
	client v1.API
	cfg    *config.PrometheusConfig
}

func NewPrometheusClient(cfg *config.PrometheusConfig) (*PrometheusClient, error) {
	client, err := api.NewClient(api.Config{
		Address: cfg.Address,
	})
	if err != nil {
		return nil, fmt.Errorf("failed to create Prometheus client: %w", err)
	}

	return &PrometheusClient{
		client: v1.NewAPI(client),
		cfg:    cfg,
	}, nil
}

func (p *PrometheusClient) GetCPUUtilization(ctx context.Context) (float64, error) {
	query := DefaultCPUQuery
	if p.cfg.CPUQuery != "" {
		query = p.cfg.CPUQuery
	}
	return p.query(ctx, query)
}

func (p *PrometheusClient) GetMemoryUtilization(ctx context.Context) (float64, error) {
	query := DefaultMemoryQuery
	if p.cfg.MemQuery != "" {
		query = p.cfg.MemQuery
	}
	return p.query(ctx, query)
}

func (p *PrometheusClient) GetCustomMetric(ctx context.Context, query string) (float64, error) {
	return p.query(ctx, query)
}

func (p *PrometheusClient) query(ctx context.Context, query string) (float64, error) {
	ctx, cancel := context.WithTimeout(ctx, p.cfg.Timeout)
	defer cancel()

	result, warnings, err := p.client.Query(ctx, query, time.Now())
	if err != nil {
		return 0, fmt.Errorf("failed to execute Prometheus query: %w", err)
	}
	if len(warnings) > 0 {
	}

	vector, ok := result.(model.Vector)
	if !ok {
		return 0, fmt.Errorf("unexpected result type: %T", result)
	}

	if len(vector) == 0 {
		return 0, fmt.Errorf("no data returned from Prometheus")
	}

	return float64(vector[0].Value), nil
}

func (p *PrometheusClient) GetMetrics(ctx context.Context) (cpu, memory float64, err error) {
	cpu, err = p.GetCPUUtilization(ctx)
	if err != nil {
		return 0, 0, fmt.Errorf("failed to get CPU utilization: %w", err)
	}

	memory, err = p.GetMemoryUtilization(ctx)
	if err != nil {
		return cpu, 0, fmt.Errorf("failed to get memory utilization: %w", err)
	}

	return cpu, memory, nil
}
