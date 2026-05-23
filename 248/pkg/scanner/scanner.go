package scanner

import (
	"bytes"
	"encoding/json"
	"fmt"
	"os"
	"os/exec"
	"strings"
)

type ScanType string

const (
	ScanTypeVuln      ScanType = "vuln"
	ScanTypeSecret    ScanType = "secret"
	ScanTypeConfig    ScanType = "config"
	ScanTypeAll       ScanType = "all"
)

type Severity string

const (
	SeverityCritical Severity = "CRITICAL"
	SeverityHigh     Severity = "HIGH"
	SeverityMedium   Severity = "MEDIUM"
	SeverityLow      Severity = "LOW"
	SeverityUnknown  Severity = "UNKNOWN"
)

type ScanConfig struct {
	ImageName    string
	ScanTypes    []ScanType
	Severities   []Severity
	Scanners     []string
	Format       string
	OutputFile   string
	Timeout      int
	CacheDir     string
	SkipUpdate   bool
}

type Vulnerability struct {
	VulnerabilityID  string   `json:"VulnerabilityID"`
	PkgName          string   `json:"PkgName"`
	InstalledVersion string   `json:"InstalledVersion"`
	FixedVersion     string   `json:"FixedVersion"`
	Severity         string   `json:"Severity"`
	Title            string   `json:"Title"`
	Description      string   `json:"Description"`
	References       []string `json:"References"`
}

type Secret struct {
	RuleID    string `json:"RuleID"`
	Category  string `json:"Category"`
	Severity  string `json:"Severity"`
	Title     string `json:"Title"`
	FilePath  string `json:"FilePath"`
	StartLine int    `json:"StartLine"`
	Match     string `json:"Match"`
}

type Misconfiguration struct {
	Type        string `json:"Type"`
	ID          string `json:"ID"`
	Title       string `json:"Title"`
	Description string `json:"Description"`
	Severity    string `json:"Severity"`
	Resolution  string `json:"Resolution"`
}

type ScanResult struct {
	Target              string             `json:"Target"`
	Vulnerabilities     []Vulnerability    `json:"Vulnerabilities"`
	Secrets             []Secret           `json:"Secrets"`
	Misconfigurations   []Misconfiguration `json:"Misconfigurations"`
}

type ScanReport struct {
	SchemaVersion int          `json:"SchemaVersion"`
	Results       []ScanResult `json:"Results"`
}

type Scanner struct {
	trivyPath string
}

func NewScanner() (*Scanner, error) {
	path, err := exec.LookPath("trivy")
	if err != nil {
		return nil, fmt.Errorf("trivy not found in PATH: %w", err)
	}
	return &Scanner{trivyPath: path}, nil
}

func (s *Scanner) TrivyPath() string {
	return s.trivyPath
}

func (s *Scanner) Scan(config ScanConfig) (*ScanReport, error) {
	args := s.buildArgs(config)
	
	var stdout, stderr bytes.Buffer
	cmd := exec.Command(s.trivyPath, args...)
	cmd.Stdout = &stdout
	cmd.Stderr = &stderr
	cmd.Env = append(os.Environ(), "TRIVY_FORMAT=json")
	
	err := cmd.Run()
	if err != nil {
		return nil, fmt.Errorf("trivy scan failed: %w, stderr: %s", err, stderr.String())
	}
	
	var report ScanReport
	if err := json.Unmarshal(stdout.Bytes(), &report); err != nil {
		return nil, fmt.Errorf("failed to parse scan result: %w", err)
	}
	
	return &report, nil
}

func (s *Scanner) buildArgs(config ScanConfig) []string {
	args := []string{"image"}
	
	if config.CacheDir != "" {
		args = append(args, "--cache-dir", config.CacheDir)
	}
	
	if config.SkipUpdate {
		args = append(args, "--skip-db-update")
	}
	
	if len(config.Scanners) > 0 {
		args = append(args, "--scanners", strings.Join(config.Scanners, ","))
	} else {
		args = append(args, "--scanners", "vuln,secret,config")
	}
	
	if len(config.Severities) > 0 {
		severities := make([]string, len(config.Severities))
		for i, sev := range config.Severities {
			severities[i] = string(sev)
		}
		args = append(args, "--severity", strings.Join(severities, ","))
	}
	
	args = append(args, "--format", "json")
	args = append(args, config.ImageName)
	
	return args
}

func (s *Scanner) UpdateDatabase(cacheDir string) error {
	args := []string{"image", "--download-db-only"}
	if cacheDir != "" {
		args = append(args, "--cache-dir", cacheDir)
	}
	
	cmd := exec.Command(s.trivyPath, args...)
	var stderr bytes.Buffer
	cmd.Stderr = &stderr
	
	err := cmd.Run()
	if err != nil {
		return fmt.Errorf("failed to update database: %w, stderr: %s", err, stderr.String())
	}
	
	return nil
}

func (s *Scanner) ScanLocalImage(imageName string) (*ScanReport, error) {
	return s.Scan(ScanConfig{
		ImageName: imageName,
		Scanners:  []string{"vuln", "secret", "config"},
	})
}

func (s *Scanner) ScanRemoteImage(imageName string) (*ScanReport, error) {
	return s.Scan(ScanConfig{
		ImageName: imageName,
		Scanners:  []string{"vuln", "secret", "config"},
	})
}

func (r *ScanReport) GetVulnerabilityCountBySeverity(severity Severity) int {
	count := 0
	for _, result := range r.Results {
		for _, vuln := range result.Vulnerabilities {
			if strings.EqualFold(vuln.Severity, string(severity)) {
				count++
			}
		}
	}
	return count
}

func (r *ScanReport) GetSecretCountBySeverity(severity Severity) int {
	count := 0
	for _, result := range r.Results {
		for _, secret := range result.Secrets {
			if strings.EqualFold(secret.Severity, string(severity)) {
				count++
			}
		}
	}
	return count
}

func (r *ScanReport) GetMisconfigurationCountBySeverity(severity Severity) int {
	count := 0
	for _, result := range r.Results {
		for _, misconfig := range result.Misconfigurations {
			if strings.EqualFold(misconfig.Severity, string(severity)) {
				count++
			}
		}
	}
	return count
}

func (r *ScanReport) TotalVulnerabilities() int {
	count := 0
	for _, result := range r.Results {
		count += len(result.Vulnerabilities)
	}
	return count
}

func (r *ScanReport) TotalSecrets() int {
	count := 0
	for _, result := range r.Results {
		count += len(result.Secrets)
	}
	return count
}

func (r *ScanReport) TotalMisconfigurations() int {
	count := 0
	for _, result := range r.Results {
		count += len(result.Misconfigurations)
	}
	return count
}

func (r *ScanReport) TotalIssues() int {
	return r.TotalVulnerabilities() + r.TotalSecrets() + r.TotalMisconfigurations()
}

func (r *ScanReport) HasCriticalIssues() bool {
	return r.GetVulnerabilityCountBySeverity(SeverityCritical) > 0 ||
		r.GetSecretCountBySeverity(SeverityCritical) > 0 ||
		r.GetMisconfigurationCountBySeverity(SeverityCritical) > 0
}
