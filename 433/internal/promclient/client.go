package promclient

import (
	"context"
	"fmt"
	"time"

	"k8s-cost-allocation/internal/config"

	"github.com/prometheus/client_golang/api"
	v1 "github.com/prometheus/client_golang/api/prometheus/v1"
	"github.com/prometheus/common/model"
)

type Client struct {
	api v1.API
}

type MetricsResult struct {
	Timestamp time.Time
	Value     float64
}

type NamespaceMetrics struct {
	Namespace     string
	CPUUsage      float64
	MemoryUsage   float64
	StorageUsage  float64
	NetworkRX     float64
	NetworkTX     float64
	ExternalRX    float64
	ExternalTX    float64
}

type ContentionMetrics struct {
	Namespace          string
	CPUThrottledTime   float64
	MemoryOOMCount     int
	CPUStealTime       float64
	MemorySwapUsage    float64
}

func NewClient(cfg config.PrometheusConfig) (*Client, error) {
	client, err := api.NewClient(api.Config{
		Address: cfg.Address,
	})
	if err != nil {
		return nil, fmt.Errorf("failed to create prometheus client: %w", err)
	}

	v1api := v1.NewAPI(client)
	return &Client{api: v1api}, nil
}

func (c *Client) Query(ctx context.Context, query string, ts time.Time) (*MetricsResult, error) {
	result, _, err := c.api.Query(ctx, query, ts)
	if err != nil {
		return nil, fmt.Errorf("query failed: %w", err)
	}

	vec, ok := result.(model.Vector)
	if !ok {
		return nil, fmt.Errorf("unexpected result type: %T", result)
	}

	if len(vec) == 0 {
		return &MetricsResult{Timestamp: ts, Value: 0}, nil
	}

	return &MetricsResult{
		Timestamp: time.Unix(int64(vec[0].Timestamp)/1000, 0),
		Value:     float64(vec[0].Value),
	}, nil
}

func (c *Client) QueryRange(ctx context.Context, query string, start, end time.Time, step time.Duration) ([]MetricsResult, error) {
	r := v1.Range{
		Start: start,
		End:   end,
		Step:  step,
	}

	result, _, err := c.api.QueryRange(ctx, query, r)
	if err != nil {
		return nil, fmt.Errorf("query range failed: %w", err)
	}

	matrix, ok := result.(model.Matrix)
	if !ok {
		return nil, fmt.Errorf("unexpected result type: %T", result)
	}

	var results []MetricsResult
	for _, sample := range matrix {
		for _, point := range sample.Values {
			results = append(results, MetricsResult{
				Timestamp: time.Unix(int64(point.Timestamp)/1000, 0),
				Value:     float64(point.Value),
			})
		}
	}

	return results, nil
}

func (c *Client) GetNamespaceCPUUsage(ctx context.Context, namespace string, duration time.Duration) (float64, error) {
	query := fmt.Sprintf(`avg(rate(container_cpu_usage_seconds_total{namespace="%s",container!="",container!="POD"}[%dm]))`, namespace, int(duration.Minutes()))
	result, err := c.Query(ctx, query, time.Now())
	if err != nil {
		return 0, err
	}
	return result.Value, nil
}

func (c *Client) GetNamespaceMemoryUsage(ctx context.Context, namespace string) (float64, error) {
	query := fmt.Sprintf(`sum(container_memory_usage_bytes{namespace="%s",container!="",container!="POD"}) / 1024 / 1024 / 1024`, namespace)
	result, err := c.Query(ctx, query, time.Now())
	if err != nil {
		return 0, err
	}
	return result.Value, nil
}

func (c *Client) GetNamespaceNetworkRX(ctx context.Context, namespace string, duration time.Duration) (float64, error) {
	query := fmt.Sprintf(`sum(rate(container_network_receive_bytes_total{namespace="%s"}[%dm])) / 1024 / 1024 / 1024`, namespace, int(duration.Minutes()))
	result, err := c.Query(ctx, query, time.Now())
	if err != nil {
		return 0, err
	}
	return result.Value, nil
}

func (c *Client) GetNamespaceNetworkTX(ctx context.Context, namespace string, duration time.Duration) (float64, error) {
	query := fmt.Sprintf(`sum(rate(container_network_transmit_bytes_total{namespace="%s"}[%dm])) / 1024 / 1024 / 1024`, namespace, int(duration.Minutes()))
	result, err := c.Query(ctx, query, time.Now())
	if err != nil {
		return 0, err
	}
	return result.Value, nil
}

