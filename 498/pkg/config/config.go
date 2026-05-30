package config

import (
	"fmt"
	"os"
	"time"

	"gopkg.in/yaml.v3"
)

type AggregationFunction string

const (
	AggAvg   AggregationFunction = "avg"
	AggMax   AggregationFunction = "max"
	AggMin   AggregationFunction = "min"
	AggSum   AggregationFunction = "sum"
	AggCount AggregationFunction = "count"
	AggP50   AggregationFunction = "p50"
	AggP90   AggregationFunction = "p90"
	AggP95   AggregationFunction = "p95"
	AggP99   AggregationFunction = "p99"
)

func (a AggregationFunction) IsValid() bool {
	switch a {
	case AggAvg, AggMax, AggMin, AggSum, AggCount,
		AggP50, AggP90, AggP95, AggP99:
		return true
	default:
		return false
	}
}

type DownsamplingLevel string

const (
	LevelRaw      DownsamplingLevel = "raw"
	LevelMinute   DownsamplingLevel = "1m"
	Level5Minutes DownsamplingLevel = "5m"
	Level15Minutes DownsamplingLevel = "15m"
	LevelHour     DownsamplingLevel = "1h"
	Level6Hours   DownsamplingLevel = "6h"
	LevelDay      DownsamplingLevel = "1d"
)

func (l DownsamplingLevel) Duration() (time.Duration, error) {
	switch l {
	case LevelRaw:
		return 0, nil
	case LevelMinute:
		return time.Minute, nil
	case Level5Minutes:
		return 5 * time.Minute, nil
	case Level15Minutes:
		return 15 * time.Minute, nil
	case LevelHour:
		return time.Hour, nil
	case Level6Hours:
		return 6 * time.Hour, nil
	case LevelDay:
		return 24 * time.Hour, nil
	default:
		return 0, fmt.Errorf("invalid downsampling level: %s", l)
	}
}

type RetentionPolicy struct {
	Level     DownsamplingLevel `yaml:"level"`
	Retention time.Duration     `yaml:"retention"`
}

type PeakDetectionConfig struct {
	Enabled        bool          `yaml:"enabled"`
	ZScoreThreshold float64      `yaml:"zscore_threshold"`
	Percentile     float64       `yaml:"percentile"`
	MinAbsoluteDev float64       `yaml:"min_absolute_deviation"`
}

type OutlierDetectionConfig struct {
	Enabled        bool          `yaml:"enabled"`
	IQRMultiplier  float64       `yaml:"iqr_multiplier"`
	PreserveCount  int           `yaml:"preserve_count"`
}

type AdaptiveDownsamplingConfig struct {
	Enabled               bool          `yaml:"enabled"`
	VolatilityThreshold   float64       `yaml:"volatility_threshold"`
	MinWindow             time.Duration `yaml:"min_window"`
	MaxWindow             time.Duration `yaml:"max_window"`
	VolatilityWindowSize  int           `yaml:"volatility_window_size"`
	HighVolatilityLevel   DownsamplingLevel `yaml:"high_volatility_level"`
	LowVolatilityLevel    DownsamplingLevel `yaml:"low_volatility_level"`
	AdaptationRate        float64       `yaml:"adaptation_rate"`
}

type ErrorAnalysisConfig struct {
	Enabled               bool          `yaml:"enabled"`
	CalculateMAE          bool          `yaml:"calculate_mae"`
	CalculateRMSE         bool          `yaml:"calculate_rmse"`
	CalculateMAPE         bool          `yaml:"calculate_mape"`
	CalculateSMAPE        bool          `yaml:"calculate_smape"`
	CalculateCorrelation  bool          `yaml:"calculate_correlation"`
	SampleInterval        time.Duration `yaml:"sample_interval"`
	StoreMetrics          bool          `yaml:"store_metrics"`
	AlertThreshold        float64       `yaml:"alert_threshold"`
}

type StrategyRecommendationConfig struct {
	Enabled                bool    `yaml:"enabled"`
	AnalyzePeriod          time.Duration `yaml:"analyze_period"`
	MinSamples             int     `yaml:"min_samples"`
	TargetErrorThreshold   float64 `yaml:"target_error_threshold"`
	StorageCostWeight      float64 `yaml:"storage_cost_weight"`
	AccuracyWeight         float64 `yaml:"accuracy_weight"`
	AutoApply              bool    `yaml:"auto_apply"`
}

