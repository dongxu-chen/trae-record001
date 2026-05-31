package config

import (
	"time"
)

type RedisConfig struct {
	Address  string `yaml:"address"`
	Password string `yaml:"password"`
	Databases []int  `yaml:"databases"`
}

type EventFilter struct {
	Enabled       bool     `yaml:"enabled"`
	IncludePrefix []string `yaml:"include_prefix"`
	ExcludePrefix []string `yaml:"exclude_prefix"`
	EventTypes    []string `yaml:"event_types"`
}

type RetryConfig struct {
	Enabled        bool          `yaml:"enabled"`
	MaxAttempts    int           `yaml:"max_attempts"`
	InitialDelay   time.Duration `yaml:"initial_delay"`
	MaxDelay       time.Duration `yaml:"max_delay"`
	BackoffFactor  float64       `yaml:"backoff_factor"`
}

type CallbackConfig struct {
	CacheClearURL string `yaml:"cache_clear_url"`
	DataSyncURL   string `yaml:"data_sync_url"`
	Timeout       time.Duration `yaml:"timeout"`
}

type Config struct {
	Redis     RedisConfig     `yaml:"redis"`
	Filter    EventFilter     `yaml:"filter"`
	Retry     RetryConfig     `yaml:"retry"`
	Callback  CallbackConfig  `yaml:"callback"`
	HTTPPort  string          `yaml:"http_port"`
	LogLevel  string          `yaml:"log_level"`
}

var AppConfig Config

func LoadDefaultConfig() {
	AppConfig = Config{
		Redis: RedisConfig{
			Address:   "localhost:6379",
			Password:  "",
			Databases: []int{0},
		},
		Filter: EventFilter{
			Enabled:    false,
			EventTypes: []string{"expired", "del", "set"},
		},
		Retry: RetryConfig{
			Enabled:       true,
			MaxAttempts:   3,
			InitialDelay:  time.Second,
			MaxDelay:      time.Second * 30,
			BackoffFactor: 2.0,
		},
		Callback: CallbackConfig{
			CacheClearURL: "http://localhost:8080/api/cache/clear",
			DataSyncURL:   "http://localhost:8080/api/data/sync",
			Timeout:       time.Second * 10,
		},
		HTTPPort: ":8081",
		LogLevel: "info",
	}
}
