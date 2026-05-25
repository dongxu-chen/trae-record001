package config

import (
	"os"

	"gopkg.in/yaml.v3"
)

type Config struct {
	Server    ServerConfig    `yaml:"server"`
	Etcd      EtcdConfig      `yaml:"etcd"`
	Redis     RedisConfig     `yaml:"redis"`
	Postgres  PostgresConfig  `yaml:"postgres"`
	Scheduler SchedulerConfig `yaml:"scheduler"`
}

type ServerConfig struct {
	Host   string `yaml:"host"`
	Port   int    `yaml:"port"`
	NodeID string `yaml:"node_id"`
}

type EtcdConfig struct {
	Endpoints   []string `yaml:"endpoints"`
	DialTimeout int      `yaml:"dial_timeout"`
	LeaseTTL    int64    `yaml:"lease_ttl"`
	RootPrefix  string   `yaml:"root_prefix"`
}

type RedisConfig struct {
	Addr             string `yaml:"addr"`
	Password         string `yaml:"password"`
	DB               int    `yaml:"db"`
	PoolSize         int    `yaml:"pool_size"`
	TaskQueuePrefix  string `yaml:"task_queue_prefix"`
	NodeTasksPrefix  string `yaml:"node_tasks_prefix"`
}

type PostgresConfig struct {
	Host           string `yaml:"host"`
	Port           int    `yaml:"port"`
	User           string `yaml:"user"`
	Password       string `yaml:"password"`
	DBName         string `yaml:"dbname"`
	MaxConnections int    `yaml:"max_connections"`
}

type SchedulerConfig struct {
	ScanInterval              int `yaml:"scan_interval"`
	BalanceInterval           int `yaml:"balance_interval"`
	RetryInterval             int `yaml:"retry_interval"`
	MaxRetries                int `yaml:"max_retries"`
	ShardSize                 int `yaml:"shard_size"`
	MissCompensationThreshold int `yaml:"miss_compensation_threshold"`
	HashSlotCount             int `yaml:"hash_slot_count"`
	HeartbeatCheckInterval    int `yaml:"heartbeat_check_interval"`
	HeartbeatTimeout          int `yaml:"heartbeat_timeout"`
}

func Load(path string) (*Config, error) {
	data, err := os.ReadFile(path)
	if err != nil {
		return nil, err
	}

	var cfg Config
	if err := yaml.Unmarshal(data, &cfg); err != nil {
		return nil, err
	}

	return &cfg, nil
}
