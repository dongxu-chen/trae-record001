package config

import (
	"encoding/json"
	"fmt"
	"os"
	"time"

	"heatcache/internal/binlog"
	"heatcache/internal/cache"
	"heatcache/internal/connector"
	"heatcache/internal/preheater"
)

type Config struct {
	Redis      RedisConfig              `json:"redis"`
	Databases  map[string]DBConfig      `json:"databases"`
	Preheat    PreheatConfig            `json:"preheat"`
	Cache      CacheConfig              `json:"cache"`
	Binlog     BinlogConfig             `json:"binlog"`
	MySQLBinlog map[string]MySQLBinlogCfg `json:"mysql_binlog"`
	PGBinlog   map[string]PGBinlogCfg   `json:"pg_binlog"`
}

type RedisConfig struct {
	Addr     string `json:"addr"`
	Password string `json:"password"`
	DB       int    `json:"db"`
}

type DBConfig struct {
	Type     connector.DBType `json:"type"`
	Host     string           `json:"host"`
	Port     int              `json:"port"`
	User     string           `json:"user"`
	Password string           `json:"password"`
	Database string           `json:"database"`
	MaxConns int              `json:"max_conns"`
}

type PreheatConfig struct {
	WorkerCount         int `json:"worker_count"`
	BatchSize           int `json:"batch_size"`
	RetryCount          int `json:"retry_count"`
	TopN                int `json:"top_n"`
	QueryTimeoutMs      int `json:"query_timeout_ms"`
	CacheTTLMins        int `json:"cache_ttl_mins"`
	PreheatIntervalMs   int `json:"preheat_interval_ms"`
	AnalysisIntervalMs  int `json:"analysis_interval_ms"`
	EnableIncremental   bool `json:"enable_incremental"`
	EnableBinlog        bool `json:"enable_binlog"`
	EnableAdaptiveInterval bool `json:"enable_adaptive_interval"`
	EnableHitRatePrediction bool `json:"enable_hitrate_prediction"`
	IncrementalIntervalMs int `json:"incremental_interval_ms"`
	DirtyLimitPerCycle  int `json:"dirty_limit_per_cycle"`
	TargetHitRate       float64 `json:"target_hit_rate"`
}

type CacheConfig struct {
	DefaultTTLMins int                         `json:"default_ttl_mins"`
	MaxMemoryMB    int                         `json:"max_memory_mb"`
	Strategy       cache.InvalidationStrategy  `json:"strategy"`
	KeyPrefix      string                      `json:"key_prefix"`
	LRUMaxKeys     int                         `json:"lru_max_keys"`
}

type BinlogConfig struct {
	Enabled       bool     `json:"enabled"`
	EventBufferSize int    `json:"event_buffer_size"`
}

type MySQLBinlogCfg struct {
	Enabled     bool     `json:"enabled"`
	Host        string   `json:"host"`
	Port        int      `json:"port"`
	User        string   `json:"user"`
	Password    string   `json:"password"`
	Database    string   `json:"database"`
	Tables      []string `json:"tables"`
	ServerID    uint32   `json:"server_id"`
	Flavor      string   `json:"flavor"`
}

type PGBinlogCfg struct {
	Enabled     bool     `json:"enabled"`
	Host        string   `json:"host"`
	Port        int      `json:"port"`
	User        string   `json:"user"`
	Password    string   `json:"password"`
	Database    string   `json:"database"`
	Tables      []string `json:"tables"`
	SlotName    string   `json:"slot_name"`
	Publication string   `json:"publication"`
}

func DefaultConfig() *Config {
	return &Config{
		Redis: RedisConfig{
			Addr:     "localhost:6379",
			Password: "",
			DB:       0,
		},
		Databases: map[string]DBConfig{
			"mysql_main": {
				Type:     connector.MySQL,
				Host:     "localhost",
				Port:     3306,
				User:     "root",
				Password: "",
				Database: "test",
				MaxConns: 5,
			},
			"pg_analytics": {
				Type:     connector.PG,
				Host:     "localhost",
				Port:     5432,
				User:     "postgres",
				Password: "",
				Database: "analytics",
				MaxConns: 5,
			},
		},
		Preheat: PreheatConfig{
			WorkerCount:          4,
			BatchSize:            50,
			RetryCount:           2,
			TopN:                 50,
			QueryTimeoutMs:       10000,
			CacheTTLMins:         30,
			PreheatIntervalMs:    300000,
			AnalysisIntervalMs:   900000,
			EnableIncremental:    true,
			EnableBinlog:         true,
			EnableAdaptiveInterval: true,
			EnableHitRatePrediction: true,
			IncrementalIntervalMs: 30000,
			DirtyLimitPerCycle:   20,
			TargetHitRate:       0.8,
		},
		Cache: CacheConfig{
			DefaultTTLMins: 30,
			MaxMemoryMB:    512,
			Strategy:       cache.InvalidationHybrid,
			KeyPrefix:      "heatcache:",
			LRUMaxKeys:     10000,
		},
		Binlog: BinlogConfig{
			Enabled:        true,
			EventBufferSize: 10000,
		},
		MySQLBinlog: map[string]MySQLBinlogCfg{
			"mysql_main": {
				Enabled:  false,
				Host:     "localhost",
				Port:     3306,
				User:     "root",
				Password: "",
				Database: "test",
				Tables:   []string{},
				ServerID: 1001,
				Flavor:   "mysql",
			},
		},
		PGBinlog: map[string]PGBinlogCfg{
			"pg_analytics": {
				Enabled:     false,
				Host:        "localhost",
				Port:        5432,
				User:        "postgres",
				Password:    "",
				Database:    "analytics",
				Tables:      []string{},
				SlotName:    "heatcache_slot",
				Publication: "heatcache_pub",
			},
		},
	}
}

