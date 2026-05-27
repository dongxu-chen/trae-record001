package config

import (
	"os"
	"path/filepath"

	"github.com/spf13/viper"
	"go.uber.org/zap"
	"go.uber.org/zap/zapcore"
)

type Config struct {
	Server      ServerConfig      `mapstructure:"server"`
	Database    DatabaseConfig    `mapstructure:"database"`
	Alert       AlertConfig       `mapstructure:"alert"`
	Cron        CronConfig        `mapstructure:"cron"`
	Scan        ScanConfig        `mapstructure:"scan"`
	RuleLibrary RuleLibraryConfig `mapstructure:"rule_library"`
	DNS         DNSConfig         `mapstructure:"dns"`
}

type ServerConfig struct {
	Port         int    `mapstructure:"port"`
	ReadTimeout  int    `mapstructure:"read_timeout"`
	WriteTimeout int    `mapstructure:"write_timeout"`
	Mode         string `mapstructure:"mode"`
}

type DatabaseConfig struct {
	Type string `mapstructure:"type"`
	DSN  string `mapstructure:"dsn"`
}

type AlertConfig struct {
	DingTalk DingTalkConfig `mapstructure:"dingtalk"`
	Email    EmailConfig    `mapstructure:"email"`
	WeCom    WeComConfig    `mapstructure:"wecom"`
}

type DingTalkConfig struct {
	Enabled  bool   `mapstructure:"enabled"`
	Webhook  string `mapstructure:"webhook"`
	Secret   string `mapstructure:"secret"`
}

type EmailConfig struct {
	Enabled  bool   `mapstructure:"enabled"`
	Host     string `mapstructure:"host"`
	Port     int    `mapstructure:"port"`
	Username string `mapstructure:"username"`
	Password string `mapstructure:"password"`
	From     string `mapstructure:"from"`
	To       string `mapstructure:"to"`
}

type WeComConfig struct {
	Enabled  bool   `mapstructure:"enabled"`
	Webhook  string `mapstructure:"webhook"`
}

type CronConfig struct {
	ScanInterval      string `mapstructure:"scan_interval"`
	CheckExpiredDays  int    `mapstructure:"check_expired_days"`
	WarningDays       int    `mapstructure:"warning_days"`
	RulesUpdateInterval string `mapstructure:"rules_update_interval"`
}

type ScanConfig struct {
	MaxConcurrent      int `mapstructure:"max_concurrent"`
	MinDelayMs         int `mapstructure:"min_delay_ms"`
	MaxDelayMs         int `mapstructure:"max_delay_ms"`
	TimeoutSeconds     int `mapstructure:"timeout_seconds"`
	RetryCount         int `mapstructure:"retry_count"`
	RetryDelayMs       int `mapstructure:"retry_delay_ms"`
	RandomizeDelay     bool `mapstructure:"randomize_delay"`
	JitterPercent      int  `mapstructure:"jitter_percent"`
}

type RuleLibraryConfig struct {
	Enabled           bool   `mapstructure:"enabled"`
	SourceURL         string `mapstructure:"source_url"`
	UpdateInterval    string `mapstructure:"update_interval"`
	AutoUpdate        bool   `mapstructure:"auto_update"`
	LocalFile         string `mapstructure:"local_file"`
}

type DNSConfig struct {
	Enabled           bool `mapstructure:"enabled"`
	AutoDiscoverMX    bool `mapstructure:"auto_discover_mx"`
	AutoDiscoverSubdomains bool `mapstructure:"auto_discover_subdomains"`
	AutoAddSubdomains bool `mapstructure:"auto_add_subdomains"`
	DNSServers        []string `mapstructure:"dns_servers"`
	TimeoutSeconds    int `mapstructure:"timeout_seconds"`
	SubdomainTags     string `mapstructure:"subdomain_tags"`
}

var (
	Cfg    *Config
	Logger *zap.Logger
)

