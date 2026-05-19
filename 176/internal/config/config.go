package config

import (
	"fmt"
	"strings"

	"github.com/spf13/viper"
)

type Config struct {
	ACME       ACMEConfig       `mapstructure:"acme"`
	DNS        DNSConfig        `mapstructure:"dns"`
	Deploy     DeployConfig     `mapstructure:"deploy"`
	Tenants    []TenantConfig   `mapstructure:"tenants"`
	Security   SecurityConfig   `mapstructure:"security"`
	Monitoring MonitoringConfig `mapstructure:"monitoring"`
	Renewal    RenewalConfig    `mapstructure:"renewal"`
}

type TenantConfig struct {
	ID           string              `mapstructure:"id"`
	Name         string              `mapstructure:"name"`
	Description  string              `mapstructure:"description"`
	ACME         *ACMEConfig         `mapstructure:"acme"`
	DNS          *DNSConfig          `mapstructure:"dns"`
	Deploy       *DeployConfig       `mapstructure:"deploy"`
	Certificates []CertificateConfig `mapstructure:"certificates"`
	Permissions  []string            `mapstructure:"permissions"`
}

type ACMEConfig struct {
	DirectoryURL string `mapstructure:"directory_url"`
	Email        string `mapstructure:"email"`
	KeyType      string `mapstructure:"key_type"`
}

type DNSConfig struct {
	Provider   string          `mapstructure:"provider"`
	Aliyun     AliyunDNSConfig `mapstructure:"aliyun"`
	Cloudflare CloudflareConfig `mapstructure:"cloudflare"`
}

type AliyunDNSConfig struct {
	AccessKeyID     string `mapstructure:"access_key_id"`
	AccessKeySecret string `mapstructure:"access_key_secret"`
	RegionID        string `mapstructure:"region_id"`
}

type CloudflareConfig struct {
	APIKey string `mapstructure:"api_key"`
	Email  string `mapstructure:"email"`
}

type DeployConfig struct {
	Nginx    NginxDeployConfig    `mapstructure:"nginx"`
	AliyunSLB AliyunSLBDeployConfig `mapstructure:"aliyun_slb"`
}

type NginxDeployConfig struct {
	Enabled      bool   `mapstructure:"enabled"`
	CertPath     string `mapstructure:"cert_path"`
	KeyPath      string `mapstructure:"key_path"`
	ReloadCommand string `mapstructure:"reload_command"`
}

type AliyunSLBDeployConfig struct {
	Enabled         bool   `mapstructure:"enabled"`
	AccessKeyID     string `mapstructure:"access_key_id"`
	AccessKeySecret string `mapstructure:"access_key_secret"`
	RegionID        string `mapstructure:"region_id"`
	LoadBalancerID  string `mapstructure:"load_balancer_id"`
	ListenerPort    int    `mapstructure:"listener_port"`
}

type CertificateConfig struct {
	Name        string   `mapstructure:"name"`
	Domains     []string `mapstructure:"domains"`
	OutputDir   string   `mapstructure:"output_dir"`
	DeployTarget string  `mapstructure:"deploy_target"`
}

type RenewalConfig struct {
	CheckInterval string `mapstructure:"check_interval"`
	DaysBefore    int    `mapstructure:"days_before"`
}

type SecurityConfig struct {
	HSM HSMConfig `mapstructure:"hsm"`
}

type HSMConfig struct {
	Enabled     bool   `mapstructure:"enabled"`
	Provider    string `mapstructure:"provider"`
	KeyID       string `mapstructure:"key_id"`
	KeyFilePath string `mapstructure:"key_file_path"`
	EncryptDir  string `mapstructure:"encrypt_dir"`
}

type MonitoringConfig struct {
	Enabled    bool   `mapstructure:"enabled"`
	ListenAddr string `mapstructure:"listen_addr"`
}

func (t *TenantConfig) GetACME(global ACMEConfig) ACMEConfig {
	if t.ACME != nil {
		return *t.ACME
	}
	return global
}

func (t *TenantConfig) GetDNS(global DNSConfig) DNSConfig {
	if t.DNS != nil {
		return *t.DNS
	}
	return global
}

func (t *TenantConfig) GetDeploy(global DeployConfig) DeployConfig {
	if t.Deploy != nil {
		return *t.Deploy
	}
	return global
}

func Load(path string) (*Config, error) {
	v := viper.New()
	v.SetConfigFile(path)
	v.SetConfigType("yaml")
	v.AutomaticEnv()
	v.SetEnvKeyReplacer(strings.NewReplacer(".", "_"))

	if err := v.ReadInConfig(); err != nil {
		return nil, fmt.Errorf("read config file failed: %w", err)
	}

	var cfg Config
	if err := v.Unmarshal(&cfg); err != nil {
		return nil, fmt.Errorf("unmarshal config failed: %w", err)
	}

	if err := validate(&cfg); err != nil {
		return nil, fmt.Errorf("validate config failed: %w", err)
	}

	setDefaults(&cfg)

	return &cfg, nil
}

func validate(cfg *Config) error {
	if cfg.ACME.Email == "" {
		return fmt.Errorf("acme.email is required")
	}
	if cfg.DNS.Provider == "" {
		return fmt.Errorf("dns.provider is required")
	}
	if len(cfg.Certificates) == 0 {
		return fmt.Errorf("at least one certificate is required")
	}
	for i, cert := range cfg.Certificates {
		if cert.Name == "" {
			return fmt.Errorf("certificates[%d].name is required", i)
		}
		if len(cert.Domains) == 0 {
			return fmt.Errorf("certificates[%d].domains is required", i)
		}
	}
	return nil
}

func setDefaults(cfg *Config) {
	if cfg.ACME.DirectoryURL == "" {
		cfg.ACME.DirectoryURL = "https://acme-v02.api.letsencrypt.org/directory"
	}
	if cfg.ACME.KeyType == "" {
		cfg.ACME.KeyType = "rsa2048"
	}
	if cfg.Renewal.CheckInterval == "" {
		cfg.Renewal.CheckInterval = "24h"
	}
	if cfg.Renewal.DaysBefore == 0 {
		cfg.Renewal.DaysBefore = 30
	}
}
