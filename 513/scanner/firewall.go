package scanner

import (
	"encoding/json"
	"fmt"
	"os"
	"os/exec"
	"path/filepath"
	"runtime"
	"strings"
	"time"
)

type BlockRule struct {
	Port        int       `json:"port"`
	Protocol    string    `json:"protocol"`
	Direction   string    `json:"direction"`
	Target      string    `json:"target"`
	Reason      string    `json:"reason"`
	RiskLevel   string    `json:"risk_level"`
	CreatedAt   time.Time `json:"created_at"`
	CreatedBy   string    `json:"created_by"`
	RuleName    string    `json:"rule_name"`
	Status      string    `json:"status"`
}

type BlockResult struct {
	Port     int    `json:"port"`
	Success  bool   `json:"success"`
	Command  string `json:"command"`
	Output   string `json:"output"`
	Error    string `json:"error,omitempty"`
}

type FirewallManager struct {
	rules     []BlockRule
	cacheDir  string
	dryRun    bool
	autoBlock bool
	whitelist map[int]string
}

func NewFirewallManager(dryRun bool) *FirewallManager {
	home, _ := os.UserHomeDir()
	if home == "" {
		home = "."
	}
	cacheDir := filepath.Join(home, ".portscanner", "firewall")
	os.MkdirAll(cacheDir, 0755)

	fm := &FirewallManager{
		rules:     make([]BlockRule, 0),
		cacheDir:  cacheDir,
		dryRun:    dryRun,
		autoBlock: false,
		whitelist: getDefaultWhitelist(),
	}

	fm.loadRules()
	return fm
}

func getDefaultWhitelist() map[int]string {
	return map[int]string{
		22:   "SSH - 管理必需",
		80:   "HTTP - Web服务必需",
		443:  "HTTPS - Web服务必需",
	}
}

func (fm *FirewallManager) SetAutoBlock(enabled bool) {
	fm.autoBlock = enabled
}

func (fm *FirewallManager) AddWhitelist(port int, reason string) {
	fm.whitelist[port] = reason
	fm.saveRules()
}

func (fm *FirewallManager) RemoveWhitelist(port int) {
	delete(fm.whitelist, port)
	fm.saveRules()
}

func (fm *FirewallManager) IsWhitelisted(port int) bool {
	_, ok := fm.whitelist[port]
	return ok
}

func (fm *FirewallManager) BlockPort(port int, protocol, target, reason, riskLevel string) *BlockResult {
	if fm.IsWhitelisted(port) {
		return &BlockResult{
			Port:    port,
			Success: false,
			Command: "",
			Output:  fmt.Sprintf("端口 %d 在白名单中: %s，跳过封禁", port, fm.whitelist[port]),
			Error:   "whitelist_blocked",
		}
	}

	for _, rule := range fm.rules {
		if rule.Port == port && rule.Target == target && rule.Status == "active" {
			return &BlockResult{
				Port:    port,
				Success: true,
				Command: "",
				Output:  fmt.Sprintf("端口 %d 已存在封禁规则，跳过", port),
			}
		}
	}

	if runtime.GOOS == "windows" {
		return fm.blockPortWindows(port, protocol, target, reason, riskLevel)
	}
	return fm.blockPortLinux(port, protocol, target, reason, riskLevel)
}

func (fm *FirewallManager) blockPortWindows(port int, protocol, target, reason, riskLevel string) *BlockResult {
	ruleName := fmt.Sprintf("PortScanner_Block_%d_%s", port, protocol)
	cmdStr := fmt.Sprintf(
		"netsh advfirewall firewall add rule name=\"%s\" dir=in action=block protocol=%s localport=%d",
		ruleName, protocol, port,
	)

	if fm.dryRun {
		fm.recordRule(port, protocol, "in", target, reason, riskLevel, ruleName, "dry_run")
		return &BlockResult{
			Port:    port,
			Success: true,
			Command: cmdStr,
			Output:  "[DRY-RUN] 将执行防火墙封禁命令",
		}
	}

	cmd := exec.Command("netsh", "advfirewall", "firewall", "add", "rule",
		fmt.Sprintf("name=%s", ruleName),
		"dir=in", "action=block",
		fmt.Sprintf("protocol=%s", protocol),
		fmt.Sprintf("localport=%d", port),
	)

	output, err := cmd.CombinedOutput()
	outputStr := string(output)

	if err != nil {
		return &BlockResult{
			Port:    port,
			Success: false,
			Command: cmdStr,
			Output:  outputStr,
			Error:   err.Error(),
		}
	}

	fm.recordRule(port, protocol, "in", target, reason, riskLevel, ruleName, "active")

	outboundCmd := exec.Command("netsh", "advfirewall", "firewall", "add", "rule",
		fmt.Sprintf("name=%s_out", ruleName),
		"dir=out", "action=block",
		fmt.Sprintf("protocol=%s", protocol),
		fmt.Sprintf("localport=%d", port),
	)
	outboundCmd.Run()

	return &BlockResult{
		Port:    port,
		Success: true,
		Command: cmdStr,
		Output:  outputStr,
	}
}

