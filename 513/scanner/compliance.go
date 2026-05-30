package scanner

import (
	"fmt"
	"sort"
	"strings"
	"time"
)

type ComplianceLevel string

const (
	Level1 ComplianceLevel = "等保一级"
	Level2 ComplianceLevel = "等保二级"
	Level3 ComplianceLevel = "等保三级"
)

type ComplianceCheckItem struct {
	ID          string         `json:"id"`
	Category    string         `json:"category"`
	Requirement string         `json:"requirement"`
	Description string         `json:"description"`
	Level       ComplianceLevel `json:"level"`
	CheckMethod string         `json:"check_method"`
	Reference   string         `json:"reference"`
}

type ComplianceResult struct {
	Item         ComplianceCheckItem `json:"item"`
	Status       string              `json:"status"`
	Findings     string              `json:"findings"`
	Evidence     string              `json:"evidence"`
	Remediation  string              `json:"remediation"`
	Severity     string              `json:"severity"`
	AffectedPorts []int              `json:"affected_ports"`
}

type ComplianceReport struct {
	Target        string              `json:"target"`
	Level         ComplianceLevel     `json:"level"`
	ScanTime      time.Time           `json:"scan_time"`
	TotalChecks   int                 `json:"total_checks"`
	PassedCount   int                 `json:"passed_count"`
	FailedCount   int                 `json:"failed_count"`
	WarnCount     int                 `json:"warn_count"`
	Score         int                 `json:"score"`
	Results       []ComplianceResult  `json:"results"`
	Summary       string              `json:"summary"`
}

