package config

import (
	"fmt"
	"strings"
	"time"

	"github.com/spf13/viper"
)

func LoadConfig(configPath string) (*Config, error) {
	v := viper.New()

	v.SetConfigName("config")
	v.SetConfigType("yaml")
	v.AddConfigPath(configPath)
	v.AddConfigPath(".")
	v.AddConfigPath("./configs")
	v.SetEnvPrefix("DB_BENCH")
	v.SetEnvKeyReplacer(strings.NewReplacer(".", "_"))
	v.AutomaticEnv()

	v.SetDefault("database.host", "localhost")
	v.SetDefault("database.port", 3306)
	v.SetDefault("database.user", "root")
	v.SetDefault("database.password", "")
	v.SetDefault("database.database", "benchmark")
	v.SetDefault("database.max_connections", 100)
	v.SetDefault("database.timeout", 10*time.Second)

	v.SetDefault("scenario.name", "default")
	v.SetDefault("scenario.duration", 60*time.Second)
	v.SetDefault("scenario.concurrency", 50)
	v.SetDefault("scenario.read_ratio", 0.7)
	v.SetDefault("scenario.write_ratio", 0.3)
	v.SetDefault("scenario.hotspot_percentage", 10.0)
	v.SetDefault("scenario.hotspot_access_ratio", 0.8)
	v.SetDefault("scenario.hotspot_distribution", "zipf")
	v.SetDefault("scenario.hotspot_skew", 1.2)
	v.SetDefault("scenario.total_records", 10000)
	v.SetDefault("scenario.rate_limit", 0)
	v.SetDefault("scenario.gradual_startup", true)
	v.SetDefault("scenario.gradual_startup_step", 0.1)
	v.SetDefault("scenario.gradual_startup_interval", 5*time.Second)

	v.SetDefault("metrics.prometheus_port", 9091)
	v.SetDefault("metrics.prometheus_path", "/metrics")

	if err := v.ReadInConfig(); err != nil {
		if _, ok := err.(viper.ConfigFileNotFoundError); ok {
			fmt.Printf("Warning: Config file not found, using defaults and environment variables\n")
		} else {
			return nil, fmt.Errorf("failed to read config file: %w", err)
		}
	}

	var cfg Config
	if err := v.Unmarshal(&cfg); err != nil {
		return nil, fmt.Errorf("failed to unmarshal config: %w", err)
	}

	if err := validateConfig(&cfg); err != nil {
		return nil, err
	}

	return &cfg, nil
}

func validateConfig(cfg *Config) error {
	switch cfg.Database.Type {
	case MySQL, PostgreSQL, MongoDB:
	default:
		return fmt.Errorf("unsupported database type: %s (must be mysql, postgres, or mongodb)", cfg.Database.Type)
	}

	if cfg.Database.Host == "" {
		return fmt.Errorf("database host is required")
	}

	if cfg.Database.User == "" {
		return fmt.Errorf("database user is required")
	}

	if cfg.Database.Database == "" {
		return fmt.Errorf("database name is required")
	}

	if cfg.Scenario.Concurrency <= 0 {
		return fmt.Errorf("concurrency must be greater than 0")
	}

	if cfg.Scenario.Duration <= 0 {
		return fmt.Errorf("duration must be greater than 0")
	}

	if cfg.Scenario.ReadRatio+cfg.Scenario.WriteRatio != 1.0 {
		return fmt.Errorf("read_ratio + write_ratio must equal 1.0")
	}

	if cfg.Scenario.TotalRecords <= 0 {
		return fmt.Errorf("total_records must be greater than 0")
	}

	if cfg.Scenario.HotspotPercentage < 0 || cfg.Scenario.HotspotPercentage > 100 {
		return fmt.Errorf("hotspot_percentage must be between 0 and 100")
	}

	if cfg.Scenario.HotspotAccessRatio < 0 || cfg.Scenario.HotspotAccessRatio > 1.0 {
		return fmt.Errorf("hotspot_access_ratio must be between 0 and 1")
	}

	if cfg.Scenario.RateLimit < 0 {
		return fmt.Errorf("rate_limit must be greater than or equal to 0 (0 means unlimited)")
	}

	switch cfg.Scenario.HotspotDistribution {
	case HotspotUniform, HotspotZipf:
	default:
		return fmt.Errorf("hotspot_distribution must be either 'uniform' or 'zipf'")
	}

	if cfg.Scenario.HotspotSkew < 1.0 || cfg.Scenario.HotspotSkew > 5.0 {
		return fmt.Errorf("hotspot_skew must be between 1.0 and 5.0")
	}

	if cfg.Scenario.GradualStartup {
		if cfg.Scenario.GradualStartupStep <= 0 || cfg.Scenario.GradualStartupStep > 1.0 {
			return fmt.Errorf("gradual_startup_step must be between 0 and 1.0")
		}
		if cfg.Scenario.GradualStartupInterval <= 0 {
			return fmt.Errorf("gradual_startup_interval must be greater than 0")
		}
	}

	return nil
}
