package config

import (
	"fmt"
	"os"
	"time"

	"gopkg.in/yaml.v3"
)

type Config struct {
	Prometheus   PrometheusConfig   `yaml:"prometheus"`
	Kubernetes   KubernetesConfig   `yaml:"kubernetes"`
	Scaling      ScalingConfig      `yaml:"scaling"`
	Analysis     AnalysisConfig     `yaml:"analysis"`
	Prediction   PredictionConfig   `yaml:"prediction"`
	Backtest     BacktestConfig     `yaml:"backtest"`
	Audit        AuditConfig        `yaml:"audit"`
	NodePressure NodePressureConfig `yaml:"node_pressure"`
	DryRun       bool               `yaml:"dry_run"`
	LogLevel     string             `yaml:"log_level"`
	CheckInterval time.Duration     `yaml:"check_interval"`
}

type PrometheusConfig struct {
	Address     string        `yaml:"address"`
	QueryRange  time.Duration `yaml:"query_range"`
	StepSize    time.Duration `yaml:"step_size"`
	Timeout     time.Duration `yaml:"timeout"`
}

type KubernetesConfig struct {
	KubeconfigPath string `yaml:"kubeconfig_path"`
	Namespace      string `yaml:"namespace"`
}

type ScalingConfig struct {
	CPUPercentileThreshold     float64 `yaml:"cpu_percentile_threshold"`
	MemoryPercentileThreshold  float64 `yaml:"memory_percentile_threshold"`
	MinCPULimit                float64 `yaml:"min_cpu_limit_m"`
	MaxCPULimit                float64 `yaml:"max_cpu_limit_m"`
	MinMemoryLimit             float64 `yaml:"min_memory_limit_mi"`
	MaxMemoryLimit             float64 `yaml:"max_memory_limit_mi"`
	CPURequestRatio            float64 `yaml:"cpu_request_ratio"`
	MemoryRequestRatio         float64 `yaml:"memory_request_ratio"`
	UtilizationHighThreshold   float64 `yaml:"utilization_high_threshold"`
	UtilizationLowThreshold    float64 `yaml:"utilization_low_threshold"`
	CooldownPeriod             time.Duration `yaml:"cooldown_period"`
	MaxAdjustmentPercent       float64 `yaml:"max_adjustment_percent"`
}

type AnalysisConfig struct {
	MinDataPoints        int           `yaml:"min_data_points"`
	PercentilesToCompute []float64     `yaml:"percentiles_to_compute"`
	ConfidenceLevel      float64       `yaml:"confidence_level"`
	MovingAverageWindow  int           `yaml:"moving_average_window"`
	OutlierRemovalEnabled bool         `yaml:"outlier_removal_enabled"`
	OutlierSigmaThreshold float64      `yaml:"outlier_sigma_threshold"`
}

type PredictionConfig struct {
	Enabled              bool          `yaml:"enabled"`
	PredictionWindow     time.Duration `yaml:"prediction_window"`
	TrainingDataRatio    float64       `yaml:"training_data_ratio"`
	ARIMAOrder           []int         `yaml:"arima_order"`
	SeasonalPeriod       int           `yaml:"seasonal_period"`
	CyclicPredictionEnabled bool       `yaml:"cyclic_prediction_enabled"`
	CyclicPeriods        []int         `yaml:"cyclic_periods"`
	PreAdjustmentLeadMinutes int       `yaml:"pre_adjustment_lead_minutes"`
	HourlyPredictionEnabled bool       `yaml:"hourly_prediction_enabled"`
	HourlyPredictionHours int          `yaml:"hourly_prediction_hours"`
	PeakPreAllocation    float64       `yaml:"peak_pre_allocation"`
}

type BacktestConfig struct {
	Enabled          bool          `yaml:"enabled"`
	DaysToSimulate   int           `yaml:"days_to_simulate"`
	StepMinutes      int           `yaml:"step_minutes"`
	CooldownMinutes  int           `yaml:"cooldown_minutes"`
	ShowChart        bool          `yaml:"show_chart"`
}

type AuditConfig struct {
	Enabled          bool          `yaml:"enabled"`
	LogPath          string        `yaml:"log_path"`
	RetentionDays    int           `yaml:"retention_days"`
	ReportInterval   time.Duration `yaml:"report_interval"`
	IncludeMetrics   bool          `yaml:"include_metrics"`
}

type NodePressureConfig struct {
	Enabled              bool          `yaml:"enabled"`
	CheckInterval        time.Duration `yaml:"check_interval"`
	CPUThreshold         float64       `yaml:"cpu_threshold"`
	MemoryThreshold      float64       `yaml:"memory_threshold"`
	MaxConcurrentUpscales int          `yaml:"max_concurrent_upscales"`
	StaggerDelay         time.Duration `yaml:"stagger_delay"`
	AvoidPeakHours       bool          `yaml:"avoid_peak_hours"`
}

