package scanner

import (
	"fmt"
	"regexp"
	"sort"
	"strconv"
	"strings"
	"time"
)

type VersionVulnerability struct {
	CVE            string   `json:"cve"`
	CVSSScore      float64  `json:"cvss_score"`
	Severity       string   `json:"severity"`
	Description    string   `json:"description"`
	AffectedVersions []string `json:"affected_versions"`
	FixedVersions  []string `json:"fixed_versions"`
	Recommendations []string `json:"recommendations"`
	ReferenceURLs  []string `json:"reference_urls"`
	PublishedDate  string   `json:"published_date"`
}

type VersionedRecommendation struct {
	Service        string                  `json:"service"`
	Version        string                  `json:"version"`
	RiskLevel      string                  `json:"risk_level"`
	IsLatest       bool                    `json:"is_latest"`
	IsEOL          bool                    `json:"is_eol"`
	Vulnerabilities []VersionVulnerability `json:"vulnerabilities"`
	GeneralRisks   []string                `json:"general_risks"`
	Recommendations []string                `json:"recommendations"`
	UpgradePath    []string                `json:"upgrade_path"`
	LatestVersion  string                  `json:"latest_version"`
	SecurityNotes  []string                `json:"security_notes"`
}

type VersionedAdviceDB struct {
	LastUpdated time.Time
	Data        map[string]map[string]VersionedRecommendation
}

