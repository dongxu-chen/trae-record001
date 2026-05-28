package config

import (
	"fmt"
	"os"
	"health-check/internal/model"

	"gopkg.in/yaml.v3"
)

type Config struct {
	Server      ServerConfig         `yaml:"server"`
	ProbePool   ProbePoolConfig    `yaml:"probe_pool"`
	Window      WindowConfig       `yaml:"window"`
	Scheduling  SchedulingConfig   `yaml:"scheduling"`
	Prediction  PredictionConfig   `yaml:"prediction"`
	Tracing     TracingConfig      `yaml:"tracing"`
	Endpoints   []model.Endpoint   `yaml:"endpoints"`
	AlertRules  []model.AlertRule `yaml:"alert_rules"`
	Alert       AlertConfig      `yaml:"alert"`
	Chaos       ChaosConfig      `yaml:"chaos"`
	Shadow      ShadowConfig     `yaml:"shadow"`
}

type ServerConfig struct {
	Port        int  `yaml:"port"`
	MetricsPort int  `yaml:"metrics_port"`
	AdminPort   int  `yaml:"admin_port"`
	EnablePprof bool `yaml:"enable_pprof"`
}

type ProbePoolConfig struct {
	MinWorkers int `yaml:"min_workers"`
	MaxWorkers int `yaml:"max_workers"`
	QueueSize  int `yaml:"queue_size"`
}

type WindowConfig struct {
	Duration int `yaml:"duration"`
	Slots    int `yaml:"slots"`
}

type SchedulingConfig struct {
	Enabled        bool    `yaml:"enabled"`
	AutoAdjust     bool    `yaml:"auto_adjust"`
	MinInterval    int     `yaml:"min_interval"`
	MaxInterval    int     `yaml:"max_interval"`
	WeightFactor   float64 `yaml:"weight_factor"`
	HealthFactor   float64 `yaml:"health_factor"`
	AdjustInterval int     `yaml:"adjust_interval"`
}

type PredictionConfig struct {
	Enabled            bool    `yaml:"enabled"`
	Algorithm          string  `yaml:"algorithm"`
	HistorySize        int     `yaml:"history_size"`
	PredictionWindow   int     `yaml:"prediction_window"`
	WarningThreshold   float64 `yaml:"warning_threshold"`
	CriticalThreshold  float64 `yaml:"critical_threshold"`
}

type TracingConfig struct {
	Enabled       bool   `yaml:"enabled"`
	GlobalTraceID bool   `yaml:"global_trace_id"`
	TraceHeader   string `yaml:"trace_header"`
}

type AlertConfig struct {
	Enabled    bool          `yaml:"enabled"`
	SMTP       *SMTPConfig   `yaml:"smtp,omitempty"`
	WebhookURL string        `yaml:"webhook_url"`
	DingTalk   *DingTalkConfig `yaml:"dingtalk,omitempty"`
}

type SMTPConfig struct {
	Host     string   `yaml:"host"`
	Port     int      `yaml:"port"`
	Username string   `yaml:"username"`
	Password string   `yaml:"password"`
	From     string   `yaml:"from"`
	To       []string `yaml:"to"`
}

type DingTalkConfig struct {
	WebhookURL string `yaml:"webhook_url"`
	Secret     string `yaml:"secret"`
}

type ChaosConfig struct {
	Enabled   bool           `yaml:"enabled"`
	Endpoints []ChaosEndpoint `yaml:"endpoints"`
}

type ChaosEndpoint struct {
	EndpointID string  `yaml:"endpoint_id"`
	FaultType  string  `yaml:"fault_type"`
	Duration   int     `yaml:"duration"`
	StartHour  int     `yaml:"start_hour"`
	EndHour    int     `yaml:"end_hour"`
	Rate       float64 `yaml:"rate"`
	Shadow     bool    `yaml:"shadow"`
}

type ShadowConfig struct {
	Enabled       bool   `yaml:"enabled"`
	DefaultShadow bool   `yaml:"default_shadow"`
	ShadowHeader  string `yaml:"shadow_header"`
	ShadowValue   string `yaml:"shadow_value"`
	RecordOnly    bool   `yaml:"record_only"`
}

