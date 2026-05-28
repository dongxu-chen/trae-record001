package model

import "time"

type CloudProvider string

const (
	AWS     CloudProvider = "aws"
	Azure   CloudProvider = "azure"
	GCP     CloudProvider = "gcp"
	Alibaba CloudProvider = "alibaba"
)

type Cluster struct {
	ID            string        `json:"id"`
	Name          string        `json:"name"`
	Provider      CloudProvider `json:"provider"`
	Region        string        `json:"region"`
	APIEndpoint   string        `json:"api_endpoint"`
	Weight        int           `json:"weight"`
	MinWeight     int           `json:"min_weight"`
	MaxWeight     int           `json:"max_weight"`
	Status        ClusterStatus `json:"status"`
	Healthy       bool          `json:"healthy"`
	Labels        map[string]string `json:"labels"`
	LastUpdated   time.Time     `json:"last_updated"`
	CreatedAt     time.Time     `json:"created_at"`
}

type ClusterStatus string

const (
	ClusterActive   ClusterStatus = "active"
	ClusterDraining ClusterStatus = "draining"
	ClusterInactive ClusterStatus = "inactive"
)

type Backend struct {
	ID           string    `json:"id"`
	ClusterID    string    `json:"cluster_id"`
	Address      string    `json:"address"`
	Port         uint32    `json:"port"`
	Weight       int       `json:"weight"`
	Healthy      bool      `json:"healthy"`
	ResponseTime int64     `json:"response_time_ms"`
	LastCheck    time.Time `json:"last_check"`
	SuccessCount int64     `json:"success_count"`
	FailureCount int64     `json:"failure_count"`
}

type HealthCheckConfig struct {
	Type               string        `json:"type"`
	Protocol           string        `json:"protocol"`
	Path               string        `json:"path"`
	Port               uint32        `json:"port"`
	Interval           time.Duration `json:"interval"`
	Timeout            time.Duration `json:"timeout"`
	UnhealthyThreshold uint32        `json:"unhealthy_threshold"`
	HealthyThreshold   uint32        `json:"healthy_threshold"`
}

type LoadBalancerConfig struct {
	Name              string            `json:"name"`
	Listeners         []ListenerConfig  `json:"listeners"`
	Clusters          []Cluster         `json:"clusters"`
	HealthCheck       HealthCheckConfig `json:"health_check"`
	SessionAffinity   SessionAffinityConfig `json:"session_affinity"`
	TrafficMirroring  TrafficMirroringConfig `json:"traffic_mirroring"`
	WeightAdjustment  WeightAdjustmentConfig `json:"weight_adjustment"`
	Failover          FailoverConfig    `json:"failover"`
	Cost              CostConfig        `json:"cost"`
	Prediction        PredictionConfig  `json:"prediction"`
	Proximity         ProximityConfig   `json:"proximity"`
}

type ListenerConfig struct {
	Port     uint32 `json:"port"`
	Protocol string `json:"protocol"`
}

type SessionAffinityConfig struct {
	Enabled       bool          `json:"enabled"`
	Type          string        `json:"type"`
	TTL           time.Duration `json:"ttl"`
	CookieName    string        `json:"cookie_name"`
	HeaderName    string        `json:"header_name"`
}

type TrafficMirroringConfig struct {
	Enabled           bool                `json:"enabled"`
	TargetCluster     string              `json:"target_cluster"`
	Percent           float64             `json:"percent"`
	BasePercent       float64             `json:"base_percent"`
	MinPercent        float64             `json:"min_percent"`
	MaxPercent        float64             `json:"max_percent"`
	CircuitBreaker    CircuitBreakerConfig `json:"circuit_breaker"`
}

type CircuitBreakerConfig struct {
	Enabled              bool          `json:"enabled"`
	FailureThreshold     int64         `json:"failure_threshold"`
	ErrorRateThreshold   float64       `json:"error_rate_threshold"`
	SlowResponseThreshold int64        `json:"slow_response_threshold"`
	OpenDuration         time.Duration `json:"open_duration"`
	HalfOpenMaxRequests  int32         `json:"half_open_max_requests"`
}

type WeightAdjustmentConfig struct {
	Enabled             bool          `json:"enabled"`
	AdjustInterval      time.Duration `json:"adjust_interval"`
	ResponseTimeWeight  float64       `json:"response_time_weight"`
	ErrorRateWeight     float64       `json:"error_rate_weight"`
	StepSize            int           `json:"step_size"`
}

type FailoverConfig struct {
	Enabled             bool          `json:"enabled"`
	FailoverThreshold   uint32        `json:"failover_threshold"`
	RecoveryThreshold   uint32        `json:"recovery_threshold"`
	CheckInterval       time.Duration `json:"check_interval"`
}

type ClusterMetrics struct {
	ClusterID         string  `json:"cluster_id"`
	AvgResponseTime   int64   `json:"avg_response_time_ms"`
	P95ResponseTime   int64   `json:"p95_response_time_ms"`
	P99ResponseTime   int64   `json:"p99_response_time_ms"`
	ErrorRate         float64 `json:"error_rate"`
	RequestRate       float64 `json:"request_rate"`
	ActiveConnections int64   `json:"active_connections"`
}

type CostConfig struct {
	Enabled         bool    `json:"enabled"`
	WeightInfluence float64 `json:"weight_influence"`
	BudgetLimit     float64 `json:"budget_limit"`
}

type PredictionConfig struct {
	Enabled            bool          `json:"enabled"`
	PredictionInterval time.Duration `json:"prediction_interval"`
	PredictionHorizon  time.Duration `json:"prediction_horizon"`
	AdjustWeights      bool          `json:"adjust_weights"`
	WeightInfluence    float64       `json:"weight_influence"`
	MinHistorySamples  int           `json:"min_history_samples"`
}

type ProximityConfig struct {
	Enabled         bool    `json:"enabled"`
	WeightInfluence float64 `json:"weight_influence"`
	PreferRTT       bool    `json:"prefer_rtt"`
	GeoIPProvider   string  `json:"geoip_provider"`
}
