package model

import (
	"time"
)

type Protocol string

const (
	ProtocolHTTP  Protocol = "http"
	ProtocolGRPC  Protocol = "grpc"
	ProtocolDubbo Protocol = "dubbo"
)

type Status string

const (
	StatusUp      Status = "UP"
	StatusDown    Status = "DOWN"
	StatusDegrade Status = "DEGRADE"
)

type AssertionType string

const (
	AssertionJSONPath AssertionType = "jsonpath"
	AssertionXPath    AssertionType = "xpath"
	AssertionContains AssertionType = "contains"
	AssertionRegex    AssertionType = "regex"
)

type RateLimitStrategy string

const (
	RateLimitTokenBucket RateLimitStrategy = "token_bucket"
	RateLimitFixedWindow RateLimitStrategy = "fixed_window"
)

type DelayStrategy string

const (
	DelayRandom      DelayStrategy = "random"
	DelayFixed       DelayStrategy = "fixed"
	DelayExponential DelayStrategy = "exponential"
)

type WeightLevel int

const (
	WeightCritical WeightLevel = 10
	WeightHigh     WeightLevel = 5
	WeightMedium   WeightLevel = 2
	WeightLow      WeightLevel = 1
)

type TrendDirection int

const (
	TrendStable    TrendDirection = 0
	TrendDegrading TrendDirection = -1
	TrendImproving TrendDirection = 1
)

type Endpoint struct {
	ID            string          `yaml:"id"`
	Name          string          `yaml:"name"`
	Protocol      Protocol        `yaml:"protocol"`
	Address       string          `yaml:"address"`
	Interval      int             `yaml:"interval"`
	Timeout       int             `yaml:"timeout"`
	Weight        int             `yaml:"weight"`
	Priority      string          `yaml:"priority"`
	HTTPConfig    *HTTPConfig     `yaml:"http,omitempty"`
	GRPCConfig    *GRPCConfig     `yaml:"grpc,omitempty"`
	DubboConfig   *DubboConfig    `yaml:"dubbo,omitempty"`
	RateLimit     *RateLimitConfig `yaml:"rate_limit,omitempty"`
	Tracing       *TracingConfig  `yaml:"tracing,omitempty"`
	Prediction    *PredictionConfig `yaml:"prediction,omitempty"`
	Dependencies  []string        `yaml:"dependencies"`
	AlertRules    []string        `yaml:"alert_rules"`
	Tags          map[string]string `yaml:"tags"`
}

type TracingConfig struct {
	Enabled     bool   `yaml:"enabled"`
	ServiceName string `yaml:"service_name"`
	TraceHeader string `yaml:"trace_header"`
}

type PredictionConfig struct {
	Enabled           bool    `yaml:"enabled"`
	Algorithm         string  `yaml:"algorithm"`
	PredictionWindow  int     `yaml:"prediction_window"`
	WarningThreshold  float64 `yaml:"warning_threshold"`
	CriticalThreshold float64 `yaml:"critical_threshold"`
}

type RateLimitConfig struct {
	Enabled  bool              `yaml:"enabled"`
	Strategy RateLimitStrategy `yaml:"strategy"`
	Rate     int               `yaml:"rate"`
	Capacity int               `yaml:"capacity"`
	MaxBurst int               `yaml:"max_burst"`
	Delay    *DelayConfig      `yaml:"delay,omitempty"`
}

type DelayConfig struct {
	Strategy     DelayStrategy `yaml:"strategy"`
	MinDelayMs   int           `yaml:"min_delay_ms"`
	MaxDelayMs   int           `yaml:"max_delay_ms"`
	FixedDelayMs int           `yaml:"fixed_delay_ms"`
}

type HTTPConfig struct {
	Method       string            `yaml:"method"`
	Path         string            `yaml:"path"`
	Headers      map[string]string `yaml:"headers"`
	Body         string            `yaml:"body"`
	ExpectedCode int               `yaml:"expected_code"`
	ExpectedBody string           `yaml:"expected_body"`
	Assertions   []Assertion      `yaml:"assertions,omitempty"`
}

type Assertion struct {
	Type     AssertionType `yaml:"type"`
	Path     string        `yaml:"path"`
	Operator string        `yaml:"operator"`
	Value    string        `yaml:"value"`
}

type GRPCConfig struct {
	Service    string            `yaml:"service"`
	Method     string            `yaml:"method"`
	Request    string            `yaml:"request"`
	Metadata   map[string]string `yaml:"metadata"`
	TLS        bool              `yaml:"tls"`
	Assertions []Assertion       `yaml:"assertions,omitempty"`
}

type DubboConfig struct {
	Interface string            `yaml:"interface"`
	Method    string            `yaml:"method"`
	Group     string            `yaml:"group"`
	Version   string            `yaml:"version"`
	Params    []interface{}     `yaml:"params"`
}

type ProbeResult struct {
	EndpointID string
	Name       string
	Protocol   Protocol
	TraceID    string
	SpanID     string
	Timestamp  time.Time
	Status     Status
	Latency    time.Duration
	HTTPStatus int
	BodyMatch  bool
	Assertions []AssertionResult
	IsShadow   bool
	Error      string
}

type AssertionResult struct {
	Type   AssertionType
	Path   string
	Passed bool
	Actual string
	Error  string
}

type AlertRule struct {
	ID                 string  `yaml:"id"`
	Name               string  `yaml:"name"`
	Condition          string  `yaml:"condition"`
	Threshold          float64 `yaml:"threshold"`
	Duration           int     `yaml:"duration"`
	Severity           string  `yaml:"severity"`
	NotificationType   string  `yaml:"notification_type"`
	NotificationTarget string  `yaml:"notification_target"`
}

type AlertEvent struct {
	ID          string
	RuleID      string
	EndpointID  string
	Name        string
	Severity    string
	Message     string
	TriggeredAt time.Time
	ResolvedAt  *time.Time
	Status      string
}

type WindowStats struct {
	TotalProbes    int
	SuccessCount   int
	FailureCount   int
	DegradeCount   int
	AvgLatency     time.Duration
	MaxLatency     time.Duration
	P95Latency     time.Duration
	Availability   float64
	ErrorRate      float64
	StartTime      time.Time
	EndTime        time.Time
}

type ShadowConfig struct {
	Enabled       bool   `yaml:"enabled"`
	ShadowAddress string `yaml:"shadow_address"`
	ShadowHeader  string `yaml:"shadow_header"`
	ShadowValue   string `yaml:"shadow_value"`
	CompareResult bool   `yaml:"compare_result"`
	RecordOnly    bool   `yaml:"record_only"`
}

type PredictionResult struct {
	EndpointID       string
	Timestamp        time.Time
	PredictedValue   float64
	TrendDirection   TrendDirection
	TrendMagnitude   float64
	Confidence       float64
	Warning          bool
	Critical         bool
	Message          string
}

type TraceSpan struct {
	TraceID      string
	SpanID       string
	ParentSpanID string
	ServiceName  string
	Operation    string
	EndpointID   string
	StartTime    time.Time
	EndTime      time.Time
	Latency      time.Duration
	Status       Status
	Tags         map[string]string
	Children     []*TraceSpan
}

type SchedulingConfig struct {
	Enabled         bool    `yaml:"enabled"`
	AutoAdjust      bool    `yaml:"auto_adjust"`
	MinInterval     int     `yaml:"min_interval"`
	MaxInterval     int     `yaml:"max_interval"`
	WeightFactor    float64 `yaml:"weight_factor"`
	HealthFactor    float64 `yaml:"health_factor"`
	AdjustInterval  int     `yaml:"adjust_interval"`
}