func (c *Client) GetAllNamespacesMetrics(ctx context.Context, duration time.Duration) ([]NamespaceMetrics, error) {
	queries := map[string]string{
		"cpu":    `avg(rate(container_cpu_usage_seconds_total{container!="",container!="POD"}[%dm])) by (namespace)`,
		"memory": `sum(container_memory_usage_bytes{container!="",container!="POD"}) by (namespace) / 1024 / 1024 / 1024`,
		"rx":     `sum(rate(container_network_receive_bytes_total{}[%dm])) by (namespace) / 1024 / 1024 / 1024`,
		"tx":     `sum(rate(container_network_transmit_bytes_total{}[%dm])) by (namespace) / 1024 / 1024 / 1024`,
	}

	results := make(map[string]map[string]float64)

	for name, q := range queries {
		query := fmt.Sprintf(q, int(duration.Minutes()))
		result, _, err := c.api.Query(ctx, query, time.Now())
		if err != nil {
			continue
		}

		vec, ok := result.(model.Vector)
		if !ok {
			continue
		}

		for _, sample := range vec {
			ns := string(sample.Metric["namespace"])
			if ns == "" {
				continue
			}
			if _, exists := results[ns]; !exists {
				results[ns] = make(map[string]float64)
			}
			results[ns][name] = float64(sample.Value)
		}
	}

	var metrics []NamespaceMetrics
	for ns, data := range results {
		metrics = append(metrics, NamespaceMetrics{
			Namespace:   ns,
			CPUUsage:    data["cpu"],
			MemoryUsage: data["memory"],
			NetworkRX:   data["rx"],
			NetworkTX:   data["tx"],
		})
	}

	return metrics, nil
}

func (c *Client) GetNamespaceStorageUsage(ctx context.Context, namespace string) (float64, error) {
	query := fmt.Sprintf(`sum(kubelet_volume_stats_used_bytes{namespace="%s"}) / 1024 / 1024 / 1024`, namespace)
	result, err := c.Query(ctx, query, time.Now())
	if err != nil {
		return 0, err
	}
	return result.Value, nil
}

func (c *Client) GetNamespaceExternalNetworkRX(ctx context.Context, namespace string, duration time.Duration) (float64, error) {
	query := fmt.Sprintf(`sum(rate(container_network_receive_bytes_total{namespace="%s",interface!~"docker.*|flannel.*|cbr.*|veth.*"}[%dm])) / 1024 / 1024 / 1024`, namespace, int(duration.Minutes()))
	result, err := c.Query(ctx, query, time.Now())
	if err != nil {
		return 0, err
	}
	return result.Value, nil
}

func (c *Client) GetNamespaceExternalNetworkTX(ctx context.Context, namespace string, duration time.Duration) (float64, error) {
	query := fmt.Sprintf(`sum(rate(container_network_transmit_bytes_total{namespace="%s",interface!~"docker.*|flannel.*|cbr.*|veth.*"}[%dm])) / 1024 / 1024 / 1024`, namespace, int(duration.Minutes()))
	result, err := c.Query(ctx, query, time.Now())
	if err != nil {
		return 0, err
	}
	return result.Value, nil
}

func (c *Client) GetCPUThrottling(ctx context.Context, namespace string, duration time.Duration) (float64, error) {
	query := fmt.Sprintf(`sum(rate(container_cpu_cfs_throttled_seconds_total{namespace="%s",container!="",container!="POD"}[%dm]))`, namespace, int(duration.Minutes()))
	result, err := c.Query(ctx, query, time.Now())
	if err != nil {
		return 0, err
	}
	return result.Value, nil
}

func (c *Client) GetOOMEvents(ctx context.Context, namespace string, duration time.Duration) (int, error) {
	query := fmt.Sprintf(`sum(kube_pod_container_status_terminated_reason{reason="OOMKilled",namespace="%s"})`, namespace)
	result, err := c.Query(ctx, query, time.Now())
	if err != nil {
		return 0, err
	}
	return int(result.Value), nil
}