func Load(path string) (*Config, error) {
	data, err := os.ReadFile(path)
	if err != nil {
		return nil, fmt.Errorf("read config failed: %w", err)
	}

	var cfg Config
	if err := yaml.Unmarshal(data, &cfg); err != nil {
		return nil, fmt.Errorf("parse config failed: %w", err)
	}

	if err := validate(&cfg); err != nil {
		return nil, err
	}

	return &cfg, nil
}

func validate(cfg *Config) error {
	if cfg.Server.Port == 0 {
		cfg.Server.Port = 8080
	}
	if cfg.Server.MetricsPort == 0 {
		cfg.Server.MetricsPort = 9090
	}
	if cfg.Server.AdminPort == 0 {
		cfg.Server.AdminPort = 8081
	}
	if cfg.ProbePool.MinWorkers <= 0 {
		cfg.ProbePool.MinWorkers = 5
	}
	if cfg.ProbePool.MaxWorkers <= 0 {
		cfg.ProbePool.MaxWorkers = 50
	}
	if cfg.ProbePool.QueueSize <= 0 {
		cfg.ProbePool.QueueSize = 1000
	}
	if cfg.Window.Duration <= 0 {
		cfg.Window.Duration = 60
	}
	if cfg.Window.Slots <= 0 {
		cfg.Window.Slots = 60
	}
	if cfg.Scheduling.MinInterval <= 0 {
		cfg.Scheduling.MinInterval = 5
	}
	if cfg.Scheduling.MaxInterval <= 0 {
		cfg.Scheduling.MaxInterval = 300
	}
	if cfg.Scheduling.WeightFactor <= 0 {
		cfg.Scheduling.WeightFactor = 0.5
	}
	if cfg.Scheduling.HealthFactor <= 0 {
		cfg.Scheduling.HealthFactor = 0.5
	}
	if cfg.Scheduling.AdjustInterval <= 0 {
		cfg.Scheduling.AdjustInterval = 60
	}
	if cfg.Prediction.HistorySize <= 0 {
		cfg.Prediction.HistorySize = 100
	}
	if cfg.Prediction.PredictionWindow <= 0 {
		cfg.Prediction.PredictionWindow = 5
	}
	if cfg.Prediction.WarningThreshold <= 0 {
		cfg.Prediction.WarningThreshold = 90
	}
	if cfg.Prediction.CriticalThreshold <= 0 {
		cfg.Prediction.CriticalThreshold = 75
	}
	if cfg.Tracing.TraceHeader == "" {
		cfg.Tracing.TraceHeader = "X-Trace-ID"
	}
	if cfg.Shadow.ShadowHeader == "" {
		cfg.Shadow.ShadowHeader = "X-Shadow-Request"
	}
	if cfg.Shadow.ShadowValue == "" {
		cfg.Shadow.ShadowValue = "true"
	}

	endpointIDs := make(map[string]bool)
	for _, ep := range cfg.Endpoints {
		if endpointIDs[ep.ID] {
			return fmt.Errorf("duplicate endpoint id: %s", ep.ID)
		}
		endpointIDs[ep.ID] = true

		if ep.Interval <= 0 {
			ep.Interval = 10
		}
		if ep.Timeout <= 0 {
			ep.Timeout = 5
		}
		if ep.Weight <= 0 {
			ep.Weight = int(model.WeightMedium)
		}

		if ep.RateLimit != nil && ep.RateLimit.Enabled {
			if ep.RateLimit.Rate <= 0 {
				ep.RateLimit.Rate = 10
			}
			if ep.RateLimit.Capacity <= 0 {
				ep.RateLimit.Capacity = ep.RateLimit.Rate * 2
			}
		}
	}

	ruleIDs := make(map[string]bool)
	for _, rule := range cfg.AlertRules {
		if ruleIDs[rule.ID] {
			return fmt.Errorf("duplicate alert rule id: %s", rule.ID)
		}
		ruleIDs[rule.ID] = true
	}

	return nil
}
