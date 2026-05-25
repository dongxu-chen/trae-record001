package monitor

import (
	"context"
	"fmt"
	"time"

	"github.com/prometheus/client_golang/api"
	v1 "github.com/prometheus/client_golang/api/prometheus/v1"
	"github.com/prometheus/common/model"
	"go.uber.org/zap"

	"autoscaler/internal/types"
)

type PrometheusConfig struct {
	Address  string
	Timeout  time.Duration
	Step     time.Duration
	Lookback time.Duration
}

type PrometheusClient struct {
	api    v1.API
	config PrometheusConfig
	logger *zap.Logger
}

func NewPrometheusClient(config PrometheusConfig, logger *zap.Logger) (*PrometheusClient, error) {
	client, err := api.NewClient(api.Config{
		Address: config.Address,
	})
	if err != nil {
		return nil, fmt.Errorf("failed to create prometheus client: %w", err)
	}

	if config.Timeout == 0 {
		config.Timeout = 30 * time.Second
	}
	if config.Step == 0 {
		config.Step = 15 * time.Second
	}
	if config.Lookback == 0 {
		config.Lookback = 1 * time.Hour
	}

	return &PrometheusClient{
		api:    v1.NewAPI(client),
		config: config,
		logger: logger,
	}, nil
}

func (p *PrometheusClient) QueryMetric(ctx context.Context, query string) (float64, error) {
	ctx, cancel := context.WithTimeout(ctx, p.config.Timeout)
	defer cancel()

	result, _, err := p.api.Query(ctx, query, time.Now())
	if err != nil {
		return 0, fmt.Errorf("query failed: %w", err)
	}

	vector, ok := result.(model.Vector)
	if !ok {
		return 0, fmt.Errorf("unexpected result type: %T", result)
	}

	if len(vector) == 0 {
		return 0, fmt.Errorf("no data returned for query: %s", query)
	}

	return float64(vector[0].Value), nil
}

func (p *PrometheusClient) QueryRange(ctx context.Context, query string, start, end time.Time) ([]types.MetricValue, error) {
	ctx, cancel := context.WithTimeout(ctx, p.config.Timeout)
	defer cancel()

	r := v1.Range{
		Start: start,
		End:   end,
		Step:  p.config.Step,
	}

	result, _, err := p.api.QueryRange(ctx, query, r)
	if err != nil {
		return nil, fmt.Errorf("range query failed: %w", err)
	}

	matrix, ok := result.(model.Matrix)
	if !ok {
		return nil, fmt.Errorf("unexpected result type: %T", result)
	}

	if len(matrix) == 0 {
		return nil, fmt.Errorf("no data returned for query: %s", query)
	}

	values := make([]types.MetricValue, 0, len(matrix[0].Values))
	for _, v := range matrix[0].Values {
		values = append(values, types.MetricValue{
			Timestamp: v.Timestamp.Time(),
			Value:     float64(v.Value),
		})
	}

	return values, nil
}

func (p *PrometheusClient) GetCPUUtilization(ctx context.Context, instanceID string) (*types.MetricData, error) {
	query := fmt.Sprintf(`100 - (avg by (instance_id) (rate(node_cpu_seconds_total{mode="idle", instance_id="%s"}[5m])) * 100)`, instanceID)
	return p.getMetricData(ctx, instanceID, types.MetricCPU, query)
}

func (p *PrometheusClient) GetMemoryUtilization(ctx context.Context, instanceID string) (*types.MetricData, error) {
	query := fmt.Sprintf(`(1 - (node_memory_MemAvailable_bytes{instance_id="%s"} / node_memory_MemTotal_bytes{instance_id="%s"})) * 100`, instanceID, instanceID)
	return p.getMetricData(ctx, instanceID, types.MetricMemory, query)
}

func (p *PrometheusClient) GetNetworkThroughput(ctx context.Context, instanceID string) (*types.MetricData, error) {
	query := fmt.Sprintf(`rate(node_network_receive_bytes_total{instance_id="%s"}[5m]) + rate(node_network_transmit_bytes_total{instance_id="%s"}[5m])`, instanceID, instanceID)
	return p.getMetricData(ctx, instanceID, types.MetricNetwork, query)
}

func (p *PrometheusClient) getMetricData(ctx context.Context, instanceID string, metricType types.MetricType, query string) (*types.MetricData, error) {
	end := time.Now()
	start := end.Add(-p.config.Lookback)

	values, err := p.QueryRange(ctx, query, start, end)
	if err != nil {
		p.logger.Warn("failed to query range, trying instant query", zap.Error(err))
		current, err := p.QueryMetric(ctx, query)
		if err != nil {
			return nil, err
		}
		return &types.MetricData{
			InstanceID: instanceID,
			MetricType: metricType,
			Values:     []types.MetricValue{{Timestamp: time.Now(), Value: current}},
			Current:    current,
		}, nil
	}

	current := values[len(values)-1].Value

	return &types.MetricData{
		InstanceID: instanceID,
		MetricType: metricType,
		Values:     values,
		Current:    current,
	}, nil
}

func (p *PrometheusClient) GetAggregatedMetric(ctx context.Context, instanceIDs []string, metricType types.MetricType) (*types.MetricData, error) {
	if len(instanceIDs) == 0 {
		return nil, fmt.Errorf("no instances provided")
	}

	var query string
	switch metricType {
	case types.MetricCPU:
		query = `100 - (avg by (job) (rate(node_cpu_seconds_total{mode="idle"}[5m])) * 100)`
	case types.MetricMemory:
		query = `(1 - (avg by (job) (node_memory_MemAvailable_bytes / node_memory_MemTotal_bytes))) * 100`
	case types.MetricNetwork:
		query = `avg by (job) (rate(node_network_receive_bytes_total[5m]) + rate(node_network_transmit_bytes_total[5m]))`
	default:
		return nil, fmt.Errorf("unsupported metric type: %s", metricType)
	}

	return p.getMetricData(ctx, "aggregated", metricType, query)
}