func (c *Client) GetAllNamespacesMetrics(ctx context.Context, duration time.Duration) ([]NamespaceMetrics, error) {
	queries := map[string]string{
		"cpu":         `avg(rate(container_cpu_usage_seconds_total{container!="",container!="POD"}[%dm])) by (namespace)`,
		"memory":      `sum(container_memory_usage_bytes{container!="",container!="POD"}) by (namespace) / 1024 / 1024 / 1024`,
		"storage":     `sum(kubelet_volume_stats_used_bytes{}) by (namespace) / 1024 / 1024 / 1024`,
		"rx":          `sum(rate(container_network_receive_bytes_total{}[%dm])) by (namespace) / 1024 / 1024 / 1024`,
		"tx":          `sum(rate(container_network_transmit_bytes_total{}[%dm])) by (namespace) / 1024 / 1024 / 1024`,
		"external_rx": `sum(rate(container_network_receive_bytes_total{interface!~"docker.*|flannel.*|cbr.*|veth.*"}[%dm])) by (namespace) / 1024 / 1024 / 1024`,
		"external_tx": `sum(rate(container_network_transmit_bytes_total{interface!~"docker.*|flannel.*|cbr.*|veth.*"}[%dm])) by (namespace) / 1024 / 1024 / 1024`,
	}

	results := make(map[string]map[string]float64)

	for name, q := range queries {
		query := fmt.Sprintf(q, int(duration.Minutes()))
		result, _, err := c.api.Query(ctx, query, time.Now())
		if err != nil {
			continue
		}

		vec, ok := result.(model.Vector)
		if !ok {
			continue
		}

		for _, sample := range vec {
			ns := string(sample.Metric["namespace"])
			if ns == "" {
				continue
			}
			if _, exists := results[ns]; !exists {
				results[ns] = make(map[string]float64)
			}
			results[ns][name] = float64(sample.Value)
		}
	}

	var metrics []NamespaceMetrics
	for ns, data := range results {
		metrics = append(metrics, NamespaceMetrics{
			Namespace:    ns,
			CPUUsage:     data["cpu"],
			MemoryUsage:  data["memory"],
			StorageUsage: data["storage"],
			NetworkRX:    data["rx"],
			NetworkTX:    data["tx"],
			ExternalRX:   data["external_rx"],
			ExternalTX:   data["external_tx"],
		})
	}

	return metrics, nil
}

func (c *Client) GetAllNamespacesContention(ctx context.Context, duration time.Duration) ([]ContentionMetrics, error) {
	queries := map[string]string{
		"throttled": `sum(rate(container_cpu_cfs_throttled_seconds_total{container!="",container!="POD"}[%dm])) by (namespace)`,
		"oom":       `sum(kube_pod_container_status_terminated_reason{reason="OOMKilled"}) by (namespace)`,
	}

	results := make(map[string]map[string]float64)

	for name, q := range queries {
		query := fmt.Sprintf(q, int(duration.Minutes()))
		result, _, err := c.api.Query(ctx, query, time.Now())
		if err != nil {
			continue
		}

		vec, ok := result.(model.Vector)
		if !ok {
			continue
		}

		for _, sample := range vec {
			ns := string(sample.Metric["namespace"])
			if ns == "" {
				continue
			}
			if _, exists := results[ns]; !exists {
				results[ns] = make(map[string]float64)
			}
			results[ns][name] = float64(sample.Value)
		}
	}

	var metrics []ContentionMetrics
	for ns, data := range results {
		metrics = append(metrics, ContentionMetrics{
			Namespace:        ns,
			CPUThrottledTime: data["throttled"],
			MemoryOOMCount:   int(data["oom"]),
		})
	}

	return metrics, nil
}

func (c *Client) GetHistoricalMetrics(ctx context.Context, namespace string, start, end time.Time, step time.Duration) (map[string][]MetricsResult, error) {
	queries := map[string]string{
		"cpu":    fmt.Sprintf(`avg(rate(container_cpu_usage_seconds_total{namespace="%s",container!="",container!="POD"}[5m]))`, namespace),
		"memory": fmt.Sprintf(`sum(container_memory_usage_bytes{namespace="%s",container!="",container!="POD"}) / 1024 / 1024 / 1024`, namespace),
	}

	resultMap := make(map[string][]MetricsResult)
	for name, query := range queries {
		results, err := c.QueryRange(ctx, query, start, end, step)
		if err != nil {
			return nil, err
		}
		resultMap[name] = results
	}

	return resultMap, nil
}