var versionedAdviceDB = map[string]map[string]VersionedRecommendation{
	"redis": {
		"default": {
			Service: "Redis",
			Version: "未知版本",
			RiskLevel: "Critical",
			Recommendations: []string{
				"配置Redis密码认证 (requirepass)",
				"绑定到localhost或内网接口 (bind 127.0.0.1)",
				"禁用危险命令 (FLUSHDB, FLUSHALL, KEYS, PEXPIRE, DEL, CONFIG, SHUTDOWN, BGREWRITEAOF, BGSAVE)",
				"启用rename-command重命名敏感命令",
				"配置防火墙限制访问IP",
				"不要以root身份运行Redis",
				"启用TLS加密连接 (Redis 6+)",
			},
		},
		"7.0": {
			Service: "Redis",
			Version: "7.0.x",
			RiskLevel: "Medium",
			IsLatest: false,
			LatestVersion: "7.2",
			Vulnerabilities: []VersionVulnerability{
				{
					CVE: "CVE-2023-41053",
					CVSSScore: 7.5,
					Severity: "High",
					Description: "Redis 7.0.x 存在CLUSTER SLOTS命令导致的崩溃漏洞",
					AffectedVersions: []string{"7.0.0", "7.0.12"},
					FixedVersions: []string{"7.0.13"},
					Recommendations: []string{"升级到 Redis 7.0.13 或 7.2.x"},
				},
				{
					CVE: "CVE-2023-41056",
					CVSSScore: 8.1,
					Severity: "High",
					Description: "Redis 7.0.x 存在MSETNX命令导致的堆缓冲区溢出",
					AffectedVersions: []string{"7.0.0", "7.0.12"},
					FixedVersions: []string{"7.0.13"},
					Recommendations: []string{"立即升级到 Redis 7.0.13 或更高版本"},
				},
			},
			SecurityNotes: []string{
				"Redis 7.0.x 支持TLS加密功能，建议启用",
				"支持ACL访问控制列表",
			},
			Recommendations: []string{
				"立即升级到 Redis 7.0.13 或 7.2.x 版本",
				"启用ACL访问控制列表",
				"配置TLS加密连接",
				"配置密码认证",
			},
			UpgradePath: []string{"7.0.13", "7.2.x"},
		},
		"7.2": {
			Service: "Redis",
			Version: "7.2.x",
			RiskLevel: "Low",
			IsLatest: true,
			LatestVersion: "7.2",
			SecurityNotes: []string{
				"当前最新稳定版本",
				"增强了安全功能",
				"支持Sharded Pub/Sub",
			},
			Recommendations: []string{
				"保持版本更新，定期检查安全补丁",
				"启用ACL访问控制列表",
				"配置TLS加密连接",
				"配置密码认证",
			},
		},
		"6.0": {
			Service: "Redis",
			Version: "6.0.x",
			RiskLevel: "High",
			IsLatest: false,
			IsEOL: false,
			LatestVersion: "7.2",
			Vulnerabilities: []VersionVulnerability{
				{
					CVE: "CVE-2021-32625",
					CVSSScore: 8.8,
					Severity: "High",
					Description: "Redis 6.0.x 存在STRALGO LCS命令的整数溢出漏洞",
					AffectedVersions: []string{"6.0.0", "6.0.14"},
					FixedVersions: []string{"6.0.15", "6.2.x"},
					Recommendations: []string{"升级到 Redis 6.0.15 或更高版本"},
				},
				{
					CVE: "CVE-2021-32626",
					CVSSScore: 8.8,
					Severity: "High",
					Description: "Redis 6.0.x 存在Lua脚本执行的堆溢出漏洞",
					AffectedVersions: []string{"6.0.0", "6.0.14"},
					FixedVersions: []string{"6.0.15"},
					Recommendations: []string{"禁用Lua脚本或升级版本"},
				},
			},
			Recommendations: []string{
				"升级到 Redis 6.0.15 或 6.2.x，建议升级到 7.2.x",
				"启用ACL访问控制列表 (Redis 6+ 支持)",
				"配置TLS加密连接 (Redis 6+ 支持)",
			},
			UpgradePath: []string{"6.0.15", "6.2.x", "7.2.x"},
		},
		"5.0": {
			Service: "Redis",
			Version: "5.0.x",
			RiskLevel: "Critical",
			IsLatest: false,
			IsEOL: true,
			LatestVersion: "7.2",
			Vulnerabilities: []VersionVulnerability{
				{
					CVE: "CVE-2018-12326",
					CVSSScore: 7.5,
					Severity: "High",
					Description: "Redis 4.0/5.0 存在CONFIG SET maxmemory导致的缓冲区溢出",
					AffectedVersions: []string{"4.0.0", "5.0.0"},
					FixedVersions: []string{"5.0.1"},
					Recommendations: []string{"升级到最新版本"},
				},
			},
			SecurityNotes: []string{
				"Redis 5.0.x 已停止安全支持 (EOL)",
				"不支持TLS加密",
				"不支持ACL访问控制",
			},
			Recommendations: []string{
				"紧急升级到 Redis 7.2.x 版本",
				"在升级前加强网络隔离",
				"配置严格的防火墙规则",
				"不要暴露到公网",
			},
			UpgradePath: []string{"6.0.x", "6.2.x", "7.2.x"},
		},
	},
	"mysql": {
		"default": {
			Service: "MySQL",
			Version: "未知版本",
			RiskLevel: "High",
			Recommendations: []string{
				"修改root默认密码，使用强密码策略",
				"删除匿名账户",
				"删除test数据库",
				"限制root用户只能本地登录",
				"启用SSL/TLS加密连接",
				"配置防火墙限制访问IP",
				"定期备份数据库",
				"启用审计日志",
			},
		},
		"8.0": {
			Service: "MySQL",
			Version: "8.0.x",
			RiskLevel: "Medium",
			IsLatest: false,
			LatestVersion: "8.2",
			Vulnerabilities: []VersionVulnerability{
				{
					CVE: "CVE-2024-21096",
					CVSSScore: 7.5,
					Severity: "High",
					Description: "MySQL 8.0.x 存在Server: Security相关的远程代码执行漏洞",
					AffectedVersions: []string{"8.0.0", "8.0.35"},
					FixedVersions: []string{"8.0.36"},
					Recommendations: []string{"升级到 MySQL 8.0.36 或 8.2.0"},
				},
			},
			SecurityNotes: []string{
				"支持caching_sha2_password认证插件，安全性更高",
				"支持InnoDB数据加密 (TDE)",
				"支持审计插件",
			},
			Recommendations: []string{
				"升级到 MySQL 8.0.36 或 8.2.0",
				"使用caching_sha2_password认证插件",
				"启用SSL/TLS加密",
				"配置TDE透明数据加密",
			},
			UpgradePath: []string{"8.0.36", "8.2.x"},
		},
		"5.7": {
			Service: "MySQL",
			Version: "5.7.x",
			RiskLevel: "Critical",
			IsLatest: false,
			IsEOL: true,
			LatestVersion: "8.2",
			Vulnerabilities: []VersionVulnerability{
				{
					CVE: "CVE-2019-5443",
					CVSSScore: 10.0,
					Severity: "Critical",
					Description: "MySQL 5.7.x 存在远程代码执行漏洞",
					AffectedVersions: []string{"5.7.0", "5.7.25"},
					FixedVersions: []string{"5.7.26"},
					Recommendations: []string{"立即升级或隔离"},
				},
			},
			SecurityNotes: []string{
				"MySQL 5.7.x 已于2023年10月停止支持 (EOL)",
				"不再接收安全更新",
				"使用mysql_native_password认证插件，安全性较低",
			},
			Recommendations: []string{
				"立即规划升级到 MySQL 8.2.x",
				"在升级前加强网络隔离",
				"禁用不必要的功能",
				"启用审计日志",
			},
			UpgradePath: []string{"8.0.x", "8.2.x"},
		},
		"10.11": {
			Service: "MariaDB",
			Version: "10.11.x",
			RiskLevel: "Low",
			IsLatest: true,
			LatestVersion: "10.11",
			Recommendations: []string{
				"保持版本更新，定期检查安全补丁",
				"启用SSL/TLS加密",
				"使用ed25519认证插件",
			},
		},
	},
	"ssh": {
		"default": {
			Service: "SSH",
			Version: "未知版本",
			RiskLevel: "Low",
			Recommendations: []string{
				"禁用root远程登录 (PermitRootLogin no)",
				"使用密钥认证替代密码认证",
				"修改默认端口 (Port 22)",
				"配置fail2ban防止暴力破解",
				"禁用空密码 (PermitEmptyPasswords no)",
				"限制登录用户 (AllowUsers, AllowGroups)",
				"启用TCP Wrappers",
				"设置登录超时时间",
			},
		},
		"7.4": {
			Service: "OpenSSH",
			Version: "7.4.x",
			RiskLevel: "Critical",
			IsLatest: false,
			IsEOL: true,
			LatestVersion: "9.3",
			Vulnerabilities: []VersionVulnerability{
				{
					CVE: "CVE-2023-38408",
					CVSSScore: 9.8,
					Severity: "Critical",
					Description: "OpenSSH 存在远程代码执行漏洞，攻击者可通过转发代理执行代码",
					AffectedVersions: []string{"5.8", "8.5"},
					FixedVersions: []string{"8.5p1"},
					Recommendations: []string{"立即升级到最新版本，或禁用ForwardAgent"},
				},
				{
					CVE: "CVE-2020-14145",
					CVSSScore: 7.5,
					Severity: "High",
					Description: "OpenSSH 7.4 存在scp命令路径遍历漏洞",
					AffectedVersions: []string{"7.4", "8.3"},
					FixedVersions: []string{"8.4"},
					Recommendations: []string{"升级到 OpenSSH 8.4 或更高版本"},
				},
			},
			SecurityNotes: []string{
				"OpenSSH 7.4 是较旧版本，存在多个已知漏洞",
				"建议尽快升级",
			},
			Recommendations: []string{
				"立即升级到 OpenSSH 8.4 或更高版本，建议升级到 9.3+",
				"在升级前禁用Agent转发 (ForwardAgent no)",
				"禁用X11转发",
			},
			UpgradePath: []string{"8.4p1", "8.9p1", "9.3p1"},
		},
		"8.9": {
			Service: "OpenSSH",
			Version: "8.9.x",
			RiskLevel: "Low",
			IsLatest: false,
			LatestVersion: "9.3",
			SecurityNotes: []string{
				"较新的稳定版本",
				"支持FIDO/U2F认证",
				"支持SFTP服务器增强",
			},
			Recommendations: []string{
				"考虑升级到 OpenSSH 9.3 获取最新安全更新",
				"使用ed25519或ecdsa-sk密钥",
			},
			UpgradePath: []string{"9.3p1"},
		},
		"9.3": {
			Service: "OpenSSH",
			Version: "9.3.x",
			RiskLevel: "Low",
			IsLatest: true,
			LatestVersion: "9.3",
			SecurityNotes: []string{
				"当前最新稳定版本",
				"增强了密钥交换算法",
				"支持更多安全特性",
			},
			Recommendations: []string{
				"保持版本更新",
				"使用现代认证方式",
			},
		},
	},
	"http": {
		"default": {
			Service: "HTTP",
			Version: "未知版本",
			RiskLevel: "Medium",
			Recommendations: []string{
				"隐藏服务器版本信息 (ServerTokens, ServerSignature)",
				"启用HTTPS并重定向HTTP到HTTPS",
				"配置安全头 (HSTS, CSP, X-Frame-Options, X-XSS-Protection, X-Content-Type-Options)",
				"禁用不安全的HTTP方法 (TRACE, DELETE, OPTIONS)",
				"启用访问日志",
				"配置WAF Web应用防火墙",
			},
		},
		"nginx/1.18": {
			Service: "Nginx",
			Version: "1.18.x",
			RiskLevel: "Medium",
			IsLatest: false,
			LatestVersion: "1.25",
			Vulnerabilities: []VersionVulnerability{
				{
					CVE: "CVE-2022-41741",
					CVSSScore: 7.0,
					Severity: "High",
					Description: "Nginx 1.18.x 存在ngx_http_mp4_module缓冲区溢出漏洞",
					AffectedVersions: []string{"1.1.4", "1.22.0"},
					FixedVersions: []string{"1.22.1", "1.23.2"},
					Recommendations: []string{"升级到 Nginx 1.22.1 或更高版本，或禁用mp4模块"},
				},
			},
			Recommendations: []string{
				"升级到 Nginx 1.24.0 或 1.25.x",
				"禁用不必要的模块",
			},
			UpgradePath: []string{"1.22.1", "1.24.0", "1.25.x"},
		},
		"nginx/1.24": {
			Service: "Nginx",
			Version: "1.24.x",
			RiskLevel: "Low",
			IsLatest: false,
			LatestVersion: "1.25",
			SecurityNotes: []string{
				"较新的稳定版本",
				"修复了多个安全问题",
			},
			Recommendations: []string{
				"考虑升级到主线版本 1.25.x 获取最新功能",
				"配置HTTP/3支持",
			},
			UpgradePath: []string{"1.25.x"},
		},
		"apache/2.4": {
			Service: "Apache HTTP Server",
			Version: "2.4.x",
			RiskLevel: "Medium",
			IsLatest: true,
			LatestVersion: "2.4",
			Vulnerabilities: []VersionVulnerability{
				{
					CVE: "CVE-2023-45802",
					CVSSScore: 7.5,
					Severity: "High",
					Description: "Apache HTTP Server 2.4.x 存在mod_http2内存泄漏漏洞",
					AffectedVersions: []string{"2.4.0", "2.4.57"},
					FixedVersions: []string{"2.4.58"},
					Recommendations: []string{"升级到 Apache 2.4.58 或更高版本"},
				},
			},
			Recommendations: []string{
				"保持版本更新，至少 2.4.58+",
				"禁用不必要的模块",
				"使用mod_security WAF",
			},
		},
	},
}

