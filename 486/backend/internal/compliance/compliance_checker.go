package compliance

import (
	"fmt"
	"time"

	"servicemesh-policy/internal/models"
)

type ComplianceChecker struct{}

func NewComplianceChecker() *ComplianceChecker {
	return &ComplianceChecker{}
}

func (cc *ComplianceChecker) RunComplianceCheck(req *models.ComplianceCheckRequest) (*models.ComplianceCheckResult, error) {
	result := &models.ComplianceCheckResult{
		CheckID:      generateCheckID(),
		Standard:     req.Standard,
		StandardName: getStandardName(req.Standard),
		Status:       "completed",
		CheckedAt:    time.Now(),
	}

	var controls []models.ComplianceControl

	switch req.Standard {
	case models.ComplianceStandardPCI:
		controls = cc.checkPCIDSS(req)
	case models.ComplianceStandardGDPR:
		controls = cc.checkGDPR(req)
	case models.ComplianceStandardHIPAA:
		controls = cc.checkHIPAA(req)
	case models.ComplianceStandardSOC2:
		controls = cc.checkSOC2(req)
	case models.ComplianceStandardISO27001:
		controls = cc.checkISO27001(req)
	default:
		controls = cc.checkPCIDSS(req)
	}

	result.Controls = controls
	result.Summary = cc.calculateSummary(controls)
	result.OverallScore = cc.calculateOverallScore(controls)
	result.ComplianceRate = float64(result.Summary.PassedControls) / float64(result.Summary.TotalControls) * 100

	passedControls := make([]models.ComplianceControl, 0)
	failedControls := make([]models.ComplianceControl, 0)
	for _, c := range controls {
		if c.Passed {
			passedControls = append(passedControls, c)
		} else {
			failedControls = append(failedControls, c)
		}
	}
	result.PassedControls = passedControls
	result.FailedControls = failedControls

	return result, nil
}

func (cc *ComplianceChecker) checkPCIDSS(req *models.ComplianceCheckRequest) []models.ComplianceControl {
	return []models.ComplianceControl{
		{
			ID:          "pci-dss-2.1",
			Name:        "传输加密要求",
			Description: "使用强加密技术传输持卡人数据",
			Requirement: "所有持卡人数据传输必须使用 TLS 1.2 或更高版本",
			Category:    "加密传输",
			Severity:    "critical",
			Status:      "passed",
			Passed:      true,
			Evidence: []string{
				"所有命名空间已配置 mTLS STRICT 模式",
				"Ingress 网关配置 TLS 1.2+",
			},
			RemediationGuidance: "确保所有服务通信启用 mTLS",
			References: []string{
				"PCI DSS Requirement 2.2.3",
				"PCI DSS Requirement 4.1",
			},
		},
		{
			ID:          "pci-dss-3.1",
			Name:        "静态数据加密",
			Description: "保护存储的持卡人数据",
			Requirement: "存储的持卡人数据必须加密",
			Category:    "数据保护",
			Severity:    "critical",
			Status:      "failed",
			Passed:      false,
			FailedReasons: []string{
				"未检测到静态数据加密策略",
				"数据库连接未强制加密",
			},
			AffectedResources: []string{
				"prod/payment-service",
				"prod/card-vault-service",
			},
			RemediationGuidance: "1. 配置数据库连接加密 2. 启用静态数据加密",
			References: []string{
				"PCI DSS Requirement 3.4",
			},
		},
		{
			ID:          "pci-dss-6.2",
			Name:        "访问控制",
			Description: "按业务需要限制系统访问",
			Requirement: "实施最小权限原则",
			Category:    "访问控制",
			Severity:    "high",
			Status:      "passed",
			Passed:      true,
			Evidence: []string{
				"已配置 23 条 AuthorizationPolicy",
				"默认拒绝策略已启用",
				"服务间访问受 RBAC 控制",
			},
			RemediationGuidance: "定期审计授权策略",
			References: []string{
				"PCI DSS Requirement 7.1",
				"PCI DSS Requirement 7.2",
			},
		},
		{
			ID:          "pci-dss-7.1",
			Name:        "身份认证",
			Description: "唯一标识和验证用户",
			Requirement: "所有用户必须经过身份验证",
			Category:    "身份认证",
			Severity:    "high",
			Status:      "warning",
			Passed:      false,
			FailedReasons: []string{
				"部分服务未配置 JWT 认证",
				"存在匿名访问路径",
			},
			AffectedResources: []string{
				"staging/public-api",
				"dev/user-service",
			},
			RemediationGuidance: "1. 为所有 API 配置 JWT 认证 2. 关闭匿名访问",
			References: []string{
				"PCI DSS Requirement 8.1",
				"PCI DSS Requirement 8.2",
			},
		},
		{
			ID:          "pci-dss-10.1",
			Name:        "审计日志",
			Description: "跟踪和监控对资源的访问",
			Requirement: "所有访问必须记录审计日志",
			Category:    "审计",
			Severity:    "medium",
			Status:      "passed",
			Passed:      true,
			Evidence: []string{
				"已启用访问日志",
				"授权决策已记录",
				"日志保留期超过 1 年",
			},
			References: []string{
				"PCI DSS Requirement 10.2",
				"PCI DSS Requirement 10.3",
			},
		},
		{
			ID:          "pci-dss-11.2",
			Name:        "网络安全",
			Description: "定期测试系统安全性",
			Requirement: "实施网络分段",
			Category:    "网络安全",
			Severity:    "medium",
			Status:      "failed",
			Passed:      false,
			FailedReasons: []string{
				"服务网络分段不完整",
				"DMZ 区域策略缺失",
			},
			AffectedResources: []string{
				"prod/*",
			},
			RemediationGuidance: "1. 配置网络策略实现分段 2. 定义 DMZ 区域",
			References: []string{
				"PCI DSS Requirement 11.3",
			},
		},
	}
}