func LoadConfig(path string) (*Config, error) {
	data, err := os.ReadFile(path)
	if err != nil {
		return nil, fmt.Errorf("failed to read config file: %w", err)
	}

	var cfg Config
	if err := json.Unmarshal(data, &cfg); err != nil {
		return nil, fmt.Errorf("failed to parse config: %w", err)
	}

	return &cfg, nil
}

func (c *Config) Save(path string) error {
	data, err := json.MarshalIndent(c, "", "  ")
	if err != nil {
		return fmt.Errorf("failed to marshal config: %w", err)
	}
	return os.WriteFile(path, data, 0644)
}

func (c *Config) ToCacheConfig() cache.CacheConfig {
	return cache.CacheConfig{
		RedisAddr:     c.Redis.Addr,
		RedisPassword: c.Redis.Password,
		RedisDB:       c.Redis.DB,
		DefaultTTL:    time.Duration(c.Cache.DefaultTTLMins) * time.Minute,
		MaxMemory:     int64(c.Cache.MaxMemoryMB) * 1024 * 1024,
		Strategy:      c.Cache.Strategy,
		KeyPrefix:     c.Cache.KeyPrefix,
		LRUMaxKeys:    c.Cache.LRUMaxKeys,
	}
}

func (c *Config) ToPreheaterConfig() preheater.PreheaterConfig {
	return preheater.PreheaterConfig{
		WorkerCount:         c.Preheat.WorkerCount,
		BatchSize:           c.Preheat.BatchSize,
		RetryCount:          c.Preheat.RetryCount,
		TopN:                c.Preheat.TopN,
		QueryTimeout:        time.Duration(c.Preheat.QueryTimeoutMs) * time.Millisecond,
		CacheTTL:            time.Duration(c.Preheat.CacheTTLMins) * time.Minute,
		PreheatInterval:     time.Duration(c.Preheat.PreheatIntervalMs) * time.Millisecond,
		AnalysisInterval:    time.Duration(c.Preheat.AnalysisIntervalMs) * time.Millisecond,
		EnableIncremental:   c.Preheat.EnableIncremental,
		EnableBinlog:        c.Preheat.EnableBinlog,
		EnableAdaptiveInterval: c.Preheat.EnableAdaptiveInterval,
		EnableHitRatePrediction: c.Preheat.EnableHitRatePrediction,
		IncrementalInterval: time.Duration(c.Preheat.IncrementalIntervalMs) * time.Millisecond,
		DirtyLimitPerCycle:  c.Preheat.DirtyLimitPerCycle,
		TargetHitRate:       c.Preheat.TargetHitRate,
		MaxMemoryBytes:      int64(c.Cache.MaxMemoryMB) * 1024 * 1024,
	}
}

func (c *Config) ToConnectors() map[string]connector.Connector {
	connectors := make(map[string]connector.Connector)
	for name, dbConf := range c.Databases {
		connectors[name] = connector.NewConnector(connector.DBConfig{
			Type:     dbConf.Type,
			Host:     dbConf.Host,
			Port:     dbConf.Port,
			User:     dbConf.User,
			Password: dbConf.Password,
			Database: dbConf.Database,
			MaxConns: dbConf.MaxConns,
		})
	}
	return connectors
}

func (c *Config) ToMySQLBinlogConfigs() map[string]binlog.BinlogListenerConfig {
	configs := make(map[string]binlog.BinlogListenerConfig)
	for name, cfg := range c.MySQLBinlog {
		if !cfg.Enabled {
			continue
		}
		configs[name] = binlog.BinlogListenerConfig{
			Host:     cfg.Host,
			Port:     cfg.Port,
			User:     cfg.User,
			Password: cfg.Password,
			Database: cfg.Database,
			Tables:   cfg.Tables,
			ServerID: cfg.ServerID,
			Flavor:   cfg.Flavor,
		}
	}
	return configs
}

func (c *Config) ToPGBinlogConfigs() map[string]binlog.PGReplicationConfig {
	configs := make(map[string]binlog.PGReplicationConfig)
	for name, cfg := range c.PGBinlog {
		if !cfg.Enabled {
			continue
		}
		configs[name] = binlog.PGReplicationConfig{
			Host:        cfg.Host,
			Port:        cfg.Port,
			User:        cfg.User,
			Password:    cfg.Password,
			Database:    cfg.Database,
			Tables:      cfg.Tables,
			SlotName:    cfg.SlotName,
			Publication: cfg.Publication,
		}
	}
	return configs
}
