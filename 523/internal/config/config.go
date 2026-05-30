package config

import (
	"fmt"
	"os"
	"strings"

	"github.com/sirupsen/logrus"
	"github.com/spf13/viper"

	"github.com/security/container-escape-detector/internal/alert"
	"github.com/security/container-escape-detector/internal/protection"
	"github.com/security/container-escape-detector/internal/simulator"
	"github.com/security/container-escape-detector/internal/threatintel"
	"github.com/security/container-escape-detector/pkg/types"
)

type Config struct {
	LogLevel    string       `yaml:"log_level"`
	BPF         BPFConfig    `yaml:"bpf"`
	Container   ContainerConfig `yaml:"container"`
	Behavior    BehaviorConfig `yaml:"behavior"`
	Rules       RulesConfig  `yaml:"rules"`
	Alert       alert.Config `yaml:"alert"`
	Metrics     MetricsConfig `yaml:"metrics"`
	Analysis    AnalysisConfig `yaml:"analysis"`
	Simulator   simulator.Config `yaml:"simulator"`
	Protection  protection.Config `yaml:"protection"`
	ThreatIntel threatintel.Config `yaml:"threat_intel"`
}

type BPFConfig struct {
	Enabled       bool   `yaml:"enabled"`
	PerfBufferSize int   `yaml:"perf_buffer_size"`
	Events        []string `yaml:"events"`
	FallbackMode  bool   `yaml:"fallback_mode"`
}

type ContainerConfig struct {
	RefreshInterval int    `yaml:"refresh_interval"`
	DockerSocket    string `yaml:"docker_socket"`
	UseProcFS       bool   `yaml:"use_procfs"`
	UseDockerAPI    bool   `yaml:"use_docker_api"`
}

type BehaviorConfig struct {
	BaselineMode        bool    `yaml:"baseline_mode"`
	BaselineDuration    int     `yaml:"baseline_duration"`
	AnomalyThreshold    float64 `yaml:"anomaly_threshold"`
	ProcessTreeDepth    int     `yaml:"process_tree_depth"`
	MaxHistorySize      int     `yaml:"max_history_size"`
	MountWhitelist      *MountWhitelistConfig `yaml:"mount_whitelist"`
}

type RulesConfig struct {
	CustomRulesDir string `yaml:"custom_rules_dir"`
	LoadBuiltin    bool   `yaml:"load_builtin"`
}

type MetricsConfig struct {
	Enabled    bool   `yaml:"enabled"`
	ListenAddr string `yaml:"listen_addr"`
}

type AnalysisConfig struct {
	EnableAttackChain bool `yaml:"enable_attack_chain"`
	EnableRiskScore   bool `yaml:"enable_risk_score"`
	RiskWindowMinutes int  `yaml:"risk_window_minutes"`
}

type MountWhitelistConfig struct {
	Enabled           bool                  `yaml:"enabled"`
	Paths             []MountWhitelistEntry `yaml:"paths"`
	ContainerPatterns []string              `yaml:"container_patterns"`
}

type MountWhitelistEntry struct {
	Source      string `yaml:"source"`
	Target      string `yaml:"target"`
	FSType      string `yaml:"fs_type"`
	Description string `yaml:"description"`
}