func (cc *ComplianceChecker) checkGDPR(req *models.ComplianceCheckRequest) []models.ComplianceControl {
	return []models.ComplianceControl{
		{
			ID:          "gdpr-5",
			Name:        "数据最小化",
			Description: "只收集必要的个人数据",
			Requirement: "数据收集应限于必要范围",
			Category:    "数据保护",
			Severity:    "high",
			Status:      "passed",
			Passed:      true,
			Evidence: []string{
				"数据收集策略已定义",
				"数据保留策略已配置",
			},
			RemediationGuidance: "定期审查数据收集范围",
			References: []string{
				"GDPR Article 5(1)(c)",
			},
		},
		{
			ID:          "gdpr-32",
			Name:        "数据安全",
			Description: "实施适当的技术和组织措施",
			Requirement: "确保个人数据的保密性、完整性、可用性和弹性",
			Category:    "安全措施",
			Severity:    "high",
			Status:      "failed",
			Passed:      false,
			FailedReasons: []string{
				"部分服务通信未加密",
				"数据备份策略缺失",
			},
			AffectedResources: []string{
				"default/user-profile",
				"dev/*",
			},
			RemediationGuidance: "1. 启用全服务 mTLS 2. 配置数据备份策略",
			References: []string{
				"GDPR Article 32",
			},
		},
		{
			ID:          "gdpr-15",
			Name:        "数据可访问性",
			Description: "数据主体访问权",
			Requirement: "数据主体有权访问其个人数据",
			Category:    "数据主体权利",
			Severity:    "medium",
			Status:      "passed",
			Passed:      true,
			Evidence: []string{
				"数据访问 API 已实现",
				"请求处理流程已定义",
			},
			References: []string{
				"GDPR Article 15",
			},
		},
		{
			ID:          "gdpr-17",
			Name:        "数据删除权",
			Description: "被遗忘权",
			Requirement: "数据主体有权要求删除其个人数据",
			Category:    "数据主体权利",
			Severity:    "medium",
			Status:      "warning",
			Passed:      false,
			FailedReasons: []string{
				"数据删除 API 未实现",
				"数据清除流程未定义",
			},
			AffectedResources: []string{
				"prod/user-service",
			},
			RemediationGuidance: "实现数据删除 API 和数据清除流程",
			References: []string{
				"GDPR Article 17",
			},
		},
		{
			ID:          "gdpr-28",
			Name:        "数据处理记录",
			Description: "处理活动记录",
			Requirement: "控制者应维护处理活动记录",
			Category:    "合规文档",
			Severity:    "low",
			Status:      "passed",
			Passed:      true,
			Evidence: []string{
				"数据处理目录已建立",
				"处理活动已记录",
			},
			References: []string{
				"GDPR Article 30",
			},
		},
	}
}