type MetricRule struct {
	Name                    string                    `yaml:"name"`
	Match                   string                    `yaml:"match"`
	Exclude                 []string                  `yaml:"exclude,omitempty"`
	Aggregations            []AggregationFunction       `yaml:"aggregations"`
	DownsamplingLevels      []DownsamplingLevel     `yaml:"downsampling_levels"`
	RetentionPolicies       []RetentionPolicy       `yaml:"retention_policies,omitempty"`
	RawRetention            time.Duration             `yaml:"raw_retention,omitempty"`
	PreserveLabels          []string                  `yaml:"preserve_labels,omitempty"`
	DropLabels              []string                  `yaml:"drop_labels,omitempty"`
	AlignToBoundary         bool                      `yaml:"align_to_boundary"`
	PreservePeaks           PeakDetectionConfig       `yaml:"preserve_peaks,omitempty"`
	PreserveOutliers        OutlierDetectionConfig  `yaml:"preserve_outliers,omitempty"`
	AdaptiveDownsampling     AdaptiveDownsamplingConfig `yaml:"adaptive_downsampling,omitempty"`
	ErrorAnalysis           ErrorAnalysisConfig       `yaml:"error_analysis,omitempty"`
	StrategyRecommendation StrategyRecommendationConfig `yaml:"strategy_recommendation,omitempty"`
}

type PrometheusConfig struct {
	Address     string        `yaml:"address"`
	Timeout     time.Duration `yaml:"timeout"`
	QueryConcurrency int      `yaml:"query_concurrency"`
}

type ThanosConfig struct {
	Enabled     bool          `yaml:"enabled"`
	Address     string        `yaml:"address"`
	Timeout     time.Duration `yaml:"timeout"`
	BatchSize   int           `yaml:"batch_size"`
	UseTLS      bool          `yaml:"use_tls"`
	TLSCertPath string        `yaml:"tls_cert_path,omitempty"`
	TLSKeyPath  string        `yaml:"tls_key_path,omitempty"`
	ExternalLabels map[string]string `yaml:"external_labels"`
}

type SchedulerConfig struct {
	Interval      time.Duration `yaml:"interval"`
	Lookback      time.Duration `yaml:"lookback"`
	MaxRetries    int           `yaml:"max_retries"`
	RetryInterval time.Duration `yaml:"retry_interval"`
}

type ProxyConfig struct {
	Enabled       bool          `yaml:"enabled"`
	ListenAddress string        `yaml:"listen_address"`
	CacheTTL      time.Duration `yaml:"cache_ttl"`
	AutoSelectLevel bool        `yaml:"auto_select_level"`
}

type Config struct {
	Global struct {
		LogLevel  string `yaml:"log_level"`
		Namespace string `yaml:"namespace"`
	} `yaml:"global"`

	Prometheus  PrometheusConfig  `yaml:"prometheus"`
	Thanos      ThanosConfig      `yaml:"thanos"`
	Scheduler   SchedulerConfig   `yaml:"scheduler"`
	Proxy       ProxyConfig       `yaml:"proxy"`
	MetricRules []MetricRule      `yaml:"metric_rules"`
}

func Load(path string) (*Config, error) {
	data, err := os.ReadFile(path)
	if err != nil {
		return nil, fmt.Errorf("failed to read config file: %w", err)
	}

	var cfg Config
	if err := yaml.Unmarshal(data, &cfg); err != nil {
		return nil, fmt.Errorf("failed to parse config file: %w", err)
	}

	if err := cfg.Validate(); err != nil {
		return nil, fmt.Errorf("config validation failed: %w", err)
	}

	cfg.setDefaults()
	return &cfg, nil
}

func (c *Config) Validate() error {
	if c.Prometheus.Address == "" {
		return fmt.Errorf("prometheus address is required")
	}

	for i, rule := range c.MetricRules {
		if rule.Name == "" {
			return fmt.Errorf("metric rule %d: name is required", i)
		}
		if rule.Match == "" {
			return fmt.Errorf("metric rule %s: match pattern is required", rule.Name)
		}
		if len(rule.Aggregations) == 0 {
			return fmt.Errorf("metric rule %s: at least one aggregation function is required", rule.Name)
		}
		for _, agg := range rule.Aggregations {
			if !agg.IsValid() {
				return fmt.Errorf("metric rule %s: invalid aggregation function %s", rule.Name, agg)
			}
		}
		if len(rule.DownsamplingLevels) == 0 {
			return fmt.Errorf("metric rule %s: at least one downsampling level is required", rule.Name)
		}
		for _, level := range rule.DownsamplingLevels {
			if _, err := level.Duration(); err != nil {
				return fmt.Errorf("metric rule %s: %w", rule.Name, err)
			}
		}
	}

	return nil
}

