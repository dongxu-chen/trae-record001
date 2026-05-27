package config

import (
	"os"
	"time"

	"gopkg.in/yaml.v3"
)

type Config struct {
	MetricsAddr  string              `yaml:"metrics_addr"`
	RulesDir     string              `yaml:"rules_dir"`
	LogLevel     string              `yaml:"log_level"`
	Outputs      []OutputConfig      `yaml:"outputs"`
	Containers   []ContainerConfig   `yaml:"containers"`
	Whitelist    WhitelistConfig     `yaml:"whitelist"`
	Remediation  RemediationConfig   `yaml:"remediation"`
	Baseline     BaselineConfig      `yaml:"baseline"`
	Correlation  CorrelationConfig   `yaml:"correlation"`
	ThreatIntel  ThreatIntelConfig   `yaml:"threat_intel"`
}

type OutputConfig struct {
	Type   string            `yaml:"type"`
	Config map[string]string `yaml:"config"`
}

type ContainerConfig struct {
	ID      string   `yaml:"id"`
	Name    string   `yaml:"name"`
	Monitor bool     `yaml:"monitor"`
	Rules   []string `yaml:"rules"`
}

type WhitelistConfig struct {
	Processes []ProcessWhitelist `yaml:"processes"`
	Networks  []NetworkWhitelist `yaml:"networks"`
}

type ProcessWhitelist struct {
	Comm        string   `yaml:"comm"`
	ContainerID string   `yaml:"container_id"`
	Description string   `yaml:"description"`
	Tags        []string `yaml:"tags"`
}

type NetworkWhitelist struct {
	IP          string   `yaml:"ip"`
	Port        uint16   `yaml:"port"`
	Protocol    string   `yaml:"protocol"`
	ContainerID string   `yaml:"container_id"`
	Description string   `yaml:"description"`
	Tags        []string `yaml:"tags"`
}

type RemediationConfig struct {
	AutoBlock      bool     `yaml:"auto_block"`
	BlockSeverity  string   `yaml:"block_severity"`
	BlockRules     []string `yaml:"block_rules"`
	NetworkIsolate bool     `yaml:"network_isolate"`
	QuarantineDir  string   `yaml:"quarantine_dir"`
}

type BaselineConfig struct {
	Enabled          bool          `yaml:"enabled"`
	Mode             string        `yaml:"mode"`
	LearningPeriod   time.Duration `yaml:"learning_period"`
	BaselineDir      string        `yaml:"baseline_dir"`
	DeviationThreshold float64     `yaml:"deviation_threshold"`
}

type CorrelationConfig struct {
	Enabled       bool          `yaml:"enabled"`
	TimeWindow    time.Duration `yaml:"time_window"`
	MaxBufferSize int           `yaml:"max_buffer_size"`
}

type ThreatIntelConfig struct {
	Enabled        bool           `yaml:"enabled"`
	AutoBlock      bool           `yaml:"auto_block"`
	BlockThreshold float64        `yaml:"block_threshold"`
	CacheDir       string         `yaml:"cache_dir"`
	Sources        []IntelSource  `yaml:"sources"`
}

type IntelSource struct {
	Name     string        `yaml:"name"`
	URL      string        `yaml:"url"`
	Type     string        `yaml:"type"`
	APIKey   string        `yaml:"api_key"`
	Interval time.Duration `yaml:"interval"`
}

func Load(path string) (*Config, error) {
	data, err := os.ReadFile(path)
	if err != nil {
		return defaultConfig(), nil
	}

	var cfg Config
	if err := yaml.Unmarshal(data, &cfg); err != nil {
		return nil, err
	}

	return &cfg, nil
}

func defaultConfig() *Config {
	return &Config{
		MetricsAddr: ":9091",
		RulesDir:    "rules",
		LogLevel:    "info",
		Outputs: []OutputConfig{
			{Type: "stdout", Config: map[string]string{}},
		},
		Whitelist: WhitelistConfig{
			Processes: []ProcessWhitelist{},
			Networks:  []NetworkWhitelist{},
		},
		Remediation: RemediationConfig{
			AutoBlock:      false,
			BlockSeverity:  "critical",
			BlockRules:     []string{},
			NetworkIsolate: false,
			QuarantineDir:  "/var/run/csm/quarantine",
		},
		Baseline: BaselineConfig{
			Enabled:          true,
			Mode:             "hybrid",
			LearningPeriod:   24 * time.Hour,
			BaselineDir:      "/var/run/csm/baselines",
			DeviationThreshold: 0.3,
		},
		Correlation: CorrelationConfig{
			Enabled:       true,
			TimeWindow:    10 * time.Minute,
			MaxBufferSize: 1000,
		},
		ThreatIntel: ThreatIntelConfig{
			Enabled:        true,
			AutoBlock:      true,
			BlockThreshold: 0.7,
			CacheDir:       "/var/run/csm/threatintel",
			Sources:        []IntelSource{},
		},
	}
}
