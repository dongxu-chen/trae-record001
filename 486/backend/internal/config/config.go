package config

import (
	"fmt"
	"time"

	"github.com/spf13/viper"
)

type Config struct {
	Server   ServerConfig   `mapstructure:"server"`
	Kubernetes KubernetesConfig `mapstructure:"kubernetes"`
	Istio    IstioConfig    `mapstructure:"istio"`
	OPA      OPAConfig      `mapstructure:"opa"`
	Kiali    KialiConfig    `mapstructure:"kiali"`
	Database DatabaseConfig `mapstructure:"database"`
	Log      LogConfig      `mapstructure:"log"`
}

type ServerConfig struct {
	Host         string        `mapstructure:"host"`
	Port         int           `mapstructure:"port"`
	ReadTimeout  time.Duration `mapstructure:"read_timeout"`
	WriteTimeout time.Duration `mapstructure:"write_timeout"`
}

type KubernetesConfig struct {
	KubeConfig string `mapstructure:"kubeconfig"`
	InCluster  bool   `mapstructure:"in_cluster"`
}

type IstioConfig struct {
	Namespace string `mapstructure:"namespace"`
}

type OPAConfig struct {
	URL     string `mapstructure:"url"`
	Timeout int    `mapstructure:"timeout"`
}

type KialiConfig struct {
	URL      string `mapstructure:"url"`
	Username string `mapstructure:"username"`
	Password string `mapstructure:"password"`
}

type DatabaseConfig struct {
	Type     string `mapstructure:"type"`
	Host     string `mapstructure:"host"`
	Port     int    `mapstructure:"port"`
	User     string `mapstructure:"user"`
	Password string `mapstructure:"password"`
	DBName   string `mapstructure:"dbname"`
}

type LogConfig struct {
	Level  string `mapstructure:"level"`
	Format string `mapstructure:"format"`
}

func Load(configPath string) (*Config, error) {
	v := viper.New()
	v.SetConfigFile(configPath)
	v.SetConfigType("yaml")

	v.SetDefault("server.host", "0.0.0.0")
	v.SetDefault("server.port", 8080)
	v.SetDefault("server.read_timeout", "30s")
	v.SetDefault("server.write_timeout", "30s")
	v.SetDefault("istio.namespace", "istio-system")
	v.SetDefault("opa.timeout", 10)
	v.SetDefault("log.level", "info")
	v.SetDefault("log.format", "json")

	if err := v.ReadInConfig(); err != nil {
		if _, ok := err.(viper.ConfigFileNotFoundError); !ok {
			return nil, fmt.Errorf("failed to read config: %w", err)
		}
	}

	var cfg Config
	if err := v.Unmarshal(&cfg); err != nil {
		return nil, fmt.Errorf("failed to unmarshal config: %w", err)
	}

	return &cfg, nil
}
