package monitor

import (
	"context"
	"fmt"
	"time"

	"github.com/prometheus/client_golang/api"
	promv1 "github.com/prometheus/client_golang/api/prometheus/v1"
	"github.com/prometheus/common/model"

	"container-autoscaler/pkg/config"
	"container-autoscaler/pkg/types"
	"container-autoscaler/pkg/utils"
)

type PrometheusMonitor struct {
	client promv1.API
	config config.PrometheusConfig
	logger *utils.Logger
}

func NewPrometheusMonitor(cfg config.PrometheusConfig, logger *utils.Logger) (*PrometheusMonitor, error) {
	client, err := api.NewClient(api.Config{
		Address: cfg.Address,
	})
	if err != nil {
		return nil, fmt.Errorf("creating prometheus client: %w", err)
	}

	v1api := promv1.NewAPI(client)

	return &PrometheusMonitor{
		client: v1api,
		config: cfg,
		logger: logger,
	}, nil
}

func (m *PrometheusMonitor) GetContainerMetrics(ctx context.Context, namespace string) ([]types.ResourceMetrics, error) {
	end := time.Now()
	start := end.Add(-m.config.QueryRange)
	step := m.config.StepSize

	m.logger.Debug("Querying Prometheus for namespace: %s, range: %s to %s, step: %s",
		namespace, start.Format(time.RFC3339), end.Format(time.RFC3339), step)

	cpuQuery := fmt.Sprintf(
		`sum(rate(container_cpu_usage_seconds_total{container!="POD", container!="", namespace="%s"}[5m])) by (pod, container, namespace)`,
		namespace,
	)
	memoryQuery := fmt.Sprintf(
		`container_memory_working_set_bytes{container!="POD", container!="", namespace="%s"}`,
		namespace,
	)
	cpuLimitQuery := fmt.Sprintf(
		`container_spec_cpu_quota{container!="POD", container!="", namespace="%s"}`,
		namespace,
	)
	memoryLimitQuery := fmt.Sprintf(
		`container_spec_memory_limit_bytes{container!="POD", container!="", namespace="%s"}`,
		namespace,
	)

	cpuData, err := m.queryRange(ctx, cpuQuery, start, end, step)
	if err != nil {
		return nil, fmt.Errorf("querying cpu metrics: %w", err)
	}

	memoryData, err := m.queryRange(ctx, memoryQuery, start, end, step)
	if err != nil {
		return nil, fmt.Errorf("querying memory metrics: %w", err)
	}

	cpuLimitData, err := m.queryRange(ctx, cpuLimitQuery, start, end, step)
	if err != nil {
		return nil, fmt.Errorf("querying cpu limits: %w", err)
	}

	memoryLimitData, err := m.queryRange(ctx, memoryLimitQuery, start, end, step)
	if err != nil {
		return nil, fmt.Errorf("querying memory limits: %w", err)
	}

	metricsMap := make(map[string]*types.ResourceMetrics)

	for _, stream := range cpuData {
		pod := string(stream.Metric["pod"])
		container := string(stream.Metric["container"])
		ns := string(stream.Metric["namespace"])
		key := fmt.Sprintf("%s/%s/%s", ns, pod, container)

		if _, exists := metricsMap[key]; !exists {
			metricsMap[key] = &types.ResourceMetrics{
				PodName:       pod,
				Namespace:     ns,
				ContainerName: container,
			}
		}

		if len(stream.Values) > 0 {
			lastVal := stream.Values[len(stream.Values)-1]
			metricsMap[key].CPUUsage = float64(lastVal.Value) * 1000
			metricsMap[key].Timestamp = lastVal.Timestamp.Time()
		}
	}

	for _, stream := range memoryData {
		pod := string(stream.Metric["pod"])
		container := string(stream.Metric["container"])
		ns := string(stream.Metric["namespace"])
		key := fmt.Sprintf("%s/%s/%s", ns, pod, container)

		if _, exists := metricsMap[key]; !exists {
			metricsMap[key] = &types.ResourceMetrics{
				PodName:       pod,
				Namespace:     ns,
				ContainerName: container,
			}
		}

		if len(stream.Values) > 0 {
			lastVal := stream.Values[len(stream.Values)-1]
			metricsMap[key].MemoryUsage = float64(lastVal.Value) / (1024 * 1024)
		}
	}

	for _, stream := range cpuLimitData {
		pod := string(stream.Metric["pod"])
		container := string(stream.Metric["container"])
		ns := string(stream.Metric["namespace"])
		key := fmt.Sprintf("%s/%s/%s", ns, pod, container)

		if _, exists := metricsMap[key]; !exists {
			continue
		}

		if len(stream.Values) > 0 {
			lastVal := stream.Values[len(stream.Values)-1]
			quota := float64(lastVal.Value)
			metricsMap[key].CPULimit = quota / 100000 * 1000
		}
	}

	for _, stream := range memoryLimitData {
		pod := string(stream.Metric["pod"])
		container := string(stream.Metric["container"])
		ns := string(stream.Metric["namespace"])
		key := fmt.Sprintf("%s/%s/%s", ns, pod, container)

		if _, exists := metricsMap[key]; !exists {
			continue
		}

		if len(stream.Values) > 0 {
			lastVal := stream.Values[len(stream.Values)-1]
			limit := float64(lastVal.Value)
			metricsMap[key].MemoryLimit = limit / (1024 * 1024)
		}
	}

	result := make([]types.ResourceMetrics, 0, len(metricsMap))
	for _, m := range metricsMap {
		result = append(result, *m)
	}

	m.logger.Debug("Collected metrics for %d containers", len(result))
	return result, nil
}

