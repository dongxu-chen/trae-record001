package report

import (
	"fmt"
	"html/template"
	"os"
	"strings"
	"time"

	"container-scanner/pkg/compliance"
	"container-scanner/pkg/dependency"
	"container-scanner/pkg/remediation"
	"container-scanner/pkg/scanner"
)

const htmlTemplate = `
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>容器安全扫描报告 - {{.ImageName}}</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background: #f5f7fa; color: #333; line-height: 1.6; }
        .container { max-width: 1400px; margin: 0 auto; padding: 20px; }
        .header { background: linear-gradient(135deg, #1e3a5f 0%, #2d5a87 100%); color: white; padding: 30px; border-radius: 12px; margin-bottom: 30px; box-shadow: 0 4px 20px rgba(0,0,0,0.1); }
        .header h1 { font-size: 28px; margin-bottom: 10px; }
        .header .meta { display: flex; gap: 30px; opacity: 0.9; font-size: 14px; flex-wrap: wrap; }
        .status-badge { display: inline-block; padding: 6px 16px; border-radius: 20px; font-weight: 600; font-size: 14px; }
        .status-pass { background: #10b981; }
        .status-fail { background: #ef4444; }
        .score-circle { width: 80px; height: 80px; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-size: 24px; font-weight: 700; border: 4px solid; }
        .score-high { border-color: #10b981; color: #10b981; }
        .score-medium { border-color: #f59e0b; color: #f59e0b; }
        .score-low { border-color: #ef4444; color: #ef4444; }
        .summary { display: grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); gap: 20px; margin-bottom: 30px; }
        .summary-card { background: white; padding: 25px; border-radius: 12px; box-shadow: 0 2px 10px rgba(0,0,0,0.05); }
        .summary-card h3 { font-size: 14px; color: #6b7280; margin-bottom: 10px; text-transform: uppercase; letter-spacing: 0.5px; }
        .summary-card .total { font-size: 36px; font-weight: 700; margin-bottom: 15px; }
        .severity-breakdown { display: flex; gap: 10px; flex-wrap: wrap; }
        .severity-tag { padding: 4px 12px; border-radius: 6px; font-size: 12px; font-weight: 600; }
        .critical { background: #fee2e2; color: #dc2626; }
        .high { background: #fed7aa; color: #ea580c; }
        .medium { background: #fef3c7; color: #d97706; }
        .low { background: #dbeafe; color: #2563eb; }
        .section { background: white; border-radius: 12px; margin-bottom: 25px; box-shadow: 0 2px 10px rgba(0,0,0,0.05); overflow: hidden; }
        .section-header { padding: 20px 25px; border-bottom: 1px solid #e5e7eb; display: flex; justify-content: space-between; align-items: center; cursor: pointer; }
        .section-header:hover { background: #f9fafb; }
        .section-header h2 { font-size: 20px; color: #1f2937; }
        .section-header .count { background: #e5e7eb; padding: 4px 12px; border-radius: 20px; font-size: 14px; font-weight: 600; }
        .section-content { padding: 0; max-height: 0; overflow: hidden; transition: max-height 0.3s ease; }
        .section-content.expanded { max-height: 2000px; overflow-y: auto; }
        .table-container { overflow-x: auto; padding: 0 25px 25px; }
        table { width: 100%; border-collapse: collapse; }
        th { background: #f9fafb; padding: 15px 20px; text-align: left; font-weight: 600; color: #374151; border-bottom: 2px solid #e5e7eb; font-size: 13px; text-transform: uppercase; letter-spacing: 0.5px; }
        td { padding: 15px 20px; border-bottom: 1px solid #f3f4f6; font-size: 14px; }
        tr:hover { background: #f9fafb; }
        .vuln-id { font-family: 'Courier New', monospace; font-weight: 600; color: #1e3a5f; }
        .pkg-name { color: #6b7280; }
        .version { font-family: 'Courier New', monospace; font-size: 13px; color: #374151; }
        .fixed { color: #10b981; font-weight: 600; }
        .no-fixed { color: #9ca3af; }
        .secret-match { font-family: 'Courier New', monospace; background: #fef3c7; padding: 2px 6px; border-radius: 4px; font-size: 12px; }
        .file-path { font-family: 'Courier New', monospace; color: #6b7280; font-size: 13px; }
        .misconfig-id { font-family: 'Courier New', monospace; font-weight: 600; color: #7c3aed; }
        .description { color: #6b7280; max-width: 400px; }
        .empty-state { padding: 60px 20px; text-align: center; color: #9ca3af; }
        .empty-state svg { width: 64px; height: 64px; margin-bottom: 15px; opacity: 0.5; }
        .pass-check { color: #10b981; }
        .fail-check { color: #dc2626; }
        .auto-fix-badge { background: #d1fae5; color: #059669; padding: 2px 8px; border-radius: 12px; font-size: 11px; font-weight: 600; }
        .manual-fix-badge { background: #fef3c7; color: #d97706; padding: 2px 8px; border-radius: 12px; font-size: 11px; font-weight: 600; }
        .code-block { background: #1f2937; color: #e5e7eb; padding: 15px; border-radius: 8px; font-family: 'Courier New', monospace; font-size: 12px; overflow-x: auto; margin: 10px 0; }
        .license-risk-high { color: #dc2626; font-weight: 600; }
        .license-risk-medium { color: #d97706; font-weight: 600; }
        .license-risk-low { color: #10b981; font-weight: 600; }
        .tree-item { font-family: 'Courier New', monospace; font-size: 13px; padding: 4px 0; }
        .tree-indent { display: inline-block; width: 20px; }
        .tabs { display: flex; border-bottom: 1px solid #e5e7eb; margin-bottom: 20px; }
        .tab { padding: 12px 20px; cursor: pointer; border-bottom: 2px solid transparent; font-weight: 500; }
        .tab.active { border-bottom-color: #1e3a5f; color: #1e3a5f; }
        .tab-content { display: none; }
        .tab-content.active { display: block; }
        .footer { text-align: center; padding: 30px; color: #9ca3af; font-size: 13px; }
        .chevron { transition: transform 0.3s ease; }
        .chevron.rotated { transform: rotate(180deg); }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🔒 容器安全扫描报告</h1>
            <div class="meta">
                <span><strong>镜像:</strong> {{.ImageName}}</span>
                <span><strong>扫描时间:</strong> {{.ScanTime}}</span>
                <span class="status-badge {{if .Passed}}status-pass{{else}}status-fail{{end}}">
                    {{if .Passed}}✓ 通过{{else}}✗ 失败{{end}}
                </span>
                {{if .ComplianceScore}}
                <div class="score-circle {{if ge .ComplianceScore 80}}score-high{{else if ge .ComplianceScore 50}}score-medium{{else}}score-low{{end}}">
                    {{printf "%.0f" .ComplianceScore}}%
                </div>
                {{end}}
            </div>
        </div>

        <div class="summary">
            <div class="summary-card">
                <h3>漏洞总数</h3>
                <div class="total">{{.VulnerabilityCount}}</div>
                <div class="severity-breakdown">
                    <span class="severity-tag critical">严重: {{.VulnCritical}}</span>
                    <span class="severity-tag high">高危: {{.VulnHigh}}</span>
                    <span class="severity-tag medium">中危: {{.VulnMedium}}</span>
                    <span class="severity-tag low">低危: {{.VulnLow}}</span>
                </div>
            </div>
            <div class="summary-card">
                <h3>敏感信息</h3>
                <div class="total">{{.SecretCount}}</div>
                <div class="severity-breakdown">
                    <span class="severity-tag critical">严重: {{.SecretCritical}}</span>
                    <span class="severity-tag high">高危: {{.SecretHigh}}</span>
                    <span class="severity-tag medium">中危: {{.SecretMedium}}</span>
                    <span class="severity-tag low">低危: {{.SecretLow}}</span>
                </div>
            </div>
            <div class="summary-card">
                <h3>配置风险</h3>
                <div class="total">{{.MisconfigCount}}</div>
                <div class="severity-breakdown">
                    <span class="severity-tag critical">严重: {{.MisconfigCritical}}</span>
                    <span class="severity-tag high">高危: {{.MisconfigHigh}}</span>
                    <span class="severity-tag medium">中危: {{.MisconfigMedium}}</span>
                    <span class="severity-tag low">低危: {{.MisconfigLow}}</span>
                </div>
            </div>
            <div class="summary-card">
                <h3>软件包依赖</h3>
                <div class="total">{{.TotalPackages}}</div>
                <div class="severity-breakdown">
                    <span class="severity-tag critical">高风险许可: {{.HighRiskLicenses}}</span>
                    <span class="severity-tag medium">许可种类: {{.UniqueLicenses}}</span>
                </div>
            </div>
        </div>

        {{if .BlockedViolations}}
        <div class="section">
            <div class="section-header">
                <h2>🚫 阻断 - 严重违规</h2>
                <span class="count" style="background: #fee2e2; color: #dc2626;">{{len .BlockedViolations}}</span>
            </div>
            <div class="section-content expanded">
                <div style="padding: 20px 25px;">
                    {{range .BlockedViolations}}
                    <div style="color: #dc2626; padding: 5px 0;">• {{.Message}}</div>
                    {{end}}
                </div>
            </div>
        </div>
        {{end}}

        {{if .WarningViolations}}
        <div class="section">
            <div class="section-header">
                <h2>⚠️ 警告 - 需要关注</h2>
                <span class="count" style="background: #fef3c7; color: #d97706;">{{len .WarningViolations}}</span>
            </div>
            <div class="section-content expanded">
                <div style="padding: 20px 25px;">
                    {{range .WarningViolations}}
                    <div style="color: #d97706; padding: 5px 0;">• {{.Message}}</div>
                    {{end}}
                </div>
            </div>
        </div>
        {{end}}

        {{if .WhitelistedSecrets}}
        <div class="section">
            <div class="section-header">
                <h2>✅ 白名单过滤</h2>
                <span class="count" style="background: #d1fae5; color: #059669;">{{.WhitelistedSecrets}}</span>
            </div>
            <div class="section-content expanded">
                <div style="padding: 20px 25px; color: #059669;">
                    已自动过滤 {{.WhitelistedSecrets}} 个匹配白名单规则的敏感信息
                </div>
            </div>
        </div>
        {{end}}

        <div class="section">
            <div class="section-header" onclick="toggleSection(this)">
                <h2>📋 CIS 基线合规检查</h2>
                <div style="display: flex; align-items: center; gap: 15px;">
                    <span class="count">通过: {{.CISPassed}} / {{.CISTotal}}</span>
                    <svg class="chevron" width="20" height="20" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <polyline points="6,9 12,15 18,9"></polyline>
                    </svg>
                </div>
            </div>
            <div class="section-content">
                <div class="table-container">
                    <table>
                        <thead>
                            <tr>
                                <th>状态</th>
                                <th>ID</th>
                                <th>检查项</th>
                                <th>严重程度</th>
                                <th>修复建议</th>
                            </tr>
                        </thead>
                        <tbody>
                            {{range .CISChecks}}
                            <tr>
                                <td>{{if eq .Status "PASS"}}<span class="pass-check">✓</span>{{else}}<span class="fail-check">✗</span>{{end}}</td>
                                <td><span class="misconfig-id">{{.ID}}</span></td>
                                <td>{{.Title}}</td>
                                <td><span class="severity-tag {{severityClass .Severity}}">{{.Severity}}</span></td>
                                <td class="description">{{.Remediation}}</td>
                            </tr>
                            {{end}}
                        </tbody>
                    </table>
                </div>
            </div>
        </div>

        <div class="section">
            <div class="section-header" onclick="toggleSection(this)">
                <h2>🔧 修复建议</h2>
                <div style="display: flex; align-items: center; gap: 15px;">
                    <span class="count">共 {{.FixSuggestionCount}} 项, 自动修复: {{.AutoFixCount}}</span>
                    <svg class="chevron" width="20" height="20" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <polyline points="6,9 12,15 18,9"></polyline>
                    </svg>
                </div>
            </div>
            <div class="section-content">
                <div class="table-container">
                    <table>
                        <thead>
                            <tr>
                                <th>类型</th>
                                <th>ID</th>
                                <th>标题</th>
                                <th>严重程度</th>
                                <th>修复方式</th>
                                <th>命令</th>
                            </tr>
                        </thead>
                        <tbody>
                            {{range .FixSuggestions}}
                            <tr>
                                <td>{{.Type}}</td>
                                <td><span class="misconfig-id">{{.ID}}</span></td>
                                <td>{{.Title}}</td>
                                <td><span class="severity-tag {{severityClass .Severity}}">{{.Severity}}</span></td>
                                <td>{{if .AutoFix}}<span class="auto-fix-badge">自动修复</span>{{else}}<span class="manual-fix-badge">手动修复</span>{{end}}</td>
                                <td><code>{{truncate .Command 50}}</code></td>
                            </tr>
                            {{end}}
                        </tbody>
                    </table>
                </div>
            </div>
        </div>

        <div class="section">
            <div class="section-header" onclick="toggleSection(this)">
                <h2>📦 依赖分析 & 许可合规</h2>
                <div style="display: flex; align-items: center; gap: 15px;">
                    <span class="count">{{.TotalPackages}} 个包, {{.UniqueLicenses}} 种许可</span>
                    <svg class="chevron" width="20" height="20" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <polyline points="6,9 12,15 18,9"></polyline>
                    </svg>
                </div>
            </div>
            <div class="section-content">
                <div style="padding: 25px;">
                    <div class="tabs">
                        <div class="tab active" onclick="switchTab(this, 'packages')">软件包列表</div>
                        <div class="tab" onclick="switchTab(this, 'licenses')">许可分析</div>
                        <div class="tab" onclick="switchTab(this, 'risk')">合规风险</div>
                    </div>

                    <div id="packages" class="tab-content active">
                        <div class="table-container" style="padding: 0;">
                            <table>
                                <thead>
                                    <tr>
                                        <th>软件包</th>
                                        <th>版本</th>
                                        <th>许可证</th>
                                        <th>风险等级</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    {{range .Packages}}
                                    <tr>
                                        <td><span class="pkg-name">{{.Name}}</span></td>
                                        <td><span class="version">{{.Version}}</span></td>
                                        <td>{{.License}}</td>
                                        <td>{{licenseRiskBadge .License}}</td>
                                    </tr>
                                    {{end}}
                                </tbody>
                            </table>
                        </div>
                    </div>

                    <div id="licenses" class="tab-content">
                        <div class="table-container" style="padding: 0;">
                            <table>
                                <thead>
                                    <tr>
                                        <th>许可证</th>
                                        <th>软件包数量</th>
                                        <th>风险等级</th>
                                        <th>限制说明</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    {{range $license, $count := .LicenseSummary}}
                                    <tr>
                                        <td>{{$license}}</td>
                                        <td>{{$count}}</td>
                                        <td>{{licenseRiskBadge $license}}</td>
                                        <td class="description">{{licenseRestrictions $license}}</td>
                                    </tr>
                                    {{end}}
                                </tbody>
                            </table>
                        </div>
                    </div>

                    <div id="risk" class="tab-content">
                        {{if .LicenseComplianceIssues}}
                        <div style="padding: 20px;">
                            {{range .LicenseComplianceIssues}}
                            <div class="license-risk-high">• {{.}}</div>
                            {{end}}
                        </div>
                        {{else}}
                        <div class="empty-state">
                            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                                <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/>
                                <polyline points="22,4 12,14.01 9,11.01"/>
                            </svg>
                            <p>未发现许可合规风险</p>
                        </div>
                        {{end}}
                    </div>
                </div>
            </div>
        </div>

        <div class="section">
            <div class="section-header" onclick="toggleSection(this)">
                <h2>🐛 漏洞扫描 (CVE)</h2>
                <div style="display: flex; align-items: center; gap: 15px;">
                    <span class="count">{{.VulnerabilityCount}}</span>
                    <svg class="chevron" width="20" height="20" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <polyline points="6,9 12,15 18,9"></polyline>
                    </svg>
                </div>
            </div>
            <div class="section-content">
                {{if .Vulnerabilities}}
                <div class="table-container">
                    <table>
                        <thead>
                            <tr>
                                <th>严重程度</th>
                                <th>CVE ID</th>
                                <th>软件包</th>
                                <th>当前版本</th>
                                <th>修复版本</th>
                                <th>标题</th>
                            </tr>
                        </thead>
                        <tbody>
                            {{range .Vulnerabilities}}
                            <tr>
                                <td><span class="severity-tag {{severityClass .Severity}}">{{.Severity}}</span></td>
                                <td><span class="vuln-id">{{.VulnerabilityID}}</span></td>
                                <td><span class="pkg-name">{{.PkgName}}</span></td>
                                <td><span class="version">{{.InstalledVersion}}</span></td>
                                <td>{{if .FixedVersion}}<span class="fixed">{{.FixedVersion}}</span>{{else}}<span class="no-fixed">暂无</span>{{end}}</td>
                                <td class="description">{{.Title}}</td>
                            </tr>
                            {{end}}
                        </tbody>
                    </table>
                </div>
                {{else}}
                <div class="empty-state">
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/>
                        <polyline points="22,4 12,14.01 9,11.01"/>
                    </svg>
                    <p>未发现任何漏洞</p>
                </div>
                {{end}}
            </div>
        </div>

        <div class="section">
            <div class="section-header" onclick="toggleSection(this)">
                <h2>🔑 敏感信息扫描</h2>
                <div style="display: flex; align-items: center; gap: 15px;">
                    <span class="count">{{.SecretCount}}</span>
                    <svg class="chevron" width="20" height="20" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <polyline points="6,9 12,15 18,9"></polyline>
                    </svg>
                </div>
            </div>
            <div class="section-content">
                {{if .Secrets}}
                <div class="table-container">
                    <table>
                        <thead>
                            <tr>
                                <th>严重程度</th>
                                <th>规则ID</th>
                                <th>类别</th>
                                <th>标题</th>
                                <th>文件路径</th>
                                <th>匹配内容</th>
                            </tr>
                        </thead>
                        <tbody>
                            {{range .Secrets}}
                            <tr>
                                <td><span class="severity-tag {{severityClass .Severity}}">{{.Severity}}</span></td>
                                <td><span class="misconfig-id">{{.RuleID}}</span></td>
                                <td>{{.Category}}</td>
                                <td>{{.Title}}</td>
                                <td><span class="file-path">{{.FilePath}}:{{.StartLine}}</span></td>
                                <td><span class="secret-match">{{truncate .Match 50}}</span></td>
                            </tr>
                            {{end}}
                        </tbody>
                    </table>
                </div>
                {{else}}
                <div class="empty-state">
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/>
                        <polyline points="22,4 12,14.01 9,11.01"/>
                    </svg>
                    <p>未发现敏感信息泄露</p>
                </div>
                {{end}}
            </div>
        </div>

        <div class="section">
            <div class="section-header" onclick="toggleSection(this)">
                <h2>⚙️ 配置风险扫描</h2>
                <div style="display: flex; align-items: center; gap: 15px;">
                    <span class="count">{{.MisconfigCount}}</span>
                    <svg class="chevron" width="20" height="20" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <polyline points="6,9 12,15 18,9"></polyline>
                    </svg>
                </div>
            </div>
            <div class="section-content">
                {{if .Misconfigurations}}
                <div class="table-container">
                    <table>
                        <thead>
                            <tr>
                                <th>严重程度</th>
                                <th>类型</th>
                                <th>规则ID</th>
                                <th>标题</th>
                                <th>描述</th>
                                <th>解决方案</th>
                            </tr>
                        </thead>
                        <tbody>
                            {{range .Misconfigurations}}
                            <tr>
                                <td><span class="severity-tag {{severityClass .Severity}}">{{.Severity}}</span></td>
                                <td>{{.Type}}</td>
                                <td><span class="misconfig-id">{{.ID}}</span></td>
                                <td>{{.Title}}</td>
                                <td class="description">{{truncate .Description 100}}</td>
                                <td class="description">{{truncate .Resolution 100}}</td>
                            </tr>
                            {{end}}
                        </tbody>
                    </table>
                </div>
                {{else}}
                <div class="empty-state">
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/>
                        <polyline points="22,4 12,14.01 9,11.01"/>
                    </svg>
                    <p>未发现配置风险</p>
                </div>
                {{end}}
            </div>
        </div>

        <div class="footer">
            <p>由 Container Security Scanner 生成 | 基于 Trivy 引擎</p>
        </div>
    </div>

    <script>
        function toggleSection(header) {
            const content = header.nextElementSibling;
            const chevron = header.querySelector('.chevron');
            content.classList.toggle('expanded');
            chevron.classList.toggle('rotated');
        }

        function switchTab(tab, tabName) {
            const tabs = tab.parentElement.querySelectorAll('.tab');
            tabs.forEach(t => t.classList.remove('active'));
            tab.classList.add('active');

            const contents = tab.parentElement.parentElement.querySelectorAll('.tab-content');
            contents.forEach(c => c.classList.remove('active'));
            document.getElementById(tabName).classList.add('active');
        }
    </script>
</body>
</html>
`

