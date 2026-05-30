package analyzer

import (
	"time"
)

type LagStatus string

const (
	StatusNormal   LagStatus = "normal"
	StatusWarning  LagStatus = "warning"
	StatusCritical LagStatus = "critical"
)

type DelayCause string

const (
	CauseSlowProcessing  DelayCause = "slow_processing"
	CauseNetworkLatency  DelayCause = "network_latency"
	CauseImbalance       DelayCause = "partition_imbalance"
	CauseRebalancing     DelayCause = "rebalancing"
	CauseHighThroughput  DelayCause = "high_throughput"
)

type PartitionLag struct {
	Topic          string
	Partition      int32
	ConsumerGroup  string
	CurrentOffset  int64
	EndOffset      int64
	Lag            int64
	PreviousLag    int64
	LagChangeRate  float64
	Status         LagStatus
	Causes         []DelayCause
	Member         string
	LastCommit     time.Time
	LogSize        int64
	AvgMessageSize float64
	BrokerRTT      time.Duration
}

type TopicLag struct {
	Topic          string
	ConsumerGroup  string
	TotalLag       int64
	AvgLag         float64
	MaxLag         int64
	MinLag         int64
	PartitionCount int
	Partitions     []PartitionLag
	HotPartitions  []int32
	Status         LagStatus
	TotalLogSize   int64
	AvgLogSize     float64
	AvgMessageSize float64
}

type ConsumerGroupAnalysis struct {
	GroupID           string
	State             string
	MemberCount       int
	TotalLag          int64
	Topics            map[string]*TopicLag
	HotPartitions     []PartitionLag
	OverallStatus     LagStatus
	DelayAttributions []DelayAttribution
	Recommendations   []Recommendation
	Timestamp         time.Time
	NetworkRTTSummary *NetworkRTTSummary
}

type NetworkRTTSummary struct {
	OverallAvgRTT time.Duration
	OverallMaxRTT time.Duration
	HighRTTCount  int
	BrokerCount   int
	BrokerRTTs    map[int32]BrokerRTTInfo
}

type BrokerRTTInfo struct {
	BrokerID int32
	Host     string
	RTT      time.Duration
	MinRTT   time.Duration
	MaxRTT   time.Duration
	Jitter   time.Duration
}

type DelayAttribution struct {
	Cause             DelayCause
	Severity          LagStatus
	Confidence        float64
	Description       string
	AffectedTopics    []string
	AffectedPartitions []string
	Metrics           map[string]float64
}

type Recommendation struct {
	Priority    string
	Category    string
	Title       string
	Description string
	Action      string
	Impact      string
	CodeExample string
}

type CodePattern struct {
	Name        string
	Description string
	Severity    LagStatus
	Suggestions []string
}

type HistoricalLag struct {
	Timestamp time.Time
	Lag       int64
	Offset    int64
	EndOffset int64
}

type ProgressPrediction struct {
	Topic                 string
	Partition             int32
	CurrentLag            int64
	ConsumptionRate       float64
	IngestionRate         float64
	NetRate               float64
	EstimatedTimeToClear  time.Duration
	Confidence            float64
	PredictionPoints      []PredictionPoint
	PredictionMethod      string
	WillCatchUp           bool
	TimeToCatchUpAtRate   time.Duration
}

type PredictionPoint struct {
	Timestamp      time.Time
	ProjectedLag   int64
	ProjectedOffset int64
}

type GroupProgressPrediction struct {
	GroupID                    string
	OverallEstimatedTimeToClear time.Duration
	TotalLag                   int64
	AggregateConsumptionRate    float64
	AggregateIngestionRate      float64
	PartitionPredictions        map[string]map[int32]ProgressPrediction
	CriticalPartitions         []string
	Confidence                 float64
}

type ConsumerSimulation struct {
	GroupID               string
	OriginalMemberCount   int
	SimulatedMemberCount  int
	OriginalTotalLag      int64
	SimulatedTotalLag     float64
	ImprovementPercent    float64
	TopicSimulations      map[string]TopicSimulation
	Assumptions           []string
	EstimatedTimeSaved    time.Duration
}

type TopicSimulation struct {
	Topic                  string
	OriginalTotalLag       int64
	SimulatedTotalLag      float64
	ImprovementPercent     float64
	PartitionDistribution  map[int32]string
	EstimatedTimeToClear   time.Duration
	OriginalTimeToClear    time.Duration
}

type RebalancePlan struct {
	GroupID                string
	HotPartitions          []HotPartitionAction
	PartitionCountIncrease int
	RecommendedPartitions  int
	TopicsToExpand         []TopicExpansion
	RebalanceImpact        RebalanceImpact
	EstimatedImprovement   float64
}

type HotPartitionAction struct {
	Topic           string
	Partition       int32
	CurrentLag      int64
	CurrentLoad     float64
	Action          string
	SplitInto       int
	TargetMembers   []string
	ExpectedLag     float64
	ImprovementPct  float64
}

type TopicExpansion struct {
	Topic                 string
	CurrentPartitions     int
	RecommendedPartitions int
	Reason                string
	ExpectedImprovement   float64
}

type RebalanceImpact struct {
	DowntimeEstimate    time.Duration
	DataMovementBytes   int64
	ConsumerImpact      string
	RiskLevel           string
}

type ForecastConfig struct {
	PredictionHorizon       time.Duration
	PredictionInterval      time.Duration
	MinDataPoints           int
	RateCalculationWindow   int
	UseWeightedRegression   bool
	ConfidenceThreshold     float64
}

type Analyzer interface {
	Analyze() ([]*ConsumerGroupAnalysis, error)
	GetPartitionHistory(groupID, topic string, partition int32) []HistoricalLag
	GetLatestAnalysis() []*ConsumerGroupAnalysis
	PredictProgress(groupID string) (*GroupProgressPrediction, error)
	SimulateConsumerAddition(groupID string, additionalConsumers int) (*ConsumerSimulation, error)
	GenerateRebalancePlan(groupID string) (*RebalancePlan, error)
}
