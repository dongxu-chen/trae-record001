package config

import (
	"os"
	"strconv"
	"strings"
	"time"
)

type Config struct {
	ZKServers          []string
	Port               string
	CollectionInterval time.Duration
	PredictionInterval time.Duration
	MaxDepth           int
	DataSizeThreshold  int64
	NodeCountThreshold int
	PathStatsTopN      int
	TTLEnabled         bool
	TTLDefaultSeconds  int
	TTLCheckInterval   time.Duration
	TTLMaxDeletePerRun int
	ColdThresholdDays  float64
	HotThresholdScore  float64
	HealthMaxNodes     int
	HealthMaxSize      int64
	HealthMaxDepth     int
}

func Load() *Config {
	zkServers := getEnv("ZK_SERVERS", "localhost:2181")
	servers := strings.Split(zkServers, ",")

	collectionInterval, _ := strconv.Atoi(getEnv("COLLECTION_INTERVAL", "60"))
	predictionInterval, _ := strconv.Atoi(getEnv("PREDICTION_INTERVAL", "300"))
	maxDepth, _ := strconv.Atoi(getEnv("MAX_DEPTH", "10"))
	dataSizeThreshold, _ := strconv.ParseInt(getEnv("DATA_SIZE_THRESHOLD", "1048576"), 10, 64)
	nodeCountThreshold, _ := strconv.Atoi(getEnv("NODE_COUNT_THRESHOLD", "1000"))
	pathStatsTopN, _ := strconv.Atoi(getEnv("PATH_STATS_TOP_N", "20"))

	ttlEnabled, _ := strconv.ParseBool(getEnv("TTL_ENABLED", "true"))
	ttlDefaultSeconds, _ := strconv.Atoi(getEnv("TTL_DEFAULT_SECONDS", "86400"))
	ttlCheckInterval, _ := strconv.Atoi(getEnv("TTL_CHECK_INTERVAL", "60"))
	ttlMaxDelete, _ := strconv.Atoi(getEnv("TTL_MAX_DELETE_PER_RUN", "100"))

	coldThresholdDays, _ := strconv.ParseFloat(getEnv("COLD_THRESHOLD_DAYS", "7"), 64)
	hotThresholdScore, _ := strconv.ParseFloat(getEnv("HOT_THRESHOLD_SCORE", "50"), 64)

	healthMaxNodes, _ := strconv.Atoi(getEnv("HEALTH_MAX_NODES", "10000"))
	healthMaxSize, _ := strconv.ParseInt(getEnv("HEALTH_MAX_SIZE", "1073741824"), 10, 64)
	healthMaxDepth, _ := strconv.Atoi(getEnv("HEALTH_MAX_DEPTH", "10"))

	return &Config{
		ZKServers:          servers,
		Port:               getEnv("PORT", "8080"),
		CollectionInterval: time.Duration(collectionInterval) * time.Second,
		PredictionInterval: time.Duration(predictionInterval) * time.Second,
		MaxDepth:           maxDepth,
		DataSizeThreshold:  dataSizeThreshold,
		NodeCountThreshold: nodeCountThreshold,
		PathStatsTopN:      pathStatsTopN,
		TTLEnabled:         ttlEnabled,
		TTLDefaultSeconds:  ttlDefaultSeconds,
		TTLCheckInterval:   time.Duration(ttlCheckInterval) * time.Second,
		TTLMaxDeletePerRun: ttlMaxDelete,
		ColdThresholdDays:  coldThresholdDays,
		HotThresholdScore:  hotThresholdScore,
		HealthMaxNodes:     healthMaxNodes,
		HealthMaxSize:      healthMaxSize,
		HealthMaxDepth:     healthMaxDepth,
	}
}

func getEnv(key, defaultValue string) string {
	if value, exists := os.LookupEnv(key); exists {
		return value
	}
	return defaultValue
}
