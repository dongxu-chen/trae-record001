package compliance

import (
	"encoding/json"
	"fmt"
	"os/exec"
	"strings"
)

type CISCheck struct {
	ID          string `json:"id"`
	Title       string `json:"title"`
	Description string `json:"description"`
	Severity    string `json:"severity"`
	Status      string `json:"status"`
	Rationale   string `json:"rationale"`
	Audit       string `json:"audit"`
	Remediation string `json:"remediation"`
}

type CISBenchmarkResult struct {
	Passed      []CISCheck `json:"passed"`
	Failed      []CISCheck `json:"failed"`
	TotalChecks int        `json:"total_checks"`
	PassCount   int        `json:"pass_count"`
	FailCount   int        `json:"fail_count"`
}

type CISBenchmark struct {
	trivyPath string
}

func NewCISBenchmark(trivyPath string) *CISBenchmark {
	return &CISBenchmark{trivyPath: trivyPath}
}

func (c *CISBenchmark) Run(imageName string) (*CISBenchmarkResult, error) {
	cmd := exec.Command(c.trivyPath, "image", "--scanners", "misconfig", 
		"--misconfig-scanners", "dockerfile", imageName)
	
	output, err := cmd.Output()
	if err != nil {
		return nil, fmt.Errorf("failed to run CIS benchmark: %w", err)
	}

	result := &CISBenchmarkResult{
		Passed:      make([]CISCheck, 0),
		Failed:      make([]CISCheck, 0),
		TotalChecks: len(cisChecks),
	}

	var misconfigs struct {
		Results []struct {
			Misconfigurations []struct {
				ID          string `json:"ID"`
				Title       string `json:"Title"`
				Description string `json:"Description"`
				Severity    string `json:"Severity"`
				Resolution  string `json:"Resolution"`
			} `json:"Misconfigurations"`
		} `json:"Results"`
	}

	if err := json.Unmarshal(output, &misconfigs); err != nil {
		return result, nil
	}

	for _, check := range cisChecks {
		isPassed := true
		for _, r := range misconfigs.Results {
			for _, m := range r.Misconfigurations {
				if strings.Contains(m.ID, check.ID) {
					isPassed = false
					check.Status = "FAIL"
					check.Severity = m.Severity
					check.Remediation = m.Resolution
					result.Failed = append(result.Failed, check)
					result.FailCount++
					break
				}
			}
		}
		if isPassed {
			check.Status = "PASS"
			result.Passed = append(result.Passed, check)
			result.PassCount++
		}
	}

	return result, nil
}

func (c *CISBenchmark) RunCustom(imageName string, customChecks []CISCheck) (*CISBenchmarkResult, error) {
	result := &CISBenchmarkResult{
		Passed:      make([]CISCheck, 0),
		Failed:      make([]CISCheck, 0),
		TotalChecks: len(customChecks),
	}

	for _, check := range customChecks {
		passed := c.runCheck(check, imageName)
		if passed {
			check.Status = "PASS"
			result.Passed = append(result.Passed, check)
			result.PassCount++
		} else {
			check.Status = "FAIL"
			result.Failed = append(result.Failed, check)
			result.FailCount++
		}
	}

	return result, nil
}

func (c *CISBenchmark) runCheck(check CISCheck, imageName string) bool {
	if check.Audit == "" {
		return true
	}
	
	cmd := exec.Command("docker", "run", "--rm", "--entrypoint", "sh", imageName, "-c", check.Audit)
	err := cmd.Run()
	return err == nil
}

func (r *CISBenchmarkResult) ComplianceScore() float64 {
	if r.TotalChecks == 0 {
		return 100.0
	}
	return float64(r.PassCount) / float64(r.TotalChecks) * 100
}

func (r *CISBenchmarkResult) GetFailedBySeverity(severity string) []CISCheck {
	var failed []CISCheck
	for _, check := range r.Failed {
		if strings.EqualFold(check.Severity, severity) {
			failed = append(failed, check)
		}
	}
	return failed
}

