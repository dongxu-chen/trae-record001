package config

import (
	"os"
)

type Config struct {
	ServerPort        string
	KubeConfigPath string
	Namespace       string
	LogLevel        string
}

func LoadConfig() *Config {
	return &Config{
		ServerPort:        getEnv("SERVER_PORT", "8080"),
		KubeConfigPath: getEnv("KUBE_CONFIG_PATH", ""),
		Namespace:       getEnv("NAMESPACE", "default"),
		LogLevel:        getEnv("LOG_LEVEL", "info"),
	}
}

func getEnv(key, defaultValue string) string {
	if value, exists := os.LookupEnv(key); exists {
		return value
	}
	return defaultValue
}