func Load(configPath string) {
	viper.SetConfigName("config")
	viper.SetConfigType("yaml")

	if configPath != "" {
		viper.AddConfigPath(configPath)
	} else {
		viper.AddConfigPath("./")
		viper.AddConfigPath("./config")
		viper.AddConfigPath(filepath.Dir(os.Args[0]))
	}

	viper.SetDefault("server.port", 8080)
	viper.SetDefault("server.read_timeout", 10)
	viper.SetDefault("server.write_timeout", 10)
	viper.SetDefault("server.mode", "release")

	viper.SetDefault("database.type", "sqlite")
	viper.SetDefault("database.dsn", "./data/ssl_monitor.db")

	viper.SetDefault("cron.scan_interval", "0 */6 * * *")
	viper.SetDefault("cron.check_expired_days", 30)
	viper.SetDefault("cron.warning_days", 7)
	viper.SetDefault("cron.rules_update_interval", "0 0 */7 * *")

	viper.SetDefault("scan.max_concurrent", 5)
	viper.SetDefault("scan.min_delay_ms", 100)
	viper.SetDefault("scan.max_delay_ms", 1000)
	viper.SetDefault("scan.timeout_seconds", 15)
	viper.SetDefault("scan.retry_count", 2)
	viper.SetDefault("scan.retry_delay_ms", 500)
	viper.SetDefault("scan.randomize_delay", true)
	viper.SetDefault("scan.jitter_percent", 20)

	viper.SetDefault("rule_library.enabled", true)
	viper.SetDefault("rule_library.source_url", "https://raw.githubusercontent.com/ssllabs/research/master/Server_Cipher_Suites/weak_ciphers.json")
	viper.SetDefault("rule_library.update_interval", "0 0 */7 * *")
	viper.SetDefault("rule_library.auto_update", true)
	viper.SetDefault("rule_library.local_file", "./data/rules.json")

	viper.SetDefault("dns.enabled", true)
	viper.SetDefault("dns.auto_discover_mx", true)
	viper.SetDefault("dns.auto_discover_subdomains", true)
	viper.SetDefault("dns.auto_add_subdomains", true)
	viper.SetDefault("dns.timeout_seconds", 10)
	viper.SetDefault("dns.subdomain_tags", "auto-discovered")
	viper.SetDefault("dns.dns_servers", []string{"8.8.8.8:53", "1.1.1.1:53", "114.114.114.114:53"})

	if err := viper.ReadInConfig(); err != nil {
		if _, ok := err.(viper.ConfigFileNotFoundError); !ok {
			panic("读取配置文件失败: " + err.Error())
		}
	}

	Cfg = &Config{}
	if err := viper.Unmarshal(Cfg); err != nil {
		panic("解析配置文件失败: " + err.Error())
	}

	initLogger()
}

func initLogger() {
	config := zap.Config{
		Level:            zap.NewAtomicLevelAt(zap.InfoLevel),
		Encoding:         "console",
		OutputPaths:      []string{"stdout"},
		ErrorOutputPaths: []string{"stderr"},
		EncoderConfig: zapcore.EncoderConfig{
			TimeKey:        "time",
			LevelKey:       "level",
			NameKey:        "logger",
			CallerKey:      "caller",
			MessageKey:     "msg",
			StacktraceKey:  "stacktrace",
			LineEnding:     zapcore.DefaultLineEnding,
			EncodeLevel:    zapcore.CapitalColorLevelEncoder,
			EncodeTime:     zapcore.TimeEncoderOfLayout("2006-01-02 15:04:05"),
			EncodeDuration: zapcore.SecondsDurationEncoder,
			EncodeCaller:   zapcore.ShortCallerEncoder,
		},
	}

	if Cfg.Server.Mode == "debug" {
		config.Level = zap.NewAtomicLevelAt(zap.DebugLevel)
	}

	var err error
	Logger, err = config.Build()
	if err != nil {
		panic("初始化日志失败: " + err.Error())
	}

	zap.ReplaceGlobals(Logger)
}
