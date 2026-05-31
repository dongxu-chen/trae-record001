package jaeger

import (
	"encoding/json"
	"fault-injection-platform/internal/model"
	"fmt"
	"io"
	"math"
	"net/http"
	"sort"
	"time"
)

type Client struct {
	queryEndpoint string
	httpClient    *http.Client
}

type TraceResponse struct {
	Data []Trace `json:"data"`
}

type Trace struct {
	TraceID   string             `json:"traceID"`
	Spans     []Span             `json:"spans"`
	Processes map[string]Process `json:"processes"`
}

type Span struct {
	SpanID        string            `json:"spanID"`
	OperationName string            `json:"operationName"`
	StartTime     int64             `json:"startTime"`
	Duration      int64             `json:"duration"`
	Tags          []Tag             `json:"tags"`
	ProcessID     string            `json:"processID"`
}

type Tag struct {
	Key   string      `json:"key"`
	Type  string      `json:"type"`
	Value interface{} `json:"value"`
}

type Process struct {
	ServiceName string `json:"serviceName"`
}

func NewClient(queryEndpoint string) *Client {
	return &Client{
		queryEndpoint: queryEndpoint,
		httpClient: &http.Client{
			Timeout: 30 * time.Second,
		},
	}
}

func (c *Client) GetTracesInRange(service string, limit int, startTime, endTime time.Time) ([]Trace, error) {
	url := fmt.Sprintf("%s?service=%s&limit=%d&start=%d&end=%d",
		c.queryEndpoint,
		service,
		limit,
		startTime.UnixNano()/1000,
		endTime.UnixNano()/1000,
	)

	resp, err := c.httpClient.Get(url)
	if err != nil {
		return nil, fmt.Errorf("failed to query jaeger: %w", err)
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		body, _ := io.ReadAll(resp.Body)
		return nil, fmt.Errorf("jaeger query failed with status %d: %s", resp.StatusCode, body)
	}

	var traceResp TraceResponse
	if err := json.NewDecoder(resp.Body).Decode(&traceResp); err != nil {
		return nil, fmt.Errorf("failed to decode response: %w", err)
	}

	return traceResp.Data, nil
}

func (c *Client) GetTraces(service string, limit int, lookback time.Duration) ([]Trace, error) {
	end := time.Now()
	start := end.Add(-lookback)
	return c.GetTracesInRange(service, limit, start, end)
}

func (c *Client) GetServiceMetricsInRange(service string, startTime, endTime time.Time) (*model.ServiceMetrics, error) {
	traces, err := c.GetTracesInRange(service, 200, startTime, endTime)
	if err != nil {
		return nil, err
	}

	metrics := c.analyzeTraces(service, traces, startTime, endTime)
	metrics.TimeWindow = model.TimeWindow{
		StartTime: startTime,
		EndTime:   endTime,
		Duration:  endTime.Sub(startTime).String(),
	}
	metrics.LatencySeries = c.buildTimeSeries(traces, service, startTime, endTime, 10)
	metrics.ErrorSeries = c.buildErrorSeries(traces, service, startTime, endTime, 10)

	return metrics, nil
}

func (c *Client) GetServiceMetrics(service string, lookback time.Duration) (*model.ServiceMetrics, error) {
	end := time.Now()
	start := end.Add(-lookback)
	return c.GetServiceMetricsInRange(service, start, end)
}

func (c *Client) GetAlignedComparison(service string, faultStartTime time.Time, beforeMinutes, afterMinutes int) (*model.ComparisonMetrics, error) {
	beforeStart := faultStartTime.Add(-time.Duration(beforeMinutes) * time.Minute)
	beforeEnd := faultStartTime
	afterStart := faultStartTime
	afterEnd := faultStartTime.Add(time.Duration(afterMinutes) * time.Minute)

	beforeMetrics, err := c.GetServiceMetricsInRange(service, beforeStart, beforeEnd)
	if err != nil {
		return nil, fmt.Errorf("failed to get before metrics: %w", err)
	}

	afterMetrics, err := c.GetServiceMetricsInRange(service, afterStart, afterEnd)
	if err != nil {
		return nil, fmt.Errorf("failed to get after metrics: %w", err)
	}

	diff := c.calculateDiff(beforeMetrics, afterMetrics)

	return &model.ComparisonMetrics{
		Before: beforeMetrics,
		After:  afterMetrics,
		Diff:   diff,
	}, nil
}

func (c *Client) analyzeTraces(service string, traces []Trace, startTime, endTime time.Time) *model.ServiceMetrics {
	if len(traces) == 0 {
		return &model.ServiceMetrics{
			ServiceName: service,
		}
	}

	var latencies []float64
	errorCount := 0
	totalCount := 0

	for _, trace := range traces {
		for _, span := range trace.Spans {
			if process, ok := trace.Processes[span.ProcessID]; ok && process.ServiceName == service {
				spanTime := time.Unix(0, span.StartTime*1000)
				if spanTime.After(startTime) && spanTime.Before(endTime) {
					latencies = append(latencies, float64(span.Duration)/1000.0)
					totalCount++

					for _, tag := range span.Tags {
						if tag.Key == "error" && tag.Value == true {
							errorCount++
							break
						}
					}
				}
			}
		}
	}

	if totalCount == 0 {
		return &model.ServiceMetrics{
			ServiceName: service,
		}
	}

	metrics := &model.ServiceMetrics{
		ServiceName:  service,
		RequestCount: totalCount,
		ErrorCount:   errorCount,
		ErrorRate:    float64(errorCount) / float64(totalCount) * 100,
	}

	if len(latencies) > 0 {
		metrics.AvgLatency = average(latencies)
		metrics.P95Latency = percentile(latencies, 95)
		metrics.P99Latency = percentile(latencies, 99)
	}

	return metrics
}

