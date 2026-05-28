package types

import (
	"time"

	corev1 "k8s.io/api/core/v1"
)

type ResourceMetrics struct {
	Timestamp    time.Time
	PodName      string
	Namespace    string
	ContainerName string
	CPUUsage     float64
	MemoryUsage  float64
	CPULimit     float64
	MemoryLimit  float64
	CPURequest   float64
	MemoryRequest float64
}

type TimeSeriesData struct {
	Timestamps []time.Time
	Values     []float64
}

type AnalysisResult struct {
	PodName       string
	Namespace     string
	ContainerName string
	CPUResult     ResourceAnalysis
	MemoryResult  ResourceAnalysis
	Prediction    ResourcePrediction
}

type ResourceAnalysis struct {
	CurrentUsage      float64
	CurrentLimit      float64
	CurrentRequest    float64
	Percentile95      float64
	Percentile99      float64
	Mean              float64
	StdDev            float64
	Trend             float64
	Volatility        float64
	UtilizationRatio  float64
	Recommendation    Recommendation
	RegressionModel   RegressionResult
}

type RegressionResult struct {
	Slope      float64
	Intercept  float64
	R2         float64
	Confidence float64
}

type ResourcePrediction struct {
	CPUPredictedUsage    float64
	MemoryPredictedUsage float64
	ConfidenceInterval   float64
	PredictionWindow     time.Duration
}

type HourlyPrediction struct {
	Hour             int
	CPUPredicted     float64
	MemoryPredicted  float64
	Confidence       float64
}

type DayPrediction struct {
	HourlyPredictions []HourlyPrediction
	PeakHour          int
	PeakCPU           float64
	PeakMemory        float64
	AvgCPU            float64
	AvgMemory         float64
	TotalCPUCapacity  float64
	TotalMemoryCapacity float64
	RecommendedLimit  float64
}

type AuditRecord struct {
	ID              string
	Timestamp       time.Time
	Namespace       string
	PodName         string
	ContainerName   string
	ResourceType    corev1.ResourceName
	NodeName        string
	Before          ResourceState
	After           ResourceState
	Reason          string
	Confidence      float64
	PerformanceDiff PerformanceMetrics
	DryRun          bool
	Success         bool
	ErrorMessage    string
}

type ResourceState struct {
	Limit    float64
	Request  float64
	Usage    float64
	UsagePct float64
}

type PerformanceMetrics struct {
	UtilizationChange  float64
	EfficiencyChange   float64
	WasteChange        float64
	ContentionRiskChange float64
}

type NodePressure struct {
	NodeName              string
	TotalCPU              float64
	TotalMemory           float64
	AllocatableCPU        float64
	AllocatableMemory     float64
	UsedCPU               float64
	UsedMemory            float64
	CPUUtilization        float64
	MemoryUtilization     float64
	CPUPressure           bool
	MemoryPressure        bool
	DiskPressure          bool
	PIDPressure           bool
	Unschedulable         bool
	PodCount              int
	PendingAdjustments    int
	HighUtilizationPods   []PodRef
	LastUpdate            time.Time
}

type PodRef struct {
	Namespace       string
	PodName         string
	ContainerName   string
	CPUUsage        float64
	MemoryUsage     float64
	CPULimit        float64
	MemoryLimit     float64
	PendingAdjustment bool
}

type ScheduledAdjustment struct {
	ID              string
	ScheduledTime   time.Time
	Namespace       string
	PodName         string
	ContainerName   string
	ResourceType    corev1.ResourceName
	NewLimit        float64
	NewRequest      float64
	Reason          string
	Confidence      float64
	Priority        int
}

type Recommendation struct {
	ProposedLimit    float64
	ProposedRequest  float64
	Confidence       float64
	AdjustmentReason string
}

type AdjustmentAction struct {
	Namespace       string
	PodName         string
	ContainerName   string
	ResourceType    corev1.ResourceName
	NewLimit        float64
	NewRequest      float64
	OldLimit        float64
	OldRequest      float64
	Reason          string
	Confidence      float64
	DryRun          bool
}

type AdjustmentResult struct {
	Success     bool
	Action      AdjustmentAction
	Applied     bool
	Message     string
	AppliedAt   time.Time
}

type BacktestAction struct {
	Timestamp    time.Time
	ResourceType corev1.ResourceName
	OldLimit     float64
	NewLimit     float64
	OldRequest   float64
	NewRequest   float64
	Reason       string
	Confidence   float64
}

type BacktestPoint struct {
	Timestamp      time.Time
	ActualUsage    float64
	Recommended    float64
	OriginalLimit  float64
	SimulatedLimit float64
	EfficiencyGain float64
	WasteAvoided   float64
	ContentionRisk float64
}

type BacktestResult struct {
	PodName        string
	Namespace      string
	ContainerName  string
	ResourceType   corev1.ResourceName
	StartDate      time.Time
	EndDate        time.Time
	Actions        []BacktestAction
	Points         []BacktestPoint
	OriginalWaste  float64
	SimulatedWaste float64
	WasteSaved     float64
	AvgEfficiency  float64
	ContentionCount int
	PeakOverage    float64
	Recommendation string
}