type ThresholdDisplay struct {
	Message   string
	IsBlocked bool
}

type CISCheckDisplay struct {
	ID          string
	Title       string
	Severity    string
	Status      string
	Remediation string
}

type FixSuggestionDisplay struct {
	ID          string
	Type        string
	Title       string
	Severity    string
	AutoFix     bool
	Command     string
}

type PackageDisplay struct {
	Name    string
	Version string
	License string
}

type ReportData struct {
	ImageName            string
	ScanTime             string
	Passed               bool
	ComplianceScore      float64
	BlockedViolations    []ThresholdDisplay
	WarningViolations    []ThresholdDisplay
	VulnerabilityCount   int
	VulnCritical         int
	VulnHigh             int
	VulnMedium           int
	VulnLow              int
	SecretCount          int
	SecretCritical       int
	SecretHigh           int
	SecretMedium         int
	SecretLow            int
	MisconfigCount       int
	MisconfigCritical    int
	MisconfigHigh        int
	MisconfigMedium      int
	MisconfigLow         int
	Vulnerabilities      []scanner.Vulnerability
	Secrets              []scanner.Secret
	Misconfigurations    []scanner.Misconfiguration
	WhitelistedSecrets   int
	CISChecks            []CISCheckDisplay
	CISPassed            int
	CISTotal             int
	FixSuggestionCount   int
	AutoFixCount         int
	FixSuggestions       []FixSuggestionDisplay
	TotalPackages        int
	UniqueLicenses       int
	HighRiskLicenses     int
	Packages             []PackageDisplay
	LicenseSummary       map[string]int
	LicenseComplianceIssues []string
}