func GetVersionedRecommendation(service, version string) VersionedRecommendation {
	service = strings.ToLower(service)
	version = strings.ToLower(version)

	serviceData, ok := versionedAdviceDB[service]
	if !ok {
		return getDefaultRecommendation(service)
	}

	majorVersion := extractMajorVersion(version)
	if rec, ok := serviceData[majorVersion]; ok {
		rec.Version = version
		return rec
	}

	if rec, ok := serviceData["default"]; ok {
		return rec
	}

	return getDefaultRecommendation(service)
}

func getDefaultRecommendation(service string) VersionedRecommendation {
	return VersionedRecommendation{
		Service:   service,
		Version:   "未知版本",
		RiskLevel: "Medium",
		Recommendations: []string{
			"确保服务保持最新版本",
			"根据业务需要开放端口",
			"配置适当的访问控制",
		},
	}
}

func extractMajorVersion(version string) string {
	if strings.Contains(version, "nginx/") {
		re := regexp.MustCompile(`nginx/(\d+\.\d+)`)
		matches := re.FindStringSubmatch(version)
		if len(matches) > 1 {
			return "nginx/" + matches[1]
		}
		return "nginx/default"
	}

	if strings.Contains(version, "apache/") {
		re := regexp.MustCompile(`apache/(\d+\.\d+)`)
		matches := re.FindStringSubmatch(version)
		if len(matches) > 1 {
			return "apache/" + matches[1]
		}
		return "apache/default"
	}

	re := regexp.MustCompile(`(\d+\.\d+)`)
	matches := re.FindStringSubmatch(version)
	if len(matches) > 1 {
		return matches[1]
	}

	return "default"
}

