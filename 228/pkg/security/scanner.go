package security

import (
	"context"
	"encoding/json"
	"fmt"
	"os"
	"os/exec"
	"path/filepath"
	"strings"
	"sync"
	"time"
)

type Vulnerability struct {
	ID              string   `json:"id"`
	Severity        Severity `json:"severity"`
	Title           string   `json:"title"`
	Description     string   `json:"description"`
	PackageName     string   `json:"package_name"`
	InstalledVersion string  `json:"installed_version"`
	FixedVersion    string   `json:"fixed_version"`
	CVSSScore       float64  `json:"cvss_score"`
	References      []string `json:"references"`
	Target          string   `json:"target"`
}

type Severity string

const (
	SeverityCritical Severity = "CRITICAL"
	SeverityHigh     Severity = "HIGH"
	SeverityMedium   Severity = "MEDIUM"
	SeverityLow      Severity = "LOW"
	SeverityUnknown  Severity = "UNKNOWN"
)

type ScanResult struct {
	ImageName       string
	StartTime       time.Time
	EndTime         time.Time
	Vulnerabilities []*Vulnerability
	Summary         *ScanSummary
	Error           error
	Format          ScanFormat
}

type ScanSummary struct {
	CriticalCount int `json:"critical"`
	HighCount     int `json:"high"`
	MediumCount   int `json:"medium"`
	LowCount      int `json:"low"`
	UnknownCount  int `json:"unknown"`
	TotalCount    int `json:"total"`
	FixableCount  int `json:"fixable"`
}

type ScanFormat string

const (
	FormatJSON   ScanFormat = "json"
	FormatTable  ScanFormat = "table"
	FormatSarif  ScanFormat = "sarif"
)

type ScanConfig struct {
	ScannerType    string
	TrivyPath      string
	DockerPath     string
	Format         ScanFormat
	OutputFile     string
	SeverityFilter []Severity
	Timeout        time.Duration
	IgnoreUnfixed  bool
	ExitOnError    bool
}

type SecurityScanner struct {
	config     *ScanConfig
	scannerPath string
	mu         sync.Mutex
}

type ScanReport struct {
	ScanMetadata  *ScanConfig     `json:"scan_metadata"`
	Results       *ScanResult     `json:"results"`
	GeneratedAt   time.Time       `json:"generated_at"`
	Recommendations []string      `json:"recommendations"`
}

func DefaultScanConfig() *ScanConfig {
	return &ScanConfig{
		ScannerType: "trivy",
		TrivyPath:   "trivy",
		DockerPath:  "docker",
		Format:      FormatTable,
		Timeout:     10 * time.Minute,
		SeverityFilter: []Severity{
			SeverityCritical,
			SeverityHigh,
			SeverityMedium,
		},
		IgnoreUnfixed: false,
		ExitOnError:   true,
	}
}

func NewSecurityScanner(config *ScanConfig) (*SecurityScanner, error) {
	if config == nil {
		config = DefaultScanConfig()
	}

	scannerPath, err := exec.LookPath(config.TrivyPath)
	if err != nil {
		return nil, fmt.Errorf("trivy not found: %w", err)
	}

	return &SecurityScanner{
		config:     config,
		scannerPath: scannerPath,
	}, nil
}

func (ss *SecurityScanner) ScanImage(ctx context.Context, imageName string) (*ScanResult, error) {
	result := &ScanResult{
		ImageName: imageName,
		StartTime: time.Now(),
		Format:    ss.config.Format,
	}

	args := []string{
		"image",
		"--format", "json",
		"--quiet",
	}

	if len(ss.config.SeverityFilter) > 0 {
		severities := make([]string, len(ss.config.SeverityFilter))
		for i, s := range ss.config.SeverityFilter {
			severities[i] = string(s)
		}
		args = append(args, "--severity", strings.Join(severities, ","))
	}

	if ss.config.IgnoreUnfixed {
		args = append(args, "--ignore-unfixed")
	}

	args = append(args, imageName)

	cmdCtx, cancel := context.WithTimeout(ctx, ss.config.Timeout)
	defer cancel()

	cmd := exec.CommandContext(cmdCtx, ss.scannerPath, args...)
	output, err := cmd.CombinedOutput()
	if err != nil {
		result.Error = fmt.Errorf("scan failed: %w, output: %s", err, string(output))
		return result, result.Error
	}

	result.EndTime = time.Now()

	vulns, err := ss.parseTrivyOutput(output)
	if err != nil {
		result.Error = err
		return result, err
	}

	result.Vulnerabilities = vulns
	result.Summary = ss.generateSummary(vulns)

	return result, nil
}

