package models

import "time"

type TrafficMetrics struct {
	ServiceName   string    `json:"serviceName"`
	Namespace     string    `json:"namespace"`
	RequestCount  int64     `json:"requestCount"`
	ErrorCount    int64     `json:"errorCount"`
	P50Latency    float64   `json:"p50Latency"`
	P95Latency    float64   `json:"p95Latency"`
	P99Latency    float64   `json:"p99Latency"`
	SuccessRate   float64   `json:"successRate"`
	Throughput    float64   `json:"throughput"`
	Timestamp     time.Time `json:"timestamp"`
}

type TrafficReport struct {
	ID             string          `json:"id"`
	Name           string          `json:"name"`
	Type           string          `json:"type"`
	StartDate      time.Time       `json:"startDate"`
	EndDate        time.Time       `json:"endDate"`
	Services       []ServiceReport `json:"services"`
	GeneratedAt    time.Time       `json:"generatedAt"`
}

type ServiceReport struct {
	ServiceName    string         `json:"serviceName"`
	TotalRequests  int64          `json:"totalRequests"`
	ErrorRate      float64        `json:"errorRate"`
	AvgLatency     float64        `json:"avgLatency"`
	TrafficIn      float64        `json:"trafficIn"`
	TrafficOut     float64        `json:"trafficOut"`
	VersionBreakdown map[string]int64 `json:"versionBreakdown"`
}

type ServiceNode struct {
	ID          string            `json:"id"`
	Name        string            `json:"name"`
	Namespace   string            `json:"namespace"`
	Type        string            `json:"type"`
	Version     string            `json:"version"`
	Labels      map[string]string `json:"labels,omitempty"`
	Metrics     *TrafficMetrics   `json:"metrics,omitempty"`
	X           float64           `json:"x,omitempty"`
	Y           float64           `json:"y,omitempty"`
}

type ServiceEdge struct {
	ID           string         `json:"id"`
	Source       string         `json:"source"`
	Target       string         `json:"target"`
	Protocol     string         `json:"protocol"`
	Traffic      float64        `json:"traffic"`
	Latency      float64        `json:"latency"`
	ErrorRate    float64        `json:"errorRate"`
	RequestCount int64          `json:"requestCount"`
}

type TrafficTopology struct {
	Nodes []ServiceNode `json:"nodes"`
	Edges []ServiceEdge `json:"edges"`
}

type TopologyQuery struct {
	Namespace    string `json:"namespace"`
	Duration     string `json:"duration"`
	IncludeEdges bool   `json:"includeEdges"`
}

type MetricQuery struct {
	ServiceName string    `json:"serviceName"`
	Namespace   string    `json:"namespace"`
	StartTime   time.Time `json:"startTime"`
	EndTime     time.Time `json:"endTime"`
	Step        string    `json:"step"`
}

type TimeSeriesData struct {
	Timestamp int64   `json:"timestamp"`
	Value     float64 `json:"value"`
}

type MetricResponse struct {
	MetricName string            `json:"metricName"`
	Labels     map[string]string `json:"labels,omitempty"`
	DataPoints []TimeSeriesData  `json:"dataPoints"`
}
