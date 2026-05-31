package metrics

import (
	"context"
	"encoding/json"
	"fmt"
	"math"
	"net/http"
	"net/url"
	"strconv"
	"time"

	metav1 "k8s.io/apimachinery/pkg/apis/meta/v1"
	"k8s.io/client-go/kubernetes"
	metricsv "k8s.io/metrics/pkg/client/clientset/versioned"
)

type MetricPoint struct {
	Timestamp time.Time `json:"timestamp"`
	Value     float64   `json:"value"`
}

type PodMetrics struct {
	PodName string  `json:"podName"`
	CPU     float64 `json:"cpu"`
	Memory  float64 `json:"memory"`
	QPS     float64 `json:"qps"`
	Latency float64 `json:"latency"`
}

type WorkloadMetrics struct {
	DeploymentName string       `json:"deploymentName"`
	Namespace      string       `json:"namespace"`
	Replicas       int32        `json:"replicas"`
	Pods           []PodMetrics `json:"pods"`
	AggCPU         float64      `json:"aggCPU"`
	AggMemory      float64      `json:"aggMemory"`
	AggQPS         float64      `json:"aggQPS"`
	AggLatency     float64      `json:"aggLatency"`
}

type MetricsCollector struct {
	k8sClient     *kubernetes.Clientset
	metricsClient *metricsv.Clientset
	prometheusURL string
	httpClient    *http.Client
}

func NewMetricsCollector(k8sClient *kubernetes.Clientset, metricsClient *metricsv.Clientset, prometheusURL string) *MetricsCollector {
	return &MetricsCollector{
		k8sClient:     k8sClient,
		metricsClient: metricsClient,
		prometheusURL: prometheusURL,
		httpClient:    &http.Client{Timeout: 30 * time.Second},
	}
}

func (c *MetricsCollector) CollectPodMetrics(namespace, deployment string) ([]PodMetrics, error) {
	ctx := context.Background()

	podList, err := c.metricsClient.MetricsV1beta1().PodMetricses(namespace).List(ctx, metav1.ListOptions{
		LabelSelector: fmt.Sprintf("app=%s", deployment),
	})
	if err != nil {
		return nil, fmt.Errorf("failed to list pod metrics: %w", err)
	}

	qpsMap, err := c.queryPrometheusVector(fmt.Sprintf(
		`sum(rate(http_requests_total{namespace="%s",deployment="%s"}[5m])) by (pod)`,
		namespace, deployment,
	))
	if err != nil {
		qpsMap = make(map[string]float64)
	}

	latencyMap, err := c.queryPrometheusVector(fmt.Sprintf(
		`histogram_quantile(0.99, sum(rate(http_request_duration_seconds_bucket{namespace="%s",deployment="%s"}[5m])) by (pod, le))`,
		namespace, deployment,
	))
	if err != nil {
		latencyMap = make(map[string]float64)
	}

	var result []PodMetrics
	for _, pm := range podList.Items {
		var totalCPU, totalMem float64
		for _, ctr := range pm.Containers {
			if cpuQ := ctr.Usage.Cpu(); cpuQ != nil {
				totalCPU += float64(cpuQ.MilliValue())
			}
			if memQ := ctr.Usage.Memory(); memQ != nil {
				totalMem += float64(memQ.Value())
			}
		}
		result = append(result, PodMetrics{
			PodName: pm.Name,
			CPU:     totalCPU,
			Memory:  totalMem,
			QPS:     qpsMap[pm.Name],
			Latency: latencyMap[pm.Name],
		})
	}
	return result, nil
}

func (c *MetricsCollector) CollectWorkloadMetrics(namespace, deployment string) (*WorkloadMetrics, error) {
	ctx := context.Background()

	deploy, err := c.k8sClient.AppsV1().Deployments(namespace).Get(ctx, deployment, metav1.GetOptions{})
	if err != nil {
		return nil, fmt.Errorf("failed to get deployment: %w", err)
	}

	pods, err := c.CollectPodMetrics(namespace, deployment)
	if err != nil {
		return nil, fmt.Errorf("failed to collect pod metrics: %w", err)
	}

	wm := &WorkloadMetrics{
		DeploymentName: deployment,
		Namespace:      namespace,
		Pods:           pods,
	}

	if deploy.Spec.Replicas != nil {
		wm.Replicas = *deploy.Spec.Replicas
	}

	for _, p := range pods {
		wm.AggCPU += p.CPU
		wm.AggMemory += p.Memory
		wm.AggQPS += p.QPS
		wm.AggLatency += p.Latency
	}
	if len(pods) > 0 {
		wm.AggLatency /= float64(len(pods))
	}

	return wm, nil
}

func (c *MetricsCollector) GetHistoricalMetrics(namespace, deployment string, duration time.Duration) ([]MetricPoint, error) {
	end := time.Now()
	start := end.Add(-duration)
	step := int64(duration.Seconds() / 60)
	if step < 1 {
		step = 1
	}

	query := fmt.Sprintf(
		`sum(rate(http_requests_total{namespace="%s",deployment="%s"}[5m]))`,
		namespace, deployment,
	)
	points, err := c.queryPrometheusMatrix(query, start, end, step)
	if err != nil {
		return nil, fmt.Errorf("failed to query historical metrics: %w", err)
	}
	return points, nil
}

type prometheusResponse struct {
	Status string `json:"status"`
	Data   struct {
		ResultType string `json:"resultType"`
		Result     []struct {
			Metric map[string]string `json:"metric"`
			Value  []interface{}     `json:"value,omitempty"`
			Values [][]interface{}   `json:"values,omitempty"`
		} `json:"result"`
	} `json:"data"`
}

