package model

import (
	"time"

	"github.com/google/uuid"
)

type FaultType string

const (
	FaultTypeDelay   FaultType = "delay"
	FaultTypeAbort   FaultType = "abort"
	FaultTypeError   FaultType = "error"
)

type FaultStatus string

const (
	FaultStatusPending   FaultStatus = "pending"
	FaultStatusRunning   FaultStatus = "running"
	FaultStatusCompleted FaultStatus = "completed"
	FaultStatusFailed    FaultStatus = "failed"
)

type Fault struct {
	ID          string       `json:"id" gorm:"primaryKey"`
	Name        string       `json:"name" gorm:"not null"`
	Description string       `json:"description"`
	Type        FaultType    `json:"type" gorm:"not null"`
	Status      FaultStatus  `json:"status" gorm:"not null;default:pending"`
	TargetService string     `json:"target_service" gorm:"not null"`
	TargetPort   int         `json:"target_port"`
	Percentage  int          `json:"percentage" gorm:"not null"`
	Duration    int          `json:"duration"`
	DelayConfig *DelayConfig `json:"delay_config,omitempty" gorm:"serializer:json"`
	AbortConfig *AbortConfig `json:"abort_config,omitempty" gorm:"serializer:json"`
	ErrorConfig *ErrorConfig `json:"error_config,omitempty" gorm:"serializer:json"`
	Scope       *FaultScope  `json:"scope,omitempty" gorm:"serializer:json"`
	RollbackConfig *RollbackConfig `json:"rollback_config,omitempty" gorm:"serializer:json"`
	CreatedAt   time.Time    `json:"created_at"`
	UpdatedAt   time.Time    `json:"updated_at"`
	StartedAt   *time.Time   `json:"started_at,omitempty"`
	EndedAt     *time.Time   `json:"ended_at,omitempty"`
}

type DelayDistribution string

const (
	DelayDistributionFixed     DelayDistribution = "fixed"
	DelayDistributionNormal    DelayDistribution = "normal"
	DelayDistributionExponential DelayDistribution = "exponential"
)

type DelayConfig struct {
	Distribution DelayDistribution `json:"distribution"`
	FixedDelay   int               `json:"fixed_delay_ms"`
	MeanDelay    int               `json:"mean_delay_ms"`
	StdDevDelay  int               `json:"std_dev_ms"`
	MinDelay     int               `json:"min_delay_ms"`
	MaxDelay     int               `json:"max_delay_ms"`
}

type AbortConfig struct {
	HTTPStatus int    `json:"http_status"`
	Message    string `json:"message"`
}

type ErrorConfig struct {
	Rate        float64 `json:"error_rate"`
	ErrorType   string  `json:"error_type"`
}

type FaultScope struct {
	Namespace    string            `json:"namespace"`
	Labels       map[string]string `json:"labels"`
	Headers      map[string]string `json:"headers"`
	SourceLabels map[string]string `json:"source_labels"`
}

type FaultScenario struct {
	ID          string    `json:"id" gorm:"primaryKey"`
	Name        string    `json:"name" gorm:"not null"`
	Description string    `json:"description"`
	FaultIDs    []string  `json:"fault_ids" gorm:"serializer:json"`
	Steps       []ScenarioStep `json:"steps,omitempty" gorm:"serializer:json"`
	CreatedAt   time.Time `json:"created_at"`
	UpdatedAt   time.Time `json:"updated_at"`
}

type ScenarioStep struct {
	StepID     string        `json:"step_id"`
	FaultID    string        `json:"fault_id"`
	DelayBefore int          `json:"delay_before_seconds"`
	Duration   int           `json:"duration_seconds"`
}

type ScenarioExecution struct {
	ID         string       `json:"id" gorm:"primaryKey"`
	ScenarioID string       `json:"scenario_id"`
	Status     FaultStatus  `json:"status"`
	CurrentStep int         `json:"current_step"`
	TotalSteps  int         `json:"total_steps"`
	StartedAt   *time.Time  `json:"started_at"`
	EndedAt     *time.Time  `json:"ended_at"`
	CreatedAt   time.Time   `json:"created_at"`
}

type MetricData struct {
	ID          string    `json:"id" gorm:"primaryKey"`
	FaultID     string    `json:"fault_id"`
	Timestamp   time.Time `json:"timestamp"`
	MetricType  string    `json:"metric_type"`
	Value       float64   `json:"value"`
	Labels      string    `json:"labels"`
}

type ServiceInfo struct {
	Name      string            `json:"name"`
	Namespace string            `json:"namespace"`
	Versions  []string          `json:"versions"`
	Labels    map[string]string `json:"labels"`
	Status    string            `json:"status"`
}

type ServiceTopology struct {
	Services    []ServiceInfo   `json:"services"`
	Connections []Connection    `json:"connections"`
}

type Connection struct {
	Source      string `json:"source"`
	Destination string `json:"destination"`
	Protocol    string `json:"protocol"`
}

type ComparisonMetrics struct {
	Before *ServiceMetrics `json:"before"`
	After  *ServiceMetrics `json:"after"`
	Diff   *MetricsDiff    `json:"diff"`
}

type MetricsDiff struct {
	AvgLatencyDiff   float64 `json:"avg_latency_diff_ms"`
	AvgLatencyChange float64 `json:"avg_latency_change_pct"`
	P95LatencyDiff   float64 `json:"p95_latency_diff_ms"`
	P95LatencyChange float64 `json:"p95_latency_change_pct"`
	P99LatencyDiff   float64 `json:"p99_latency_diff_ms"`
	P99LatencyChange float64 `json:"p99_latency_change_pct"`
	ErrorRateDiff    float64 `json:"error_rate_diff_pct"`
	ErrorRateChange  float64 `json:"error_rate_change_pct"`
	RequestCountDiff int     `json:"request_count_diff"`
}

