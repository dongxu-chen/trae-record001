package config

import (
	"fmt"
	"time"

	"github.com/spf13/viper"
)

type Config struct {
	RabbitMQ   RabbitMQConfig   `mapstructure:"rabbitmq"`
	Balancer   BalancerConfig   `mapstructure:"balancer"`
	Prediction PredictionConfig `mapstructure:"prediction"`
	Tenant     TenantConfig     `mapstructure:"tenant"`
	AutoScaler AutoScalerConfig `mapstructure:"autoscaler"`
	Drill      DrillConfig      `mapstructure:"drill"`
	Prometheus PrometheusConfig `mapstructure:"prometheus"`
	Log        LogConfig        `mapstructure:"log"`
}

type RabbitMQConfig struct {
	URL      string        `mapstructure:"url"`
	Username string        `mapstructure:"username"`
	Password string        `mapstructure:"password"`
	Timeout  time.Duration `mapstructure:"timeout"`
	Vhost    string        `mapstructure:"vhost"`
}

type BalancerConfig struct {
	CheckInterval         time.Duration `mapstructure:"check_interval"`
	RebalanceThreshold    float64       `mapstructure:"rebalance_threshold"`
	MaxMigrationsPerCycle int           `mapstructure:"max_migrations_per_cycle"`
	MinMessagesPerQueue   int64         `mapstructure:"min_messages_per_queue"`
	MaxQueueSize          int64         `mapstructure:"max_queue_size"`
	NodeFailureTimeout    time.Duration `mapstructure:"node_failure_timeout"`
	DryRun                bool          `mapstructure:"dry_run"`
	ExcludeQueues         []string      `mapstructure:"exclude_queues"`
	ExcludeVhosts         []string      `mapstructure:"exclude_vhosts"`
	MigrationCooldown     time.Duration `mapstructure:"migration_cooldown"`
	LowTrafficThreshold   float64       `mapstructure:"low_traffic_threshold"`
	MigrationWindowStart  string        `mapstructure:"migration_window_start"`
	MigrationWindowEnd    string        `mapstructure:"migration_window_end"`
}

type PredictionConfig struct {
	Enabled              bool          `mapstructure:"enabled"`
	HistoryWindow        time.Duration `mapstructure:"history_window"`
	PredictionWindow     time.Duration `mapstructure:"prediction_window"`
	DataPoints           int           `mapstructure:"data_points"`
	CollectionInterval   time.Duration `mapstructure:"collection_interval"`
	PredictionThreshold  float64       `mapstructure:"prediction_threshold"`
	BurstDetectionWindow int           `mapstructure:"burst_detection_window"`
	BurstThreshold       float64       `mapstructure:"burst_threshold"`
}

type TenantConfig struct {
	Enabled         bool                  `mapstructure:"enabled"`
	Tenants         []TenantDefinition    `mapstructure:"tenants"`
	DedicatedQueues []DedicatedQueueDef   `mapstructure:"dedicated_queues"`
}

type TenantDefinition struct {
	Name           string   `mapstructure:"name"`
	Vhost          string   `mapstructure:"vhost"`
	Queues         []string `mapstructure:"queues"`
	ExclusiveNodes []string `mapstructure:"exclusive_nodes"`
	Priority       int      `mapstructure:"priority"`
	MaxLoadScore   float64  `mapstructure:"max_load_score"`
}

type DedicatedQueueDef struct {
	QueueName string   `mapstructure:"queue_name"`
	Vhost     string   `mapstructure:"vhost"`
	Nodes     []string `mapstructure:"nodes"`
	Priority  int      `mapstructure:"priority"`
	MinNodes  int      `mapstructure:"min_nodes"`
}

type AutoScalerConfig struct {
	Enabled            bool          `mapstructure:"enabled"`
	MinNodes           int           `mapstructure:"min_nodes"`
	MaxNodes           int           `mapstructure:"max_nodes"`
	ScaleUpThreshold   float64       `mapstructure:"scale_up_threshold"`
	ScaleDownThreshold float64       `mapstructure:"scale_down_threshold"`
	ScaleUpStep        int           `mapstructure:"scale_up_step"`
	ScaleUpCooldown    time.Duration `mapstructure:"scale_up_cooldown"`
	ScaleDownCooldown  time.Duration `mapstructure:"scale_down_cooldown"`
	EvaluationInterval time.Duration `mapstructure:"evaluation_interval"`
	Provider           string        `mapstructure:"provider"`
}

