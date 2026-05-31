package config

import (
	"os"

	"gopkg.in/yaml.v3"
)

type Config struct {
	Server     ServerConfig     `yaml:"server"`
	Cluster    ClusterConfig    `yaml:"cluster"`
	Monitor    MonitorConfig    `yaml:"monitor"`
	Scaler     ScalerConfig     `yaml:"scaler"`
	Migration  MigrationConfig  `yaml:"migration"`
	Backup     BackupConfig     `yaml:"backup"`
	Failover   FailoverConfig   `yaml:"failover"`
	Cost       CostConfig       `yaml:"cost"`
	Simulation SimulationConfig `yaml:"simulation"`
}

type ServerConfig struct {
	Addr string `yaml:"addr"`
}

type ClusterConfig struct {
	Addrs    []string `yaml:"addrs"`
	Password string   `yaml:"password"`
	PoolSize int      `yaml:"pool_size"`
}

type MonitorConfig struct {
	IntervalSeconds int `yaml:"interval_seconds"`
	HistorySize     int `yaml:"history_size"`
}

type ScalerConfig struct {
	Enabled            bool    `yaml:"enabled"`
	CheckIntervalSec   int     `yaml:"check_interval_sec"`
	MemoryThresholdUp  float64 `yaml:"memory_threshold_up"`
	MemoryThresholdDown float64 `yaml:"memory_threshold_down"`
	QPSThresholdUp     float64 `yaml:"qps_threshold_up"`
	QPSThresholdDown   float64 `yaml:"qps_threshold_down"`
	HitRateThreshold   float64 `yaml:"hit_rate_threshold"`
	MaxNodes           int     `yaml:"max_nodes"`
	MinNodes           int     `yaml:"min_nodes"`
	CooldownSec        int     `yaml:"cooldown_sec"`
}

type MigrationConfig struct {
	BatchSize         int  `yaml:"batch_size"`
	TimeoutSec        int  `yaml:"timeout_sec"`
	RetryCount        int  `yaml:"retry_count"`
	RetryIntervalMs   int  `yaml:"retry_interval_ms"`
	AdaptiveBatching  bool `yaml:"adaptive_batching"`
	PostMigrationBackup bool `yaml:"post_migration_backup"`
	DonorPriorityByMemory bool `yaml:"donor_priority_by_memory"`
	SmallSlotThreshold  int64 `yaml:"small_slot_threshold"`
	LargeSlotThreshold  int64 `yaml:"large_slot_threshold"`
}

type BackupConfig struct {
	Enabled       bool   `yaml:"enabled"`
	IntervalSec   int    `yaml:"interval_sec"`
	Dir           string `yaml:"dir"`
	RetainCount   int    `yaml:"retain_count"`
	PostMigration bool   `yaml:"post_migration"`
}

type FailoverConfig struct {
	Enabled                 bool `yaml:"enabled"`
	HealthCheckIntervalSec  int  `yaml:"health_check_interval_sec"`
	FailureThreshold        int  `yaml:"failure_threshold"`
	HealthCheckRetries      int  `yaml:"health_check_retries"`
	AutoFailover            bool `yaml:"auto_failover"`
	ManualFailoverAllowed   bool `yaml:"manual_failover_allowed"`
}

type CostConfig struct {
	Enabled              bool    `yaml:"enabled"`
	Currency             string  `yaml:"currency"`
	PricePerGBHour       float64 `yaml:"price_per_gb_hour"`
	DefaultMemoryGB      float64 `yaml:"default_memory_gb"`
	MasterMultiplier     float64 `yaml:"master_multiplier"`
	ReplicaMultiplier    float64 `yaml:"replica_multiplier"`
}

type SimulationConfig struct {
	Enabled              bool `yaml:"enabled"`
	MaxSimulatedNodes    int  `yaml:"max_simulated_nodes"`
	EstimatedMsPerKey    int  `yaml:"estimated_ms_per_key"`
	AutoApproveLowRisk   bool `yaml:"auto_approve_low_risk"`
}

func Load(path string) (*Config, error) {
	data, err := os.ReadFile(path)
	if err != nil {
		return nil, err
	}
	cfg := &Config{}
	if err := yaml.Unmarshal(data, cfg); err != nil {
		return nil, err
	}
	cfg.setDefaults()
	return cfg, nil
}

