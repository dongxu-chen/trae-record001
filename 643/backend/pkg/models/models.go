package models

import "time"

type Service struct {
	ID            string   `json:"id"`
	Name          string   `json:"name"`
	Dependencies  []string `json:"dependencies"`
	RequestWeight float64  `json:"requestWeight"`
}

type PerformanceData struct {
	ServiceID     string    `json:"serviceId"`
	Timestamp     time.Time `json:"timestamp"`
	CPUUsage      float64   `json:"cpuUsage"`
	MemoryUsage   float64   `json:"memoryUsage"`
	RequestsPerSec float64  `json:"requestsPerSec"`
	AvgLatencyMs  float64   `json:"avgLatencyMs"`
	P99LatencyMs  float64   `json:"p99LatencyMs"`
	ErrorRate     float64   `json:"errorRate"`
	Environment   string    `json:"environment"`
}

type LoadTestData struct {
	ServiceID          string  `json:"serviceId"`
	ConcurrentUsers    int     `json:"concurrentUsers"`
	Throughput         float64 `json:"throughput"`
	AvgLatencyMs       float64 `json:"avgLatencyMs"`
	P99LatencyMs       float64 `json:"p99LatencyMs"`
	CPUUsage           float64 `json:"cpuUsage"`
	MemoryUsage        float64 `json:"memoryUsage"`
	ErrorRate          float64 `json:"errorRate"`
	Environment        string  `json:"environment"`
	InstanceType       string  `json:"instanceType"`
	TestDurationSec    int     `json:"testDurationSec"`
}

type TrafficForecast struct {
	ServiceID      string        `json:"serviceId"`
	ForecastPeriod time.Duration `json:"forecastPeriod"`
	GrowthRate     float64       `json:"growthRate"`
	HistoricalData []TrafficData `json:"historicalData"`
	PredictedData  []TrafficData `json:"predictedData"`
}

type TrafficData struct {
	Timestamp      time.Time `json:"timestamp"`
	RequestsPerSec float64   `json:"requestsPerSec"`
}

type ServerConfig struct {
	ID                string  `json:"id"`
	Name              string  `json:"name"`
	CPUCores          int     `json:"cpuCores"`
	MemoryGB          int     `json:"memoryGB"`
	CostPerHour       float64 `json:"costPerHour"`
	ReservedCostPerHour float64 `json:"reservedCostPerHour"`
	MaxRequestsPerSec float64 `json:"maxRequestsPerSec"`
}

type CapacityResult struct {
	ServiceID            string          `json:"serviceId"`
	ServerConfig         ServerConfig    `json:"serverConfig"`
	RequiredServers      int             `json:"requiredServers"`
	RecommendedServers   int             `json:"recommendedServers"`
	ReservedInstances    int             `json:"reservedInstances"`
	OnDemandInstances    int             `json:"onDemandInstances"`
	EstimatedCPUUsage    float64         `json:"estimatedCpuUsage"`
	EstimatedMemoryUsage float64         `json:"estimatedMemoryUsage"`
	EstimatedLatencyMs   float64         `json:"estimatedLatencyMs"`
	QueueLength          float64         `json:"queueLength"`
	Utilization          float64         `json:"utilization"`
	SensitivityIndex     float64         `json:"sensitivityIndex"`
	CriticalityScore     float64         `json:"criticalityScore"`
	MonthlyCost          float64         `json:"monthlyCost"`
	OptimizedMonthlyCost float64         `json:"optimizedMonthlyCost"`
	CostSavings          float64         `json:"costSavings"`
	Breakdown            CostBreakdown   `json:"breakdown"`
}

type CostBreakdown struct {
	ComputeCost         float64 `json:"computeCost"`
	ReservedComputeCost float64 `json:"reservedComputeCost"`
	OnDemandComputeCost float64 `json:"onDemandComputeCost"`
	StorageCost         float64 `json:"storageCost"`
	NetworkCost         float64 `json:"networkCost"`
	LaborCost           float64 `json:"laborCost"`
	TotalCost           float64 `json:"totalCost"`
}

type DependencyResult struct {
	ServiceID           string             `json:"serviceId"`
	RequiredServers     int                `json:"requiredServers"`
	DependencyImpact    map[string]float64 `json:"dependencyImpact"`
	TotalCapacity       int                `json:"totalCapacity"`
	CriticalPath        []string           `json:"criticalPath"`
	ChainImpacts        []ChainImpactData  `json:"chainImpacts"`
	PropagationMatrix   [][]float64        `json:"propagationMatrix,omitempty"`
}

type ChainImpactData struct {
	Chain        []string `json:"chain"`
	ImpactFactor float64  `json:"impactFactor"`
	TrafficRatio float64  `json:"trafficRatio"`
}

type CalibrationFactor struct {
	ServiceID           string  `json:"serviceId"`
	CPUCorrection       float64 `json:"cpuCorrection"`
	MemoryCorrection    float64 `json:"memoryCorrection"`
	LatencyCorrection   float64 `json:"latencyCorrection"`
	ThroughputCorrection float64 `json:"throughputCorrection"`
	EnvironmentFactor   float64 `json:"environmentFactor"`
	NormalizationScore  float64 `json:"normalizationScore"`
}

type EnvironmentNormalization struct {
	EnvType     string
	CPUFactor   float64
	MemoryFactor float64
	NetworkFactor float64
	Description string
}

type EvaluationRequest struct {
	Services             []Service         `json:"services"`
	PerformanceData      []PerformanceData `json:"performanceData"`
	LoadTestData         []LoadTestData    `json:"loadTestData"`
	ServerConfigs        []ServerConfig    `json:"serverConfigs"`
	ForecastPeriodDays   int               `json:"forecastPeriodDays"`
	TargetUtilization    float64           `json:"targetUtilization"`
	MaxLatencyMs         float64           `json:"maxLatencyMs"`
	IncludeDependencies  bool              `json:"includeDependencies"`
	UseTrafficMatrix     bool              `json:"useTrafficMatrix"`
	ReservedInstanceRatio float64          `json:"reservedInstanceRatio"`
	AvailabilityTarget   float64           `json:"availabilityTarget"`
	Environment          string            `json:"environment"`
}

type EvaluationResponse struct {
	Results            []CapacityResult    `json:"results"`
	DependencyResults  []DependencyResult  `json:"dependencyResults"`
	TrafficForecasts   []TrafficForecast   `json:"trafficForecasts"`
	CalibrationFactors []CalibrationFactor `json:"calibrationFactors"`
	TotalMonthlyCost   float64             `json:"totalMonthlyCost"`
	OptimizedTotalCost float64             `json:"optimizedTotalCost"`
	TotalCostSavings   float64             `json:"totalCostSavings"`
}
