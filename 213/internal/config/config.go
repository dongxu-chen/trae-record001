package config

import (
	"fmt"
	"log"
	"path/filepath"
	"sync"
	"time"

	"github.com/fsnotify/fsnotify"
	"github.com/spf13/viper"
)

type Config struct {
	Server    ServerConfig    `mapstructure:"server"`
	Collector CollectorConfig `mapstructure:"collector"`
	Storage   StorageConfig   `mapstructure:"storage"`
	Alert     AlertConfig     `mapstructure:"alert"`
	DingTalk  DingTalkConfig  `mapstructure:"dingtalk"`
}

type ServerConfig struct {
	Port int    `mapstructure:"port"`
	Host string `mapstructure:"host"`
}

type CollectorConfig struct {
	IntervalSeconds int      `mapstructure:"interval_seconds"`
	TopProcessCount int      `mapstructure:"top_process_count"`
	Disks           []string `mapstructure:"disks"`
	NetInterfaces   []string `mapstructure:"net_interfaces"`
}

type StorageConfig struct {
	Enabled  bool   `mapstructure:"enabled"`
	DataDir  string `mapstructure:"data_dir"`
	RetentionDays int `mapstructure:"retention_days"`
}

type SilentPeriod struct {
	StartHour int `mapstructure:"start_hour"`
	EndHour   int `mapstructure:"end_hour"`
}

type AlertConfig struct {
	CPUThreshold    float64        `mapstructure:"cpu_threshold"`
	MemoryThreshold float64        `mapstructure:"memory_threshold"`
	DurationMinutes int            `mapstructure:"duration_minutes"`
	Enabled         bool           `mapstructure:"enabled"`
	SilentPeriods   []SilentPeriod `mapstructure:"silent_periods"`
}

type DingTalkConfig struct {
	WebhookURL string `mapstructure:"webhook_url"`
	Secret     string `mapstructure:"secret"`
	AtMobiles  []string `mapstructure:"at_mobiles"`
	IsAtAll    bool   `mapstructure:"is_at_all"`
}

var (
	instance *Config
	once     sync.Once
	mu       sync.RWMutex
)

func GetConfig() *Config {
	mu.RLock()
	defer mu.RUnlock()
	return instance
}

func Load(configPath string) (*Config, error) {
	v := viper.New()
	v.SetConfigFile(configPath)
	v.SetConfigType("yaml")

	v.SetDefault("server.port", 9091)
	v.SetDefault("server.host", "0.0.0.0")
	v.SetDefault("collector.interval_seconds", 10)
	v.SetDefault("collector.top_process_count", 10)
	v.SetDefault("storage.enabled", true)
	v.SetDefault("storage.data_dir", "./data")
	v.SetDefault("storage.retention_days", 7)
	v.SetDefault("alert.cpu_threshold", 80.0)
	v.SetDefault("alert.memory_threshold", 85.0)
	v.SetDefault("alert.duration_minutes", 5)
	v.SetDefault("alert.enabled", true)

	if err := v.ReadInConfig(); err != nil {
		return nil, fmt.Errorf("failed to read config file: %w", err)
	}

	var cfg Config
	if err := v.Unmarshal(&cfg); err != nil {
		return nil, fmt.Errorf("failed to unmarshal config: %w", err)
	}

	mu.Lock()
	instance = &cfg
	mu.Unlock()

	return &cfg, nil
}

func Watch(configPath string, onChange func()) error {
	watcher, err := fsnotify.NewWatcher()
	if err != nil {
		return fmt.Errorf("failed to create watcher: %w", err)
	}

	absPath, err := filepath.Abs(configPath)
	if err != nil {
		return fmt.Errorf("failed to get absolute path: %w", err)
	}

	configDir := filepath.Dir(absPath)
	if err := watcher.Add(configDir); err != nil {
		return fmt.Errorf("failed to watch directory: %w", err)
	}

	var debounceTimer *time.Timer
	debounceDuration := 500 * time.Millisecond

	go func() {
		defer watcher.Close()

		for {
			select {
			case event, ok := <-watcher.Events:
				if !ok {
					return
				}

				eventAbsPath, err := filepath.Abs(event.Name)
				if err != nil {
					continue
				}

				if eventAbsPath == absPath && (event.Op&fsnotify.Write == fsnotify.Write || event.Op&fsnotify.Create == fsnotify.Create) {
					log.Printf("Config file change detected: %s (%s)", event.Name, event.Op)

					if debounceTimer != nil {
						debounceTimer.Stop()
					}

					debounceTimer = time.AfterFunc(debounceDuration, func() {
						log.Println("Reloading config...")
						if _, err := Load(configPath); err != nil {
							log.Printf("Failed to reload config: %v", err)
							return
						}
						if onChange != nil {
							onChange()
						}
						log.Println("Config reloaded successfully")
					})
				}

			case err, ok := <-watcher.Errors:
				if !ok {
					return
				}
				log.Printf("Config watcher error: %v", err)
			}
		}
	}()

	log.Printf("Started watching config file: %s", absPath)
	return nil
}

func (c *CollectorConfig) GetInterval() time.Duration {
	return time.Duration(c.IntervalSeconds) * time.Second
}

func (c *AlertConfig) GetDuration() time.Duration {
	return time.Duration(c.DurationMinutes) * time.Minute
}

func (c *AlertConfig) IsSilentPeriod(t time.Time) bool {
	hour := t.Hour()
	for _, sp := range c.SilentPeriods {
		if sp.StartHour < sp.EndHour {
			if hour >= sp.StartHour && hour < sp.EndHour {
				return true
			}
		} else {
			if hour >= sp.StartHour || hour < sp.EndHour {
				return true
			}
		}
	}
	return false
}