var complianceChecklist = []ComplianceCheckItem{
	{
		ID: "NET-001", Category: "网络架构",
		Requirement: "应保证网络设备的业务处理能力满足业务需要",
		Description: "检查是否存在非必要的网络服务端口开放，确保只开放业务必需端口",
		Level: Level2,
		CheckMethod: "扫描所有开放端口，比对业务需求清单",
		Reference: "GB/T 22239-2019 8.1.2.1",
	},
	{
		ID: "NET-002", Category: "网络架构",
		Requirement: "应划分不同的网络区域，并按照方便管理和控制的原则为各网络区域分配地址",
		Description: "检查数据库端口（3306/5432/27017/6379等）是否直接暴露在非信任网络",
		Level: Level2,
		CheckMethod: "检查数据库服务端口是否对外网开放",
		Reference: "GB/T 22239-2019 8.1.2.2",
	},
	{
		ID: "NET-003", Category: "边界防护",
		Requirement: "应保证跨越边界的访问和数据流通过边界设备提供的受控接口进行通信",
		Description: "检查高危端口（Telnet/23、FTP/21、RDP/3389等）是否直接暴露",
		Level: Level3,
		CheckMethod: "扫描高危端口是否对外可达",
		Reference: "GB/T 22239-2019 8.1.3.1",
	},
	{
		ID: "NET-004", Category: "边界防护",
		Requirement: "应能够对非授权设备私自联到内部网络的行为进行检查并准确定位",
		Description: "检查是否存在未授权的新开放端口（对比历史基线）",
		Level: Level3,
		CheckMethod: "与端口历史基线对比，识别新增端口",
		Reference: "GB/T 22239-2019 8.1.3.2",
	},
	{
		ID: "NET-005", Category: "访问控制",
		Requirement: "应在网络边界或区域之间根据访问控制策略设置访问控制规则",
		Description: "检查是否存在未配置访问控制的高危端口",
		Level: Level2,
		CheckMethod: "检查高危端口是否有防火墙规则保护",
		Reference: "GB/T 22239-2019 8.1.3.3",
	},
	{
		ID: "NET-006", Category: "入侵防范",
		Requirement: "应在关键网络节点处检测、防止或限制从外部发起的网络攻击",
		Description: "检查是否存在已知漏洞的服务版本暴露",
		Level: Level3,
		CheckMethod: "检测服务版本是否包含已知CVE漏洞",
		Reference: "GB/T 22239-2019 8.1.4.1",
	},
	{
		ID: "NET-007", Category: "入侵防范",
		Requirement: "应采取技术措施对网络行为进行分析，实现对网络攻击特别是新型网络攻击行为的分析",
		Description: "检查是否存在异常端口变化（新开放/服务变更）",
		Level: Level3,
		CheckMethod: "对比历史快照，分析端口变化趋势",
		Reference: "GB/T 22239-2019 8.1.4.2",
	},
	{
		ID: "SRV-001", Category: "身份鉴别",
		Requirement: "应对登录的用户进行身份标识和鉴别，身份标识具有唯一性",
		Description: "检查数据库服务是否存在弱口令或未授权访问",
		Level: Level2,
		CheckMethod: "检测MySQL/Redis等服务的弱口令和未授权访问",
		Reference: "GB/T 22239-2019 8.2.1.1",
	},
	{
		ID: "SRV-002", Category: "身份鉴别",
		Requirement: "应采用口令、密码技术等实现身份鉴别",
		Description: "检查Redis是否配置了密码认证",
		Level: Level2,
		CheckMethod: "测试Redis是否无需密码即可连接",
		Reference: "GB/T 22239-2019 8.2.1.2",
	},
	{
		ID: "SRV-003", Category: "访问控制",
		Requirement: "应对登录的用户分配账户和权限，实现最小权限原则",
		Description: "检查数据库是否使用root/superuser账户远程登录",
		Level: Level2,
		CheckMethod: "检测MySQL root远程登录、Redis无密码等",
		Reference: "GB/T 22239-2019 8.2.2.1",
	},
	{
		ID: "SRV-004", Category: "安全审计",
		Requirement: "应启用安全审计功能，审计覆盖到每个用户",
		Description: "检查服务是否暴露了不必要的调试/管理端口（如9200/5601/8161等）",
		Level: Level3,
		CheckMethod: "扫描管理端口和调试端口是否开放",
		Reference: "GB/T 22239-2019 8.2.3.1",
	},
	{
		ID: "SRV-005", Category: "入侵防范",
		Requirement: "应遵循最小安装原则，仅安装需要的组件和应用程序",
		Description: "检查是否存在非必需服务端口开放（如Telnet、FTP等）",
		Level: Level2,
		CheckMethod: "扫描并识别非必需服务端口",
		Reference: "GB/T 22239-2019 8.2.4.1",
	},
	{
		ID: "SRV-006", Category: "入侵防范",
		Requirement: "应关闭不需要的系统服务、默认共享和高危端口",
		Description: "检查是否存在已知高危端口直接暴露（23/21/3389等）",
		Level: Level2,
		CheckMethod: "扫描高危端口是否开放",
		Reference: "GB/T 22239-2019 8.2.4.2",
	},
	{
		ID: "DAT-001", Category: "数据完整性",
		Requirement: "应采用校验技术或密码技术保证重要数据在传输过程中的完整性",
		Description: "检查数据库端口是否启用了SSL/TLS加密传输",
		Level: Level3,
		CheckMethod: "检查MySQL/PostgreSQL是否配置了SSL",
		Reference: "GB/T 22239-2019 8.3.1.1",
	},
	{
		ID: "DAT-002", Category: "数据保密性",
		Requirement: "应采用密码技术保证重要数据在传输过程中的保密性",
		Description: "检查HTTP服务是否配置了HTTPS加密",
		Level: Level2,
		CheckMethod: "检查80端口是否开放但443端口未开放",
		Reference: "GB/T 22239-2019 8.3.2.1",
	},
	{
		ID: "CTR-001", Category: "集中管控",
		Requirement: "应划分出特定的管理区域，对分布在网络中的安全设备或安全组件进行管控",
		Description: "检查管理端口（22/3389/8080等）是否限制访问来源",
		Level: Level3,
		CheckMethod: "检查管理端口是否对外网开放",
		Reference: "GB/T 22239-2019 8.4.1.1",
	},
}

var dbPorts = map[int]string{
	3306: "MySQL", 5432: "PostgreSQL", 27017: "MongoDB",
	6379: "Redis", 1433: "MSSQL", 1521: "Oracle",
}

var highRiskExposedPorts = map[int]string{
	23: "Telnet", 21: "FTP", 3389: "RDP",
	5900: "VNC", 512: "rexec", 513: "rlogin",
	514: "rsh", 523: "IBM DB2",
}

var managementPorts = map[int]string{
	22: "SSH", 3389: "RDP", 8080: "HTTP-Admin",
	8443: "HTTPS-Admin", 9090: "WebConsole",
	8161: "ActiveMQ", 7001: "WebLogic",
}

var debugAdminPorts = map[int]string{
	9200: "Elasticsearch", 5601: "Kibana",
	8161: "ActiveMQ-Admin", 7001: "WebLogic-Admin",
	4848: "GlassFish", 135: "RPC",
}