func LoadConfig(path string) (*Config, error) {
	data, err := os.ReadFile(path)
	if err != nil {
		return nil, fmt.Errorf("reading config file: %w", err)
	}

	var config Config
	if err := yaml.Unmarshal(data, &config); err != nil {
		return nil, fmt.Errorf("parsing config file: %w", err)
	}

	if err := config.validate(); err != nil {
		return nil, fmt.Errorf("validating config: %w", err)
	}

	config.setDefaults()
	return &config, nil
}

func (c *Config) validate() error {
	if c.Prometheus.Address == "" {
		return fmt.Errorf("prometheus address is required")
	}
	if c.Scaling.CPUPercentileThreshold <= 0 || c.Scaling.CPUPercentileThreshold > 100 {
		return fmt.Errorf("cpu_percentile_threshold must be between 0 and 100")
	}
	if c.Scaling.MemoryPercentileThreshold <= 0 || c.Scaling.MemoryPercentileThreshold > 100 {
		return fmt.Errorf("memory_percentile_threshold must be between 0 and 100")
	}
	return nil
}

func (c *Config) setDefaults() {
	if c.Prometheus.QueryRange == 0 {
		c.Prometheus.QueryRange = 24 * time.Hour
	}
	if c.Prometheus.StepSize == 0 {
		c.Prometheus.StepSize = 5 * time.Minute
	}
	if c.Prometheus.Timeout == 0 {
		c.Prometheus.Timeout = 30 * time.Second
	}
	if c.CheckInterval == 0 {
		c.CheckInterval = 15 * time.Minute
	}
	if c.Analysis.MinDataPoints == 0 {
		c.Analysis.MinDataPoints = 10
	}
	if c.Analysis.ConfidenceLevel == 0 {
		c.Analysis.ConfidenceLevel = 0.95
	}
	if c.Analysis.MovingAverageWindow == 0 {
		c.Analysis.MovingAverageWindow = 5
	}
	if c.Analysis.PercentilesToCompute == nil {
		c.Analysis.PercentilesToCompute = []float64{50, 95, 99}
	}
	if c.Analysis.OutlierSigmaThreshold == 0 {
		c.Analysis.OutlierSigmaThreshold = 3.0
	}
	if c.Scaling.CPURequestRatio == 0 {
		c.Scaling.CPURequestRatio = 0.75
	}
	if c.Scaling.MemoryRequestRatio == 0 {
		c.Scaling.MemoryRequestRatio = 0.75
	}
	if c.Scaling.UtilizationHighThreshold == 0 {
		c.Scaling.UtilizationHighThreshold = 0.85
	}
	if c.Scaling.UtilizationLowThreshold == 0 {
		c.Scaling.UtilizationLowThreshold = 0.2
	}
	if c.Scaling.CooldownPeriod == 0 {
		c.Scaling.CooldownPeriod = 5 * time.Minute
	}
	if c.Scaling.MaxAdjustmentPercent == 0 {
		c.Scaling.MaxAdjustmentPercent = 0.5
	}
	if c.Prediction.PredictionWindow == 0 {
		c.Prediction.PredictionWindow = 15 * time.Minute
	}
	if c.Prediction.TrainingDataRatio == 0 {
		c.Prediction.TrainingDataRatio = 0.8
	}
	if c.Prediction.PreAdjustmentLeadMinutes == 0 {
		c.Prediction.PreAdjustmentLeadMinutes = 30
	}
	if c.Prediction.CyclicPeriods == nil {
		c.Prediction.CyclicPeriods = []int{12, 24, 48, 96, 168, 288}
	}
	if c.Prediction.HourlyPredictionHours == 0 {
		c.Prediction.HourlyPredictionHours = 24
	}
	if c.Prediction.PeakPreAllocation == 0 {
		c.Prediction.PeakPreAllocation = 0.2
	}
	if c.Backtest.DaysToSimulate == 0 {
		c.Backtest.DaysToSimulate = 7
	}
	if c.Backtest.StepMinutes == 0 {
		c.Backtest.StepMinutes = 15
	}
	if c.Backtest.CooldownMinutes == 0 {
		c.Backtest.CooldownMinutes = 60
	}
	if c.Audit.RetentionDays == 0 {
		c.Audit.RetentionDays = 30
	}
	if c.Audit.ReportInterval == 0 {
		c.Audit.ReportInterval = 24 * time.Hour
	}
	if c.NodePressure.CPUThreshold == 0 {
		c.NodePressure.CPUThreshold = 0.85
	}
	if c.NodePressure.MemoryThreshold == 0 {
		c.NodePressure.MemoryThreshold = 0.85
	}
	if c.NodePressure.MaxConcurrentUpscales == 0 {
		c.NodePressure.MaxConcurrentUpscales = 3
	}
	if c.NodePressure.StaggerDelay == 0 {
		c.NodePressure.StaggerDelay = 2 * time.Minute
	}
	if c.LogLevel == "" {
		c.LogLevel = "info"
	}
}