func (c *Config) setDefaults() {
	if c.Server.Addr == "" {
		c.Server.Addr = ":8080"
	}
	if c.Cluster.PoolSize == 0 {
		c.Cluster.PoolSize = 10
	}
	if c.Monitor.IntervalSeconds == 0 {
		c.Monitor.IntervalSeconds = 5
	}
	if c.Monitor.HistorySize == 0 {
		c.Monitor.HistorySize = 360
	}
	if c.Scaler.CheckIntervalSec == 0 {
		c.Scaler.CheckIntervalSec = 30
	}
	if c.Scaler.MemoryThresholdUp == 0 {
		c.Scaler.MemoryThresholdUp = 0.8
	}
	if c.Scaler.MemoryThresholdDown == 0 {
		c.Scaler.MemoryThresholdDown = 0.3
	}
	if c.Scaler.QPSThresholdUp == 0 {
		c.Scaler.QPSThresholdUp = 50000
	}
	if c.Scaler.QPSThresholdDown == 0 {
		c.Scaler.QPSThresholdDown = 5000
	}
	if c.Scaler.HitRateThreshold == 0 {
		c.Scaler.HitRateThreshold = 0.7
	}
	if c.Scaler.MaxNodes == 0 {
		c.Scaler.MaxNodes = 12
	}
	if c.Scaler.MinNodes == 0 {
		c.Scaler.MinNodes = 3
	}
	if c.Scaler.CooldownSec == 0 {
		c.Scaler.CooldownSec = 300
	}
	if c.Migration.BatchSize == 0 {
		c.Migration.BatchSize = 1000
	}
	if c.Migration.TimeoutSec == 0 {
		c.Migration.TimeoutSec = 60
	}
	if c.Migration.RetryCount == 0 {
		c.Migration.RetryCount = 3
	}
	if c.Migration.RetryIntervalMs == 0 {
		c.Migration.RetryIntervalMs = 500
	}
	if c.Migration.AdaptiveBatching == false && c.Migration.BatchSize == 1000 {
		c.Migration.AdaptiveBatching = true
	}
	if !c.Migration.PostMigrationBackup {
		c.Migration.PostMigrationBackup = true
	}
	if !c.Migration.DonorPriorityByMemory {
		c.Migration.DonorPriorityByMemory = true
	}
	if c.Migration.SmallSlotThreshold == 0 {
		c.Migration.SmallSlotThreshold = 1000
	}
	if c.Migration.LargeSlotThreshold == 0 {
		c.Migration.LargeSlotThreshold = 100000
	}
	if !c.Backup.PostMigration {
		c.Backup.PostMigration = true
	}
	if c.Backup.IntervalSec == 0 {
		c.Backup.IntervalSec = 3600
	}
	if c.Backup.Dir == "" {
		c.Backup.Dir = "./backups"
	}
	if c.Backup.RetainCount == 0 {
		c.Backup.RetainCount = 5
	}

	if !c.Failover.Enabled && c.Failover.HealthCheckIntervalSec == 0 {
		c.Failover.Enabled = true
	}
	if c.Failover.HealthCheckIntervalSec == 0 {
		c.Failover.HealthCheckIntervalSec = 5
	}
	if c.Failover.FailureThreshold == 0 {
		c.Failover.FailureThreshold = 3
	}
	if c.Failover.HealthCheckRetries == 0 {
		c.Failover.HealthCheckRetries = 3
	}
	if !c.Failover.AutoFailover {
		c.Failover.AutoFailover = true
	}
	if !c.Failover.ManualFailoverAllowed {
		c.Failover.ManualFailoverAllowed = true
	}

	if !c.Cost.Enabled {
		c.Cost.Enabled = true
	}
	if c.Cost.Currency == "" {
		c.Cost.Currency = "CNY"
	}
	if c.Cost.PricePerGBHour == 0 {
		c.Cost.PricePerGBHour = 0.15
	}
	if c.Cost.DefaultMemoryGB == 0 {
		c.Cost.DefaultMemoryGB = 16
	}
	if c.Cost.MasterMultiplier == 0 {
		c.Cost.MasterMultiplier = 1.2
	}
	if c.Cost.ReplicaMultiplier == 0 {
		c.Cost.ReplicaMultiplier = 0.8
	}

	if !c.Simulation.Enabled {
		c.Simulation.Enabled = true
	}
	if c.Simulation.MaxSimulatedNodes == 0 {
		c.Simulation.MaxSimulatedNodes = 24
	}
	if c.Simulation.EstimatedMsPerKey == 0 {
		c.Simulation.EstimatedMsPerKey = 5
	}
}