func RunComplianceCheck(target string, level ComplianceLevel, ports []PortResult, vulns []Vulnerability) *ComplianceReport {
	report := &ComplianceReport{
		Target:      target,
		Level:       level,
		ScanTime:    time.Now(),
		TotalChecks: 0,
	}

	portMap := make(map[int]PortResult)
	for _, p := range ports {
		portMap[p.Port] = p
	}

	vulnMap := make(map[int][]Vulnerability)
	for _, v := range vulns {
		vulnMap[v.Port] = append(vulnMap[v.Port], v)
	}

	for _, item := range complianceChecklist {
		if !isApplicableLevel(item.Level, level) {
			continue
		}

		report.TotalChecks++
		result := checkComplianceItem(item, portMap, vulnMap, ports)
		report.Results = append(report.Results, result)

		switch result.Status {
		case "pass":
			report.PassedCount++
		case "fail":
			report.FailedCount++
		case "warn":
			report.WarnCount++
		}
	}

	if report.TotalChecks > 0 {
		report.Score = (report.PassedCount * 100) / report.TotalChecks
	}

	report.Summary = generateComplianceSummary(report)

	return report
}

func isApplicableLevel(itemLevel, targetLevel ComplianceLevel) bool {
	levels := map[ComplianceLevel]int{Level1: 1, Level2: 2, Level3: 3}
	return levels[itemLevel] <= levels[targetLevel]
}

func checkComplianceItem(item ComplianceCheckItem, portMap map[int]PortResult, vulnMap map[int][]Vulnerability, allPorts []PortResult) ComplianceResult {
	result := ComplianceResult{
		Item:    item,
		Status:  "pass",
		Findings: "",
		Evidence: "",
		Remediation: "",
		Severity: "Info",
	}

	switch item.ID {
	case "NET-001":
		checkNonEssentialPorts(&result, portMap, allPorts)
	case "NET-002":
		checkDBExposure(&result, portMap)
	case "NET-003":
		checkHighRiskExposure(&result, portMap)
	case "NET-004":
		result.Status = "warn"
		result.Findings = "需要历史基线数据对比，请运行端口历史对比功能"
		result.Severity = "Medium"
		result.Remediation = "使用 history 子命令建立端口基线，定期对比检查"
	case "NET-005":
		checkAccessControl(&result, portMap)
	case "NET-006":
		checkKnownVulns(&result, vulnMap)
	case "NET-007":
		result.Status = "warn"
		result.Findings = "需要历史数据支持端口变化分析"
		result.Severity = "Medium"
		result.Remediation = "定期运行扫描并保存快照，启用端口变化监控"
	case "SRV-001":
		checkWeakPasswords(&result, vulnMap)
	case "SRV-002":
		checkRedisAuth(&result, vulnMap)
	case "SRV-003":
		checkLeastPrivilege(&result, vulnMap)
	case "SRV-004":
		checkDebugPorts(&result, portMap)
	case "SRV-005":
		checkNonEssentialServices(&result, portMap)
	case "SRV-006":
		checkHighRiskPorts(&result, portMap)
	case "DAT-001":
		checkDataEncryption(&result, portMap)
	case "DAT-002":
		checkHTTPSConfig(&result, portMap)
	case "CTR-001":
		checkManagementPorts(&result, portMap)
	}

	return result
}

func checkNonEssentialPorts(result *ComplianceResult, portMap map[int]PortResult, _ []PortResult) {
	var nonEssential []int
	for port, pr := range portMap {
		risk := AssessRisk(port, pr.Service)
		if risk.RiskLevel == "Medium" || risk.RiskLevel == "Low" || risk.RiskLevel == "Info" {
			if _, isDB := dbPorts[port]; !isDB {
				if _, isHR := highRiskExposedPorts[port]; !isHR {
					nonEssential = append(nonEssential, port)
				}
			}
		}
	}

	if len(nonEssential) > 5 {
		result.Status = "fail"
		result.Findings = fmt.Sprintf("发现 %d 个非必需端口开放，可能超出业务需要", len(nonEssential))
		result.Severity = "Medium"
		result.Remediation = "审查业务需求，关闭非必需端口"
		result.AffectedPorts = nonEssential
	} else if len(nonEssential) > 0 {
		result.Status = "warn"
		result.Findings = fmt.Sprintf("发现 %d 个可能非必需的端口开放", len(nonEssential))
		result.Severity = "Low"
		result.AffectedPorts = nonEssential
	} else {
		result.Evidence = "开放端口数量合理"
	}
}

