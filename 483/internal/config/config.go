package config

import (
	"time"

	"github.com/spf13/viper"
)

type Config struct {
	Kafka    KafkaConfig    `mapstructure:"kafka"`
	Analyzer AnalyzerConfig `mapstructure:"analyzer"`
	Metrics  MetricsConfig  `mapstructure:"metrics"`
	Server   ServerConfig   `mapstructure:"server"`
}

type KafkaConfig struct {
	Brokers             []string      `mapstructure:"brokers"`
	ConsumerGroups      []string      `mapstructure:"consumer_groups"`
	Topics              []string      `mapstructure:"topics"`
	Username            string        `mapstructure:"username"`
	Password            string        `mapstructure:"password"`
	TLSEnabled          bool          `mapstructure:"tls_enabled"`
	Timeout             time.Duration `mapstructure:"timeout"`
	ScrapeInterval      time.Duration `mapstructure:"scrape_interval"`
	RTTWarningThreshold int           `mapstructure:"rtt_warning_threshold"`
	RTTCriticalThreshold int          `mapstructure:"rtt_critical_threshold"`
	EnableRTTProbe      bool          `mapstructure:"enable_rtt_probe"`
	RTTProbeInterval    time.Duration `mapstructure:"rtt_probe_interval"`
}

type AnalyzerConfig struct {
	LagThreshold            int64   `mapstructure:"lag_threshold"`
	HotspotThreshold        float64 `mapstructure:"hotspot_threshold"`
	SlowProcessingThreshold float64 `mapstructure:"slow_processing_threshold"`
	NetworkLatencyThreshold float64 `mapstructure:"network_latency_threshold"`
	ImbalanceThreshold      float64 `mapstructure:"imbalance_threshold"`
	HistoryRetention        int     `mapstructure:"history_retention"`
	MessageSizeWeight       float64 `mapstructure:"message_size_weight"`
}

type MetricsConfig struct {
	EnablePrometheus bool   `mapstructure:"enable_prometheus"`
	Path             string `mapstructure:"path"`
}

type ServerConfig struct {
	Host string `mapstructure:"host"`
	Port int    `mapstructure:"port"`
}

func Load(path string) (*Config, error) {
	v := viper.New()
	v.SetConfigFile(path)
	v.SetConfigType("yaml")

	v.SetDefault("kafka.timeout", 30*time.Second)
	v.SetDefault("kafka.scrape_interval", 15*time.Second)
	v.SetDefault("kafka.rtt_warning_threshold", 50)
	v.SetDefault("kafka.rtt_critical_threshold", 200)
	v.SetDefault("kafka.enable_rtt_probe", true)
	v.SetDefault("kafka.rtt_probe_interval", 10*time.Second)
	v.SetDefault("analyzer.lag_threshold", 1000)
	v.SetDefault("analyzer.hotspot_threshold", 0.5)
	v.SetDefault("analyzer.slow_processing_threshold", 100.0)
	v.SetDefault("analyzer.network_latency_threshold", 500.0)
	v.SetDefault("analyzer.imbalance_threshold", 0.3)
	v.SetDefault("analyzer.history_retention", 100)
	v.SetDefault("analyzer.message_size_weight", 0.5)
	v.SetDefault("metrics.enable_prometheus", true)
	v.SetDefault("metrics.path", "/metrics")
	v.SetDefault("server.host", "0.0.0.0")
	v.SetDefault("server.port", 8080)

	if err := v.ReadInConfig(); err != nil {
		return nil, err
	}

	var cfg Config
	if err := v.Unmarshal(&cfg); err != nil {
		return nil, err
	}

	return &cfg, nil
}