func (m *PrometheusMonitor) GetMetricTimeSeries(
	ctx context.Context,
	namespace string,
	metricType string,
) (map[string]types.TimeSeriesData, error) {
	end := time.Now()
	start := end.Add(-m.config.QueryRange)
	step := m.config.StepSize

	var query string
	switch metricType {
	case "cpu":
		query = fmt.Sprintf(
			`sum(rate(container_cpu_usage_seconds_total{container!="POD", container!="", namespace="%s"}[5m])) by (pod, container, namespace)`,
			namespace,
		)
	case "memory":
		query = fmt.Sprintf(
			`container_memory_working_set_bytes{container!="POD", container!="", namespace="%s"}`,
			namespace,
		)
	default:
		return nil, fmt.Errorf("unknown metric type: %s", metricType)
	}

	rangeResult, err := m.queryRange(ctx, query, start, end, step)
	if err != nil {
		return nil, fmt.Errorf("querying %s time series: %w", metricType, err)
	}

	result := make(map[string]types.TimeSeriesData)

	for _, stream := range rangeResult {
		pod := string(stream.Metric["pod"])
		container := string(stream.Metric["container"])
		ns := string(stream.Metric["namespace"])
		key := fmt.Sprintf("%s/%s/%s", ns, pod, container)

		ts := types.TimeSeriesData{
			Timestamps: make([]time.Time, 0, len(stream.Values)),
			Values:     make([]float64, 0, len(stream.Values)),
		}

		for _, v := range stream.Values {
			ts.Timestamps = append(ts.Timestamps, v.Timestamp.Time())
			val := float64(v.Value)
			if metricType == "cpu" {
				val = val * 1000
			} else {
				val = val / (1024 * 1024)
			}
			ts.Values = append(ts.Values, val)
		}

		result[key] = ts
	}

	return result, nil
}

func (m *PrometheusMonitor) queryRange(
	ctx context.Context,
	query string,
	start, end time.Time,
	step time.Duration,
) (model.Matrix, error) {
	rangeQueryCtx, cancel := context.WithTimeout(ctx, m.config.Timeout)
	defer cancel()

	result, warnings, err := m.client.QueryRange(
		rangeQueryCtx,
		query,
		promv1.Range{
			Start: start,
			End:   end,
			Step:  step,
		},
	)
	if err != nil {
		return nil, fmt.Errorf("executing prometheus query: %w", err)
	}

	if len(warnings) > 0 {
		m.logger.Warning("Prometheus query warnings: %v", warnings)
	}

	matrix, ok := result.(model.Matrix)
	if !ok {
		return nil, fmt.Errorf("unexpected result type: %T", result)
	}

	return matrix, nil
}