func checkDBExposure(result *ComplianceResult, portMap map[int]PortResult) {
	var exposed []int
	for port, service := range dbPorts {
		if pr, ok := portMap[port]; ok {
			exposed = append(exposed, port)
			result.Evidence += fmt.Sprintf("端口 %d (%s) 对外开放; ", port, service)
			if pr.Version != "unknown" {
				versionRec := GetVersionedRecommendation(service, pr.Version)
				if versionRec.IsEOL {
					result.Evidence += fmt.Sprintf("[EOL] %s %s 已停止支持; ", service, pr.Version)
				}
			}
		}
	}

	if len(exposed) > 0 {
		result.Status = "fail"
		result.Findings = fmt.Sprintf("发现 %d 个数据库端口直接暴露: %v", len(exposed), exposed)
		result.Severity = "Critical"
		result.Remediation = "数据库端口应仅限内网访问，配置防火墙规则限制来源IP，启用SSL加密"
		result.AffectedPorts = exposed
	} else {
		result.Evidence = "未发现数据库端口直接暴露"
	}
}

func checkHighRiskExposure(result *ComplianceResult, portMap map[int]PortResult) {
	var exposed []int
	for port, service := range highRiskExposedPorts {
		if _, ok := portMap[port]; ok {
			exposed = append(exposed, port)
		}
	}

	if len(exposed) > 0 {
		result.Status = "fail"
		result.Findings = fmt.Sprintf("发现 %d 个高危端口直接暴露: %v", len(exposed), exposed)
		result.Severity = "Critical"
		result.Remediation = "立即关闭Telnet(23)/FTP(21)/RDP(3389)等高危端口的公网访问，使用VPN或跳板机替代"
		result.AffectedPorts = exposed
	} else {
		result.Evidence = "未发现高危端口直接暴露"
	}
}

func checkAccessControl(result *ComplianceResult, portMap map[int]PortResult) {
	var unprotected []int
	for port := range portMap {
		risk := AssessRisk(port, portMap[port].Service)
		if risk.RiskLevel == "Critical" || risk.RiskLevel == "High" {
			unprotected = append(unprotected, port)
		}
	}

	if len(unprotected) > 0 {
		result.Status = "fail"
		result.Findings = fmt.Sprintf("发现 %d 个高危端口未配置访问控制: %v", len(unprotected), unprotected)
		result.Severity = "High"
		result.Remediation = "为所有高危端口配置防火墙访问控制规则，限制来源IP"
		result.AffectedPorts = unprotected
	} else {
		result.Evidence = "高危端口已配置访问控制"
	}
}

func checkKnownVulns(result *ComplianceResult, vulnMap map[int][]Vulnerability) {
	var criticalVulns, highVulns []Vulnerability
	for _, vulns := range vulnMap {
		for _, v := range vulns {
			if v.Severity == "Critical" {
				criticalVulns = append(criticalVulns, v)
			} else if v.Severity == "High" {
				highVulns = append(highVulns, v)
			}
		}
	}

	if len(criticalVulns) > 0 {
		result.Status = "fail"
		result.Findings = fmt.Sprintf("发现 %d 个严重漏洞和 %d 个高危漏洞", len(criticalVulns), len(highVulns))
		result.Severity = "Critical"
		result.Remediation = "立即修补所有已知漏洞，升级到安全版本"
	} else if len(highVulns) > 0 {
		result.Status = "fail"
		result.Findings = fmt.Sprintf("发现 %d 个高危漏洞", len(highVulns))
		result.Severity = "High"
		result.Remediation = "尽快修补高危漏洞，升级到安全版本"
	} else {
		result.Evidence = "未发现已知高危漏洞"
	}
}

func checkWeakPasswords(result *ComplianceResult, vulnMap map[int][]Vulnerability) {
	for _, vulns := range vulnMap {
		for _, v := range vulns {
			if v.Type == "Weak Password" || v.Type == "Unauthorized Access" {
				result.Status = "fail"
				result.Findings = fmt.Sprintf("发现弱口令/未授权访问: %s", v.Description)
				result.Severity = "Critical"
				result.Remediation = "立即修改弱口令，配置强密码策略，启用认证机制"
				return
			}
		}
	}
	result.Evidence = "未发现弱口令或未授权访问"
}

func checkRedisAuth(result *ComplianceResult, vulnMap map[int][]Vulnerability) {
	for _, vulns := range vulnMap {
		for _, v := range vulns {
			if v.Service == "Redis" && v.Type == "Unauthorized Access" {
				result.Status = "fail"
				result.Findings = "Redis服务未配置密码认证"
				result.Severity = "Critical"
				result.Remediation = "配置Redis密码(requirepass)，绑定localhost，禁用危险命令"
				result.AffectedPorts = []int{6379}
				return
			}
		}
	}
	result.Evidence = "Redis已配置认证或端口未开放"
}

