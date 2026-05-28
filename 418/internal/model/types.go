package model

import "time"

type Phase string

const (
	PhaseTrigger       Phase = "trigger"
	PhaseImagePull     Phase = "image_pull"
	PhaseImageExtract  Phase = "image_extract"
	PhaseSnapshotSetup Phase = "snapshot_setup"
	PhaseContainerInit Phase = "container_init"
	PhaseRuntimeBoot   Phase = "runtime_boot"
	PhaseDependencyLoad Phase = "dependency_load"
	PhaseUserCode      Phase = "user_code"
	PhaseReady         Phase = "ready"
)

type Event struct {
	Timestamp  time.Time     `json:"timestamp"`
	Phase      Phase         `json:"phase"`
	ContainerID string       `json:"container_id"`
	Function   string        `json:"function"`
	Runtime    string        `json:"runtime"`
	Pod        string        `json:"pod"`
	Node       string        `json:"node"`
	Labels     map[string]string `json:"labels,omitempty"`
}

type PhaseRecord struct {
	Phase     Phase         `json:"phase"`
	Start     time.Time     `json:"start"`
	End       time.Time     `json:"end"`
	Duration  time.Duration `json:"duration_ms"`
	Source    string        `json:"source"`
	Detail    string        `json:"detail,omitempty"`
}

type ColdStartProfile struct {
	Function    string         `json:"function"`
	Runtime     string         `json:"runtime"`
	ContainerID string         `json:"container_id"`
	TriggeredAt time.Time      `json:"triggered_at"`
	ReadyAt     time.Time      `json:"ready_at"`
	Total       time.Duration  `json:"total_ms"`
	Phases      []PhaseRecord  `json:"phases"`
	Resources   ResourceUsage  `json:"resources"`
	Metadata    map[string]string `json:"metadata,omitempty"`
}

type ResourceUsage struct {
	CPUMillis  float64 `json:"cpu_millis"`
	MemoryMB   uint64  `json:"memory_mb"`
	DiskReadKB uint64  `json:"disk_read_kb"`
	DiskWriteKB uint64 `json:"disk_write_kb"`
	NetRxKB    uint64  `json:"net_rx_kb"`
	NetTxKB    uint64  `json:"net_tx_kb"`
}

type OptimizationKind string

const (
	OptImagePreload      OptimizationKind = "image_preload"
	OptNodeAffinity      OptimizationKind = "node_affinity"
	OptDependencySnap    OptimizationKind = "dependency_snapshot"
	OptReuseEnv          OptimizationKind = "reuse_env"
	OptWarmPool          OptimizationKind = "warm_pool"
	OptPoolLeakGuard     OptimizationKind = "pool_leak_guard"
	OptSnapFuse          OptimizationKind = "snapshot_fuse"
	OptKernelOpt         OptimizationKind = "kernel_opt"
	OptPredictivePreheat OptimizationKind = "predictive_preheat"
	OptGeoReplication    OptimizationKind = "geo_replication"
	OptCostControl       OptimizationKind = "cost_control"
)

type SnapshotMeta struct {
	Kind     string `json:"kind"`
	Language string `json:"language"`
	Tool     string `json:"tool"`
}

type NodeAffinityAdvice struct {
	PreferZones  []string          `json:"prefer_zones,omitempty"`
	Labels       map[string]string `json:"labels,omitempty"`
	PinNode      string            `json:"pin_node,omitempty"`
	PreloadNodes []string          `json:"preload_nodes,omitempty"`
	ReplicaCount int               `json:"replica_count"`
}

type PoolAdvice struct {
	MaxConnsPerEnv int           `json:"max_conns_per_env"`
	IdleTimeout    time.Duration `json:"idle_timeout_ms"`
	MaxAge         time.Duration `json:"max_age_ms"`
	ReclaimTimeout time.Duration `json:"reclaim_timeout_ms"`
	MaxPoolSize    int           `json:"max_pool_size"`
}