func (c *Config) setDefaults() {
	if c.Global.LogLevel == "" {
		c.Global.LogLevel = "info"
	}
	if c.Global.Namespace == "" {
		c.Global.Namespace = "downsampled"
	}
	if c.Prometheus.Timeout == 0 {
		c.Prometheus.Timeout = 30 * time.Second
	}
	if c.Prometheus.QueryConcurrency == 0 {
		c.Prometheus.QueryConcurrency = 5
	}
	if c.Scheduler.Interval == 0 {
		c.Scheduler.Interval = 5 * time.Minute
	}
	if c.Scheduler.Lookback == 0 {
		c.Scheduler.Lookback = 1 * time.Hour
	}
	if c.Scheduler.MaxRetries == 0 {
		c.Scheduler.MaxRetries = 3
	}
	if c.Scheduler.RetryInterval == 0 {
		c.Scheduler.RetryInterval = 10 * time.Second
	}
	if c.Thanos.BatchSize == 0 {
		c.Thanos.BatchSize = 1000
	}
	if c.Proxy.ListenAddress == "" {
		c.Proxy.ListenAddress = ":9090"
	}
	if c.Proxy.CacheTTL == 0 {
		c.Proxy.CacheTTL = 5 * time.Minute
	}

	for i := range c.MetricRules {
		rule := &c.MetricRules[i]
		rule.AlignToBoundary = true
		if rule.PreservePeaks.Enabled && rule.PreservePeaks.ZScoreThreshold == 0 {
			rule.PreservePeaks.ZScoreThreshold = 3.0
		}
		if rule.PreservePeaks.Enabled && rule.PreservePeaks.Percentile == 0 {
			rule.PreservePeaks.Percentile = 99.0
		}
		if rule.PreserveOutliers.Enabled && rule.PreserveOutliers.IQRMultiplier == 0 {
			rule.PreserveOutliers.IQRMultiplier = 1.5
		}
		if rule.PreserveOutliers.Enabled && rule.PreserveOutliers.PreserveCount == 0 {
			rule.PreserveOutliers.PreserveCount = 5
		}

		if rule.AdaptiveDownsampling.Enabled {
			if rule.AdaptiveDownsampling.VolatilityThreshold == 0 {
				rule.AdaptiveDownsampling.VolatilityThreshold = 0.5
			}
			if rule.AdaptiveDownsampling.MinWindow == 0 {
				rule.AdaptiveDownsampling.MinWindow = time.Minute
			}
			if rule.AdaptiveDownsampling.MaxWindow == 0 {
				rule.AdaptiveDownsampling.MaxWindow = time.Hour
			}
			if rule.AdaptiveDownsampling.VolatilityWindowSize == 0 {
				rule.AdaptiveDownsampling.VolatilityWindowSize = 10
			}
			if rule.AdaptiveDownsampling.HighVolatilityLevel == "" {
				rule.AdaptiveDownsampling.HighVolatilityLevel = LevelMinute
			}
			if rule.AdaptiveDownsampling.LowVolatilityLevel == "" {
				rule.AdaptiveDownsampling.LowVolatilityLevel = Level15Minutes
			}
			if rule.AdaptiveDownsampling.AdaptationRate == 0 {
				rule.AdaptiveDownsampling.AdaptationRate = 0.1
			}
		}

		if rule.ErrorAnalysis.Enabled {
			if !rule.ErrorAnalysis.CalculateMAE && !rule.ErrorAnalysis.CalculateRMSE &&
				!rule.ErrorAnalysis.CalculateMAPE && !rule.ErrorAnalysis.CalculateSMAPE {
				rule.ErrorAnalysis.CalculateMAE = true
				rule.ErrorAnalysis.CalculateRMSE = true
				rule.ErrorAnalysis.CalculateMAPE = true
			}
			if rule.ErrorAnalysis.SampleInterval == 0 {
				rule.ErrorAnalysis.SampleInterval = 5 * time.Minute
			}
			if rule.ErrorAnalysis.AlertThreshold == 0 {
				rule.ErrorAnalysis.AlertThreshold = 0.1
			}
		}

		if rule.StrategyRecommendation.Enabled {
			if rule.StrategyRecommendation.AnalyzePeriod == 0 {
				rule.StrategyRecommendation.AnalyzePeriod = 24 * time.Hour
			}
			if rule.StrategyRecommendation.MinSamples == 0 {
				rule.StrategyRecommendation.MinSamples = 100
			}
			if rule.StrategyRecommendation.TargetErrorThreshold == 0 {
				rule.StrategyRecommendation.TargetErrorThreshold = 0.05
			}
			if rule.StrategyRecommendation.StorageCostWeight == 0 {
				rule.StrategyRecommendation.StorageCostWeight = 0.6
			}
			if rule.StrategyRecommendation.AccuracyWeight == 0 {
				rule.StrategyRecommendation.AccuracyWeight = 0.4
			}
		}
	}

	if c.Thanos.ExternalLabels == nil {
		c.Thanos.ExternalLabels = make(map[string]string)
	}
	c.Thanos.ExternalLabels["downsampled"] = "true"
}

func (c *Config) GetRuleByName(name string) *MetricRule {
	for i := range c.MetricRules {
		if c.MetricRules[i].Name == name {
			return &c.MetricRules[i]
		}
	}
	return nil
}
