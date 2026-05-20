package config

import (
	"fmt"
	"strings"

	"github.com/spf13/viper"
)

type Config struct {
	Kubeconfig string      `mapstructure:"kubeconfig"`
	Namespace  string      `mapstructure:"namespace"`
	Audit      AuditConfig `mapstructure:"audit"`
	Rules      RulesConfig `mapstructure:"rules"`
	Webhook    WebhookConfig `mapstructure:"webhook"`
}

type AuditConfig struct {
	Schedule      string   `mapstructure:"schedule"`
	OutputDir     string   `mapstructure:"outputDir"`
	EnableTrends  bool     `mapstructure:"enableTrends"`
	EnableRBAC    bool     `mapstructure:"enableRBAC"`
	AutoRemediate bool     `mapstructure:"autoRemediate"`
	DryRun        bool     `mapstructure:"dryRun"`
	Resources     []string `mapstructure:"resources"`
}

type RulesConfig struct {
	ResourceQuota ResourceQuotaConfig `mapstructure:"resourceQuota"`
	Labels        LabelsConfig        `mapstructure:"labels"`
	ImageSource   ImageSourceConfig   `mapstructure:"imageSource"`
}

type ResourceQuotaConfig struct {
	Enabled          bool   `mapstructure:"enabled"`
	CPURequestMin    string `mapstructure:"cpuRequestMin"`
	CPURequestMax    string `mapstructure:"cpuRequestMax"`
	MemoryRequestMin string `mapstructure:"memoryRequestMin"`
	MemoryRequestMax string `mapstructure:"memoryRequestMax"`
	CPULimitMin      string `mapstructure:"cpuLimitMin"`
	CPULimitMax      string `mapstructure:"cpuLimitMax"`
	MemoryLimitMin   string `mapstructure:"memoryLimitMin"`
	MemoryLimitMax   string `mapstructure:"memoryLimitMax"`
}

type LabelsConfig struct {
	Enabled  bool              `mapstructure:"enabled"`
	Required []string          `mapstructure:"required"`
	Patterns map[string]string `mapstructure:"patterns"`
}

type ImageSourceConfig struct {
	Enabled               bool     `mapstructure:"enabled"`
	AllowedRegistries     []string `mapstructure:"allowedRegistries"`
	DisallowedTags        []string `mapstructure:"disallowedTags"`
	CheckPrivateRegistryAuth bool   `mapstructure:"checkPrivateRegistryAuth"`
	PrivateRegistries     []string `mapstructure:"privateRegistries"`
}

type WebhookConfig struct {
	Enabled bool   `mapstructure:"enabled"`
	URL     string `mapstructure:"url"`
	Secret  string `mapstructure:"secret"`
	Timeout string `mapstructure:"timeout"`
}

func Load(path string) (*Config, error) {
	v := viper.New()
	v.SetConfigFile(path)
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

	return &cfg, nil
}
