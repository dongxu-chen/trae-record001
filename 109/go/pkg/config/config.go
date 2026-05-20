package config

import (
	"fmt"
	"strings"

	"github.com/spf13/viper"
)

type Config struct {
	Server   ServerConfig   `mapstructure:"server"`
	Database DatabaseConfig `mapstructure:"database"`
	Storage  StorageConfig  `mapstructure:"storage"`
	Backup   BackupConfig   `mapstructure:"backup"`
	Notify   NotifyConfig   `mapstructure:"notify"`
	Logging  LoggingConfig  `mapstructure:"logging"`
}

type ServerConfig struct {
	HTTPPort    int    `mapstructure:"http_port"`
	MetricsPath string `mapstructure:"metrics_path"`
}

type DatabaseConfig struct {
	MySQL      MySQLConfig      `mapstructure:"mysql"`
	PostgreSQL PostgreSQLConfig `mapstructure:"postgresql"`
}

type MySQLConfig struct {
	Host             string   `mapstructure:"host"`
	Port             int      `mapstructure:"port"`
	User             string   `mapstructure:"user"`
	Password         string   `mapstructure:"password"`
	Databases        []string `mapstructure:"databases"`
	MysqldumpPath    string   `mapstructure:"mysqldump_path"`
	MysqlbinlogPath  string   `mapstructure:"mysqlbinlog_path"`
}

type PostgreSQLConfig struct {
	Host         string   `mapstructure:"host"`
	Port         int      `mapstructure:"port"`
	User         string   `mapstructure:"user"`
	Password     string   `mapstructure:"password"`
	Databases    []string `mapstructure:"databases"`
	PgDumpPath   string   `mapstructure:"pg_dump_path"`
}

type StorageConfig struct {
	Type string       `mapstructure:"type"`
	S3   S3Config     `mapstructure:"s3"`
}

type S3Config struct {
	Endpoint   string `mapstructure:"endpoint"`
	Region     string `mapstructure:"region"`
	Bucket     string `mapstructure:"bucket"`
	AccessKey  string `mapstructure:"access_key"`
	SecretKey  string `mapstructure:"secret_key"`
	UseSSL     bool   `mapstructure:"use_ssl"`
	PathStyle  bool   `mapstructure:"path_style"`
	Prefix     string `mapstructure:"prefix"`
}

type BackupConfig struct {
	LocalDir        string `mapstructure:"local_dir"`
	RetentionDays   int    `mapstructure:"retention_days"`
	Compress        bool   `mapstructure:"compress"`
	Encrypt         bool   `mapstructure:"encrypt"`
	EncryptionKey   string `mapstructure:"encryption_key"`
	EnableIncremental bool `mapstructure:"enable_incremental"`
	EnableVerify    bool   `mapstructure:"enable_verify"`
	ParallelWorkers int    `mapstructure:"parallel_workers"`
	PipelineSize    int    `mapstructure:"pipeline_size"`
}

type NotifyConfig struct {
	Dingtalk DingtalkConfig `mapstructure:"dingtalk"`
	Email    EmailConfig    `mapstructure:"email"`
}

type DingtalkConfig struct {
	WebhookURL string   `mapstructure:"webhook_url"`
	Secret     string   `mapstructure:"secret"`
	AtMobiles  []string `mapstructure:"at_mobiles"`
	AtAll      bool     `mapstructure:"at_all"`
}

type EmailConfig struct {
	SMTPHost string   `mapstructure:"smtp_host"`
	SMTPPort int      `mapstructure:"smtp_port"`
	UseTLS   bool     `mapstructure:"use_tls"`
	Username string   `mapstructure:"username"`
	Password string   `mapstructure:"password"`
	From     string   `mapstructure:"from"`
	To       []string `mapstructure:"to"`
}

type LoggingConfig struct {
	Level      string `mapstructure:"level"`
	File       string `mapstructure:"file"`
	MaxSize    int    `mapstructure:"max_size"`
	MaxBackups int    `mapstructure:"max_backups"`
	MaxAge     int    `mapstructure:"max_age"`
}

func Load(configPath string) (*Config, error) {
	v := viper.New()
	v.SetConfigFile(configPath)
	v.SetConfigType("yaml")

	v.AutomaticEnv()
	v.SetEnvKeyReplacer(strings.NewReplacer(".", "_"))

	if err := v.ReadInConfig(); err != nil {
		return nil, fmt.Errorf("failed to read config: %w", err)
	}

	var cfg Config
	if err := v.Unmarshal(&cfg); err != nil {
		return nil, fmt.Errorf("failed to unmarshal config: %w", err)
	}

	if err := validateConfig(&cfg); err != nil {
		return nil, fmt.Errorf("config validation failed: %w", err)
	}

	return &cfg, nil
}

func validateConfig(cfg *Config) error {
	if cfg.Backup.Encrypt && len(cfg.Backup.EncryptionKey) != 32 {
		return fmt.Errorf("encryption key must be exactly 32 bytes for AES-256")
	}

	if cfg.Backup.ParallelWorkers <= 0 {
		cfg.Backup.ParallelWorkers = 4
	}

	if cfg.Backup.PipelineSize <= 0 {
		cfg.Backup.PipelineSize = 10
	}

	if cfg.Server.HTTPPort <= 0 {
		cfg.Server.HTTPPort = 9090
	}

	if cfg.Server.MetricsPath == "" {
		cfg.Server.MetricsPath = "/metrics"
	}

	return nil
}
