package config

import "os"

type Config struct {
	MySQLDSN string
	RedisAddr string
	RedisPassword string
	RedisDB int
	HTTPPort string
	SchedulerID string
}

func Load() *Config {
	return &Config{
		MySQLDSN: getEnv("MYSQL_DSN", "root:password@tcp(127.0.0.1:3306)/scheduler?charset=utf8mb4&parseTime=True&loc=Local"),
		RedisAddr: getEnv("REDIS_ADDR", "127.0.0.1:6379"),
		RedisPassword: getEnv("REDIS_PASSWORD", ""),
		RedisDB: 0,
		HTTPPort: getEnv("HTTP_PORT", ":8080"),
		SchedulerID: getEnv("SCHEDULER_ID", "scheduler-1"),
	}
}

func getEnv(key, defaultValue string) string {
	if value, exists := os.LookupEnv(key); exists {
		return value
	}
	return defaultValue
}