var cisChecks = []CISCheck{
	{
		ID:          "CIS-DI-0001",
		Title:       "不要以root用户运行容器",
		Description: "容器应使用非root用户运行以减少攻击面",
		Severity:    "HIGH",
		Rationale:   "以root用户运行容器会增加容器逃逸的风险",
		Audit:       "id | grep -q uid=0",
		Remediation: "在Dockerfile中添加 USER 指令切换到非root用户",
	},
	{
		ID:          "CIS-DI-0002",
		Title:       "不要使用特权容器",
		Description: "容器不应以特权模式运行",
		Severity:    "CRITICAL",
		Rationale:   "特权容器拥有主机的所有权限",
		Audit:       "",
		Remediation: "移除 --privileged 标志，使用特定的capabilities",
	},
	{
		ID:          "CIS-DI-0003",
		Title:       "限制容器的内存使用",
		Description: "应设置容器的内存限制",
		Severity:    "MEDIUM",
		Rationale:   "防止单个容器消耗过多主机内存",
		Audit:       "",
		Remediation: "使用 docker run --memory 或在compose中设置 mem_limit",
	},
	{
		ID:          "CIS-DI-0004",
		Title:       "限制容器的CPU使用",
		Description: "应设置容器的CPU限制",
		Severity:    "MEDIUM",
		Rationale:   "防止单个容器消耗过多主机CPU资源",
		Audit:       "",
		Remediation: "使用 docker run --cpus 或在compose中设置 cpus",
	},
	{
		ID:          "CIS-DI-0005",
		Title:       "不要挂载敏感的主机目录",
		Description: "不应挂载 /proc, /sys, /dev 等敏感目录",
		Severity:    "HIGH",
		Rationale:   "挂载敏感目录可能导致容器逃逸",
		Audit:       "",
		Remediation: "移除对敏感系统目录的挂载",
	},
	{
		ID:          "CIS-DI-0006",
		Title:       "设置健康检查",
		Description: "Dockerfile应包含HEALTHCHECK指令",
		Severity:    "LOW",
		Rationale:   "健康检查可以监控容器运行状态",
		Audit:       "cat /Dockerfile | grep -i HEALTHCHECK",
		Remediation: "在Dockerfile中添加 HEALTHCHECK 指令",
	},
	{
		ID:          "CIS-DI-0007",
		Title:       "不要在镜像中存储密钥",
		Description: "镜像中不应包含SSH密钥、API密钥等敏感信息",
		Severity:    "CRITICAL",
		Rationale:   "密钥泄露可能导致安全漏洞",
		Audit:       "find / -name 'id_rsa' -o -name '*.pem' 2>/dev/null | head -1",
		Remediation: "使用secrets管理工具，不要在镜像中硬编码密钥",
	},
	{
		ID:          "CIS-DI-0008",
		Title:       "更新系统包",
		Description: "镜像中的系统包应保持最新",
		Severity:    "MEDIUM",
		Rationale:   "过时的包可能包含已知漏洞",
		Audit:       "",
		Remediation: "在Dockerfile中运行 apt-get upgrade 或 yum update",
	},
	{
		ID:          "CIS-DI-0009",
		Title:       "移除不必要的包",
		Description: "移除不需要的系统包以减少攻击面",
		Severity:    "LOW",
		Rationale:   "较少的包意味着较少的漏洞",
		Audit:       "",
		Remediation: "在安装后清理不需要的包",
	},
	{
		ID:          "CIS-DI-0010",
		Title:       "使用内容信任机制",
		Description: "启用Docker内容信任验证镜像签名",
		Severity:    "MEDIUM",
		Rationale:   "防止运行被篡改的镜像",
		Audit:       "",
		Remediation: "设置 DOCKER_CONTENT_TRUST=1",
	},
}

func GetCISChecks() []CISCheck {
	return cisChecks
}

func GetFailedChecksRemediations(result *CISBenchmarkResult) map[string][]string {
	remediations := make(map[string][]string)
	
	for severity := range []string{"CRITICAL", "HIGH", "MEDIUM", "LOW"} {
		var fixes []string
		for _, check := range result.GetFailedBySeverity(severity) {
			fixes = append(fixes, fmt.Sprintf("[%s] %s: %s", check.ID, check.Title, check.Remediation))
		}
		if len(fixes) > 0 {
			remediations[severity] = fixes
		}
	}
	
	return remediations
}