func (ss *SecurityScanner) parseTrivyOutput(data []byte) ([]*Vulnerability, error) {
	var trivyOutput struct {
		Results []struct {
			Target          string `json:"Target"`
			Vulnerabilities []struct {
				VulnerabilityID  string  `json:"VulnerabilityID"`
				Severity         string  `json:"Severity"`
				Title            string  `json:"Title"`
				Description      string  `json:"Description"`
				PkgName          string  `json:"PkgName"`
				InstalledVersion string  `json:"InstalledVersion"`
				FixedVersion     string  `json:"FixedVersion"`
				CVSSScore        float64 `json:"CVSSScore"`
				References       []string `json:"References"`
			} `json:"Vulnerabilities"`
		} `json:"Results"`
	}

	if err := json.Unmarshal(data, &trivyOutput); err != nil {
		return nil, fmt.Errorf("failed to parse trivy output: %w", err)
	}

	var vulns []*Vulnerability
	for _, res := range trivyOutput.Results {
		for _, v := range res.Vulnerabilities {
			vulns = append(vulns, &Vulnerability{
				ID:               v.VulnerabilityID,
				Severity:         Severity(strings.ToUpper(v.Severity)),
				Title:            v.Title,
				Description:      v.Description,
				PackageName:      v.PkgName,
				InstalledVersion: v.InstalledVersion,
				FixedVersion:     v.FixedVersion,
				CVSSScore:        v.CVSSScore,
				References:       v.References,
				Target:           res.Target,
			})
		}
	}

	return vulns, nil
}

func (ss *SecurityScanner) generateSummary(vulns []*Vulnerability) *ScanSummary {
	summary := &ScanSummary{}
	for _, v := range vulns {
		summary.TotalCount++
		if v.FixedVersion != "" {
			summary.FixableCount++
		}
		switch v.Severity {
		case SeverityCritical:
			summary.CriticalCount++
		case SeverityHigh:
			summary.HighCount++
		case SeverityMedium:
			summary.MediumCount++
		case SeverityLow:
			summary.LowCount++
		default:
			summary.UnknownCount++
		}
	}
	return summary
}

func (ss *SecurityScanner) GenerateReport(result *ScanResult) (*ScanReport, error) {
	report := &ScanReport{
		ScanMetadata:  ss.config,
		Results:       result,
		GeneratedAt:   time.Now(),
		Recommendations: make([]string, 0),
	}

	report.Recommendations = ss.generateRecommendations(result)

	return report, nil
}

func (ss *SecurityScanner) generateRecommendations(result *ScanResult) []string {
	var recs []string

	if result.Summary == nil {
		return recs
	}

	if result.Summary.CriticalCount > 0 {
		recs = append(recs,
			fmt.Sprintf("🔴 发现 %d 个严重漏洞，建议立即修复", result.Summary.CriticalCount))
	}

	if result.Summary.HighCount > 0 {
		recs = append(recs,
			fmt.Sprintf("🟠 发现 %d 个高危漏洞，建议安排修复", result.Summary.HighCount))
	}

	if result.Summary.MediumCount > 0 {
		recs = append(recs,
			fmt.Sprintf("🟡 发现 %d 个中危漏洞", result.Summary.MediumCount))
	}

	if result.Summary.FixableCount > 0 {
		recs = append(recs,
			fmt.Sprintf("💡 有 %d 个漏洞已有修复版本，建议升级相关包", result.Summary.FixableCount))
	}

	if result.Summary.TotalCount == 0 {
		recs = append(recs, "✅ 未发现漏洞")
	}

	criticalVulns := make([]*Vulnerability, 0)
	for _, v := range result.Vulnerabilities {
		if v.Severity == SeverityCritical {
			criticalVulns = append(criticalVulns, v)
		}
	}
	if len(criticalVulns) > 0 {
		recs = append(recs, "严重漏洞示例:")
		for i, v := range criticalVulns {
			if i >= 3 {
				break
			}
			recs = append(recs,
				fmt.Sprintf("  - %s (%s) in %s", v.ID, v.Title, v.PackageName))
		}
	}

	return recs
}

