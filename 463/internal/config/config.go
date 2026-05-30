package config

import (
	"fmt"
	"os"
	"time"

	"gopkg.in/yaml.v3"
)

type DatabaseType string

const (
	MySQL      DatabaseType = "mysql"
	PostgreSQL DatabaseType = "postgresql"
)

type DatabaseConfig struct {
	Type     DatabaseType `yaml:"type"`
	Host     string       `yaml:"host"`
	Port     int          `yaml:"port"`
	User     string       `yaml:"user"`
	Password string       `yaml:"password"`
	DBName   string       `yaml:"dbname"`
	DSN      string       `yaml:"dsn,omitempty"`
}

type ThresholdConfig struct {
	MaxExecutionTime time.Duration `yaml:"max_execution_time"`
	MaxRowsExamined  int64         `yaml:"max_rows_examined,omitempty"`
	MaxLockTime      time.Duration `yaml:"max_lock_time,omitempty"`
}

type TransactionWaitConfig struct {
	Enabled      bool          `yaml:"enabled"`
	WaitDuration time.Duration `yaml:"wait_duration"`
	CheckInterval time.Duration `yaml:"check_interval"`
}

type WhitelistConfig struct {
	Users       []string `yaml:"users"`
	Databases   []string `yaml:"databases"`
	QueryPrefix []string `yaml:"query_prefix"`
	SQLFingerprints []string `yaml:"sql_fingerprints"`
}

type RuleConfig struct {
	Name        string        `yaml:"name"`
	Enabled     bool          `yaml:"enabled"`
	Threshold   time.Duration `yaml:"threshold"`
	QueryRegex  string        `yaml:"query_regex,omitempty"`
	KillMode    string        `yaml:"kill_mode"`
	NotifyOnly  bool          `yaml:"notify_only,omitempty"`
}

type PredictionConfig struct {
	Enabled           bool          `yaml:"enabled"`
	ConfidenceThreshold float64    `yaml:"confidence_threshold"`
	ReportInterval    time.Duration `yaml:"report_interval"`
}

type IndexerConfig struct {
	Enabled              bool          `yaml:"enabled"`
	MinKillCount         int           `yaml:"min_kill_count"`
	AutoSuggestThreshold int           `yaml:"auto_suggest_threshold"`
	ReportInterval       time.Duration `yaml:"report_interval"`
}

type AuditConfig struct {
	Enabled     bool   `yaml:"enabled"`
	LogPath     string `yaml:"log_path"`
	RotateDaily bool   `yaml:"rotate_daily"`
}

type MonitorConfig struct {
	Interval         time.Duration         `yaml:"interval"`
	DefaultKillMode  string                `yaml:"default_kill_mode"`
	DryRun           bool                  `yaml:"dry_run"`
	Rules            []RuleConfig          `yaml:"rules"`
	Threshold        ThresholdConfig       `yaml:"threshold"`
	Whitelist        WhitelistConfig       `yaml:"whitelist"`
	TransactionWait  TransactionWaitConfig `yaml:"transaction_wait"`
	Prediction       PredictionConfig      `yaml:"prediction"`
	Indexer          IndexerConfig         `yaml:"indexer"`
	Audit            AuditConfig           `yaml:"audit"`
}

type LogConfig struct {
	Level     string `yaml:"level"`
	Format    string `yaml:"format"`
	Output    string `yaml:"output"`
	KillLog   string `yaml:"kill_log"`
}

type Config struct {
	Databases map[string]DatabaseConfig `yaml:"databases"`
	Monitor   MonitorConfig             `yaml:"monitor"`
	Log       LogConfig                 `yaml:"log"`
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

	if err := cfg.validate(); err != nil {
		return nil, fmt.Errorf("invalid configuration: %w", err)
	}

	cfg.setDefaults()

	return &cfg, nil
}

func (c *Config) validate() error {
	if len(c.Databases) == 0 {
		return fmt.Errorf("no databases configured")
	}

	for name, db := range c.Databases {
		if db.Type != MySQL && db.Type != PostgreSQL {
			return fmt.Errorf("database %s has unsupported type: %s", name, db.Type)
		}
	}

	if c.Monitor.Interval <= 0 {
		return fmt.Errorf("monitor interval must be positive")
	}

	if c.Monitor.Threshold.MaxExecutionTime <= 0 {
		return fmt.Errorf("max_execution_time threshold must be positive")
	}

	return nil
}

func (c *Config) setDefaults() {
	if c.Monitor.DefaultKillMode == "" {
		c.Monitor.DefaultKillMode = "connection"
	}

	if c.Monitor.TransactionWait.WaitDuration == 0 {
		c.Monitor.TransactionWait.WaitDuration = 5 * time.Second
	}

	if c.Monitor.TransactionWait.CheckInterval == 0 {
		c.Monitor.TransactionWait.CheckInterval = 100 * time.Millisecond
	}

	if c.Monitor.Prediction.ConfidenceThreshold == 0 {
		c.Monitor.Prediction.ConfidenceThreshold = 0.7
	}

	if c.Monitor.Prediction.ReportInterval == 0 {
		c.Monitor.Prediction.ReportInterval = 1 * time.Hour
	}

	if c.Monitor.Indexer.MinKillCount == 0 {
		c.Monitor.Indexer.MinKillCount = 3
	}

	if c.Monitor.Indexer.AutoSuggestThreshold == 0 {
		c.Monitor.Indexer.AutoSuggestThreshold = 10
	}

	if c.Monitor.Indexer.ReportInterval == 0 {
		c.Monitor.Indexer.ReportInterval = 2 * time.Hour
	}

	if c.Monitor.Audit.LogPath == "" {
		c.Monitor.Audit.LogPath = "logs/audit.jsonl"
	}

	if c.Log.Level == "" {
		c.Log.Level = "info"
	}

	if c.Log.Format == "" {
		c.Log.Format = "text"
	}

	if c.Log.Output == "" {
		c.Log.Output = "stdout"
	}

	if c.Log.KillLog == "" {
		c.Log.KillLog = "killed_queries.log"
	}
}

func (c *Config) GetDSN(dbName string) (string, error) {
	db, exists := c.Databases[dbName]
	if !exists {
		return "", fmt.Errorf("database %s not found", dbName)
	}

	if db.DSN != "" {
		return db.DSN, nil
	}

	switch db.Type {
	case MySQL:
		return fmt.Sprintf("%s:%s@tcp(%s:%d)/%s?charset=utf8mb4&parseTime=true",
			db.User, db.Password, db.Host, db.Port, db.DBName), nil
	case PostgreSQL:
		return fmt.Sprintf("postgres://%s:%s@%s:%d/%s?sslmode=disable",
			db.User, db.Password, db.Host, db.Port, db.DBName), nil
	default:
		return "", fmt.Errorf("unsupported database type: %s", db.Type)
	}
}
