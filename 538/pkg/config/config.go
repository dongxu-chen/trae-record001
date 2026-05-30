package config

import (
	"fmt"
	"strings"

	"github.com/spf13/viper"
)

type Config struct {
	Server     ServerConfig     `mapstructure:"server"`
	Neo4j      Neo4jConfig      `mapstructure:"neo4j"`
	Kubernetes KubernetesConfig `mapstructure:"kubernetes"`
	Cilium     CiliumConfig     `mapstructure:"cilium"`
	Policy     PolicyConfig     `mapstructure:"policy"`
}

type ServerConfig struct {
	Port string `mapstructure:"port"`
}

type Neo4jConfig struct {
	URI      string `mapstructure:"uri"`
	Username string `mapstructure:"username"`
	Password string `mapstructure:"password"`
}

type KubernetesConfig struct {
	InCluster  bool   `mapstructure:"inCluster"`
	Kubeconfig string `mapstructure:"kubeconfig"`
}

type CiliumConfig struct {
	HubbleRelay string  `mapstructure:"hubbleRelay"`
	Namespace   string  `mapstructure:"namespace"`
	SampleRate  float64 `mapstructure:"sampleRate"`
	MaxEntries  int     `mapstructure:"maxEntries"`
	FlushInterval string `mapstructure:"flushInterval"`
}

type PolicyConfig struct {
	DefaultDeny bool `mapstructure:"defaultDeny"`
	AllowDNS    bool `mapstructure:"allowDNS"`
}

func LoadConfig() (*Config, error) {
	viper.SetConfigName("config")
	viper.SetConfigType("yaml")
	viper.AddConfigPath(".")
	viper.AddConfigPath("..")
	viper.AutomaticEnv()
	viper.SetEnvKeyReplacer(strings.NewReplacer(".", "_"))

	if err := viper.ReadInConfig(); err != nil {
		return nil, fmt.Errorf("error reading config file: %w", err)
	}

	var cfg Config
	if err := viper.Unmarshal(&cfg); err != nil {
		return nil, fmt.Errorf("unable to decode into struct: %w", err)
	}

	return &cfg, nil
}
