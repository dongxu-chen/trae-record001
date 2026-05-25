package config

import "time"

type DatabaseType string

const (
	MySQL      DatabaseType = "mysql"
	PostgreSQL DatabaseType = "postgres"
	MongoDB    DatabaseType = "mongodb"
)

type DatabaseConfig struct {
	Type           DatabaseType `mapstructure:"type"`
	Host           string       `mapstructure:"host"`
	Port           int          `mapstructure:"port"`
	User           string       `mapstructure:"user"`
	Password       string       `mapstructure:"password"`
	Database       string       `mapstructure:"database"`
	MaxConnections int          `mapstructure:"max_connections"`
	Timeout        time.Duration `mapstructure:"timeout"`
}

type HotspotDistributionType string

const (
	HotspotUniform HotspotDistributionType = "uniform"
	HotspotZipf    HotspotDistributionType = "zipf"
)

type ScenarioConfig struct {
	Name                  string                  `mapstructure:"name"`
	Duration              time.Duration           `mapstructure:"duration"`
	Concurrency           int                     `mapstructure:"concurrency"`
	ReadRatio             float64                 `mapstructure:"read_ratio"`
	WriteRatio            float64                 `mapstructure:"write_ratio"`
	HotspotPercentage     float64                 `mapstructure:"hotspot_percentage"`
	HotspotAccessRatio    float64                 `mapstructure:"hotspot_access_ratio"`
	HotspotDistribution   HotspotDistributionType `mapstructure:"hotspot_distribution"`
	HotspotSkew           float64                 `mapstructure:"hotspot_skew"`
	TotalRecords          int                     `mapstructure:"total_records"`
	RateLimit             int                     `mapstructure:"rate_limit"`
	GradualStartup        bool                    `mapstructure:"gradual_startup"`
	GradualStartupStep    float64                 `mapstructure:"gradual_startup_step"`
	GradualStartupInterval time.Duration          `mapstructure:"gradual_startup_interval"`
}

type MetricsConfig struct {
	PrometheusPort int    `mapstructure:"prometheus_port"`
	PrometheusPath string `mapstructure:"prometheus_path"`
}

type StorageConfig struct {
	DataDir            string        `mapstructure:"data_dir"`
	TimeSeriesInterval time.Duration `mapstructure:"timeseries_interval"`
	SnapshotInterval   time.Duration `mapstructure:"snapshot_interval"`
}

type ResumeConfig struct {
	Enabled       bool   `mapstructure:"enabled"`
	ResumeRunID   string `mapstructure:"resume_run_id"`
	FromCheckpoint bool   `mapstructure:"from_checkpoint"`
}

type AutoTuneMode string

const (
	AutoTuneLatency    AutoTuneMode = "latency"
	AutoTuneThroughput AutoTuneMode = "throughput"
)

type AutoTuneConfig struct {
	Enabled           bool          `mapstructure:"enabled"`
	Mode              AutoTuneMode  `mapstructure:"mode"`
	TargetLatencyP99  float64       `mapstructure:"target_latency_p99"`
	MaxConcurrency    int           `mapstructure:"max_concurrency"`
	MinConcurrency    int           `mapstructure:"min_concurrency"`
	AdjustInterval    time.Duration `mapstructure:"adjust_interval"`
	Kp                float64       `mapstructure:"kp"`
	Ki                float64       `mapstructure:"ki"`
	Kd                float64       `mapstructure:"kd"`
	StopOnInflection  bool          `mapstructure:"stop_on_inflection"`
	InflectionWindow  int           `mapstructure:"inflection_window"`
}

type Config struct {
	Database DatabaseConfig `mapstructure:"database"`
	Scenario ScenarioConfig `mapstructure:"scenario"`
	Metrics  MetricsConfig  `mapstructure:"metrics"`
	Storage  StorageConfig  `mapstructure:"storage"`
	Resume   ResumeConfig   `mapstructure:"resume"`
	AutoTune AutoTuneConfig `mapstructure:"auto_tune"`
}
