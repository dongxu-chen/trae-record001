package config

import (
	"time"
)

type Config struct {
	Server         ServerConfig
	ClickHouse     ClickHouseConfig
	Limiter        LimiterConfig
	Priority       PriorityConfig
	ResourceGroups []ResourceGroupConfig
}

type ServerConfig struct {
	Address      string
	ReadTimeout  time.Duration
	WriteTimeout time.Duration
}

type ClickHouseConfig struct {
	Address  string
	Username string
	Password string
	Database string
	Timeout  time.Duration
}

type LimiterConfig struct {
	GlobalRate       float64
	GlobalBurst      int
	UserRate         float64
	UserBurst        int
	MaxScanRows      int64
	MaxMemoryBytes   int64
	QueryTimeout     time.Duration
	CircuitBreaker   CircuitBreakerConfig
}

type CircuitBreakerConfig struct {
	FailureThreshold float64
	SuccessThreshold int
	Timeout          time.Duration
}

type PriorityConfig struct {
	HighPriorityWeight   int
	MediumPriorityWeight int
	LowPriorityWeight    int
	QueueSize            int
}

type ResourceGroupConfig struct {
	Name           string
	Weight         int
	MaxConcurrency int
	MaxQueueSize   int
	Limiter        LimiterConfig
}

func Load() *Config {
	return &Config{
		Server: ServerConfig{
			Address:      ":8080",
			ReadTimeout:  30 * time.Second,
			WriteTimeout: 30 * time.Second,
		},
		ClickHouse: ClickHouseConfig{
			Address:  "localhost:9000",
			Username: "default",
			Password: "",
			Database: "default",
			Timeout:  30 * time.Second,
		},
		Limiter: LimiterConfig{
			GlobalRate:     10,
			GlobalBurst:    20,
			UserRate:       5,
			UserBurst:      10,
			MaxScanRows:    100000000,
			MaxMemoryBytes: 1024 * 1024 * 1024,
			QueryTimeout:   60 * time.Second,
			CircuitBreaker: CircuitBreakerConfig{
				FailureThreshold: 0.5,
				SuccessThreshold: 3,
				Timeout:          30 * time.Second,
			},
		},
		Priority: PriorityConfig{
			HighPriorityWeight:   5,
			MediumPriorityWeight: 3,
			LowPriorityWeight:    1,
			QueueSize:            1000,
		},
		ResourceGroups: []ResourceGroupConfig{
			{
				Name:           "data_team",
				Weight:         50,
				MaxConcurrency: 8,
				MaxQueueSize:   500,
				Limiter: LimiterConfig{
					GlobalRate:     8,
					GlobalBurst:    16,
					UserRate:       4,
					UserBurst:      8,
					MaxScanRows:    80000000,
					MaxMemoryBytes: 512 * 1024 * 1024,
					QueryTimeout:   60 * time.Second,
					CircuitBreaker: CircuitBreakerConfig{
						FailureThreshold: 0.5,
						SuccessThreshold: 3,
						Timeout:          30 * time.Second,
					},
				},
			},
			{
				Name:           "reporting",
				Weight:         30,
				MaxConcurrency: 4,
				MaxQueueSize:   200,
				Limiter: LimiterConfig{
					GlobalRate:     5,
					GlobalBurst:    10,
					UserRate:       2,
					UserBurst:      5,
					MaxScanRows:    50000000,
					MaxMemoryBytes: 256 * 1024 * 1024,
					QueryTimeout:   120 * time.Second,
					CircuitBreaker: CircuitBreakerConfig{
						FailureThreshold: 0.4,
						SuccessThreshold: 5,
						Timeout:          60 * time.Second,
					},
				},
			},
			{
				Name:           "realtime",
				Weight:         100,
				MaxConcurrency: 15,
				MaxQueueSize:   1000,
				Limiter: LimiterConfig{
					GlobalRate:     20,
					GlobalBurst:    40,
					UserRate:       10,
					UserBurst:      20,
					MaxScanRows:    10000000,
					MaxMemoryBytes: 128 * 1024 * 1024,
					QueryTimeout:   30 * time.Second,
					CircuitBreaker: CircuitBreakerConfig{
						FailureThreshold: 0.6,
						SuccessThreshold: 3,
						Timeout:          15 * time.Second,
					},
				},
			},
		},
	}
}