func severityClass(severity string) string {
	switch strings.ToUpper(severity) {
	case "CRITICAL":
		return "critical"
	case "HIGH":
		return "high"
	case "MEDIUM":
		return "medium"
	case "LOW":
		return "low"
	default:
		return "low"
	}
}

func truncate(s string, maxLen int) string {
	if len(s) <= maxLen {
		return s
	}
	return s[:maxLen] + "..."
}

func getLicenseRisk(license string) string {
	highRisk := map[string]bool{
		"GPL-2.0": true, "GPL-3.0": true, "AGPL-3.0": true, "Proprietary": true,
	}
	mediumRisk := map[string]bool{
		"LGPL-2.1": true, "LGPL-3.0": true, "MPL-2.0": true, "CDDL-1.0": true,
	}

	normalized := normalizeLicense(license)
	if highRisk[normalized] {
		return "high"
	}
	if mediumRisk[normalized] {
		return "medium"
	}
	return "low"
}

func normalizeLicense(license string) string {
	license = strings.TrimSpace(license)
	license = strings.TrimPrefix(license, "(")
	license = strings.TrimSuffix(license, ")")
	
	knownLicenses := []string{"GPL-2.0", "GPL-3.0", "LGPL-2.1", "LGPL-3.0", "AGPL-3.0", 
		"MPL-2.0", "CDDL-1.0", "MIT", "Apache-2.0", "BSD"}
	
	for _, known := range knownLicenses {
		if strings.Contains(strings.ToUpper(license), strings.ToUpper(known)) {
			return known
		}
	}
	return license
}