func checkLeastPrivilege(result *ComplianceResult, vulnMap map[int][]Vulnerability) {
	for _, vulns := range vulnMap {
		for _, v := range vulns {
			if strings.Contains(v.Description, "root") {
				result.Status = "fail"
				result.Findings = "数据库使用root/superuser账户远程访问"
				result.Severity = "High"
				result.Remediation = "创建普通权限账户，禁止root远程登录，实施最小权限原则"
				return
			}
		}
	}
	result.Evidence = "数据库未使用特权账户远程登录"
}

func checkDebugPorts(result *ComplianceResult, portMap map[int]PortResult) {
	var exposed []int
	for port, service := range debugAdminPorts {
		if _, ok := portMap[port]; ok {
			exposed = append(exposed, port)
			result.Evidence += fmt.Sprintf("端口 %d (%s) 开放; ", port, service)
		}
	}

	if len(exposed) > 0 {
		result.Status = "fail"
		result.Findings = fmt.Sprintf("发现 %d 个调试/管理端口暴露: %v", len(exposed), exposed)
		result.Severity = "High"
		result.Remediation = "关闭调试和管理端口的公网访问，仅限内网或本地访问"
		result.AffectedPorts = exposed
	} else {
		result.Evidence = "未发现调试/管理端口暴露"
	}
}

func checkNonEssentialServices(result *ComplianceResult, portMap map[int]PortResult) {
	var found []int
	if _, ok := portMap[23]; ok {
		found = append(found, 23)
	}
	if _, ok := portMap[21]; ok {
		found = append(found, 21)
	}
	if _, ok := portMap[512]; ok {
		found = append(found, 512)
	}
	if _, ok := portMap[513]; ok {
		found = append(found, 513)
	}
	if _, ok := portMap[514]; ok {
		found = append(found, 514)
	}

	if len(found) > 0 {
		result.Status = "fail"
		result.Findings = fmt.Sprintf("发现非必需服务端口: %v", found)
		result.Severity = "High"
		result.Remediation = "关闭Telnet(23)、FTP(21)、r系列服务(512-514)，使用SSH/SFTP替代"
		result.AffectedPorts = found
	} else {
		result.Evidence = "无非必需服务端口"
	}
}

func checkHighRiskPorts(result *ComplianceResult, portMap map[int]PortResult) {
	for port := range highRiskExposedPorts {
		if _, ok := portMap[port]; ok {
			result.Status = "fail"
			result.Findings = fmt.Sprintf("高危端口 %d 开放", port)
			result.Severity = "Critical"
			result.Remediation = "立即关闭高危端口，使用安全的替代方案"
			result.AffectedPorts = []int{port}
			return
		}
	}
	result.Evidence = "未发现高危端口开放"
}

func checkDataEncryption(result *ComplianceResult, portMap map[int]PortResult) {
	for port := range dbPorts {
		if _, ok := portMap[port]; ok {
			result.Status = "warn"
			result.Findings = fmt.Sprintf("数据库端口 %d 开放，需确认是否启用SSL/TLS加密传输", port)
			result.Severity = "Medium"
			result.Remediation = "启用数据库SSL/TLS加密连接，配置证书认证"
			result.AffectedPorts = []int{port}
			return
		}
	}
	result.Evidence = "数据库端口未暴露或已确认加密"
}

func checkHTTPSConfig(result *ComplianceResult, portMap map[int]PortResult) {
	_, hasHTTP := portMap[80]
	_, hasHTTPS := portMap[443]
	_, hasHTTPProxy := portMap[8080]

	if hasHTTP && !hasHTTPS {
		result.Status = "fail"
		result.Findings = "HTTP(80)端口开放但未配置HTTPS(443)，数据传输未加密"
		result.Severity = "High"
		result.Remediation = "配置HTTPS加密传输，将HTTP请求重定向到HTTPS"
		result.AffectedPorts = []int{80}
	} else if hasHTTPProxy && !hasHTTPS {
		result.Status = "warn"
		result.Findings = "HTTP代理端口开放但未检测到HTTPS"
		result.Severity = "Medium"
		result.Remediation = "确保所有Web服务启用HTTPS加密"
	} else if hasHTTPS {
		result.Evidence = "已配置HTTPS加密传输"
	}
}

