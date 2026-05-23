package config

import (
	"fmt"
	"io"
	"os"
	"path/filepath"
	"strings"
	"time"

	"container-scanner/pkg/scanner"
	"gopkg.in/yaml.v3"
)

type ThresholdAction string

const (
	ActionBlock  ThresholdAction = "block"
	ActionWarn   ThresholdAction = "warn"
	ActionAllow  ThresholdAction = "allow"
)

type SeverityThreshold struct {
	Action   ThresholdAction `yaml:"action"`
	MaxCount int             `yaml:"max_count"`
}

type CategoryThresholds struct {
	Critical SeverityThreshold `yaml:"critical"`
	High     SeverityThreshold `yaml:"high"`
	Medium   SeverityThreshold `yaml:"medium"`
	Low      SeverityThreshold `yaml:"low"`
}

type ScanThresholds struct {
	Vulnerabilities   CategoryThresholds `yaml:"vulnerabilities"`
	Secrets           CategoryThresholds `yaml:"secrets"`
	Misconfigurations CategoryThresholds `yaml:"misconfigurations"`
}

type DatabaseConfig struct {
	CacheDir      string `yaml:"cache_dir"`
	AutoUpdate    bool   `yaml:"auto_update"`
	UpdateHour    int    `yaml:"update_hour"`
	UpdateMinute  int    `yaml:"update_minute"`
	SkipUpdate    bool   `yaml:"skip_update"`
}

type SecretWhitelist struct {
	Rules       []string `yaml:"rules"`
	Files       []string `yaml:"files"`
	Paths       []string `yaml:"paths"`
	MatchValues []string `yaml:"match_values"`
}

type Config struct {
	Image          string            `yaml:"image"`
	Output         string            `yaml:"output"`
	Format         string            `yaml:"format"`
	Severities     []string          `yaml:"severities"`
	Scanners       []string          `yaml:"scanners"`
	Thresholds     ScanThresholds    `yaml:"thresholds"`
	Database       DatabaseConfig    `yaml:"database"`
	SecretWhitelist SecretWhitelist  `yaml:"secret_whitelist"`
	FailOnError    bool              `yaml:"fail_on_error"`
}

type ThresholdViolation struct {
	Category   string
	Severity   string
	Actual     int
	Threshold  int
	Action     ThresholdAction
	Message    string
}

type ThresholdCheckResult struct {
	Passed     bool
	Blocked    []ThresholdViolation
	Warning    []ThresholdViolation
}

func DefaultConfig() Config {
	homeDir, _ := os.UserHomeDir()
	cacheDir := filepath.Join(homeDir, ".trivy", "db")

	return Config{
		Output:     "scan-report.html",
		Format:     "html",
		Severities: []string{"CRITICAL", "HIGH", "MEDIUM", "LOW"},
		Scanners:   []string{"vuln", "secret", "config"},
		Thresholds: ScanThresholds{
			Vulnerabilities: CategoryThresholds{
				Critical: SeverityThreshold{Action: ActionBlock, MaxCount: 0},
				High:     SeverityThreshold{Action: ActionBlock, MaxCount: 0},
				Medium:   SeverityThreshold{Action: ActionWarn, MaxCount: -1},
				Low:      SeverityThreshold{Action: ActionAllow, MaxCount: -1},
			},
			Secrets: CategoryThresholds{
				Critical: SeverityThreshold{Action: ActionBlock, MaxCount: 0},
				High:     SeverityThreshold{Action: ActionBlock, MaxCount: 0},
				Medium:   SeverityThreshold{Action: ActionWarn, MaxCount: -1},
				Low:      SeverityThreshold{Action: ActionAllow, MaxCount: -1},
			},
			Misconfigurations: CategoryThresholds{
				Critical: SeverityThreshold{Action: ActionBlock, MaxCount: 0},
				High:     SeverityThreshold{Action: ActionBlock, MaxCount: 0},
				Medium:   SeverityThreshold{Action: ActionWarn, MaxCount: -1},
				Low:      SeverityThreshold{Action: ActionAllow, MaxCount: -1},
			},
		},
		Database: DatabaseConfig{
			CacheDir:     cacheDir,
			AutoUpdate:   true,
			UpdateHour:   2,
			UpdateMinute: 0,
			SkipUpdate:   false,
		},
		SecretWhitelist: SecretWhitelist{
			MatchValues: []string{
				"test",
				"example",
				"placeholder",
				"dummy",
				"fake",
				"sample",
				"xxxx",
				"****",
				"----",
			},
		},
		FailOnError: true,
	}
}

func LoadConfig(path string) (*Config, error) {
	file, err := os.Open(path)
	if err != nil {
		if os.IsNotExist(err) {
			defaultCfg := DefaultConfig()
			return &defaultCfg, nil
		}
		return nil, fmt.Errorf("failed to open config file: %w", err)
	}
	defer file.Close()

	data, err := io.ReadAll(file)
	if err != nil {
		return nil, fmt.Errorf("failed to read config file: %w", err)
	}

	cfg := DefaultConfig()
	if err := yaml.Unmarshal(data, &cfg); err != nil {
		return nil, fmt.Errorf("failed to parse config file: %w", err)
	}

	return &cfg, nil
}

func (c *Config) ShouldUpdateDatabase() bool {
	if c.Database.SkipUpdate {
		return false
	}

	if !c.Database.AutoUpdate {
		return false
	}

	cacheDir := c.Database.CacheDir
	if _, err := os.Stat(cacheDir); os.IsNotExist(err) {
		return true
	}

	metadataFile := filepath.Join(cacheDir, "metadata.json")
	info, err := os.Stat(metadataFile)
	if err != nil {
		return true
	}

	now := time.Now()
	lastUpdate := info.ModTime()

	if now.Sub(lastUpdate).Hours() >= 24 {
		return true
	}

	nextUpdate := time.Date(now.Year(), now.Month(), now.Day(), 
		c.Database.UpdateHour, c.Database.UpdateMinute, 0, 0, now.Location())
	
	if nextUpdate.Before(lastUpdate) {
		nextUpdate = nextUpdate.Add(24 * time.Hour)
	}

	return now.After(nextUpdate)
}

