package types

import (
	"sync"
	"time"
)

type MetricType string

const (
	MetricCPU     MetricType = "cpu"
	MetricMemory  MetricType = "memory"
	MetricNetwork MetricType = "network"
)

type MetricValue struct {
	Timestamp time.Time
	Value     float64
}

type MetricData struct {
	InstanceID string
	MetricType MetricType
	Values     []MetricValue
	Current    float64
	Predicted  float64
	LastError  float64
	Corrected  float64
}

type ScalingDirection string

const (
	ScaleUp   ScalingDirection = "up"
	ScaleDown ScalingDirection = "down"
	NoScale   ScalingDirection = "none"
)

type ScalingType string

const (
	VerticalScaling   ScalingType = "vertical"
	HorizontalScaling ScalingType = "horizontal"
)

type DeploymentStrategy string

const (
	DeploymentBlueGreen DeploymentStrategy = "bluegreen"
	DeploymentRolling   DeploymentStrategy = "rolling"
	DeploymentInPlace   DeploymentStrategy = "inplace"
)

type BlueGreenStatus string

const (
	BlueGreenIdle       BlueGreenStatus = "idle"
	BlueGreenPreparing  BlueGreenStatus = "preparing"
	BlueGreenReady      BlueGreenStatus = "ready"
	BlueGreenSwitching  BlueGreenStatus = "switching"
	BlueGreenCompleted  BlueGreenStatus = "completed"
	BlueGreenRollingBack BlueGreenStatus = "rolling_back"
	BlueGreenFailed     BlueGreenStatus = "failed"
)

type ServiceLevel string

const (
	ServiceLevelCritical ServiceLevel = "critical"
	ServiceLevelHigh     ServiceLevel = "high"
	ServiceLevelMedium   ServiceLevel = "medium"
	ServiceLevelLow      ServiceLevel = "low"
)

type ScalingPolicy struct {
	MetricType     MetricType
	TargetValue    float64
	Tolerance      float64
	StepSize       int
	CooldownPeriod time.Duration
	MaxInstances   int
	MinInstances   int
	MaxSize        string
	MinSize        string
	ServiceLevel   ServiceLevel
}

type ServiceCooldownConfig struct {
	Critical time.Duration
	High     time.Duration
	Medium   time.Duration
	Low      time.Duration
}

type BlueGreenDeployment struct {
	ID             string
	Service        string
	Status         BlueGreenStatus
	BlueVersion    string
	GreenVersion   string
	CurrentVersion string
	BlueInstances  []InstanceInfo
	GreenInstances []InstanceInfo
	StartTime      time.Time
	ReadyTime      time.Time
	SwitchTime     time.Time
	TrafficSplit   int
	HealthCheck    string
	Timeout        time.Duration
	mu             sync.RWMutex
}

func (bg *BlueGreenDeployment) UpdateStatus(status BlueGreenStatus) {
	bg.mu.Lock()
	defer bg.mu.Unlock()
	bg.Status = status
}

func (bg *BlueGreenDeployment) GetStatus() BlueGreenStatus {
	bg.mu.RLock()
	defer bg.mu.RUnlock()
	return bg.Status
}

func (bg *BlueGreenDeployment) AddGreenInstance(inst InstanceInfo) {
	bg.mu.Lock()
	defer bg.mu.Unlock()
	bg.GreenInstances = append(bg.GreenInstances, inst)
}

func (bg *BlueGreenDeployment) AllGreenReady() bool {
	bg.mu.RLock()
	defer bg.mu.RUnlock()
	if len(bg.GreenInstances) == 0 {
		return false
	}
	for _, inst := range bg.GreenInstances {
		if inst.Status != "running" || !inst.Healthy {
			return false
		}
	}
	return true
}

type PredictionError struct {
	MetricType MetricType
	Timestamp  time.Time
	Predicted  float64
	Actual     float64
	Error      float64
	ErrorRatio float64
	Correction float64
}

type ErrorFeedbackConfig struct {
	Enabled        bool
	WindowSize     int
	MinSamples     int
	MaxCorrection  float64
	UpdateInterval time.Duration
	Alpha          float64
}

type ErrorFeedbackState struct {
	Errors     []PredictionError
	Corrections map[MetricType]float64
	LastUpdate time.Time
	mu         sync.RWMutex
}

func (efs *ErrorFeedbackState) RecordError(err PredictionError) {
	efs.mu.Lock()
	defer efs.mu.Unlock()

	efs.Errors = append(efs.Errors, err)
	maxSize := 1000
	if len(efs.Errors) > maxSize {
		efs.Errors = efs.Errors[len(efs.Errors)-maxSize:]
	}
}

func (efs *ErrorFeedbackState) GetCorrection(metricType MetricType, config ErrorFeedbackConfig) float64 {
	efs.mu.RLock()
	defer efs.mu.RUnlock()

	if !config.Enabled {
		return 0
	}

	correction, exists := efs.Corrections[metricType]
	if !exists {
		return 0
	}

	if correction > config.MaxCorrection {
		correction = config.MaxCorrection
	}
	if correction < -config.MaxCorrection {
		correction = -config.MaxCorrection
	}

	return correction
}

