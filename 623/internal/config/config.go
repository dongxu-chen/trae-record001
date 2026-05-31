package config

import (
	"os"
	"strconv"
	"time"
)

type Config struct {
	LogLevel string
	Proxy    ProxyConfig
	Analyzer AnalyzerConfig
	Limiter  LimiterConfig
	API      APIConfig
}

type ProxyConfig struct {
	Host           string
	Port           int
	TargetDBHost   string
	TargetDBPort   int
	MaxConnections int
}

type AnalyzerConfig struct {
	SlowConnectionThreshold time.Duration
	LeakDetectionThreshold  time.Duration
	IdleConnectionTimeout   time.Duration
	StatsInterval           time.Duration
}

type LimiterConfig struct {
	MaxTotalConnections   int
	MaxPerClientIP        int
	ConnectionRateLimit   int
	RateLimitWindow       time.Duration
	EnableAutoScaling     bool
	StormDetectionThreshold int
}

type APIConfig struct {
	Host string
	Port int
}

func Load() *Config {
	return &Config{
		LogLevel: getEnv("LOG_LEVEL", "info"),
		Proxy: ProxyConfig{
			Host:           getEnv("PROXY_HOST", "0.0.0.0"),
			Port:           getEnvInt("PROXY_PORT", 3307),
			TargetDBHost:   getEnv("DB_HOST", "localhost"),
			TargetDBPort:   getEnvInt("DB_PORT", 3306),
			MaxConnections: getEnvInt("PROXY_MAX_CONN", 1000),
		},
		Analyzer: AnalyzerConfig{
			SlowConnectionThreshold: getEnvDuration("SLOW_CONN_THRESHOLD", 5*time.Second),
			LeakDetectionThreshold:  getEnvDuration("LEAK_THRESHOLD", 30*time.Minute),
			IdleConnectionTimeout:   getEnvDuration("IDLE_TIMEOUT", 10*time.Minute),
			StatsInterval:           getEnvDuration("STATS_INTERVAL", 5*time.Second),
		},
		Limiter: LimiterConfig{
			MaxTotalConnections:     getEnvInt("MAX_TOTAL_CONN", 500),
			MaxPerClientIP:          getEnvInt("MAX_PER_CLIENT", 50),
			ConnectionRateLimit:     getEnvInt("RATE_LIMIT", 100),
			RateLimitWindow:         getEnvDuration("RATE_WINDOW", time.Minute),
			EnableAutoScaling:       getEnvBool("AUTO_SCALING", true),
			StormDetectionThreshold: getEnvInt("STORM_THRESHOLD", 50),
		},
		API: APIConfig{
			Host: getEnv("API_HOST", "0.0.0.0"),
			Port: getEnvInt("API_PORT", 8080),
		},
	}
}

func getEnv(key, defaultValue string) string {
	if value := os.Getenv(key); value != "" {
		return value
	}
	return defaultValue
}

func getEnvInt(key string, defaultValue int) int {
	if value := os.Getenv(key); value != "" {
		if v, err := strconv.Atoi(value); err == nil {
			return v
		}
	}
	return defaultValue
}

func getEnvDuration(key string, defaultValue time.Duration) time.Duration {
	if value := os.Getenv(key); value != "" {
		if v, err := time.ParseDuration(value); err == nil {
			return v
		}
	}
	return defaultValue
}

func getEnvBool(key string, defaultValue bool) bool {
	if value := os.Getenv(key); value != "" {
		if v, err := strconv.ParseBool(value); err == nil {
			return v
		}
	}
	return defaultValue
}
