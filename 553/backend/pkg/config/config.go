package config

import (
	"fmt"

	"github.com/spf13/viper"
)

type Config struct {
	Elasticsearch ElasticsearchConfig `mapstructure:"elasticsearch"`
	Server        ServerConfig        `mapstructure:"server"`
	Balancer      BalancerConfig      `mapstructure:"balancer"`
	Logging       LoggingConfig       `mapstructure:"logging"`
}

type ElasticsearchConfig struct {
	URL      string `mapstructure:"url"`
	Username string `mapstructure:"username"`
	Password string `mapstructure:"password"`
	Timeout  int    `mapstructure:"timeout"`
}

type ServerConfig struct {
	Port int    `mapstructure:"port"`
	Mode string `mapstructure:"mode"`
}

type BalancerConfig struct {
	Enabled               bool              `mapstructure:"enabled"`
	Schedule              string            `mapstructure:"schedule"`
	MaxMigrationsPerCycle int               `mapstructure:"max_migrations_per_cycle"`
	MigrationTimeout      int               `mapstructure:"migration_timeout"`
	DiskWatermark         DiskWatermark     `mapstructure:"disk_watermark"`
	SpeedLimit            SpeedLimit        `mapstructure:"speed_limit"`
	HotCold               HotColdConfig     `mapstructure:"hot_cold"`
	LoadAwareness         LoadAwareness     `mapstructure:"load_awareness"`
	ShardHeat             ShardHeatConfig   `mapstructure:"shard_heat"`
	AutoScaling           AutoScalingConfig `mapstructure:"auto_scaling"`
}

type ShardHeatConfig struct {
	Enabled            bool    `mapstructure:"enabled"`
	HistorySize        int     `mapstructure:"history_size"`
	QueryWeight        float64 `mapstructure:"query_weight"`
	IndexWeight        float64 `mapstructure:"index_weight"`
	HeatThreshold      float64 `mapstructure:"heat_threshold"`
	PriorityBoost      float64 `mapstructure:"priority_boost"`
	CollectIntervalSec int     `mapstructure:"collect_interval_sec"`
}

type AutoScalingConfig struct {
	Enabled              bool   `mapstructure:"enabled"`
	FloodThreshold       float64 `mapstructure:"flood_threshold"`
	CooldownMinutes      int    `mapstructure:"cooldown_minutes"`
	MinNodes             int    `mapstructure:"min_nodes"`
	MaxNodes             int    `mapstructure:"max_nodes"`
	Provider             string `mapstructure:"provider"`
	NodeType             string `mapstructure:"node_type"`
	DiskSizeGB           int    `mapstructure:"disk_size_gb"`
	WebhookURL           string `mapstructure:"webhook_url"`
}

type DiskWatermark struct {
	Low            float64 `mapstructure:"low"`
	High           float64 `mapstructure:"high"`
	Flood          float64 `mapstructure:"flood"`
	DynamicEnabled bool    `mapstructure:"dynamic_enabled"`
	BaseCapacityGB float64 `mapstructure:"base_capacity_gb"`
	MaxExtraPercent float64 `mapstructure:"max_extra_percent"`
}

type SpeedLimit struct {
	MaxBytesPerSec      string `mapstructure:"max_bytes_per_sec"`
	MinBytesPerSec      string `mapstructure:"min_bytes_per_sec"`
	AdaptiveEnabled     bool   `mapstructure:"adaptive_enabled"`
	TargetPendingTasks  int    `mapstructure:"target_pending_tasks"`
	AdjustIntervalSec   int    `mapstructure:"adjust_interval_sec"`
}

type LoadAwareness struct {
	Enabled           bool    `mapstructure:"enabled"`
	HistorySize       int     `mapstructure:"history_size"`
	HighLoadThreshold float64 `mapstructure:"high_load_threshold"`
	IOWaitThreshold   float64 `mapstructure:"io_wait_threshold"`
	CPULoadThreshold  float64 `mapstructure:"cpu_load_threshold"`
	AvoidHighLoadNodes bool   `mapstructure:"avoid_high_load_nodes"`
}

type HotColdConfig struct {
	Enabled        bool   `mapstructure:"enabled"`
	HotNodeAttr    string `mapstructure:"hot_node_attr"`
	HotNodeValue   string `mapstructure:"hot_node_value"`
	ColdNodeAttr   string `mapstructure:"cold_node_attr"`
	ColdNodeValue  string `mapstructure:"cold_node_value"`
}

type LoggingConfig struct {
	Level  string `mapstructure:"level"`
	Format string `mapstructure:"format"`
}

func Load(path string) (*Config, error) {
	v := viper.New()
	v.SetConfigFile(path)
	v.SetConfigType("yaml")

	if err := v.ReadInConfig(); err != nil {
		return nil, fmt.Errorf("failed to read config: %w", err)
	}

	var cfg Config
	if err := v.Unmarshal(&cfg); err != nil {
		return nil, fmt.Errorf("failed to unmarshal config: %w", err)
	}

	return &cfg, nil
}