func (result *ScanResult) Print() {
	fmt.Printf("\n=== 镜像安全扫描报告: %s ===\n", result.ImageName)
	fmt.Printf("扫描时间: %s\n", result.EndTime.Sub(result.StartTime).Round(time.Second))
	fmt.Printf("结束时间: %s\n\n", result.EndTime.Format("2006-01-02 15:04:05"))

	if result.Error != nil {
		fmt.Printf("❌ 扫描错误: %v\n", result.Error)
		return
	}

	if result.Summary == nil {
		fmt.Println("无扫描结果")
		return
	}

	fmt.Println("--- 漏洞统计 ---")
	fmt.Printf("🔴 严重: %d\n", result.Summary.CriticalCount)
	fmt.Printf("🟠 高危: %d\n", result.Summary.HighCount)
	fmt.Printf("🟡 中危: %d\n", result.Summary.MediumCount)
	fmt.Printf("🟢 低危: %d\n", result.Summary.LowCount)
	fmt.Printf("⚪ 未知: %d\n", result.Summary.UnknownCount)
	fmt.Printf("📊 总计: %d\n", result.Summary.TotalCount)
	fmt.Printf("🔧 可修复: %d\n\n", result.Summary.FixableCount)

	if result.Summary.TotalCount > 0 {
		fmt.Println("--- 漏洞详情 (Top 10) ---")
		sortedVulns := make([]*Vulnerability, len(result.Vulnerabilities))
		copy(sortedVulns, result.Vulnerabilities)
		sortVulnerabilitiesBySeverity(sortedVulns)

		for i, v := range sortedVulns {
			if i >= 10 {
				fmt.Printf("  ... 还有 %d 个漏洞\n", len(sortedVulns)-10)
				break
			}

			var icon string
			switch v.Severity {
			case SeverityCritical:
				icon = "🔴"
			case SeverityHigh:
				icon = "🟠"
			case SeverityMedium:
				icon = "🟡"
			case SeverityLow:
				icon = "🟢"
			default:
				icon = "⚪"
			}

			fixed := "无"
			if v.FixedVersion != "" {
				fixed = v.FixedVersion
			}

			fmt.Printf("\n  %s %s\n", icon, v.ID)
			fmt.Printf("     包: %s (%s -> %s)\n", v.PackageName, v.InstalledVersion, fixed)
			fmt.Printf("     描述: %s\n", truncateString(v.Title, 80))
			if v.CVSSScore > 0 {
				fmt.Printf("     CVSS: %.1f\n", v.CVSSScore)
			}
		}
	}

	fmt.Println("\n--- 建议 ---")
	recs := GenerateRecommendations(result)
	for _, rec := range recs {
		fmt.Printf("  %s\n", rec)
	}
}

func GenerateRecommendations(result *ScanResult) []string {
	var recs []string

	if result.Summary == nil {
		return recs
	}

	if result.Summary.CriticalCount > 0 {
		recs = append(recs,
			fmt.Sprintf("🔴 发现 %d 个严重漏洞，建议立即修复", result.Summary.CriticalCount))
	}

	if result.Summary.HighCount > 0 {
		recs = append(recs,
			fmt.Sprintf("🟠 发现 %d 个高危漏洞，建议安排修复", result.Summary.HighCount))
	}

	if result.Summary.MediumCount > 0 {
		recs = append(recs,
			fmt.Sprintf("🟡 发现 %d 个中危漏洞", result.Summary.MediumCount))
	}

	if result.Summary.FixableCount > 0 {
		recs = append(recs,
			fmt.Sprintf("💡 有 %d 个漏洞已有修复版本，建议升级相关包", result.Summary.FixableCount))
	}

	if result.Summary.TotalCount == 0 {
		recs = append(recs, "✅ 未发现漏洞")
	}

	criticalVulns := make([]*Vulnerability, 0)
	for _, v := range result.Vulnerabilities {
		if v.Severity == SeverityCritical {
			criticalVulns = append(criticalVulns, v)
		}
	}
	if len(criticalVulns) > 0 {
		recs = append(recs, "严重漏洞示例:")
		for i, v := range criticalVulns {
			if i >= 3 {
				break
			}
			recs = append(recs,
				fmt.Sprintf("  - %s (%s) in %s", v.ID, v.Title, v.PackageName))
		}
	}

	return recs
}

func (ss *SecurityScanner) SaveReport(report *ScanReport, outputPath string) error {
	var data []byte
	var err error

	switch report.ScanMetadata.Format {
	case FormatJSON:
		data, err = json.MarshalIndent(report, "", "  ")
	case FormatSarif:
		data, err = ss.generateSARIF(report)
	default:
		return fmt.Errorf("unsupported format: %s", report.ScanMetadata.Format)
	}

	if err != nil {
		return err
	}

	dir := filepath.Dir(outputPath)
	if dir != "." && dir != "" {
		if err := os.MkdirAll(dir, 0755); err != nil {
			return err
		}
	}

	return os.WriteFile(outputPath, data, 0644)
}