func (c *MetricsCollector) queryPrometheusVector(query string) (map[string]float64, error) {
	u, err := url.Parse(c.prometheusURL)
	if err != nil {
		return nil, fmt.Errorf("invalid prometheus URL: %w", err)
	}
	u.Path = "/api/v1/query"
	q := u.Query()
	q.Set("query", query)
	u.RawQuery = q.Encode()

	resp, err := c.httpClient.Get(u.String())
	if err != nil {
		return nil, fmt.Errorf("prometheus query failed: %w", err)
	}
	defer resp.Body.Close()

	var promResp prometheusResponse
	if err := json.NewDecoder(resp.Body).Decode(&promResp); err != nil {
		return nil, fmt.Errorf("failed to decode prometheus response: %w", err)
	}

	result := make(map[string]float64)
	for _, r := range promResp.Data.Result {
		pod := r.Metric["pod"]
		if len(r.Value) < 2 {
			continue
		}
		valStr, ok := r.Value[1].(string)
		if !ok {
			continue
		}
		val, err := strconv.ParseFloat(valStr, 64)
		if err != nil {
			continue
		}
		result[pod] = val
	}
	return result, nil
}

func (c *MetricsCollector) queryPrometheusMatrix(query string, start, end time.Time, step int64) ([]MetricPoint, error) {
	u, err := url.Parse(c.prometheusURL)
	if err != nil {
		return nil, fmt.Errorf("invalid prometheus URL: %w", err)
	}
	u.Path = "/api/v1/query_range"
	q := u.Query()
	q.Set("query", query)
	q.Set("start", strconv.FormatInt(start.Unix(), 10))
	q.Set("end", strconv.FormatInt(end.Unix(), 10))
	q.Set("step", strconv.FormatInt(step, 10))
	u.RawQuery = q.Encode()

	resp, err := c.httpClient.Get(u.String())
	if err != nil {
		return nil, fmt.Errorf("prometheus range query failed: %w", err)
	}
	defer resp.Body.Close()

	var promResp prometheusResponse
	if err := json.NewDecoder(resp.Body).Decode(&promResp); err != nil {
		return nil, fmt.Errorf("failed to decode prometheus response: %w", err)
	}

	var points []MetricPoint
	for _, r := range promResp.Data.Result {
		for _, pair := range r.Values {
			if len(pair) < 2 {
				continue
			}
			tsFloat, ok := pair[0].(float64)
			if !ok {
				continue
			}
			valStr, ok := pair[1].(string)
			if !ok {
				continue
			}
			val, err := strconv.ParseFloat(valStr, 64)
			if err != nil {
				continue
			}
			points = append(points, MetricPoint{
				Timestamp: time.Unix(int64(tsFloat), 0),
				Value:     val,
			})
		}
	}
	return points, nil
}

type MockMetricsCollector struct {
	BaseCPU     float64
	BaseMemory  float64
	BaseQPS     float64
	BaseLatency float64
	PodCount    int
	startTime   time.Time
}

func NewMockMetricsCollector(podCount int) *MockMetricsCollector {
	return &MockMetricsCollector{
		BaseCPU:     100,
		BaseMemory:  512 * 1024 * 1024,
		BaseQPS:     50,
		BaseLatency: 0.1,
		PodCount:    podCount,
		startTime:   time.Now(),
	}
}

func (m *MockMetricsCollector) sineWave(t time.Time, frequency, amplitude, offset float64) float64 {
	elapsed := t.Sub(m.startTime).Seconds()
	return offset + amplitude*math.Sin(2*math.Pi*frequency*elapsed)
}

func (m *MockMetricsCollector) CollectPodMetrics(namespace, deployment string) ([]PodMetrics, error) {
	now := time.Now()
	var pods []PodMetrics
	for i := 0; i < m.PodCount; i++ {
		phase := float64(i) * 0.5
		cpu := m.sineWave(now, 0.01, 30, m.BaseCPU+phase)
		mem := m.sineWave(now, 0.005, 100*1024*1024, m.BaseMemory+phase*50*1024*1024)
		qps := m.sineWave(now, 0.02, 15, m.BaseQPS+phase*5)
		lat := m.sineWave(now, 0.015, 0.03, m.BaseLatency+phase*0.01)
		pods = append(pods, PodMetrics{
			PodName: fmt.Sprintf("%s-%d", deployment, i),
			CPU:     math.Max(cpu, 0),
			Memory:  math.Max(mem, 0),
			QPS:     math.Max(qps, 0),
			Latency: math.Max(lat, 0),
		})
	}
	return pods, nil
}

func (m *MockMetricsCollector) CollectWorkloadMetrics(namespace, deployment string) (*WorkloadMetrics, error) {
	pods, err := m.CollectPodMetrics(namespace, deployment)
	if err != nil {
		return nil, err
	}

	wm := &WorkloadMetrics{
		DeploymentName: deployment,
		Namespace:      namespace,
		Replicas:       int32(m.PodCount),
		Pods:           pods,
	}

	for _, p := range pods {
		wm.AggCPU += p.CPU
		wm.AggMemory += p.Memory
		wm.AggQPS += p.QPS
		wm.AggLatency += p.Latency
	}
	if len(pods) > 0 {
		wm.AggLatency /= float64(len(pods))
	}

	return wm, nil
}

func (m *MockMetricsCollector) GetHistoricalMetrics(namespace, deployment string, duration time.Duration) ([]MetricPoint, error) {
	end := time.Now()
	start := end.Add(-duration)
	interval := 15 * time.Second
	var points []MetricPoint

	for t := start; !t.After(end); t = t.Add(interval) {
		qps := m.sineWave(t, 0.02, 15, m.BaseQPS)
		points = append(points, MetricPoint{
			Timestamp: t,
			Value:     math.Max(qps, 0),
		})
	}
	return points, nil
}
