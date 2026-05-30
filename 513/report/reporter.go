package report

import (
	"fmt"
	"os"
	"sort"
	"strings"
	"time"

	"portscanner/scanner"
)

type ScanReport struct {
	Target        string
	ScanTime      time.Time
	ScanDuration  time.Duration
	OpenPorts     []scanner.PortResult
	Vulnerabilities []scanner.Vulnerability
	RiskAssessments []scanner.RiskAssessment
}

func NewScanReport(target string) *ScanReport {
	return &ScanReport{
		Target:   target,
		ScanTime: time.Now(),
	}
}

func (r *ScanReport) PrintConsole() {
	fmt.Println("\n" + strings.Repeat("=", 80))
	fmt.Printf("端口扫描报告 - %s\n", r.Target)
	fmt.Printf("扫描时间: %s\n", r.ScanTime.Format("2006-01-02 15:04:05"))
	fmt.Printf("扫描时长: %v\n", r.ScanDuration)
	fmt.Println(strings.Repeat("=", 80))

	fmt.Println("\n【开放端口清单】")
	fmt.Println(strings.Repeat("-", 80))
	fmt.Printf("%-8s %-15s %-30s %-15s\n", "端口", "服务", "版本", "状态")
	fmt.Println(strings.Repeat("-", 80))

	sort.Slice(r.OpenPorts, func(i, j int) bool {
		return r.OpenPorts[i].Port < r.OpenPorts[j].Port
	})

	for _, port := range r.OpenPorts {
		fmt.Printf("%-8d %-15s %-30s %-15s\n", port.Port, port.Service, port.Version, port.State)
	}

	if len(r.Vulnerabilities) > 0 {
		fmt.Println("\n【发现的漏洞】")
		fmt.Println(strings.Repeat("-", 80))
		for _, vuln := range r.Vulnerabilities {
			color := scanner.GetRiskColor(vuln.Severity)
			fmt.Printf("%s[%s]%s %s - 端口 %d (%s)\n", color, vuln.Severity, "\033[0m", vuln.Type, vuln.Port, vuln.Service)
			fmt.Printf("   描述: %s\n", vuln.Description)
			fmt.Println()
		}
	}

	if len(r.RiskAssessments) > 0 {
		fmt.Println("\n【风险评估与加固建议】")
		fmt.Println(strings.Repeat("-", 80))

		sort.Slice(r.RiskAssessments, func(i, j int) bool {
			order := map[string]int{"Critical": 0, "High": 1, "Medium": 2, "Low": 3, "Info": 4}
			return order[r.RiskAssessments[i].RiskLevel] < order[r.RiskAssessments[j].RiskLevel]
		})

		for _, risk := range r.RiskAssessments {
			color := scanner.GetRiskColor(risk.RiskLevel)
			fmt.Printf("\n%s端口 %d (%s) - 风险等级: [%s]%s\n", color, risk.Port, risk.Service, risk.RiskLevel, "\033[0m")
			fmt.Printf("   风险描述: %s\n", risk.Description)
			fmt.Println("   加固建议:")
			for i, rec := range risk.Recommendations {
				fmt.Printf("      %d. %s\n", i+1, rec)
			}
		}
	}

	riskCount := map[string]int{"Critical": 0, "High": 0, "Medium": 0, "Low": 0, "Info": 0}
	for _, risk := range r.RiskAssessments {
		riskCount[risk.RiskLevel]++
	}

	fmt.Println("\n" + strings.Repeat("=", 80))
	fmt.Println("【扫描统计】")
	fmt.Printf("开放端口数量: %d\n", len(r.OpenPorts))
	fmt.Printf("发现漏洞数量: %d\n", len(r.Vulnerabilities))
	fmt.Printf("风险等级分布: Critical=%d, High=%d, Medium=%d, Low=%d, Info=%d\n",
		riskCount["Critical"], riskCount["High"], riskCount["Medium"], riskCount["Low"], riskCount["Info"])
	fmt.Println(strings.Repeat("=", 80))
}