func (c *Client) calculateDiff(before, after *model.ServiceMetrics) *model.MetricsDiff {
	diff := &model.MetricsDiff{}

	if before.RequestCount > 0 {
		diff.AvgLatencyDiff = after.AvgLatency - before.AvgLatency
		if before.AvgLatency > 0 {
			diff.AvgLatencyChange = ((after.AvgLatency - before.AvgLatency) / before.AvgLatency) * 100
		}

		diff.P95LatencyDiff = after.P95Latency - before.P95Latency
		if before.P95Latency > 0 {
			diff.P95LatencyChange = ((after.P95Latency - before.P95Latency) / before.P95Latency) * 100
		}

		diff.P99LatencyDiff = after.P99Latency - before.P99Latency
		if before.P99Latency > 0 {
			diff.P99LatencyChange = ((after.P99Latency - before.P99Latency) / before.P99Latency) * 100
		}

		diff.ErrorRateDiff = after.ErrorRate - before.ErrorRate
		if before.ErrorRate > 0 {
			diff.ErrorRateChange = ((after.ErrorRate - before.ErrorRate) / before.ErrorRate) * 100
		} else if after.ErrorRate > 0 {
			diff.ErrorRateChange = 100
		}

		diff.RequestCountDiff = after.RequestCount - before.RequestCount
	}

	return diff
}

func (c *Client) buildTimeSeries(traces []Trace, service string, startTime, endTime time.Time, buckets int) []model.TimeSeriesPoint {
	if buckets <= 0 {
		buckets = 10
	}

	duration := endTime.Sub(startTime)
	bucketDuration := duration / time.Duration(buckets)

	type bucketData struct {
		sum   float64
		count int
	}

	bucketMap := make(map[int]bucketData)

	for _, trace := range traces {
		for _, span := range trace.Spans {
			if process, ok := trace.Processes[span.ProcessID]; ok && process.ServiceName == service {
				spanTime := time.Unix(0, span.StartTime*1000)
				if spanTime.After(startTime) && spanTime.Before(endTime) {
					offset := spanTime.Sub(startTime)
					bucketIdx := int(offset / bucketDuration)
					if bucketIdx >= buckets {
						bucketIdx = buckets - 1
					}
					bd := bucketMap[bucketIdx]
					bd.sum += float64(span.Duration) / 1000.0
					bd.count++
					bucketMap[bucketIdx] = bd
				}
			}
		}
	}

	points := make([]model.TimeSeriesPoint, buckets)
	for i := 0; i < buckets; i++ {
		bd := bucketMap[i]
		var value float64
		if bd.count > 0 {
			value = bd.sum / float64(bd.count)
		}
		points[i] = model.TimeSeriesPoint{
			Timestamp: startTime.Add(time.Duration(i) * bucketDuration),
			Value:     value,
		}
	}

	return points
}

func (c *Client) buildErrorSeries(traces []Trace, service string, startTime, endTime time.Time, buckets int) []model.TimeSeriesPoint {
	if buckets <= 0 {
		buckets = 10
	}

	duration := endTime.Sub(startTime)
	bucketDuration := duration / time.Duration(buckets)

	type bucketData struct {
		total int
		errors int
	}

	bucketMap := make(map[int]bucketData)

	for _, trace := range traces {
		for _, span := range trace.Spans {
			if process, ok := trace.Processes[span.ProcessID]; ok && process.ServiceName == service {
				spanTime := time.Unix(0, span.StartTime*1000)
				if spanTime.After(startTime) && spanTime.Before(endTime) {
					offset := spanTime.Sub(startTime)
					bucketIdx := int(offset / bucketDuration)
					if bucketIdx >= buckets {
						bucketIdx = buckets - 1
					}
					bd := bucketMap[bucketIdx]
					bd.total++
					for _, tag := range span.Tags {
						if tag.Key == "error" && tag.Value == true {
							bd.errors++
							break
						}
					}
					bucketMap[bucketIdx] = bd
				}
			}
		}
	}

	points := make([]model.TimeSeriesPoint, buckets)
	for i := 0; i < buckets; i++ {
		bd := bucketMap[i]
		var value float64
		if bd.total > 0 {
			value = float64(bd.errors) / float64(bd.total) * 100
		}
		points[i] = model.TimeSeriesPoint{
			Timestamp: startTime.Add(time.Duration(i) * bucketDuration),
			Value:     value,
		}
	}

	return points
}

func average(values []float64) float64 {
	if len(values) == 0 {
		return 0
	}
	sum := 0.0
	for _, v := range values {
		sum += v
	}
	return sum / float64(len(values))
}

func percentile(values []float64, p int) float64 {
	if len(values) == 0 {
		return 0
	}
	sorted := make([]float64, len(values))
	copy(sorted, values)
	sort.Float64s(sorted)
	index := int(math.Ceil(float64(len(sorted)) * float64(p) / 100.0))
	if index >= len(sorted) {
		index = len(sorted) - 1
	}
	if index < 0 {
		index = 0
	}
	return sorted[index]
}

func (c *Client) GetServices() ([]string, error) {
	url := fmt.Sprintf("%s/../services", c.queryEndpoint)
	resp, err := c.httpClient.Get(url)
	if err != nil {
		return nil, err
	}
	defer resp.Body.Close()

	var result struct {
		Data []string `json:"data"`
	}
	if err := json.NewDecoder(resp.Body).Decode(&result); err != nil {
		return nil, err
	}

	return result.Data, nil
}
