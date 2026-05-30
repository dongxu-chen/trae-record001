package config

import (
	"time"
)

type DatabaseConfig struct {
	Type     string `json:"type"`
	Host     string `json:"host"`
	Port     int    `json:"port"`
	User     string `json:"user"`
	Password string `json:"password"`
	DBName   string `json:"dbname"`
}

type StrategyConfig struct {
	Enabled            bool          `json:"enabled"`
	DetectionInterval  time.Duration `json:"detection_interval"`
	AutoKill           bool          `json:"auto_kill"`
	KillStrategy       string        `json:"kill_strategy"`
	MaxTransactionTime time.Duration `json:"max_transaction_time"`
	MinAffectedRows    int           `json:"min_affected_rows"`
	ExcludeUsers       []string      `json:"exclude_users"`
	ExcludeDatabases   []string      `json:"exclude_databases"`
}

type Config struct {
	Database  DatabaseConfig `json:"database"`
	Strategy  StrategyConfig `json:"strategy"`
	HTTPPort  int            `json:"http_port"`
	LogLevel  string         `json:"log_level"`
	StorePath string         `json:"store_path"`
}

func DefaultConfig() *Config {
	return &Config{
		Database: DatabaseConfig{
			Type:     "mysql",
			Host:     "localhost",
			Port:     3306,
			User:     "root",
			Password: "",
			DBName:   "information_schema",
		},
		Strategy: StrategyConfig{
			Enabled:            true,
			DetectionInterval:  5 * time.Second,
			AutoKill:           false,
			KillStrategy:       "youngest",
			MaxTransactionTime: 300 * time.Second,
			MinAffectedRows:    0,
			ExcludeUsers:       []string{"system", "admin"},
			ExcludeDatabases:   []string{"information_schema", "mysql", "performance_schema"},
		},
		HTTPPort:  8080,
		LogLevel:  "info",
		StorePath: "./data",
	}
}