func (fm *FirewallManager) blockPortLinux(port int, protocol, target, reason, riskLevel string) *BlockResult {
	ruleName := fmt.Sprintf("PortScanner_Block_%d_%s", port, protocol)
	cmdStr := fmt.Sprintf("iptables -A INPUT -p %s --dport %d -j DROP", protocol, port)

	if fm.dryRun {
		fm.recordRule(port, protocol, "in", target, reason, riskLevel, ruleName, "dry_run")
		return &BlockResult{
			Port:    port,
			Success: true,
			Command: cmdStr,
			Output:  "[DRY-RUN] 将执行防火墙封禁命令",
		}
	}

	cmd := exec.Command("iptables", "-A", "INPUT", "-p", protocol, "--dport", fmt.Sprintf("%d", port), "-j", "DROP")
	output, err := cmd.CombinedOutput()
	outputStr := string(output)

	if err != nil {
		cmdAlt := exec.Command("firewall-cmd", "--permanent", "--add-port", fmt.Sprintf("%d/%s", port, protocol))
		cmdAlt.Args = append(cmdAlt.Args, "--zone=drop")
		outputAlt, errAlt := cmdAlt.CombinedOutput()

		if errAlt != nil {
			return &BlockResult{
				Port:    port,
				Success: false,
				Command: cmdStr,
				Output:  outputStr + "; " + string(outputAlt),
				Error:   err.Error() + "; " + errAlt.Error(),
			}
		}

		exec.Command("firewall-cmd", "--reload").Run()
	}

	fm.recordRule(port, protocol, "in", target, reason, riskLevel, ruleName, "active")
	return &BlockResult{
		Port:    port,
		Success: true,
		Command: cmdStr,
		Output:  outputStr,
	}
}

func (fm *FirewallManager) UnblockPort(port int) *BlockResult {
	for i, rule := range fm.rules {
		if rule.Port == port && rule.Status == "active" {
			if runtime.GOOS == "windows" {
				cmd := exec.Command("netsh", "advfirewall", "firewall", "delete", "rule",
					fmt.Sprintf("name=%s", rule.RuleName),
				)
				output, _ := cmd.CombinedOutput()

				cmdOut := exec.Command("netsh", "advfirewall", "firewall", "delete", "rule",
					fmt.Sprintf("name=%s_out", rule.RuleName),
				)
				cmdOut.Run()

				fm.rules[i].Status = "removed"
				fm.saveRules()

				return &BlockResult{
					Port:    port,
					Success: true,
					Command: fmt.Sprintf("netsh advfirewall firewall delete rule name=%s", rule.RuleName),
					Output:  string(output),
				}
			}

			cmd := exec.Command("iptables", "-D", "INPUT", "-p", rule.Protocol,
				"--dport", fmt.Sprintf("%d", port), "-j", "DROP")
			output, _ := cmd.CombinedOutput()

			fm.rules[i].Status = "removed"
			fm.saveRules()

			return &BlockResult{
				Port:    port,
				Success: true,
				Command: fmt.Sprintf("iptables -D INPUT -p %s --dport %d -j DROP", rule.Protocol, port),
				Output:  string(output),
			}
		}
	}

	return &BlockResult{
		Port:    port,
		Success: false,
		Output:  fmt.Sprintf("端口 %d 无封禁规则", port),
		Error:   "rule_not_found",
	}
}

func (fm *FirewallManager) AutoBlockHighRiskPorts(ports []PortResult) []BlockResult {
	var results []BlockResult

	for _, port := range ports {
		if fm.IsWhitelisted(port.Port) {
			continue
		}

		risk := AssessRisk(port.Port, port.Service)
		if risk.RiskLevel == "Critical" || risk.RiskLevel == "High" {
			reason := fmt.Sprintf("自动封禁: %s - %s", risk.RiskLevel, risk.Description)
			result := fm.BlockPort(port.Port, "tcp", "", reason, risk.RiskLevel)
			results = append(results, *result)
		}
	}

	return results
}

