package remediation

import (
	"fmt"
	"os"
	"strings"
	"text/template"

	"container-scanner/pkg/compliance"
	"container-scanner/pkg/scanner"
)

type FixSuggestion struct {
	ID          string
	Type        string
	Severity    string
	Title       string
	Description string
	AutoFix     bool
	Command     string
	Script      string
	Dockerfile  string
}

type FixReport struct {
	TotalSuggestions   int
	AutoFixAvailable   int
	ManualFixRequired  int
	Suggestions        []FixSuggestion
	BySeverity         map[string][]FixSuggestion
}

var autoFixRules = map[string]FixSuggestion{
	"CVE-APT-UPGRADE": {
		Type:       "vulnerability",
		Severity:   "HIGH",
		AutoFix:    true,
		Command:    "apt-get update && apt-get upgrade -y",
		Script:     "#!/bin/bash\napt-get update && apt-get upgrade -y && apt-get clean",
		Dockerfile: "RUN apt-get update && apt-get upgrade -y && apt-get clean",
	},
	"CVE-YUM-UPDATE": {
		Type:       "vulnerability",
		Severity:   "HIGH",
		AutoFix:    true,
		Command:    "yum update -y",
		Script:     "#!/bin/bash\nyum update -y && yum clean all",
		Dockerfile: "RUN yum update -y && yum clean all",
	},
	"CVE-APK-UPGRADE": {
		Type:       "vulnerability",
		Severity:   "HIGH",
		AutoFix:    true,
		Command:    "apk upgrade --no-cache",
		Script:     "#!/bin/bash\napk upgrade --no-cache",
		Dockerfile: "RUN apk upgrade --no-cache",
	},
	"CIS-NONROOT": {
		Type:       "compliance",
		Severity:   "HIGH",
		AutoFix:    true,
		Command:    "useradd -m appuser && su appuser",
		Script:     "#!/bin/bash\nuseradd -m appuser",
		Dockerfile: "RUN useradd -m appuser\nUSER appuser",
	},
	"CIS-HEALTHCHECK": {
		Type:       "compliance",
		Severity:   "LOW",
		AutoFix:    true,
		Command:    "",
		Script:     "",
		Dockerfile: "HEALTHCHECK --interval=30s --timeout=3s CMD curl -f http://localhost/ || exit 1",
	},
}

func GenerateFixReport(vulnReport *scanner.ScanReport, cisResult *compliance.CISBenchmarkResult) *FixReport {
	report := &FixReport{
		Suggestions: make([]FixSuggestion, 0),
		BySeverity:  make(map[string][]FixSuggestion),
	}

	for _, result := range vulnReport.Results {
		for _, vuln := range result.Vulnerabilities {
			if vuln.FixedVersion != "" {
				suggestion := FixSuggestion{
					ID:          vuln.VulnerabilityID,
					Type:        "vulnerability",
					Severity:    vuln.Severity,
					Title:       fmt.Sprintf("升级 %s 到 %s", vuln.PkgName, vuln.FixedVersion),
					Description: vuln.Description,
					AutoFix:     false,
					Command:     generatePackageUpdateCommand(vuln.PkgName, vuln.FixedVersion),
				}
				report.Suggestions = append(report.Suggestions, suggestion)
				report.BySeverity[vuln.Severity] = append(report.BySeverity[vuln.Severity], suggestion)
			}
		}
	}

	if cisResult != nil {
		for _, check := range cisResult.Failed {
			suggestion := FixSuggestion{
				ID:          check.ID,
				Type:        "compliance",
				Severity:    check.Severity,
				Title:       check.Title,
				Description: check.Remediation,
				AutoFix:     canAutoFix(check.ID),
				Command:     check.Remediation,
			}
			
			if rule, ok := autoFixRules[check.ID]; ok {
				suggestion.AutoFix = true
				suggestion.Script = rule.Script
				suggestion.Dockerfile = rule.Dockerfile
				suggestion.Command = rule.Command
				report.AutoFixAvailable++
			} else {
				report.ManualFixRequired++
			}
			
			report.Suggestions = append(report.Suggestions, suggestion)
			report.BySeverity[check.Severity] = append(report.BySeverity[check.Severity], suggestion)
		}
	}

	report.TotalSuggestions = len(report.Suggestions)
	return report
}

func generatePackageUpdateCommand(pkgName, fixedVersion string) string {
	if strings.Contains(pkgName, "lib") || strings.Contains(pkgName, "openssl") {
		return fmt.Sprintf("apt-get install --only-upgrade %s=%s", pkgName, fixedVersion)
	}
	return fmt.Sprintf("请更新 %s 到版本 %s", pkgName, fixedVersion)
}