func (c *Config) IsSecretWhitelisted(secret scanner.Secret) bool {
	for _, rule := range c.SecretWhitelist.Rules {
		if strings.EqualFold(secret.RuleID, rule) {
			return true
		}
	}

	for _, file := range c.SecretWhitelist.Files {
		if strings.EqualFold(filepath.Base(secret.FilePath), file) {
			return true
		}
	}

	for _, path := range c.SecretWhitelist.Paths {
		if strings.Contains(secret.FilePath, path) {
			return true
		}
	}

	for _, value := range c.SecretWhitelist.MatchValues {
		if strings.Contains(strings.ToLower(secret.Match), strings.ToLower(value)) {
			return true
		}
	}

	return false
}

func (c *Config) FilterWhitelistedSecrets(report *scanner.ScanReport) *scanner.ScanReport {
	filtered := &scanner.ScanReport{
		SchemaVersion: report.SchemaVersion,
		Results:       make([]scanner.ScanResult, len(report.Results)),
	}

	for i, result := range report.Results {
		filteredResult := scanner.ScanResult{
			Target:            result.Target,
			Vulnerabilities:   result.Vulnerabilities,
			Misconfigurations: result.Misconfigurations,
		}

		for _, secret := range result.Secrets {
			if !c.IsSecretWhitelisted(secret) {
				filteredResult.Secrets = append(filteredResult.Secrets, secret)
			}
		}

		filtered.Results[i] = filteredResult
	}

	return filtered
}

func (c *Config) CheckThresholds(report *scanner.ScanReport) ThresholdCheckResult {
	var blocked []ThresholdViolation
	var warnings []ThresholdViolation

	checkSeverity := func(category string, actual int, threshold SeverityThreshold, severity string) {
		if threshold.Action == ActionAllow {
			return
		}

		if threshold.MaxCount >= 0 && actual > threshold.MaxCount {
			violation := ThresholdViolation{
				Category:  category,
				Severity:  severity,
				Actual:    actual,
				Threshold: threshold.MaxCount,
				Action:    threshold.Action,
				Message: fmt.Sprintf("%s: %d %s issues exceed threshold of %d",
					category, actual, severity, threshold.MaxCount),
			}

			if threshold.Action == ActionBlock {
				blocked = append(blocked, violation)
			} else if threshold.Action == ActionWarn {
				warnings = append(warnings, violation)
			}
		}
	}

	vulnCfg := c.Thresholds.Vulnerabilities
	checkSeverity("Vulnerabilities",
		report.GetVulnerabilityCountBySeverity(scanner.SeverityCritical),
		vulnCfg.Critical, "CRITICAL")
	checkSeverity("Vulnerabilities",
		report.GetVulnerabilityCountBySeverity(scanner.SeverityHigh),
		vulnCfg.High, "HIGH")
	checkSeverity("Vulnerabilities",
		report.GetVulnerabilityCountBySeverity(scanner.SeverityMedium),
		vulnCfg.Medium, "MEDIUM")
	checkSeverity("Vulnerabilities",
		report.GetVulnerabilityCountBySeverity(scanner.SeverityLow),
		vulnCfg.Low, "LOW")

	secretCfg := c.Thresholds.Secrets
	checkSeverity("Secrets",
		report.GetSecretCountBySeverity(scanner.SeverityCritical),
		secretCfg.Critical, "CRITICAL")
	checkSeverity("Secrets",
		report.GetSecretCountBySeverity(scanner.SeverityHigh),
		secretCfg.High, "HIGH")
	checkSeverity("Secrets",
		report.GetSecretCountBySeverity(scanner.SeverityMedium),
		secretCfg.Medium, "MEDIUM")
	checkSeverity("Secrets",
		report.GetSecretCountBySeverity(scanner.SeverityLow),
		secretCfg.Low, "LOW")

	misconfigCfg := c.Thresholds.Misconfigurations
	checkSeverity("Misconfigurations",
		report.GetMisconfigurationCountBySeverity(scanner.SeverityCritical),
		misconfigCfg.Critical, "CRITICAL")
	checkSeverity("Misconfigurations",
		report.GetMisconfigurationCountBySeverity(scanner.SeverityHigh),
		misconfigCfg.High, "HIGH")
	checkSeverity("Misconfigurations",
		report.GetMisconfigurationCountBySeverity(scanner.SeverityMedium),
		misconfigCfg.Medium, "MEDIUM")
	checkSeverity("Misconfigurations",
		report.GetMisconfigurationCountBySeverity(scanner.SeverityLow),
		misconfigCfg.Low, "LOW")

	return ThresholdCheckResult{
		Passed:  len(blocked) == 0,
		Blocked: blocked,
		Warning: warnings,
	}
}

func (c *Config) ToScanConfig(imageName string) scanner.ScanConfig {
	severities := make([]scanner.Severity, len(c.Severities))
	for i, s := range c.Severities {
		severities[i] = scanner.Severity(s)
	}

	return scanner.ScanConfig{
		ImageName:  imageName,
		Severities: severities,
		Scanners:   c.Scanners,
		Format:     c.Format,
		OutputFile: c.Output,
		CacheDir:   c.Database.CacheDir,
		SkipUpdate: c.Database.SkipUpdate,
	}
}