func (fm *FirewallManager) BlockSpecificPorts(ports []int, reason string) []BlockResult {
	var results []BlockResult

	for _, port := range ports {
		risk := AssessRisk(port, "")
		result := fm.BlockPort(port, "tcp", "", reason, risk.RiskLevel)
		results = append(results, *result)
	}

	return results
}

func (fm *FirewallManager) recordRule(port int, protocol, direction, target, reason, riskLevel, ruleName, status string) {
	rule := BlockRule{
		Port:      port,
		Protocol:  protocol,
		Direction: direction,
		Target:    target,
		Reason:    reason,
		RiskLevel: riskLevel,
		CreatedAt: time.Now(),
		CreatedBy: "PortScanner",
		RuleName:  ruleName,
		Status:    status,
	}

	fm.rules = append(fm.rules, rule)
	fm.saveRules()
}

func (fm *FirewallManager) loadRules() {
	dbPath := filepath.Join(fm.cacheDir, "rules.json")
	data, err := os.ReadFile(dbPath)
	if err != nil {
		return
	}

	json.Unmarshal(data, &fm.rules)
}

func (fm *FirewallManager) saveRules() {
	dbPath := filepath.Join(fm.cacheDir, "rules.json")
	data, _ := json.MarshalIndent(fm.rules, "", "  ")
	os.WriteFile(dbPath, data, 0644)
}

func (fm *FirewallManager) GetActiveRules() []BlockRule {
	var active []BlockRule
	for _, rule := range fm.rules {
		if rule.Status == "active" || rule.Status == "dry_run" {
			active = append(active, rule)
		}
	}
	return active
}

func (fm *FirewallManager) GetAllRules() []BlockRule {
	return fm.rules
}

func (fm *FirewallManager) GetWhitelist() map[int]string {
	return fm.whitelist
}

func (fm *FirewallManager) PrintBlockReport(results []BlockResult) {
	if len(results) == 0 {
		fmt.Println("\n✅ 无需封禁的端口")
		return
	}

	fmt.Println("\n" + strings.Repeat("=", 80))
	fmt.Println("【防火墙封禁报告】")
	fmt.Println(strings.Repeat("=", 80))

	successCount := 0
	failCount := 0
	for _, r := range results {
		if r.Success {
			successCount++
		} else {
			failCount++
		}
	}

	fmt.Printf("\n封禁统计: 成功=%d, 失败=%d\n", successCount, failCount)

	for _, result := range results {
		if result.Success {
			fmt.Printf("\n✅ 端口 %d 封禁成功\n", result.Port)
		} else {
			fmt.Printf("\n❌ 端口 %d 封禁失败\n", result.Port)
		}
		if result.Command != "" {
			fmt.Printf("   命令: %s\n", result.Command)
		}
		if result.Output != "" {
			fmt.Printf("   输出: %s\n", result.Output)
		}
		if result.Error != "" {
			fmt.Printf("   错误: %s\n", result.Error)
		}
	}

	fmt.Println("\n" + strings.Repeat("=", 80))
}

func (fm *FirewallManager) PrintStatus() {
	fmt.Println("\n🛡️  防火墙封禁状态:")
	fmt.Println(strings.Repeat("-", 60))

	activeRules := fm.GetActiveRules()
	if len(activeRules) == 0 {
		fmt.Println("   当前无活跃的封禁规则")
	} else {
		for _, rule := range activeRules {
			statusIcon := "🟢"
			if rule.Status == "dry_run" {
				statusIcon = "🟡"
			}
			fmt.Printf("   %s 端口 %d/%s - %s [%s]\n", statusIcon, rule.Port, rule.Protocol, rule.Reason, rule.RiskLevel)
			fmt.Printf("      创建时间: %s\n", rule.CreatedAt.Format("2006-01-02 15:04:05"))
		}
	}

	fmt.Println("\n📋 白名单端口:")
	for port, reason := range fm.whitelist {
		fmt.Printf("   %-6d %s\n", port, reason)
	}

	if fm.dryRun {
		fmt.Println("\n🟡 当前为试运行模式 (dry-run)，不会实际执行封禁")
	}
}