func checkManagementPorts(result *ComplianceResult, portMap map[int]PortResult) {
	var exposed []int
	for port, service := range managementPorts {
		if _, ok := portMap[port]; ok {
			exposed = append(exposed, port)
			result.Evidence += fmt.Sprintf("端口 %d (%s) 开放; ", port, service)
		}
	}

	if len(exposed) > 0 {
		result.Status = "fail"
		result.Findings = fmt.Sprintf("发现 %d 个管理端口对外暴露: %v", len(exposed), exposed)
		result.Severity = "High"
		result.Remediation = "管理端口应限制来源IP，仅允许从管理网络访问，建议使用VPN或堡垒机"
		result.AffectedPorts = exposed
	} else {
		result.Evidence = "管理端口未直接暴露"
	}
}

func generateComplianceSummary(report *ComplianceReport) string {
	var sb strings.Builder

	sb.WriteString(fmt.Sprintf("等保合规评估结果 - %s\n", report.Level))
	sb.WriteString(fmt.Sprintf("扫描目标: %s\n", report.Target))
	sb.WriteString(fmt.Sprintf("合规评分: %d/100\n", report.Score))
	sb.WriteString(fmt.Sprintf("检查项数: %d (通过: %d, 不通过: %d, 警告: %d)\n",
		report.TotalChecks, report.PassedCount, report.FailedCount, report.WarnCount))

	if report.Score >= 90 {
		sb.WriteString("合规等级: 优秀 ✅\n")
	} else if report.Score >= 70 {
		sb.WriteString("合规等级: 良好 ⚠️\n")
	} else if report.Score >= 50 {
		sb.WriteString("合规等级: 需改进 ❌\n")
	} else {
		sb.WriteString("合规等级: 不合规 🚨\n")
	}

	var criticalFails, highFails int
	for _, r := range report.Results {
		if r.Status == "fail" {
			if r.Severity == "Critical" {
				criticalFails++
			} else if r.Severity == "High" {
				highFails++
			}
		}
	}

	if criticalFails > 0 {
		sb.WriteString(fmt.Sprintf("\n⚠️ 存在 %d 个严重不合规项，需要立即整改！\n", criticalFails))
	}
	if highFails > 0 {
		sb.WriteString(fmt.Sprintf("⚠️ 存在 %d 个高危不合规项，建议尽快整改\n", highFails))
	}

	return sb.String()
}

func (report *ComplianceReport) PrintConsole() {
	fmt.Println("\n" + strings.Repeat("=", 80))
	fmt.Println("【等保2.0合规检查报告】")
	fmt.Println(strings.Repeat("=", 80))

	fmt.Println(report.Summary)

	fmt.Println("\n" + strings.Repeat("-", 80))
	fmt.Println("检查项详情:")
	fmt.Println(strings.Repeat("-", 80))

	sort.Slice(report.Results, func(i, j int) bool {
		priority := map[string]int{"Critical": 0, "High": 1, "Medium": 2, "Low": 3, "Info": 4}
		statusPriority := map[string]int{"fail": 0, "warn": 1, "pass": 2}
		if statusPriority[report.Results[i].Status] != statusPriority[report.Results[j].Status] {
			return statusPriority[report.Results[i].Status] < statusPriority[report.Results[j].Status]
		}
		return priority[report.Results[i].Severity] < priority[report.Results[j].Severity]
	})

	for _, r := range report.Results {
		statusIcon := "✅"
		if r.Status == "fail" {
			statusIcon = "❌"
		} else if r.Status == "warn" {
			statusIcon = "⚠️"
		}

		color := GetRiskColor(r.Severity)
		reset := "\033[0m"

		fmt.Printf("\n%s [%s] %s - %s%s%s\n", statusIcon, r.Item.ID, r.Item.Category, color, r.Item.Requirement, reset)
		fmt.Printf("   等级: %s | 参考: %s\n", r.Item.Level, r.Item.Reference)

		if r.Findings != "" {
			fmt.Printf("   发现: %s\n", r.Findings)
		}
		if r.Evidence != "" {
			fmt.Printf("   证据: %s\n", r.Evidence)
		}
		if r.Remediation != "" {
			fmt.Printf("   整改: %s\n", r.Remediation)
		}
		if len(r.AffectedPorts) > 0 {
			fmt.Printf("   涉及端口: %v\n", r.AffectedPorts)
		}
	}

	fmt.Println("\n" + strings.Repeat("=", 80))
}