var defaultConfig = &Config{
	LogLevel: "info",
	BPF: BPFConfig{
		Enabled:        true,
		PerfBufferSize: 1024,
		FallbackMode:   false,
		Events: []string{
			"mount", "umount", "chroot", "pivot_root",
			"setns", "unshare", "ptrace",
			"init_module", "delete_module",
			"execve", "openat", "mknod",
			"cap_capable", "commit_creds",
		},
	},
	Container: ContainerConfig{
		RefreshInterval: 30,
		DockerSocket:    "/var/run/docker.sock",
		UseProcFS:       true,
		UseDockerAPI:    true,
	},
	Behavior: BehaviorConfig{
		BaselineMode:     false,
		BaselineDuration: 300,
		AnomalyThreshold: 2.0,
		ProcessTreeDepth: 10,
		MaxHistorySize:   10000,
		MountWhitelist: &MountWhitelistConfig{
			Enabled: true,
			Paths: []MountWhitelistEntry{
				{Source: "/dev/null", Target: "/dev/null", FSType: "devtmpfs", Description: "Standard device"},
				{Source: "/dev/urandom", Target: "/dev/urandom", FSType: "devtmpfs", Description: "Random device"},
				{Source: "/dev/random", Target: "/dev/random", FSType: "devtmpfs", Description: "Random device"},
				{Source: "/dev/zero", Target: "/dev/zero", FSType: "devtmpfs", Description: "Zero device"},
				{Source: "proc", Target: "/proc", FSType: "proc", Description: "Standard proc mount"},
				{Source: "sysfs", Target: "/sys", FSType: "sysfs", Description: "Standard sys mount"},
				{Source: "tmpfs", Target: "/dev/shm", FSType: "tmpfs", Description: "Shared memory"},
				{Source: "tmpfs", Target: "/run", FSType: "tmpfs", Description: "Runtime data"},
				{Source: "tmpfs", Target: "/tmp", FSType: "tmpfs", Description: "Temp directory"},
				{Source: "cgroup", Target: "/sys/fs/cgroup", FSType: "cgroup", Description: "Cgroup filesystem"},
				{Source: "mqueue", Target: "/dev/mqueue", FSType: "mqueue", Description: "Message queue"},
				{Source: "/etc/resolv.conf", Target: "/etc/resolv.conf", FSType: "bind", Description: "DNS config"},
				{Source: "/etc/hosts", Target: "/etc/hosts", FSType: "bind", Description: "Hosts file"},
				{Source: "/etc/hostname", Target: "/etc/hostname", FSType: "bind", Description: "Hostname file"},
			},
		},
	},
	Rules: RulesConfig{
		CustomRulesDir: "/etc/escape-detector/rules",
		LoadBuiltin:    true,
	},
	Alert: alert.Config{
		LogLevel:  types.RiskInfo,
		RateLimit: 60,
		Aggregation: &alert.AggregationConfig{
			Enabled:          true,
			WindowSeconds:    300,
			MaxEventsPerGroup: 100,
			SendInterval:     60,
		},
	},
	Metrics: MetricsConfig{
		Enabled:    true,
		ListenAddr: ":9090",
	},
	Analysis: AnalysisConfig{
		EnableAttackChain: true,
		EnableRiskScore:   true,
		RiskWindowMinutes: 60,
	},
	Simulator: simulator.Config{
		Enabled:           false,
		Mode:              "passive",
		IntervalSeconds:   3600,
		MaxAttemptsPerRun: 10,
		EnableDangerous:   false,
	},
	Protection: protection.Config{
		Enabled:             false,
		Mode:                "monitor",
		AutoBlockSeverity:   "HIGH",
		NetworkIsolation:    true,
		KillProcess:         true,
		QuarantineContainer: false,
	},
	ThreatIntel: threatintel.Config{
		Enabled:        true,
		UpdateInterval: 24,
		CacheDir:       "/var/lib/escape-detector/threatintel",
		AutoUpdate:     true,
	},
}

func Load(path string, logger *logrus.Logger) (*Config, error) {
	v := viper.New()

	v.SetConfigType("yaml")
	v.SetEnvPrefix("ESCAPE_DETECTOR")
	v.SetEnvKeyReplacer(strings.NewReplacer(".", "_"))
	v.AutomaticEnv()

	setDefaults(v)

	if path != "" {
		if _, err := os.Stat(path); err == nil {
			v.SetConfigFile(path)
			logger.Infof("Loading config from: %s", path)

			if err := v.ReadInConfig(); err != nil {
				return nil, fmt.Errorf("failed to read config: %w", err)
			}
		} else {
			logger.Warnf("Config file %s not found, using defaults", path)
		}
	}

	var cfg Config
	if err := v.Unmarshal(&cfg); err != nil {
		return nil, fmt.Errorf("failed to unmarshal config: %w", err)
	}

	if err := validate(&cfg, logger); err != nil {
		return nil, fmt.Errorf("invalid config: %w", err)
	}

	return &cfg, nil
}

