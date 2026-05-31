package config

import (
	"fmt"
	"os"
	"strconv"
	"time"
)

type Config struct {
	Server   ServerConfig
	Storage  StorageConfig
	Jenkins  JenkinsConfig
	Cache    CacheConfig
	LogLevel string
}

type ServerConfig struct {
	Port         int
	ReadTimeout  time.Duration
	WriteTimeout time.Duration
	AllowOrigins []string
}

type StorageConfig struct {
	Endpoint        string
	AccessKey       string
	SecretKey       string
	Bucket          string
	Region          string
	UseSSL          bool
	MaxUploadBytes  int64
}

type StorageBackendConfig struct {
	ID       string
	Name     string
	Type     string
	Endpoint string
	AccessKey string
	SecretKey string
	Bucket   string
	Region   string
	UseSSL   bool
	IsDefault bool
}

type JenkinsConfig struct {
	URL      string
	Username string
	APIToken string
	Timeout  time.Duration
}

type CacheConfig struct {
	DefaultTTL      time.Duration
	MaxVersions     int
	WarmupWorkers   int
	CleanupInterval time.Duration
	MetaStorePath   string
}

func Load() *Config {
	return &Config{
		Server: ServerConfig{
			Port:         getEnvInt("SERVER_PORT", 8080),
			ReadTimeout:  getEnvDuration("SERVER_READ_TIMEOUT", 30*time.Second),
			WriteTimeout: getEnvDuration("SERVER_WRITE_TIMEOUT", 60*time.Second),
			AllowOrigins: getEnvSlice("SERVER_ALLOW_ORIGINS", []string{"*"}),
		},
		Storage: StorageConfig{
			Endpoint:       getEnv("STORAGE_ENDPOINT", "localhost:9000"),
			AccessKey:      getEnv("STORAGE_ACCESS_KEY", "minioadmin"),
			SecretKey:      getEnv("STORAGE_SECRET_KEY", "minioadmin"),
			Bucket:         getEnv("STORAGE_BUCKET", "jenkins-cache"),
			Region:         getEnv("STORAGE_REGION", "us-east-1"),
			UseSSL:         getEnvBool("STORAGE_USE_SSL", false),
			MaxUploadBytes: getEnvInt64("STORAGE_MAX_UPLOAD_BYTES", 5<<30),
		},
		Jenkins: JenkinsConfig{
			URL:      getEnv("JENKINS_URL", "http://localhost:8080"),
			Username: getEnv("JENKINS_USERNAME", "admin"),
			APIToken: getEnv("JENKINS_API_TOKEN", ""),
			Timeout:  getEnvDuration("JENKINS_TIMEOUT", 30*time.Second),
		},
		Cache: CacheConfig{
			DefaultTTL:      getEnvDuration("CACHE_DEFAULT_TTL", 7*24*time.Hour),
			MaxVersions:     getEnvInt("CACHE_MAX_VERSIONS", 10),
			WarmupWorkers:   getEnvInt("CACHE_WARMUP_WORKERS", 3),
			CleanupInterval: getEnvDuration("CACHE_CLEANUP_INTERVAL", 1*time.Hour),
			MetaStorePath:   getEnv("CACHE_META_STORE_PATH", "./data/meta"),
		},
		LogLevel: getEnv("LOG_LEVEL", "info"),
	}
}

func (c *Config) Validate() error {
	if c.Storage.Endpoint == "" {
		return fmt.Errorf("STORAGE_ENDPOINT is required")
	}
	if c.Storage.Bucket == "" {
		return fmt.Errorf("STORAGE_BUCKET is required")
	}
	return nil
}

func getEnv(key, fallback string) string {
	if v := os.Getenv(key); v != "" {
		return v
	}
	return fallback
}

func getEnvInt(key string, fallback int) int {
	if v := os.Getenv(key); v != "" {
		if i, err := strconv.Atoi(v); err == nil {
			return i
		}
	}
	return fallback
}

func getEnvInt64(key string, fallback int64) int64 {
	if v := os.Getenv(key); v != "" {
		if i, err := strconv.ParseInt(v, 10, 64); err == nil {
			return i
		}
	}
	return fallback
}

func getEnvBool(key string, fallback bool) bool {
	if v := os.Getenv(key); v != "" {
		if b, err := strconv.ParseBool(v); err == nil {
			return b
		}
	}
	return fallback
}

func getEnvDuration(key string, fallback time.Duration) time.Duration {
	if v := os.Getenv(key); v != "" {
		if d, err := time.ParseDuration(v); err == nil {
			return d
		}
	}
	return fallback
}

func getEnvSlice(key string, fallback []string) []string {
	if v := os.Getenv(key); v != "" {
		return []string{v}
	}
	return fallback
}