func canAutoFix(checkID string) bool {
	_, ok := autoFixRules[checkID]
	return ok
}

func (r *FixReport) GetAutoFixSuggestions() []FixSuggestion {
	var autoFixes []FixSuggestion
	for _, s := range r.Suggestions {
		if s.AutoFix {
			autoFixes = append(autoFixes, s)
		}
	}
	return autoFixes
}

func (r *FixReport) GenerateFixScript(outputPath string) error {
	const scriptTemplate = `#!/bin/bash
# 自动修复脚本 - 生成时间: {{.GeneratedAt}}
# 总计: {{.TotalSuggestions}} 个建议, {{.AutoFixAvailable}} 个可自动修复

echo "=============================================="
echo "  容器安全自动修复脚本"
echo "=============================================="

echo ""
echo "[!] 注意: 建议在测试环境先验证此脚本"
echo ""

read -p "是否继续执行修复? (y/N) " -n 1 -r
echo ""
if [[ ! $REPLY =~ ^[Yy]$ ]]
then
    exit 1
fi

echo ""
echo "[*] 开始执行修复..."
echo ""

{{range .AutoFixes}}
# {{.ID}} - {{.Title}}
{{.Script}}
{{end}}

echo ""
echo "[✓] 自动修复完成!"
echo ""
echo "[!] 请重新构建镜像以应用所有修复"
`
	type TemplateData struct {
		GeneratedAt       string
		TotalSuggestions  int
		AutoFixAvailable  int
		AutoFixes         []FixSuggestion
	}

	data := TemplateData{
		GeneratedAt:      "now",
		TotalSuggestions: r.TotalSuggestions,
		AutoFixAvailable: r.AutoFixAvailable,
		AutoFixes:        r.GetAutoFixSuggestions(),
	}

	tmpl, err := template.New("fix-script").Parse(scriptTemplate)
	if err != nil {
		return fmt.Errorf("failed to parse template: %w", err)
	}

	file, err := os.Create(outputPath)
	if err != nil {
		return fmt.Errorf("failed to create script: %w", err)
	}
	defer file.Close()

	if err := tmpl.Execute(file, data); err != nil {
		return fmt.Errorf("failed to generate script: %w", err)
	}

	if err := os.Chmod(outputPath, 0755); err != nil {
		return fmt.Errorf("failed to chmod script: %w", err)
	}

	return nil
}

func (r *FixReport) GenerateDockerfilePatch(outputPath string) error {
	const dockerfileTemplate = `# Dockerfile 修复补丁
# 总计: {{.TotalSuggestions}} 个建议, {{.AutoFixAvailable}} 个可自动修复

# ===== 漏洞修复 =====
# 系统包更新
RUN apt-get update && apt-get upgrade -y && apt-get clean

# ===== 合规修复 =====
{{range .AutoFixes}}
# {{.ID}} - {{.Title}}
{{.Dockerfile}}
{{end}}

# ===== 注意事项 =====
# 1. 请根据实际基础镜像选择适当的包管理器 (apt/yum/apk)
# 2. HEALTHCHECK 命令需要根据实际应用调整
# 3. USER 指令可能需要调整权限配置
`
	type TemplateData struct {
		TotalSuggestions int
		AutoFixAvailable int
		AutoFixes        []FixSuggestion
	}

	data := TemplateData{
		TotalSuggestions: r.TotalSuggestions,
		AutoFixAvailable: r.AutoFixAvailable,
		AutoFixes:        r.GetAutoFixSuggestions(),
	}

	tmpl, err := template.New("dockerfile").Parse(dockerfileTemplate)
	if err != nil {
		return fmt.Errorf("failed to parse template: %w", err)
	}

	file, err := os.Create(outputPath)
	if err != nil {
		return fmt.Errorf("failed to create patch: %w", err)
	}
	defer file.Close()

	if err := tmpl.Execute(file, data); err != nil {
		return fmt.Errorf("failed to generate patch: %w", err)
	}

	return nil
}

func (r *FixReport) Summary() string {
	var sb strings.Builder
	sb.WriteString(fmt.Sprintf("\n修复建议汇总:\n"))
	sb.WriteString(fmt.Sprintf("  总计建议: %d\n", r.TotalSuggestions))
	sb.WriteString(fmt.Sprintf("  可自动修复: %d\n", r.AutoFixAvailable))
	sb.WriteString(fmt.Sprintf("  需要手动修复: %d\n", r.ManualFixRequired))
	
	for _, severity := range []string{"CRITICAL", "HIGH", "MEDIUM", "LOW"} {
		if items, ok := r.BySeverity[severity]; ok && len(items) > 0 {
			sb.WriteString(fmt.Sprintf("  %s: %d\n", severity, len(items)))
		}
	}
	
	return sb.String()
}