func licenseRiskBadge(license string) template.HTML {
	risk := getLicenseRisk(license)
	switch risk {
	case "high":
		return `<span class="severity-tag critical">高风险</span>`
	case "medium":
		return `<span class="severity-tag medium">中风险</span>`
	default:
		return `<span class="severity-tag low">低风险</span>`
	}
}

func licenseRestrictions(license string) string {
	restrictions := map[string]string{
		"GPL-2.0":  "衍生作品必须以相同许可证开源",
		"GPL-3.0":  "衍生作品必须以相同许可证开源",
		"AGPL-3.0": "网络服务也需开源",
		"LGPL-2.1": "库修改需开源，静态链接需开源",
		"LGPL-3.0": "库修改需开源",
		"MPL-2.0":  "修改的文件需开源",
		"MIT":      "需保留版权声明",
		"Apache-2.0": "需声明修改、保留版权",
	}

	normalized := normalizeLicense(license)
	if r, ok := restrictions[normalized]; ok {
		return r
	}
	return "需人工审查"
}

func GenerateFullReport(
	scanReport *scanner.ScanReport,
	cisResult *compliance.CISBenchmarkResult,
	fixReport *remediation.FixReport,
	depAnalysis *dependency.DependencyAnalysis,
	imageName string,
	outputPath string,
	blockedMessages []string,
	warningMessages []string,
	whitelistedCount int,
) error {
	allVulns := make([]scanner.Vulnerability, 0)
	allSecrets := make([]scanner.Secret, 0)
	allMisconfigs := make([]scanner.Misconfiguration, 0)

	for _, result := range scanReport.Results {
		allVulns = append(allVulns, result.Vulnerabilities...)
		allSecrets = append(allSecrets, result.Secrets...)
		allMisconfigs = append(allMisconfigs, result.Misconfigurations...)
	}

	blockedDisplays := make([]ThresholdDisplay, len(blockedMessages))
	for i, msg := range blockedMessages {
		blockedDisplays[i] = ThresholdDisplay{Message: msg, IsBlocked: true}
	}

	warningDisplays := make([]ThresholdDisplay, len(warningMessages))
	for i, msg := range warningMessages {
		warningDisplays[i] = ThresholdDisplay{Message: msg, IsBlocked: false}
	}

	cisChecks := make([]CISCheckDisplay, 0)
	cisPassed := 0
	if cisResult != nil {
		for _, check := range cisResult.Passed {
			cisChecks = append(cisChecks, CISCheckDisplay{
				ID:          check.ID,
				Title:       check.Title,
				Severity:    check.Severity,
				Status:      "PASS",
				Remediation: check.Remediation,
			})
			cisPassed++
		}
		for _, check := range cisResult.Failed {
			cisChecks = append(cisChecks, CISCheckDisplay{
				ID:          check.ID,
				Title:       check.Title,
				Severity:    check.Severity,
				Status:      "FAIL",
				Remediation: check.Remediation,
			})
		}
	}

	fixSuggestions := make([]FixSuggestionDisplay, 0)
	autoFixCount := 0
	if fixReport != nil {
		for _, s := range fixReport.Suggestions {
			fixSuggestions = append(fixSuggestions, FixSuggestionDisplay{
				ID:       s.ID,
				Type:     s.Type,
				Title:    s.Title,
				Severity: s.Severity,
				AutoFix:  s.AutoFix,
				Command:  s.Command,
			})
			if s.AutoFix {
				autoFixCount++
			}
		}
	}

	packages := make([]PackageDisplay, 0)
	licenseSummary := make(map[string]int)
	totalPackages := 0
	uniqueLicenses := 0
	highRiskLicenses := 0
	licenseIssues := make([]string, 0)

	if depAnalysis != nil {
		totalPackages = depAnalysis.TotalPackages
		uniqueLicenses = depAnalysis.UniqueLicenses
		highRiskLicenses = depAnalysis.HighRiskLicenses
		licenseSummary = depAnalysis.LicenseSummary
		licenseIssues = depAnalysis.LicenseComplianceReport()

		for _, pkg := range depAnalysis.Packages {
			packages = append(packages, PackageDisplay{
				Name:    pkg.Name,
				Version: pkg.Version,
				License: pkg.License,
			})
		}
	}

	var complianceScore float64
	if cisResult != nil && cisResult.TotalChecks > 0 {
		complianceScore = cisResult.ComplianceScore()
	}

	data := ReportData{
		ImageName:            imageName,
		ScanTime:             time.Now().Format("2006-01-02 15:04:05"),
		Passed:               len(blockedMessages) == 0,
		ComplianceScore:      complianceScore,
		BlockedViolations:    blockedDisplays,
		WarningViolations:    warningDisplays,
		VulnerabilityCount:   len(allVulns),
		VulnCritical:         scanReport.GetVulnerabilityCountBySeverity(scanner.SeverityCritical),
		VulnHigh:             scanReport.GetVulnerabilityCountBySeverity(scanner.SeverityHigh),
		VulnMedium:           scanReport.GetVulnerabilityCountBySeverity(scanner.SeverityMedium),
		VulnLow:              scanReport.GetVulnerabilityCountBySeverity(scanner.SeverityLow),
		SecretCount:          len(allSecrets),
		SecretCritical:       scanReport.GetSecretCountBySeverity(scanner.SeverityCritical),
		SecretHigh:           scanReport.GetSecretCountBySeverity(scanner.SeverityHigh),
		SecretMedium:         scanReport.GetSecretCountBySeverity(scanner.SeverityMedium),
		SecretLow:            scanReport.GetSecretCountBySeverity(scanner.SeverityLow),
		MisconfigCount:       len(allMisconfigs),
		MisconfigCritical:    scanReport.GetMisconfigurationCountBySeverity(scanner.SeverityCritical),
		MisconfigHigh:        scanReport.GetMisconfigurationCountBySeverity(scanner.SeverityHigh),
		MisconfigMedium:      scanReport.GetMisconfigurationCountBySeverity(scanner.SeverityMedium),
		MisconfigLow:         scanReport.GetMisconfigurationCountBySeverity(scanner.SeverityLow),
		Vulnerabilities:      allVulns,
		Secrets:              allSecrets,
		Misconfigurations:    allMisconfigs,
		WhitelistedSecrets:   whitelistedCount,
		CISChecks:            cisChecks,
		CISPassed:            cisPassed,
		CISTotal:             len(cisChecks),
		FixSuggestionCount:   len(fixSuggestions),
		AutoFixCount:         autoFixCount,
		FixSuggestions:       fixSuggestions,
		TotalPackages:        totalPackages,
		UniqueLicenses:       uniqueLicenses,
		HighRiskLicenses:     highRiskLicenses,
		Packages:             packages,
		LicenseSummary:       licenseSummary,
		LicenseComplianceIssues: licenseIssues,
	}

	funcMap := template.FuncMap{
		"severityClass":       severityClass,
		"truncate":            truncate,
		"licenseRiskBadge":    licenseRiskBadge,
		"licenseRestrictions": licenseRestrictions,
	}

	tmpl, err := template.New("report").Funcs(funcMap).Parse(htmlTemplate)
	if err != nil {
		return fmt.Errorf("failed to parse template: %w", err)
	}

	file, err := os.Create(outputPath)
	if err != nil {
		return fmt.Errorf("failed to create output file: %w", err)
	}
	defer file.Close()

	if err := tmpl.Execute(file, data); err != nil {
		return fmt.Errorf("failed to execute template: %w", err)
	}

	return nil
}