func setDefaults(v *viper.Viper) {
	v.SetDefault("log_level", defaultConfig.LogLevel)

	v.SetDefault("bpf.enabled", defaultConfig.BPF.Enabled)
	v.SetDefault("bpf.perf_buffer_size", defaultConfig.BPF.PerfBufferSize)
	v.SetDefault("bpf.fallback_mode", defaultConfig.BPF.FallbackMode)
	v.SetDefault("bpf.events", defaultConfig.BPF.Events)

	v.SetDefault("container.refresh_interval", defaultConfig.Container.RefreshInterval)
	v.SetDefault("container.docker_socket", defaultConfig.Container.DockerSocket)
	v.SetDefault("container.use_procfs", defaultConfig.Container.UseProcFS)
	v.SetDefault("container.use_docker_api", defaultConfig.Container.UseDockerAPI)

	v.SetDefault("behavior.baseline_mode", defaultConfig.Behavior.BaselineMode)
	v.SetDefault("behavior.baseline_duration", defaultConfig.Behavior.BaselineDuration)
	v.SetDefault("behavior.anomaly_threshold", defaultConfig.Behavior.AnomalyThreshold)
	v.SetDefault("behavior.process_tree_depth", defaultConfig.Behavior.ProcessTreeDepth)
	v.SetDefault("behavior.max_history_size", defaultConfig.Behavior.MaxHistorySize)
	v.SetDefault("behavior.mount_whitelist.enabled", defaultConfig.Behavior.MountWhitelist.Enabled)

	v.SetDefault("rules.custom_rules_dir", defaultConfig.Rules.CustomRulesDir)
	v.SetDefault("rules.load_builtin", defaultConfig.Rules.LoadBuiltin)

	v.SetDefault("alert.log_level", string(defaultConfig.Alert.LogLevel))
	v.SetDefault("alert.rate_limit", defaultConfig.Alert.RateLimit)

	v.SetDefault("metrics.enabled", defaultConfig.Metrics.Enabled)
	v.SetDefault("metrics.listen_addr", defaultConfig.Metrics.ListenAddr)

	v.SetDefault("analysis.enable_attack_chain", defaultConfig.Analysis.EnableAttackChain)
	v.SetDefault("analysis.enable_risk_score", defaultConfig.Analysis.EnableRiskScore)
	v.SetDefault("analysis.risk_window_minutes", defaultConfig.Analysis.RiskWindowMinutes)
}

func validate(cfg *Config, logger *logrus.Logger) error {
	if cfg.BPF.PerfBufferSize < 128 {
		logger.Warnf("BPF perf buffer size %d is too small, setting to 128", cfg.BPF.PerfBufferSize)
		cfg.BPF.PerfBufferSize = 128
	}

	if cfg.Container.RefreshInterval < 5 {
		logger.Warnf("Container refresh interval %d is too small, setting to 5", cfg.Container.RefreshInterval)
		cfg.Container.RefreshInterval = 5
	}

	if cfg.Behavior.AnomalyThreshold < 0.1 {
		logger.Warnf("Anomaly threshold %f is too small, setting to 0.1", cfg.Behavior.AnomalyThreshold)
		cfg.Behavior.AnomalyThreshold = 0.1
	}

	if cfg.Analysis.RiskWindowMinutes < 1 {
		logger.Warnf("Risk window %d is too small, setting to 1", cfg.Analysis.RiskWindowMinutes)
		cfg.Analysis.RiskWindowMinutes = 1
	}

	validLevels := map[string]bool{
		string(types.RiskInfo):     true,
		string(types.RiskLow):      true,
		string(types.RiskMedium):   true,
		string(types.RiskHigh):     true,
		string(types.RiskCritical): true,
	}

	if cfg.Alert.LogLevel != "" && !validLevels[string(cfg.Alert.LogLevel)] {
		return fmt.Errorf("invalid alert log level: %s", cfg.Alert.LogLevel)
	}

	return nil
}

func (c *Config) GetLogLevel() logrus.Level {
	switch strings.ToLower(c.LogLevel) {
	case "debug":
		return logrus.DebugLevel
	case "info":
		return logrus.InfoLevel
	case "warn", "warning":
		return logrus.WarnLevel
	case "error":
		return logrus.ErrorLevel
	case "fatal":
		return logrus.FatalLevel
	default:
		return logrus.InfoLevel
	}
}