func (efs *ErrorFeedbackState) UpdateCorrections(config ErrorFeedbackConfig) {
	if !config.Enabled {
		return
	}

	efs.mu.Lock()
	defer efs.mu.Unlock()

	if len(efs.Errors) < config.MinSamples {
		return
	}

	now := time.Now()
	if now.Sub(efs.LastUpdate) < config.UpdateInterval {
		return
	}

	windowSize := config.WindowSize
	if windowSize <= 0 {
		windowSize = 50
	}

	startIdx := len(efs.Errors) - windowSize
	if startIdx < 0 {
		startIdx = 0
	}

	recentErrors := efs.Errors[startIdx:]

	metricErrors := make(map[MetricType][]PredictionError)
	for _, err := range recentErrors {
		metricErrors[err.MetricType] = append(metricErrors[err.MetricType], err)
	}

	if efs.Corrections == nil {
		efs.Corrections = make(map[MetricType]float64)
	}

	for mt, errs := range metricErrors {
		if len(errs) < config.MinSamples/2 {
			continue
		}

		avgError := 0.0
		for _, e := range errs {
			avgError += e.Error
		}
		avgError /= float64(len(errs))

		alpha := config.Alpha
		if alpha <= 0 {
			alpha = 0.3
		}

		oldCorrection := efs.Corrections[mt]
		newCorrection := alpha*avgError + (1-alpha)*oldCorrection

		if newCorrection > config.MaxCorrection {
			newCorrection = config.MaxCorrection
		}
		if newCorrection < -config.MaxCorrection {
			newCorrection = -config.MaxCorrection
		}

		efs.Corrections[mt] = newCorrection
	}

	efs.LastUpdate = now
}

type CloudProvider string

const (
	ProviderAWS    CloudProvider = "aws"
	ProviderAliyun CloudProvider = "aliyun"
	ProviderMock   CloudProvider = "mock"
)

type InstanceChargeType string

const (
	ChargeTypeReserved InstanceChargeType = "reserved"
	ChargeTypeOnDemand InstanceChargeType = "ondemand"
	ChargeTypeSpot     InstanceChargeType = "spot"
)

type InstanceCostInfo struct {
	InstanceID    string
	Flavor        string
	ChargeType    InstanceChargeType
	HourlyPrice   float64
	MonthlyPrice  float64
	ReservedTerm  int
	ReservedUsage float64
	StartTime     time.Time
}

type CostConfig struct {
	Enabled              bool
	ReservedInstanceRatio float64
	MaxOnDemandInstances int
	SpotInstanceEnabled  bool
	SpotMaxPrice         float64
	CostThreshold        float64
	OptimizationInterval time.Duration
}

type CostOptimizationAction struct {
	Type         string
	InstanceID   string
	FromCharge   InstanceChargeType
	ToCharge     InstanceChargeType
	FromFlavor   string
	ToFlavor     string
	CostSavings  float64
	Reason       string
	Timestamp    time.Time
}

type DryRunMode string

const (
	DryRunOff      DryRunMode = "off"
	DryRunSimulate DryRunMode = "simulate"
	DryRunValidate DryRunMode = "validate"
	DryRunReport   DryRunMode = "report"
)

type DryRunResult struct {
	Mode            DryRunMode
	Timestamp       time.Time
	OriginalAction  ScalingAction
	SimulatedResult string
	ExpectedImpact  string
	RiskLevel       string
	Recommendations []string
	ValidationPass  bool
}

type ScalingHistoryRecord struct {
	ID             string
	Timestamp      time.Time
	ServiceName    string
	ServiceLevel   ServiceLevel
	Action         ScalingAction
	MetricSnapshot map[MetricType]MetricData
	PolicyUsed     ScalingPolicy
	Result         string
	Error          string
	Duration       time.Duration
	CostChange     float64
	InstanceCount  int
	AvgFlavor      string
}

type HistoryReplayConfig struct {
	Enabled       bool
	StartTime     time.Time
	EndTime       time.Time
	Speed         float64
	OutputFormat  string
	Visualize     bool
	MetricsOnly   bool
}

type ReplayStep struct {
	Sequence      int
	Timestamp     time.Time
	Action        ScalingHistoryRecord
	MetricChart   string
	DecisionTree  string
	ImpactSummary string
}

type ReplayResult struct {
	TotalSteps     int
	StartTime      time.Time
	EndTime        time.Time
	ActionsTaken   int
	ScaleUps       int
	ScaleDowns     int
	CostSaved      float64
	AvgResponseTime time.Duration
	Recommendations []string
	Steps          []ReplayStep
}

type InstanceInfo struct {
	ID         string
	Name       string
	Status     string
	Flavor     string
	CPUCores   int
	MemoryGB   int
	PrivateIP  string
	PublicIP   string
	CreateTime time.Time
	Deployment BlueGreenStatus
	Version    string
	Service    string
	Weight     int
	Healthy    bool
	ChargeType InstanceChargeType
	CostInfo   InstanceCostInfo
}

type ScalingAction struct {
	Type          ScalingType
	Direction     ScalingDirection
	InstanceID    string
	Step          int
	Reason        string
	Timestamp     time.Time
	ServiceName   string
	ServiceLevel  ServiceLevel
	ChargeType    InstanceChargeType
	CostEstimate  float64
}

type InstanceGroup struct {
	ID               string
	Name             string
	Instances        []InstanceInfo
	MinSize          int
	MaxSize          int
	Desired          int
	Service          string
	Version          string
	ReservedCount    int
	OnDemandCount    int
	SpotCount        int
	TotalHourlyCost  float64
}