func (ss *SecurityScanner) generateSARIF(report *ScanReport) ([]byte, error) {
	sarif := map[string]interface{}{
		"$schema": "https://json.schemastore.org/sarif-2.1.0.json",
		"version": "2.1.0",
		"runs": []map[string]interface{}{
			{
				"tool": map[string]interface{}{
					"driver": map[string]interface{}{
						"name":         "Trivy",
						"informationUri": "https://aquasecurity.github.io/trivy/",
						"rules":        ss.generateSARIFRules(report.Results.Vulnerabilities),
					},
				},
				"results": ss.generateSARIFResults(report.Results.Vulnerabilities),
			},
		},
	}

	return json.MarshalIndent(sarif, "", "  ")
}

func (ss *SecurityScanner) generateSARIFRules(vulns []*Vulnerability) []map[string]interface{} {
	rules := make([]map[string]interface{}, 0)
	seen := make(map[string]bool)

	for _, v := range vulns {
		if seen[v.ID] {
			continue
		}
		seen[v.ID] = true

		rules = append(rules, map[string]interface{}{
			"id": v.ID,
			"shortDescription": map[string]interface{}{
				"text": v.Title,
			},
			"fullDescription": map[string]interface{}{
				"text": v.Description,
			},
			"defaultConfiguration": map[string]interface{}{
				"level": severityToSARIFLevel(v.Severity),
			},
			"help": map[string]interface{}{
				"text": fmt.Sprintf("Package: %s, Fixed: %s", v.PackageName, v.FixedVersion),
			},
		})
	}

	return rules
}

func (ss *SecurityScanner) generateSARIFResults(vulns []*Vulnerability) []map[string]interface{} {
	results := make([]map[string]interface{}, 0)

	for _, v := range vulns {
		results = append(results, map[string]interface{}{
			"ruleId":    v.ID,
			"level":     severityToSARIFLevel(v.Severity),
			"message": map[string]interface{}{
				"text": fmt.Sprintf("%s in %s (%s)", v.Title, v.PackageName, v.InstalledVersion),
			},
			"locations": []map[string]interface{}{
				{
					"physicalLocation": map[string]interface{}{
						"artifactLocation": map[string]interface{}{
							"uri": v.Target,
						},
					},
				},
			},
		})
	}

	return results
}

func severityToSARIFLevel(s Severity) string {
	switch s {
	case SeverityCritical, SeverityHigh:
		return "error"
	case SeverityMedium:
		return "warning"
	case SeverityLow:
		return "note"
	default:
		return "none"
	}
}

func sortVulnerabilitiesBySeverity(vulns []*Vulnerability) {
	severityOrder := map[Severity]int{
		SeverityCritical: 0,
		SeverityHigh:     1,
		SeverityMedium:   2,
		SeverityLow:      3,
		SeverityUnknown:  4,
	}

	for i := 0; i < len(vulns); i++ {
		for j := i + 1; j < len(vulns); j++ {
			if severityOrder[vulns[i].Severity] > severityOrder[vulns[j].Severity] {
				vulns[i], vulns[j] = vulns[j], vulns[i]
			}
		}
	}
}

func truncateString(s string, maxLen int) string {
	if len(s) <= maxLen {
		return s
	}
	return s[:maxLen-3] + "..."
}

func (ss *SecurityScanner) CheckScannerAvailable() bool {
	_, err := exec.LookPath(ss.scannerPath)
	return err == nil
}

func (ss *SecurityScanner) InstallScanner(ctx context.Context) error {
	fmt.Println("正在安装 Trivy 安全扫描器...")
	
	if _, err := exec.LookPath("brew"); err == nil {
		cmd := exec.CommandContext(ctx, "brew", "install", "trivy")
		cmd.Stdout = os.Stdout
		cmd.Stderr = os.Stderr
		if err := cmd.Run(); err == nil {
			return nil
		}
	}

	if _, err := exec.LookPath("apt-get"); err == nil {
		cmds := [][]string{
			{"apt-get", "update"},
			{"apt-get", "install", "-y", "wget", "apt-transport-https", "gnupg"},
			{"wget", "-qO", "-", "https://aquasecurity.github.io/trivy-repo/deb/public.key", "|", "apt-key", "add", "-"},
			{"echo", "deb", "https://aquasecurity.github.io/trivy-repo/deb", "generic", "main", "|", "tee", "-a", "/etc/apt/sources.list.d/trivy.list"},
			{"apt-get", "update"},
			{"apt-get", "install", "-y", "trivy"},
		}
		for _, args := range cmds {
			cmd := exec.CommandContext(ctx, args[0], args[1:]...)
			cmd.Stdout = os.Stdout
			cmd.Stderr = os.Stderr
			if err := cmd.Run(); err != nil {
				return fmt.Errorf("failed to run %v: %w", args, err)
			}
		}
		return nil
	}

	return fmt.Errorf("please install trivy manually: https://aquasecurity.github.io/trivy/latest/getting-started/installation/")
}