type DrillConfig struct {
	Enabled       bool          `mapstructure:"enabled"`
	Interval      time.Duration `mapstructure:"interval"`
	AutoRun       bool          `mapstructure:"auto_run"`
	MaxRiskLevel  string        `mapstructure:"max_risk_level"`
	BlockOnRisk   bool          `mapstructure:"block_on_risk"`
}

type PrometheusConfig struct {
	Enabled bool   `mapstructure:"enabled"`
	Address string `mapstructure:"address"`
	Path    string `mapstructure:"path"`
}

type LogConfig struct {
	Level  string `mapstructure:"level"`
	Format string `mapstructure:"format"`
}

func Load(path string) (*Config, error) {
	v := viper.New()

	v.SetDefault("rabbitmq.url", "http://localhost:15672")
	v.SetDefault("rabbitmq.username", "guest")
	v.SetDefault("rabbitmq.password", "guest")
	v.SetDefault("rabbitmq.timeout", "10s")
	v.SetDefault("rabbitmq.vhost", "/")

	v.SetDefault("balancer.check_interval", "30s")
	v.SetDefault("balancer.rebalance_threshold", 0.2)
	v.SetDefault("balancer.max_migrations_per_cycle", 5)
	v.SetDefault("balancer.min_messages_per_queue", 100)
	v.SetDefault("balancer.max_queue_size", 1000000)
	v.SetDefault("balancer.node_failure_timeout", "60s")
	v.SetDefault("balancer.dry_run", false)
	v.SetDefault("balancer.exclude_queues", []string{})
	v.SetDefault("balancer.exclude_vhosts", []string{})
	v.SetDefault("balancer.migration_cooldown", "5m")
	v.SetDefault("balancer.low_traffic_threshold", 1.0)
	v.SetDefault("balancer.migration_window_start", "")
	v.SetDefault("balancer.migration_window_end", "")

	v.SetDefault("prediction.enabled", true)
	v.SetDefault("prediction.history_window", "1h")
	v.SetDefault("prediction.prediction_window", "30m")
	v.SetDefault("prediction.data_points", 60)
	v.SetDefault("prediction.collection_interval", "1m")
	v.SetDefault("prediction.prediction_threshold", 0.8)
	v.SetDefault("prediction.burst_detection_window", 10)
	v.SetDefault("prediction.burst_threshold", 3.0)

	v.SetDefault("tenant.enabled", false)
	v.SetDefault("tenant.tenants", []interface{}{})
	v.SetDefault("tenant.dedicated_queues", []interface{}{})

	v.SetDefault("autoscaler.enabled", false)
	v.SetDefault("autoscaler.min_nodes", 2)
	v.SetDefault("autoscaler.max_nodes", 10)
	v.SetDefault("autoscaler.scale_up_threshold", 2.0)
	v.SetDefault("autoscaler.scale_down_threshold", 0.3)
	v.SetDefault("autoscaler.scale_up_step", 1)
	v.SetDefault("autoscaler.scale_up_cooldown", "5m")
	v.SetDefault("autoscaler.scale_down_cooldown", "10m")
	v.SetDefault("autoscaler.evaluation_interval", "1m")
	v.SetDefault("autoscaler.provider", "mock")

	v.SetDefault("drill.enabled", true)
	v.SetDefault("drill.interval", "5m")
	v.SetDefault("drill.auto_run", true)
	v.SetDefault("drill.max_risk_level", "high")
	v.SetDefault("drill.block_on_risk", true)

	v.SetDefault("prometheus.enabled", true)
	v.SetDefault("prometheus.address", ":9090")
	v.SetDefault("prometheus.path", "/metrics")

	v.SetDefault("log.level", "info")
	v.SetDefault("log.format", "json")

	v.SetConfigFile(path)
	v.SetConfigType("yaml")

	if err := v.ReadInConfig(); err != nil {
		if _, ok := err.(viper.ConfigFileNotFoundError); !ok {
			return nil, fmt.Errorf("read config failed: %w", err)
		}
	}

	var config Config
	if err := v.Unmarshal(&config); err != nil {
		return nil, fmt.Errorf("unmarshal config failed: %w", err)
	}

	return &config, nil
}
