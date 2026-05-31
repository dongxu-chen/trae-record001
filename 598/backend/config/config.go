package config

import (
	"fmt"
	"log"
	"os"
	"strconv"

	"github.com/joho/godotenv"
)

type Config struct {
	ServerPort     string
	AllowOrigins   string
	DBHost         string
	DBPort         string
	DBUser         string
	DBPassword     string
	DBName         string
	DBCharset      string
	DBParseTime    bool
	DBLoc          string

	PartitionThresholdRows int64
	PartitionTargetRows    int64
	PartitionHistoryDays   int
	PartitionFutureDays    int
}

var AppConfig *Config

func Load() {
	if err := godotenv.Load(); err != nil {
		log.Printf("Warning: .env file not found, using environment variables: %v", err)
	}

	AppConfig = &Config{
		ServerPort:     getEnv("SERVER_PORT", "8080"),
		AllowOrigins:   getEnv("ALLOW_ORIGINS", "*"),
		DBHost:         getEnv("DB_HOST", "localhost"),
		DBPort:         getEnv("DB_PORT", "3306"),
		DBUser:         getEnv("DB_USER", "root"),
		DBPassword:     getEnv("DB_PASSWORD", ""),
		DBName:         getEnv("DB_NAME", ""),
		DBCharset:      getEnv("DB_CHARSET", "utf8mb4"),
		DBParseTime:    getEnvBool("DB_PARSE_TIME", true),
		DBLoc:          getEnv("DB_LOC", "Local"),

		PartitionThresholdRows: getEnvInt64("PARTITION_THRESHOLD_ROWS", 1000000),
		PartitionTargetRows:    getEnvInt64("PARTITION_TARGET_ROWS", 500000),
		PartitionHistoryDays:   getEnvInt("PARTITION_HISTORY_DAYS", 90),
		PartitionFutureDays:    getEnvInt("PARTITION_FUTURE_DAYS", 30),
	}
}

func (c *Config) GetDSN() string {
	parseTime := "false"
	if c.DBParseTime {
		parseTime = "true"
	}
	return fmt.Sprintf("%s:%s@tcp(%s:%s)/%s?charset=%s&parseTime=%s&loc=%s",
		c.DBUser, c.DBPassword, c.DBHost, c.DBPort, c.DBName,
		c.DBCharset, parseTime, c.DBLoc,
	)
}

func (c *Config) GetDSNWithoutDB() string {
	parseTime := "false"
	if c.DBParseTime {
		parseTime = "true"
	}
	return fmt.Sprintf("%s:%s@tcp(%s:%s)/?charset=%s&parseTime=%s&loc=%s",
		c.DBUser, c.DBPassword, c.DBHost, c.DBPort,
		c.DBCharset, parseTime, c.DBLoc,
	)
}

func getEnv(key, defaultValue string) string {
	if value, exists := os.LookupEnv(key); exists {
		return value
	}
	return defaultValue
}

func getEnvInt(key string, defaultValue int) int {
	if value, exists := os.LookupEnv(key); exists {
		if v, err := strconv.Atoi(value); err == nil {
			return v
		}
	}
	return defaultValue
}

func getEnvInt64(key string, defaultValue int64) int64 {
	if value, exists := os.LookupEnv(key); exists {
		if v, err := strconv.ParseInt(value, 10, 64); err == nil {
			return v
		}
	}
	return defaultValue
}

func getEnvBool(key string, defaultValue bool) bool {
	if value, exists := os.LookupEnv(key); exists {
		if v, err := strconv.ParseBool(value); err == nil {
			return v
		}
	}
	return defaultValue
}
