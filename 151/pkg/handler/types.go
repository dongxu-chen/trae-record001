package handler

import (
	"servicemesh-console/pkg/k8sclient"
)

type Handlers struct {
	client    *k8sclient.Client
	namespace string
}

func NewHandlers(client *k8sclient.Client, namespace string) *Handlers {
	return &Handlers{
		client:    client,
		namespace: namespace,
	}
}

type TrafficMirrorConfig struct {
	SourceService   string `json:"source_service" binding:"required"`
	TargetService   string `json:"target_service" binding:"required"`
	Namespace       string `json:"namespace"`
	Percentage      int    `json:"percentage" binding:"min=0,max=100"`
	Enabled         bool   `json:"enabled"`
}

type CanaryReleaseConfig struct {
	ServiceName       string            `json:"service_name" binding:"required"`
	Namespace         string            `json:"namespace"`
	StableVersion     string            `json:"stable_version" binding:"required"`
	CanaryVersion     string            `json:"canary_version" binding:"required"`
	TrafficPercentage int               `json:"traffic_percentage" binding:"min=0,max=100"`
	MatchHeaders      map[string]string `json:"match_headers"`
	MatchCookies      map[string]string `json:"match_cookies"`
	Enabled           bool              `json:"enabled"`
	EnableWarmup      bool              `json:"enable_warmup"`
	WarmupDurationSec int               `json:"warmup_duration_sec"`
}

type GradualTrafficUpdateRequest struct {
	TargetPercentage   int `json:"target_percentage" binding:"min=0,max=100"`
	StepPercentage     int `json:"step_percentage" binding:"min=1,max=50"`
	IntervalSec        int `json:"interval_sec" binding:"min=1"`
}

type FaultInjectionConfig struct {
	ServiceName   string `json:"service_name" binding:"required"`
	Namespace     string `json:"namespace"`
	Enabled       bool   `json:"enabled"`
	Delay         *DelayConfig `json:"delay,omitempty"`
	Abort         *AbortConfig `json:"abort,omitempty"`
}

type DelayConfig struct {
	Percentage     int    `json:"percentage" binding:"min=0,max=100"`
	FixedDelayMs   int64  `json:"fixed_delay_ms" binding:"min=1"`
}

type AbortConfig struct {
	Percentage     int   `json:"percentage" binding:"min=0,max=100"`
	HttpStatus     int   `json:"http_status" binding:"min=200,max=599"`
}

type SamplingConfig struct {
	ServiceName      string            `json:"service_name" binding:"required"`
	Namespace        string            `json:"namespace"`
	Enabled          bool              `json:"enabled"`
	SamplePercentage int               `json:"sample_percentage" binding:"min=0,max=100"`
	SamplingRules    []SamplingRule    `json:"sampling_rules,omitempty"`
}

type SamplingRule struct {
	RuleName         string            `json:"rule_name"`
	MatchHeaders     map[string]string `json:"match_headers,omitempty"`
	MatchPaths       []string          `json:"match_paths,omitempty"`
	SamplePercentage int               `json:"sample_percentage" binding:"min=0,max=100"`
	Priority         int               `json:"priority"`
}

type SmartRouteConfig struct {
	ServiceName string       `json:"service_name" binding:"required"`
	Namespace   string       `json:"namespace"`
	Enabled     bool         `json:"enabled"`
	Rules       []RouteRule  `json:"rules"`
}

type RouteRule struct {
	RuleName        string             `json:"rule_name"`
	MatchHeaders    map[string]string  `json:"match_headers,omitempty"`
	MatchSourceIPs  []string           `json:"match_source_ips,omitempty"`
	MatchPaths      []string           `json:"match_paths,omitempty"`
	Destination     RouteDestination   `json:"destination"`
	Priority        int                `json:"priority"`
}

type RouteDestination struct {
	Host       string `json:"host"`
	Subset     string `json:"subset,omitempty"`
	Port       int    `json:"port,omitempty"`
	Weight     int    `json:"weight" binding:"min=0,max=100"`
}

type AnomalyDetectionConfig struct {
	ServiceName             string `json:"service_name" binding:"required"`
	Namespace               string `json:"namespace"`
	Enabled                 bool   `json:"enabled"`
	ConsecutiveErrors       int    `json:"consecutive_errors" binding:"min=1"`
	ErrorThresholdPercent   int    `json:"error_threshold_percent" binding:"min=1,max=100"`
	IntervalSeconds         int    `json:"interval_seconds" binding:"min=1"`
	BaseEjectionSeconds     int    `json:"base_ejection_seconds" binding:"min=1"`
	MaxEjectionPercent      int    `json:"max_ejection_percent" binding:"min=1,max=100"`
	MinHealthPercent        int    `json:"min_health_percent" binding:"min=0,max=100"`
}

type TrafficTopologyRequest struct {
	Namespace string `json:"namespace"`
	Service   string `json:"service,omitempty"`
	TimeRange string `json:"time_range,omitempty"`
}

type TrafficTopologyResponse struct {
	Nodes    []TopologyNode `json:"nodes"`
	Edges    []TopologyEdge `json:"edges"`
	Metadata TopologyMeta   `json:"metadata"`
}

type TopologyNode struct {
	ID          string            `json:"id"`
	Name        string            `json:"name"`
	Type        string            `json:"type"`
	Service     string            `json:"service"`
	Version     string            `json:"version,omitempty"`
	Namespace   string            `json:"namespace"`
	Metadata    map[string]string `json:"metadata,omitempty"`
	RequestRate float64           `json:"request_rate"`
	ErrorRate   float64           `json:"error_rate"`
	LatencyP50  float64           `json:"latency_p50"`
	LatencyP95  float64           `json:"latency_p95"`
	HealthStatus string           `json:"health_status"`
}

type TopologyEdge struct {
	Source      string  `json:"source"`
	Target      string  `json:"target"`
	RequestRate float64 `json:"request_rate"`
	ErrorRate   float64 `json:"error_rate"`
	LatencyP50  float64 `json:"latency_p50"`
	TrafficType string  `json:"traffic_type"`
}

type TopologyMeta struct {
	GeneratedAt string `json:"generated_at"`
	TimeRange   string `json:"time_range"`
	NodeCount   int    `json:"node_count"`
	EdgeCount   int    `json:"edge_count"`
}

type CircuitBreakerConfig struct {
	ServiceName         string `json:"service_name" binding:"required"`
	Namespace           string `json:"namespace"`
	MaxConnections      int    `json:"max_connections" binding:"min=1"`
	Http1MaxPendingRequests int `json:"http1_max_pending_requests" binding:"min=1"`
	Http2MaxRequests     int    `json:"http2_max_requests" binding:"min=1"`
	MaxRequestsPerConnection int `json:"max_requests_per_connection" binding:"min=1"`
	MaxRetries          int    `json:"max_retries" binding:"min=0"`
	ConsecutiveErrors   int    `json:"consecutive_errors" binding:"min=1"`
	SleepWindowSeconds  int    `json:"sleep_window_seconds" binding:"min=1"`
	Enabled             bool   `json:"enabled"`
}

type ApiResponse struct {
	Success bool        `json:"success"`
	Message string      `json:"message"`
	Data    interface{} `json:"data,omitempty"`
	TraceID string      `json:"trace_id,omitempty"`
}