func CompareVersions(v1, v2 string) int {
	v1Parts := parseVersion(v1)
	v2Parts := parseVersion(v2)

	for i := 0; i < len(v1Parts) && i < len(v2Parts); i++ {
		if v1Parts[i] > v2Parts[i] {
			return 1
		} else if v1Parts[i] < v2Parts[i] {
			return -1
		}
	}

	return 0
}

func parseVersion(version string) []int {
	re := regexp.MustCompile(`\d+`)
	matches := re.FindAllString(version, -1)
	parts := make([]int, 0, len(matches))

	for _, m := range matches {
		if n, err := strconv.Atoi(m); err == nil {
			parts = append(parts, n)
		}
	}

	return parts
}

func AssessRiskWithVersion(port int, service, version string) RiskAssessment {
	baseAssessment := AssessRisk(port, service)

	if version == "" || version == "unknown" {
		return baseAssessment
	}

	versionedRec := GetVersionedRecommendation(service, version)

	description := baseAssessment.Description
	if versionedRec.IsEOL {
		description += "⚠️  该版本已停止支持(EOL)，存在严重安全风险！"
	}

	if len(versionedRec.Vulnerabilities) > 0 {
		for _, vuln := range versionedRec.Vulnerabilities {
			description += fmt.Sprintf("\n   - %s (CVSS: %.1f) - %s", vuln.CVE, vuln.CVSSScore, vuln.Description)
		}
	}

	var recommendations []string
	recommendations = append(recommendations, versionedRec.Recommendations...)
	recommendations = append(recommendations, baseAssessment.Recommendations...)

	if len(versionedRec.UpgradePath) > 0 {
		upgradeNote := fmt.Sprintf("升级路径: %s", strings.Join(versionedRec.UpgradePath, " → "))
		recommendations = append([]string{upgradeNote}, recommendations...)
	}

	riskLevel := baseAssessment.RiskLevel
	if versionedRec.RiskLevel != "" {
		riskPriority := map[string]int{"Critical": 0, "High": 1, "Medium": 2, "Low": 3, "Info": 4}
		if riskPriority[versionedRec.RiskLevel] < riskPriority[riskLevel] {
			riskLevel = versionedRec.RiskLevel
		}
	}

	return RiskAssessment{
		Port:            port,
		Service:         service,
		RiskLevel:       riskLevel,
		Description:     description,
		Recommendations: recommendations,
	}
}

func AssessAllRisksWithVersion(ports []PortResult) []RiskAssessment {
	assessments := make([]RiskAssessment, 0, len(ports))
	for _, port := range ports {
		assessment := AssessRiskWithVersion(port.Port, port.Service, port.Version)
		assessments = append(assessments, assessment)
	}
	return assessments
}

func GetAllServicesWithVersions() map[string][]string {
	result := make(map[string][]string)
	for service, versions := range versionedAdviceDB {
		var versionList []string
		for v := range versions {
			if v != "default" {
				versionList = append(versionList, v)
			}
		}
		sort.Strings(versionList)
		result[service] = versionList
	}
	return result
}

func SearchVulnerabilities(service, keyword string) []VersionVulnerability {
	var results []VersionVulnerability
	service = strings.ToLower(service)

	if serviceData, ok := versionedAdviceDB[service]; ok {
		for _, rec := range serviceData {
			for _, vuln := range rec.Vulnerabilities {
				if keyword == "" ||
					strings.Contains(strings.ToLower(vuln.CVE), strings.ToLower(keyword)) ||
					strings.Contains(strings.ToLower(vuln.Description), strings.ToLower(keyword)) {
					results = append(results, vuln)
				}
			}
		}
	}

	return results
}
