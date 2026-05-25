package configs

import (
	"os"
	"path/filepath"

	"gopkg.in/yaml.v3"
)

type Config struct {
	Storage StorageConfig `yaml:"storage"`
	Cache   CacheConfig   `yaml:"cache"`
	Project ProjectConfig `yaml:"project"`
	Watcher WatcherConfig `yaml:"watcher"`
}

type StorageConfig struct {
	Type      string `yaml:"type"`
	Endpoint  string `yaml:"endpoint"`
	Bucket    string `yaml:"bucket"`
	Region    string `yaml:"region"`
	AccessKey string `yaml:"access_key"`
	SecretKey string `yaml:"secret_key"`
	UseSSL    bool   `yaml:"use_ssl"`
	BasePath  string `yaml:"base_path"`
}

type CacheConfig struct {
	MaxSize    string   `yaml:"max_size"`
	CacheDir   string   `yaml:"cache_dir"`
	KeyPrefix  string   `yaml:"key_prefix"`
	IncludeDir []string `yaml:"include_dirs"`
	ExcludeDir []string `yaml:"exclude_dirs"`
}

type ProjectConfig struct {
	Type       string   `yaml:"type"`
	DepFiles   []string `yaml:"dep_files"`
	CacheDirs  []string `yaml:"cache_dirs"`
	WorkingDir string   `yaml:"working_dir"`
}

type WatcherConfig struct {
	Enabled          bool     `yaml:"enabled"`
	WatchDirs        []string `yaml:"watch_dirs"`
	DebounceDuration string   `yaml:"debounce_duration"`
	PreWarm          bool     `yaml:"prewarm"`
}

func LoadConfig(path string) (*Config, error) {
	data, err := os.ReadFile(path)
	if err != nil {
		return nil, err
	}

	var config Config
	if err := yaml.Unmarshal(data, &config); err != nil {
		return nil, err
	}

	return &config, nil
}

func SaveConfig(path string, config *Config) error {
	if err := os.MkdirAll(filepath.Dir(path), 0755); err != nil {
		return err
	}

	data, err := yaml.Marshal(config)
	if err != nil {
		return err
	}

	return os.WriteFile(path, data, 0644)
}

func DefaultConfig() *Config {
	home, _ := os.UserHomeDir()
	return &Config{
		Storage: StorageConfig{
			Type:     "local",
			BasePath: filepath.Join(home, ".cicache", "storage"),
			UseSSL:   true,
		},
		Cache: CacheConfig{
			MaxSize:   "10GB",
			CacheDir:  filepath.Join(home, ".cicache", "local"),
			KeyPrefix: "cicache",
		},
		Project: ProjectConfig{
			WorkingDir: ".",
		},
		Watcher: WatcherConfig{
			Enabled:          false,
			DebounceDuration: "2s",
			PreWarm:          true,
		},
	}
}
