package config

import (
	"fmt"
	"strings"

	"github.com/spf13/viper"
)

type KafkaConfig struct {
	Brokers          string `mapstructure:"brokers"`
	Username         string `mapstructure:"username"`
	Password         string `mapstructure:"password"`
	SecurityProtocol string `mapstructure:"security_protocol"`
	SASLMechanism    string `mapstructure:"sasl_mechanism"`
}

type StandbyClusterConfig struct {
	Enabled          bool   `mapstructure:"enabled"`
	KafkaConfig      `mapstructure:",squash"`
	HealthCheckIntervalSeconds int `mapstructure:"health_check_interval_seconds"`
	FailoverThreshold int   `mapstructure:"failover_threshold"`
	AutoSwitchBack   bool   `mapstructure:"auto_switch_back"`
	SwitchBackIntervalMinutes int `mapstructure:"switch_back_interval_minutes"`
}

type FilterConfig struct {
	KeyRegex   string `mapstructure:"key_regex"`
	ValueRegex string `mapstructure:"value_regex"`
	TopicRegex string `mapstructure:"topic_regex"`
	JSONPaths  []JSONPathFilter `mapstructure:"json_paths"`
}

type JSONPathFilter struct {
	Path     string `mapstructure:"path"`
	Operator string `mapstructure:"operator"`
	Value    string `mapstructure:"value"`
}

type LoopPreventionConfig struct {
	Enabled   bool   `mapstructure:"enabled"`
	HeaderKey string `mapstructure:"header_key"`
	MaxHops   int    `mapstructure:"max_hops"`
}

type LagMonitorConfig struct {
	CollectIntervalSeconds int     `mapstructure:"collect_interval_seconds"`
	WindowSize             int     `mapstructure:"window_size"`
	AlertThreshold         float64 `mapstructure:"alert_threshold"`
}

type TopicDiscoveryConfig struct {
	Enabled              bool   `mapstructure:"enabled"`
	IntervalSeconds      int    `mapstructure:"interval_seconds"`
	TopicNameRegex       string `mapstructure:"topic_name_regex"`
	ExcludeInternalTopics bool  `mapstructure:"exclude_internal_topics"`
}

type TopicAutoCreateConfig struct {
	Enabled              bool `mapstructure:"enabled"`
	DefaultPartitions    int  `mapstructure:"default_partitions"`
	DefaultReplicationFactor int `mapstructure:"default_replication_factor"`
	RetentionMs          int64 `mapstructure:"retention_ms"`
}

type CompressionConfig struct {
	Enabled  bool   `mapstructure:"enabled"`
	Codec    string `mapstructure:"codec"`
	Level    int    `mapstructure:"level"`
}

type MirrorConfig struct {
	SourceCluster     KafkaConfig          `mapstructure:"source_cluster"`
	StandbyCluster    StandbyClusterConfig `mapstructure:"standby_cluster"`
	TargetCluster     KafkaConfig          `mapstructure:"target_cluster"`
	Topics            []string             `mapstructure:"topics"`
	ConsumerGroupID   string               `mapstructure:"consumer_group_id"`
	SyncMode          string               `mapstructure:"sync_mode"`
	Filter            FilterConfig         `mapstructure:"filter"`
	LoopPrevention    LoopPreventionConfig `mapstructure:"loop_prevention"`
	PrometheusPort    int                  `mapstructure:"prometheus_port"`
	BatchSize         int                  `mapstructure:"batch_size"`
	FlushIntervalMs   int                  `mapstructure:"flush_interval_ms"`
	LagMonitor        LagMonitorConfig     `mapstructure:"lag_monitor"`
	TopicDiscovery    TopicDiscoveryConfig `mapstructure:"topic_discovery"`
	TopicAutoCreate   TopicAutoCreateConfig `mapstructure:"topic_auto_create"`
	Compression       CompressionConfig    `mapstructure:"compression"`
}

