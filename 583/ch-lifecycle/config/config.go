package config

import (
	"os"

	"go.uber.org/zap"
	"gopkg.in/yaml.v3"
)

type ClickHouseConfig struct {
	Hosts       []string `yaml:"hosts"`
	Port        int      `yaml:"port"`
	HTTPPort    int      `yaml:"http_port"`
	Username    string   `yaml:"username"`
	Password    string   `yaml:"password"`
	Database    string   `yaml:"database"`
	MaxOpenConns int     `yaml:"max_open_conns"`
	MaxIdleConns int     `yaml:"max_idle_conns"`
	DialTimeout  int     `yaml:"dial_timeout_seconds"`
}

type StorageTier struct {
	Name     string `yaml:"name"`
	Type     string `yaml:"type"`
	Path     string `yaml:"path"`
	Priority int    `yaml:"priority"`
}

type SchedulerConfig struct {
	Enabled          bool   `yaml:"enabled"`
	CheckInterval    string `yaml:"check_interval"`
	TTLCheckCron     string `yaml:"ttl_check_cron"`
	TieringCron      string `yaml:"tiering_cron"`
	CleanupCron      string `yaml:"cleanup_cron"`
	OptimizeCron     string `yaml:"optimize_cron"`
}

type MonitorConfig struct {
	Enabled         bool   `yaml:"enabled"`
	MetricsPath     string `yaml:"metrics_path"`
	MetricsPort     int    `yaml:"metrics_port"`
	CollectInterval string `yaml:"collect_interval"`
}

type ObjectStorageConfig struct {
	Enabled      bool   `yaml:"enabled"`
	Endpoint     string `yaml:"endpoint"`
	Region       string `yaml:"region"`
	Bucket       string `yaml:"bucket"`
	AccessKey    string `yaml:"access_key"`
	SecretKey    string `yaml:"secret_key"`
	UseSSL       bool   `yaml:"use_ssl"`
	PathPrefix   string `yaml:"path_prefix"`
	ArchiveCron  string `yaml:"archive_cron"`
	ExportFormat string `yaml:"export_format"`
}

type ServerConfig struct {
	Port int    `yaml:"port"`
	Mode string `yaml:"mode"`
}

type Config struct {
	ClickHouse     ClickHouseConfig    `yaml:"clickhouse"`
	Storage        []StorageTier       `yaml:"storage_tiers"`
	Scheduler      SchedulerConfig     `yaml:"scheduler"`
	Monitor        MonitorConfig       `yaml:"monitor"`
	Archive        ObjectStorageConfig `yaml:"archive"`
	Server         ServerConfig        `yaml:"server"`
}

func Load(path string) (*Config, error) {
	data, err := os.ReadFile(path)
	if err != nil {
		return nil, err
	}
	var cfg Config
	if err := yaml.Unmarshal(data, &cfg); err != nil {
		return nil, err
	}
	setDefaults(&cfg)
	return &cfg, nil
}

func setDefaults(cfg *Config) {
	if cfg.ClickHouse.Port == 0 {
		cfg.ClickHouse.Port = 9000
	}
	if cfg.ClickHouse.HTTPPort == 0 {
		cfg.ClickHouse.HTTPPort = 8123
	}
	if cfg.ClickHouse.MaxOpenConns == 0 {
		cfg.ClickHouse.MaxOpenConns = 10
	}
	if cfg.ClickHouse.MaxIdleConns == 0 {
		cfg.ClickHouse.MaxIdleConns = 5
	}
	if cfg.ClickHouse.DialTimeout == 0 {
		cfg.ClickHouse.DialTimeout = 10
	}
	if cfg.Scheduler.CheckInterval == "" {
		cfg.Scheduler.CheckInterval = "5m"
	}
	if cfg.Scheduler.TTLCheckCron == "" {
		cfg.Scheduler.TTLCheckCron = "0 */10 * * * *"
	}
	if cfg.Scheduler.TieringCron == "" {
		cfg.Scheduler.TieringCron = "0 0 */1 * * *"
	}
	if cfg.Scheduler.CleanupCron == "" {
		cfg.Scheduler.CleanupCron = "0 0 2 * * *"
	}
	if cfg.Scheduler.OptimizeCron == "" {
		cfg.Scheduler.OptimizeCron = "0 0 3 * * *"
	}
	if cfg.Monitor.MetricsPath == "" {
		cfg.Monitor.MetricsPath = "/metrics"
	}
	if cfg.Monitor.MetricsPort == 0 {
		cfg.Monitor.MetricsPort = 9090
	}
	if cfg.Monitor.CollectInterval == "" {
		cfg.Monitor.CollectInterval = "30s"
	}
	if cfg.Server.Port == 0 {
		cfg.Server.Port = 8080
	}
	if cfg.Server.Mode == "" {
		cfg.Server.Mode = "release"
	}
	if cfg.Archive.Endpoint == "" {
		cfg.Archive.Endpoint = "localhost:9000"
	}
	if cfg.Archive.Region == "" {
		cfg.Archive.Region = "us-east-1"
	}
	if cfg.Archive.PathPrefix == "" {
		cfg.Archive.PathPrefix = "clickhouse-archives"
	}
	if cfg.Archive.ArchiveCron == "" {
		cfg.Archive.ArchiveCron = "0 0 4 * * *"
	}
	if cfg.Archive.ExportFormat == "" {
		cfg.Archive.ExportFormat = "Parquet"
	}
}

func MustLogger() *zap.Logger {
	logger, err := zap.NewProduction()
	if err != nil {
		panic(err)
	}
	return logger
}