func (cc *ComplianceChecker) checkHIPAA(req *models.ComplianceCheckRequest) []models.ComplianceControl {
	return []models.ComplianceControl{
		{
			ID:          "hipaa-164.312(a)",
			Name:        "访问控制",
			Description: "电子受保护健康信息的访问控制",
			Requirement: "实施技术策略和程序，只允许授权人员访问",
			Category:    "访问控制",
			Severity:    "critical",
			Status:      "passed",
			Passed:      true,
			Evidence: []string{
				"基于角色的访问控制已实施",
				"授权策略覆盖所有医疗服务",
			},
			References: []string{
				"HIPAA §164.312(a)(1)",
			},
		},
		{
			ID:          "hipaa-164.312(e)",
			Name:        "传输安全",
			Description: "电子受保护健康信息传输",
			Requirement: "传输过程中保护电子受保护健康信息",
			Category:    "传输安全",
			Severity:    "critical",
			Status:      "failed",
			Passed:      false,
			FailedReasons: []string{
				"部分医疗服务通信未端到端加密",
				"外部传输未强制使用 VPN",
			},
			AffectedResources: []string{
				"health/telemedicine-service",
			},
			RemediationGuidance: "1. 启用所有服务 mTLS 2. 配置外部传输 VPN",
			References: []string{
				"HIPAA §164.312(e)(1)",
			},
		},
		{
			ID:          "hipaa-164.312(b)",
			Name:        "审计控制",
			Description: "实施硬件、软件和/或程序性机制",
			Requirement: "记录和检查所有访问电子受保护健康信息的活动",
			Category:    "审计",
			Severity:    "high",
			Status:      "passed",
			Passed:      true,
			Evidence: []string{
				"所有 ePHI 访问已记录",
				"审计日志保留 6 年",
			},
			References: []string{
				"HIPAA §164.312(b)",
			},
		},
	}
}

func (cc *ComplianceChecker) checkSOC2(req *models.ComplianceCheckRequest) []models.ComplianceControl {
	return []models.ComplianceControl{
		{
			ID:          "soc2-cc1",
			Name:        "控制环境",
			Description: "组织对内部控制的承诺",
			Requirement: "建立适当的控制环境",
			Category:    "治理",
			Severity:    "high",
			Status:      "passed",
			Passed:      true,
			References: []string{
				"SOC2 TSP CC1.1",
			},
		},
		{
			ID:          "soc2-cc7",
			Name:        "系统操作",
			Description: "系统操作控制",
			Requirement: "检测并缓解不符合要求的系统操作",
			Category:    "运营",
			Severity:    "medium",
			Status:      "passed",
			Passed:      true,
			References: []string{
				"SOC2 TSP CC7.1",
			},
		},
	}
}

func (cc *ComplianceChecker) checkISO27001(req *models.ComplianceCheckRequest) []models.ComplianceControl {
	return []models.ComplianceControl{
		{
			ID:          "iso27001-a5",
			Name:        "信息安全策略",
			Description: "信息安全策略管理",
			Requirement: "定义、评审和批准信息安全策略",
			Category:    "策略",
			Severity:    "high",
			Status:      "passed",
			Passed:      true,
			References: []string{
				"ISO 27001 A.5.1.1",
			},
		},
		{
			ID:          "iso27001-a8",
			Name:        "资产管理",
			Description: "资产清单和所有权",
			Requirement: "维护资产清单并分配所有权",
			Category:    "资产管理",
			Severity:    "medium",
			Status:      "warning",
			Passed:      false,
			FailedReasons: []string{
				"部分服务资产未分类",
			},
			RemediationGuidance: "完成所有服务的资产分类",
			References: []string{
				"ISO 27001 A.8.1.1",
			},
		},
	}
}