func PrintConsoleSummary(report *scanner.ScanReport, imageName string) {
	fmt.Println("\n" + strings.Repeat("=", 80))
	fmt.Printf("  容器安全扫描报告 - %s\n", imageName)
	fmt.Println(strings.Repeat("=", 80))

	fmt.Printf("\n📊 漏洞统计:\n")
	fmt.Printf("  总数: %d | 严重: %d | 高危: %d | 中危: %d | 低危: %d\n",
		report.TotalVulnerabilities(),
		report.GetVulnerabilityCountBySeverity(scanner.SeverityCritical),
		report.GetVulnerabilityCountBySeverity(scanner.SeverityHigh),
		report.GetVulnerabilityCountBySeverity(scanner.SeverityMedium),
		report.GetVulnerabilityCountBySeverity(scanner.SeverityLow))

	fmt.Printf("\n🔑 敏感信息统计:\n")
	fmt.Printf("  总数: %d | 严重: %d | 高危: %d | 中危: %d | 低危: %d\n",
		report.TotalSecrets(),
		report.GetSecretCountBySeverity(scanner.SeverityCritical),
		report.GetSecretCountBySeverity(scanner.SeverityHigh),
		report.GetSecretCountBySeverity(scanner.SeverityMedium),
		report.GetSecretCountBySeverity(scanner.SeverityLow))

	fmt.Printf("\n⚙️  配置风险统计:\n")
	fmt.Printf("  总数: %d | 严重: %d | 高危: %d | 中危: %d | 低危: %d\n",
		report.TotalMisconfigurations(),
		report.GetMisconfigurationCountBySeverity(scanner.SeverityCritical),
		report.GetMisconfigurationCountBySeverity(scanner.SeverityHigh),
		report.GetMisconfigurationCountBySeverity(scanner.SeverityMedium),
		report.GetMisconfigurationCountBySeverity(scanner.SeverityLow))

	fmt.Println("\n" + strings.Repeat("-", 80))
}