type Suggestion struct {
	Kind        OptimizationKind `json:"kind"`
	Priority    int              `json:"priority"`
	TargetPhase Phase            `json:"target_phase"`
	Description string           `json:"description"`
	ExpectedGain time.Duration   `json:"expected_gain_ms"`
	Confidence   float64         `json:"confidence"`
}

type PredictionRecord struct {
	Function    string        `json:"function"`
	Runtime     string        `json:"runtime"`
	ImageRef    string        `json:"image_ref"`
	Score       float64       `json:"score"`
	Probability float64       `json:"probability"`
	Reason      string        `json:"reason"`
	Region      string        `json:"region"`
	HotHours    []int         `json:"hot_hours,omitempty"`
	LastSeen    time.Time     `json:"last_seen"`
	FreqPerDay  float64       `json:"freq_per_day"`
}

type PredictedPreheat struct {
	GeneratedAt time.Time           `json:"generated_at"`
	Window      time.Duration       `json:"window"`
	Threshold   float64             `json:"threshold"`
	Predictions []PredictionRecord  `json:"predictions"`
}

type GeoRegion struct {
	ID         string    `json:"id"`
	Name       string    `json:"name"`
	Zone       string    `json:"zone"`
	Region     string    `json:"region"`
	Endpoint   string    `json:"endpoint"`
	BandwidthMB int64    `json:"bandwidth_mb"`
	LatencyMs  int64     `json:"latency_ms"`
	PriceFactor float64  `json:"price_factor"`
}

type GeoSnapshot struct {
	SnapshotID   string      `json:"snapshot_id"`
	SourceRegion string      `json:"source_region"`
	TargetRegion GeoRegion   `json:"target_region"`
	SizeBytes    int64       `json:"size_bytes"`
	ReplicatedAt time.Time   `json:"replicated_at"`
	TransferMs   int64       `json:"transfer_ms"`
	Checksum     string      `json:"checksum"`
	Available    bool        `json:"available"`
	LocalPath    string      `json:"local_path"`
}

type GeoReplicationPlan struct {
	Function     string         `json:"function"`
	SnapshotID   string         `json:"snapshot_id"`
	SourceRegion string         `json:"source_region"`
	Targets      []GeoSnapshot  `json:"targets"`
	TotalSize    int64          `json:"total_size_bytes"`
	TotalTransferMs int64       `json:"total_transfer_ms"`
}

type CostBreakdown struct {
	Currency       string           `json:"currency"`
	TotalCost      float64          `json:"total_cost"`
	CPUCost        float64          `json:"cpu_cost"`
	MemoryCost     float64          `json:"memory_cost"`
	PullCost       float64          `json:"pull_cost"`
	IOCost         float64          `json:"io_cost"`
	LatencyPenalty float64          `json:"latency_penalty"`
	CompareWarm    float64          `json:"compare_warm_savings"`
}

type CostAnalysis struct {
	ColdStart      CostBreakdown    `json:"cold_start"`
	WarmStart      CostBreakdown    `json:"warm_start"`
	Delta          CostBreakdown    `json:"delta"`
	PerInvocations  float64         `json:"per_invocation_cost"`
	PerMonthEst    float64          `json:"per_month_estimate"`
	OptimizationSavings float64     `json:"optimization_savings"`
	Currency       string           `json:"currency"`
}

type ColdStartReport struct {
	Profile        ColdStartProfile  `json:"profile"`
	Suggestions    []Suggestion      `json:"suggestions"`
	CostAnalysis   *CostAnalysis     `json:"cost_analysis,omitempty"`
	GeneratedAt    time.Time         `json:"generated_at"`
}

func (p *ColdStartProfile) PhaseDuration(phase Phase) time.Duration {
	for _, rec := range p.Phases {
		if rec.Phase == phase {
			return rec.Duration
		}
	}
	return 0
}