func (cc *ComplianceChecker) calculateSummary(controls []models.ComplianceControl) models.ComplianceSummary {
	summary := models.ComplianceSummary{
		TotalControls:  len(controls),
		PassedControls: 0,
		FailedControls: 0,
	}

	criticalCount := 0
	highCount := 0
	mediumCount := 0
	lowCount := 0

	for _, c := range controls {
		if c.Passed {
			summary.PassedControls++
		} else {
			summary.FailedControls++
			switch c.Severity {
			case "critical":
				criticalCount++
			case "high":
				highCount++
			case "medium":
				mediumCount++
			case "low":
				lowCount++
			}
		}
	}

	summary.CriticalFailures = criticalCount
	summary.HighFailures = highCount
	summary.MediumFailures = mediumCount
	summary.LowFailures = lowCount

	estimatedHours := criticalCount*8 + highCount*4 + mediumCount*2 + lowCount*1
	if estimatedHours < 8 {
		summary.EstimatedRemediationTime = fmt.Sprintf("约 %d 小时", estimatedHours)
	} else if estimatedHours < 40 {
		summary.EstimatedRemediationTime = fmt.Sprintf("约 %d 个工作日", estimatedHours/8)
	} else {
		summary.EstimatedRemediationTime = fmt.Sprintf("约 %d 周", estimatedHours/40)
	}

	return summary
}

func (cc *ComplianceChecker) calculateOverallScore(controls []models.ComplianceControl) float64 {
	score := 0.0
	maxScore := 0.0

	for _, c := range controls {
		var weight float64
		switch c.Severity {
		case "critical":
			weight = 30
		case "high":
			weight = 20
		case "medium":
			weight = 10
		case "low":
			weight = 5
		default:
			weight = 10
		}

		maxScore += weight
		if c.Passed {
			score += weight
		}
	}

	if maxScore == 0 {
		return 100
	}

	return (score / maxScore) * 100
}

func getStandardName(standard models.ComplianceStandard) string {
	switch standard {
	case models.ComplianceStandardPCI:
		return "PCI DSS"
	case models.ComplianceStandardGDPR:
		return "GDPR"
	case models.ComplianceStandardHIPAA:
		return "HIPAA"
	case models.ComplianceStandardSOC2:
		return "SOC 2"
	case models.ComplianceStandardISO27001:
		return "ISO 27001"
	default:
		return string(standard)
	}
}

func generateCheckID() string {
	return fmt.Sprintf("check-%d", time.Now().Unix())
}

func (cc *ComplianceChecker) GetAvailableStandards() []map[string]string {
	return []map[string]string{
		{
			"id":          string(models.ComplianceStandardPCI),
			"name":        "PCI DSS",
			"description": "支付卡行业数据安全标准",
			"controls":    "12项要求",
		},
		{
			"id":          string(models.ComplianceStandardGDPR),
			"name":        "GDPR",
			"description": "欧盟通用数据保护条例",
			"controls":    "99条规定",
		},
		{
			"id":          string(models.ComplianceStandardHIPAA),
			"name":        "HIPAA",
			"description": "健康保险流通与责任法案",
			"controls":    "隐私规则与安全规则",
		},
		{
			"id":          string(models.ComplianceStandardSOC2),
			"name":        "SOC 2",
			"description": "服务组织控制报告",
			"controls":    "信任服务标准",
		},
		{
			"id":          string(models.ComplianceStandardISO27001),
			"name":        "ISO 27001",
			"description": "信息安全管理体系",
			"controls":    "14个控制域",
		},
	}
}
