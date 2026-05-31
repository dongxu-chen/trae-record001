package config

import (
	"os"

	"gopkg.in/yaml.v3"
)

type Config struct {
	Server   ServerConfig   `yaml:"server"`
	Accounts []AccountConfig `yaml:"accounts"`
	Rules    RulesConfig    `yaml:"rules"`
}

type ServerConfig struct {
	Port int    `yaml:"port"`
	Mode string `yaml:"mode"`
}

type AccountConfig struct {
	ID           string `yaml:"id"`
	Name         string `yaml:"name"`
	Cloud        string `yaml:"cloud"`
	AccessKey    string `yaml:"accessKey"`
	AccessSecret string `yaml:"accessSecret"`
	Region       string `yaml:"region"`
}

type RulesConfig struct {
	DefaultRules []string `yaml:"defaultRules"`
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

	if cfg.Server.Port == 0 {
		cfg.Server.Port = 8080
	}
	if cfg.Server.Mode == "" {
		cfg.Server.Mode = "debug"
	}

	return &cfg, nil
}