func (r *ScanReport) GenerateHTML(filename string) error {
	html := `<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>端口扫描报告 - ` + r.Target + `</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background: #f5f5f5; padding: 20px; }
        .container { max-width: 1200px; margin: 0 auto; background: white; padding: 30px; border-radius: 8px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
        h1 { color: #2c3e50; border-bottom: 3px solid #3498db; padding-bottom: 10px; margin-bottom: 20px; }
        .header-info { background: #f8f9fa; padding: 15px; border-radius: 5px; margin-bottom: 20px; }
        .header-info p { margin: 5px 0; color: #555; }
        h2 { color: #2c3e50; margin: 25px 0 15px 0; border-left: 4px solid #3498db; padding-left: 10px; }
        table { width: 100%; border-collapse: collapse; margin-bottom: 20px; }
        th, td { padding: 12px; text-align: left; border-bottom: 1px solid #ddd; }
        th { background: #3498db; color: white; }
        tr:hover { background: #f5f5f5; }
        .critical { color: #e74c3c; font-weight: bold; }
        .high { color: #9b59b6; font-weight: bold; }
        .medium { color: #f39c12; font-weight: bold; }
        .low { color: #27ae60; font-weight: bold; }
        .info { color: #3498db; font-weight: bold; }
        .vuln-card { background: #fff5f5; border: 1px solid #e74c3c; border-radius: 5px; padding: 15px; margin-bottom: 15px; }
        .vuln-card h3 { color: #e74c3c; margin-bottom: 10px; }
        .risk-card { border-radius: 5px; padding: 15px; margin-bottom: 15px; }
        .risk-card.critical { background: #fff5f5; border-left: 4px solid #e74c3c; }
        .risk-card.high { background: #faf5ff; border-left: 4px solid #9b59b6; }
        .risk-card.medium { background: #fffaf0; border-left: 4px solid #f39c12; }
        .risk-card.low { background: #f0fff4; border-left: 4px solid #27ae60; }
        .risk-card.info { background: #f0f8ff; border-left: 4px solid #3498db; }
        .recommendations { margin-top: 10px; padding-left: 20px; }
        .recommendations li { margin: 5px 0; color: #555; }
        .stats { display: flex; gap: 20px; flex-wrap: wrap; }
        .stat-box { flex: 1; min-width: 150px; background: #3498db; color: white; padding: 15px; border-radius: 5px; text-align: center; }
        .stat-box.critical { background: #e74c3c; }
        .stat-box.high { background: #9b59b6; }
        .stat-box.medium { background: #f39c12; }
    </style>
</head>
<body>
    <div class="container">
        <h1>🔍 端口扫描报告</h1>
        <div class="header-info">
            <p><strong>目标主机:</strong> ` + r.Target + `</p>
            <p><strong>扫描时间:</strong> ` + r.ScanTime.Format("2006-01-02 15:04:05") + `</p>
            <p><strong>扫描时长:</strong> ` + r.ScanDuration.String() + `</p>
        </div>

        <h2>📊 扫描统计</h2>
        <div class="stats">
            <div class="stat-box"><h3>` + fmt.Sprintf("%d", len(r.OpenPorts)) + `</h3><p>开放端口</p></div>
            <div class="stat-box critical"><h3>` + fmt.Sprintf("%d", len(r.Vulnerabilities)) + `</h3><p>发现漏洞</p></div>
        </div>

        <h2>📋 开放端口清单</h2>
        <table>
            <tr><th>端口</th><th>服务</th><th>版本</th><th>状态</th></tr>
`

	sort.Slice(r.OpenPorts, func(i, j int) bool {
		return r.OpenPorts[i].Port < r.OpenPorts[j].Port
	})

	for _, port := range r.OpenPorts {
		html += fmt.Sprintf("            <tr><td>%d</td><td>%s</td><td>%s</td><td>%s</td></tr>\n",
			port.Port, port.Service, port.Version, port.State)
	}

	html += `
        </table>
`

	if len(r.Vulnerabilities) > 0 {
		html += `
        <h2>⚠️ 发现的漏洞</h2>
`
		for _, vuln := range r.Vulnerabilities {
			html += fmt.Sprintf(`
        <div class="vuln-card">
            <h3>[%s] %s - %s (端口 %d)</h3>
            <p><strong>描述:</strong> %s</p>
        </div>
`, vuln.Severity, vuln.Type, vuln.Service, vuln.Port, vuln.Description)
		}
	}

	if len(r.RiskAssessments) > 0 {
		html += `
        <h2>🛡️ 风险评估与加固建议</h2>
`
		sort.Slice(r.RiskAssessments, func(i, j int) bool {
			order := map[string]int{"Critical": 0, "High": 1, "Medium": 2, "Low": 3, "Info": 4}
			return order[r.RiskAssessments[i].RiskLevel] < order[r.RiskAssessments[j].RiskLevel]
		})

		for _, risk := range r.RiskAssessments {
			riskClass := strings.ToLower(risk.RiskLevel)
			html += fmt.Sprintf(`
        <div class="risk-card %s">
            <h3 class="%s">端口 %d - %s [%s]</h3>
            <p><strong>风险描述:</strong> %s</p>
            <div class="recommendations">
                <strong>加固建议:</strong>
                <ul>
`, riskClass, riskClass, risk.Port, risk.Service, risk.RiskLevel, risk.Description)

			for _, rec := range risk.Recommendations {
				html += fmt.Sprintf("                    <li>%s</li>\n", rec)
			}

			html += `
                </ul>
            </div>
        </div>
`
		}
	}

	html += `
    </div>
</body>
</html>
`

	return os.WriteFile(filename, []byte(html), 0644)
}