func LoadConfig(configPath string) (*MirrorConfig, error) {
	v := viper.New()

	v.SetConfigFile(configPath)
	v.SetConfigType("yaml")

	v.AutomaticEnv()
	v.SetEnvKeyReplacer(strings.NewReplacer(".", "_"))

	setDefaults(v)

	if err := v.ReadInConfig(); err != nil {
		return nil, fmt.Errorf("failed to read config file: %w", err)
	}

	var cfg MirrorConfig
	if err := v.Unmarshal(&cfg); err != nil {
		return nil, fmt.Errorf("failed to unmarshal config: %w", err)
	}

	if err := validateConfig(&cfg); err != nil {
		return nil, fmt.Errorf("config validation failed: %w", err)
	}

	return &cfg, nil
}

func setDefaults(v *viper.Viper) {
	v.SetDefault("sync_mode", "incremental")
	v.SetDefault("loop_prevention.enabled", true)
	v.SetDefault("loop_prevention.header_key", "x-mirror-hop")
	v.SetDefault("loop_prevention.max_hops", 15)
	v.SetDefault("prometheus_port", 9090)
	v.SetDefault("batch_size", 100)
	v.SetDefault("flush_interval_ms", 1000)
	v.SetDefault("consumer_group_id", "kafka-mirror-group")
	v.SetDefault("lag_monitor.collect_interval_seconds", 5)
	v.SetDefault("lag_monitor.window_size", 12)
	v.SetDefault("lag_monitor.alert_threshold", 10000)
	v.SetDefault("topic_discovery.enabled", false)
	v.SetDefault("topic_discovery.interval_seconds", 60)
	v.SetDefault("topic_discovery.exclude_internal_topics", true)
	v.SetDefault("topic_auto_create.enabled", true)
	v.SetDefault("topic_auto_create.default_partitions", 6)
	v.SetDefault("topic_auto_create.default_replication_factor", 3)
	v.SetDefault("topic_auto_create.retention_ms", 604800000)
	v.SetDefault("compression.enabled", true)
	v.SetDefault("compression.codec", "zstd")
	v.SetDefault("compression.level", 3)
	v.SetDefault("standby_cluster.enabled", false)
	v.SetDefault("standby_cluster.health_check_interval_seconds", 10)
	v.SetDefault("standby_cluster.failover_threshold", 3)
	v.SetDefault("standby_cluster.auto_switch_back", true)
	v.SetDefault("standby_cluster.switch_back_interval_minutes", 5)
}

func validateConfig(cfg *MirrorConfig) error {
	if cfg.SourceCluster.Brokers == "" {
		return fmt.Errorf("source cluster brokers is required")
	}
	if cfg.TargetCluster.Brokers == "" {
		return fmt.Errorf("target cluster brokers is required")
	}
	if len(cfg.Topics) == 0 && !cfg.TopicDiscovery.Enabled {
		return fmt.Errorf("at least one topic is required or enable topic_discovery")
	}
	if cfg.SyncMode != "full" && cfg.SyncMode != "incremental" && cfg.SyncMode != "full+incremental" {
		return fmt.Errorf("invalid sync_mode: must be 'full', 'incremental', or 'full+incremental'")
	}
	if cfg.LoopPrevention.MaxHops < 1 || cfg.LoopPrevention.MaxHops > 15 {
		return fmt.Errorf("loop_prevention.max_hops must be between 1 and 15")
	}
	if cfg.LagMonitor.CollectIntervalSeconds < 1 {
		return fmt.Errorf("lag_monitor.collect_interval_seconds must be >= 1")
	}
	if cfg.LagMonitor.WindowSize < 1 {
		return fmt.Errorf("lag_monitor.window_size must be >= 1")
	}
	if cfg.Compression.Enabled {
		if cfg.Compression.Codec != "zstd" && cfg.Compression.Codec != "snappy" && cfg.Compression.Codec != "lz4" && cfg.Compression.Codec != "gzip" {
			return fmt.Errorf("compression.codec must be zstd, snappy, lz4, or gzip")
		}
	}
	if cfg.StandbyCluster.Enabled && cfg.StandbyCluster.Brokers == "" {
		return fmt.Errorf("standby_cluster.brokers is required when standby_cluster.enabled is true")
	}
	return nil
}

func (k *KafkaConfig) GetBrokers() []string {
	return strings.Split(k.Brokers, ",")
}
