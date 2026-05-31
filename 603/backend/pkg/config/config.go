package config

import (
	"os"
	"strconv"
)

type Config struct {
	Pulsar PulsarConfig
	Server ServerConfig
	Monitor MonitorConfig
	AutoScaler AutoScalerConfig
	RateLimiter RateLimiterConfig
	Prediction PredictionConfig
}

type PulsarConfig struct {
	URL            string
	AdminURL       string
	Token          string
	TrustCertsFile string
}

type ServerConfig struct {
	Port           string
	EnableCORS     bool
}

type MonitorConfig struct {
	IntervalSeconds int
	Topics          []string
}

type AutoScalerConfig struct {
	Enabled          bool
	MinConsumers     int
	MaxConsumers     int
	ScaleUpThreshold  int64
	ScaleDownThreshold int64
}

type RateLimiterConfig struct {
	Enabled       bool
	MaxRate     float64
}

type PredictionConfig struct {
	Enabled      bool
	HistoryHours int
	ModelType    string
}

func Load() *Config {
	return &Config{
		Pulsar: PulsarConfig{
			URL:            getEnv("PULSAR_URL", "pulsar://localhost:6650"),
			AdminURL:       getEnv("PULSAR_ADMIN_URL", "http://localhost:8080"),
			Token:          getEnv("PULSAR_TOKEN", ""),
		},
		Server: ServerConfig{
			Port:       getEnv("SERVER_PORT", "8081"),
			EnableCORS: getEnvBool("ENABLE_CORS", true),
		},
		Monitor: MonitorConfig{
			IntervalSeconds: getEnvInt("MONITOR_INTERVAL", 30),
		},
		AutoScaler: AutoScalerConfig{
			Enabled:          getEnvBool("AUTOSCALER_ENABLED", true),
			MinConsumers:     getEnvInt("MIN_CONSUMERS", 1),
			MaxConsumers:     getEnvInt("MAX_CONSUMERS", 20),
			ScaleUpThreshold:  int64(getEnvInt("SCALE_UP_THRESHOLD", 10000)),
			ScaleDownThreshold: int64(getEnvInt("SCALE_DOWN_THRESHOLD", 1000)),
		},
		RateLimiter: RateLimiterConfig{
			Enabled:   getEnvBool("RATE_LIMITER_ENABLED", true),
			MaxRate: float64(getEnvInt("MAX_RATE", 1000)),
		},
		Prediction: PredictionConfig{
			Enabled:      getEnvBool("PREDICTION_ENABLED", true),
			HistoryHours: getEnvInt("PREDICTION_HISTORY_HOURS", 24),
			ModelType:    getEnv("PREDICTION_MODEL", "linear"),
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

func getEnvBool(key string, defaultValue bool) bool {
	if value := os.Getenv(key); value != "" {
		if v, err := strconv.ParseBool(value); err == nil {
			return v
		}
	}
	return defaultValue
}