func (r *ScanReport) GenerateText(filename string) error {
	var report strings.Builder

	report.WriteString(strings.Repeat("=", 80) + "\n")
	report.WriteString(fmt.Sprintf("端口扫描报告 - %s\n", r.Target))
	report.WriteString(fmt.Sprintf("扫描时间: %s\n", r.ScanTime.Format("2006-01-02 15:04:05")))
	report.WriteString(fmt.Sprintf("扫描时长: %v\n", r.ScanDuration))
	report.WriteString(strings.Repeat("=", 80) + "\n\n")

	report.WriteString("【开放端口清单】\n")
	report.WriteString(strings.Repeat("-", 80) + "\n")
	report.WriteString(fmt.Sprintf("%-8s %-15s %-30s %-15s\n", "端口", "服务", "版本", "状态"))
	report.WriteString(strings.Repeat("-", 80) + "\n")

	sort.Slice(r.OpenPorts, func(i, j int) bool {
		return r.OpenPorts[i].Port < r.OpenPorts[j].Port
	})

	for _, port := range r.OpenPorts {
		report.WriteString(fmt.Sprintf("%-8d %-15s %-30s %-15s\n", port.Port, port.Service, port.Version, port.State))
	}

	if len(r.Vulnerabilities) > 0 {
		report.WriteString("\n【发现的漏洞】\n")
		report.WriteString(strings.Repeat("-", 80) + "\n")
		for _, vuln := range r.Vulnerabilities {
			report.WriteString(fmt.Sprintf("[%s] %s - 端口 %d (%s)\n", vuln.Severity, vuln.Type, vuln.Port, vuln.Service))
			report.WriteString(fmt.Sprintf("   描述: %s\n\n", vuln.Description))
		}
	}

	if len(r.RiskAssessments) > 0 {
		report.WriteString("\n【风险评估与加固建议】\n")
		report.WriteString(strings.Repeat("-", 80) + "\n")

		sort.Slice(r.RiskAssessments, func(i, j int) bool {
			order := map[string]int{"Critical": 0, "High": 1, "Medium": 2, "Low": 3, "Info": 4}
			return order[r.RiskAssessments[i].RiskLevel] < order[r.RiskAssessments[j].RiskLevel]
		})

		for _, risk := range r.RiskAssessments {
			report.WriteString(fmt.Sprintf("\n端口 %d (%s) - 风险等级: [%s]\n", risk.Port, risk.Service, risk.RiskLevel))
			report.WriteString(fmt.Sprintf("   风险描述: %s\n", risk.Description))
			report.WriteString("   加固建议:\n")
			for i, rec := range risk.Recommendations {
				report.WriteString(fmt.Sprintf("      %d. %s\n", i+1, rec))
			}
		}
	}

	riskCount := map[string]int{"Critical": 0, "High": 0, "Medium": 0, "Low": 0, "Info": 0}
	for _, risk := range r.RiskAssessments {
		riskCount[risk.RiskLevel]++
	}

	report.WriteString("\n" + strings.Repeat("=", 80) + "\n")
	report.WriteString("【扫描统计】\n")
	report.WriteString(fmt.Sprintf("开放端口数量: %d\n", len(r.OpenPorts)))
	report.WriteString(fmt.Sprintf("发现漏洞数量: %d\n", len(r.Vulnerabilities)))
	report.WriteString(fmt.Sprintf("风险等级分布: Critical=%d, High=%d, Medium=%d, Low=%d, Info=%d\n",
		riskCount["Critical"], riskCount["High"], riskCount["Medium"], riskCount["Low"], riskCount["Info"]))
	report.WriteString(strings.Repeat("=", 80) + "\n")

	return os.WriteFile(filename, []byte(report.String()), 0644)
}