type TimeWindow struct {
	StartTime time.Time `json:"start_time"`
	EndTime   time.Time `json:"end_time"`
	Duration  string    `json:"duration"`
}

type AlignedComparisonRequest struct {
	ServiceName   string     `json:"service_name"`
	FaultID       string     `json:"fault_id,omitempty"`
	FaultStartTime time.Time `json:"fault_start_time"`
	BeforeWindow  int        `json:"before_window_minutes"`
	AfterWindow   int        `json:"after_window_minutes"`
}

type ServiceMetrics struct {
	ServiceName     string     `json:"service_name"`
	AvgLatency      float64    `json:"avg_latency_ms"`
	P95Latency      float64    `json:"p95_latency_ms"`
	P99Latency      float64    `json:"p99_latency_ms"`
	ErrorRate       float64    `json:"error_rate"`
	RequestCount    int        `json:"request_count"`
	ErrorCount      int        `json:"error_count"`
	TimeWindow      TimeWindow `json:"time_window"`
	LatencySeries   []TimeSeriesPoint `json:"latency_series,omitempty"`
	ErrorSeries     []TimeSeriesPoint `json:"error_series,omitempty"`
}

type TimeSeriesPoint struct {
	Timestamp time.Time `json:"timestamp"`
	Value     float64   `json:"value"`
}

type PresetScenarioCategory string

const (
	PresetCategoryNetwork  PresetScenarioCategory = "network"
	PresetCategoryService  PresetScenarioCategory = "service"
	PresetCategoryDatabase PresetScenarioCategory = "database"
	PresetCategoryChaos    PresetScenarioCategory = "chaos"
)

type PresetScenario struct {
	ID          string               `json:"id"`
	Name        string               `json:"name"`
	Description string               `json:"description"`
	Category    PresetScenarioCategory `json:"category"`
	Tags        []string             `json:"tags"`
	Severity    string               `json:"severity"`
	EstimatedDuration int            `json:"estimated_duration_seconds"`
	FaultConfig *Fault               `json:"fault_config" gorm:"serializer:json"`
	IsBuiltin   bool                 `json:"is_builtin"`
	CreatedAt   time.Time            `json:"created_at"`
	UpdatedAt   time.Time            `json:"updated_at"`
}

type RollbackConfig struct {
	Enabled               bool    `json:"enabled"`
	MaxLatencyThreshold   float64 `json:"max_latency_threshold_ms"`
	MaxErrorRateThreshold float64 `json:"max_error_rate_threshold_pct"`
	MinRequestCount       int     `json:"min_request_count"`
	ConsecutiveFailures   int     `json:"consecutive_failures_trigger"`
	CheckIntervalSeconds  int     `json:"check_interval_seconds"`
}

type RollbackEvent struct {
	ID              string    `json:"id" gorm:"primaryKey"`
	FaultID         string    `json:"fault_id"`
	Reason          string    `json:"reason"`
	TriggerMetric   string    `json:"trigger_metric"`
	ThresholdValue  float64   `json:"threshold_value"`
	ActualValue     float64   `json:"actual_value"`
	RollbackTime    time.Time `json:"rollback_time"`
	RollbackSuccess bool      `json:"rollback_success"`
}

type ResilienceScore struct {
	ID                  string    `json:"id" gorm:"primaryKey"`
	FaultID             string    `json:"fault_id"`
	ServiceName         string    `json:"service_name"`
	OverallScore        float64   `json:"overall_score"`
	RecoverySpeedScore  float64   `json:"recovery_speed_score"`
	StabilityScore      float64   `json:"stability_score"`
	ErrorHandlingScore  float64   `json:"error_handling_score"`
	PerformanceScore    float64   `json:"performance_score"`
	RecoveryTimeSeconds float64   `json:"recovery_time_seconds"`
	MaxDegradationPct   float64   `json:"max_degradation_pct"`
	Grade               string    `json:"grade"`
	Recommendations     []string  `json:"recommendations" gorm:"serializer:json"`
	CalculatedAt        time.Time `json:"calculated_at"`
}

type RecoveryTrendPoint struct {
	Timestamp     time.Time `json:"timestamp"`
	RecoveryPct   float64   `json:"recovery_pct"`
	LatencyMs     float64   `json:"latency_ms"`
	ErrorRatePct  float64   `json:"error_rate_pct"`
}

type ResilienceReport struct {
	Score           *ResilienceScore    `json:"score"`
	RecoveryTrend   []RecoveryTrendPoint `json:"recovery_trend"`
	BaselineMetrics *ServiceMetrics     `json:"baseline_metrics"`
	PeakImpact      *MetricsDiff        `json:"peak_impact"`
}

func NewFault() *Fault {
	return &Fault{
		ID:     uuid.New().String(),
		Status: FaultStatusPending,
	}
}

func NewFaultScenario() *FaultScenario {
	return &FaultScenario{
		ID: uuid.New().String(),
	}
}

func NewScenarioExecution(scenarioID string, totalSteps int) *ScenarioExecution {
	return &ScenarioExecution{
		ID:         uuid.New().String(),
		ScenarioID: scenarioID,
		Status:     FaultStatusPending,
		TotalSteps: totalSteps,
	}
}
