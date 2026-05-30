package scanner

type RiskAssessment struct {
	Port         int
	Service      string
	RiskLevel    string
	Description  string
	Recommendations []string
}

var riskProfiles = map[int]RiskAssessment{
	21: {
		RiskLevel:    "Medium",
		Description:  "FTP服务明文传输，存在密码嗅探风险",
		Recommendations: []string{
			"禁用FTP，改用SFTP/SCP",
			"启用FTP over TLS (FTPS)",
			"使用强密码策略",
			"限制访问IP白名单",
		},
	},
	22: {
		RiskLevel:    "Low",
		Description:  "SSH服务通常较为安全，但需正确配置",
		Recommendations: []string{
			"禁用root远程登录",
			"使用密钥认证替代密码认证",
			"更改默认端口",
			"配置fail2ban防止暴力破解",
		},
	},
	23: {
		RiskLevel:    "Critical",
		Description:  "Telnet明文传输所有数据，极易被窃听",
		Recommendations: []string{
			"立即禁用Telnet服务",
			"改用SSH替代",
			"过滤23端口访问",
		},
	},
	3306: {
		RiskLevel:    "High",
		Description:  "MySQL数据库直接暴露存在数据泄露风险",
		Recommendations: []string{
			"限制MySQL仅监听localhost",
			"使用强密码策略",
			"删除匿名账户",
			"限制root用户只能本地登录",
			"启用SSL/TLS加密连接",
			"配置防火墙限制访问IP",
		},
	},
	6379: {
		RiskLevel:    "Critical",
		Description:  "Redis默认无认证，暴露公网极易被入侵",
		Recommendations: []string{
			"配置Redis密码 (requirepass)",
			"绑定localhost (bind 127.0.0.1)",
			"禁用危险命令 (FLUSHDB, FLUSHALL, KEYS)",
			"启用rename-command重命名命令",
			"配置防火墙限制访问IP",
			"不要以root身份运行Redis",
		},
	},
	27017: {
		RiskLevel:    "High",
		Description:  "MongoDB默认无认证，存在数据泄露风险",
		Recommendations: []string{
			"启用MongoDB认证",
			"绑定localhost",
			"启用TLS/SSL加密",
			"配置角色访问控制",
			"限制访问IP白名单",
		},
	},
	5432: {
		RiskLevel:    "High",
		Description:  "PostgreSQL数据库直接暴露存在风险",
		Recommendations: []string{
			"限制监听localhost",
			"配置pg_hba.conf访问控制",
			"使用强密码",
			"启用SSL连接",
			"定期备份数据",
		},
	},
	9200: {
		RiskLevel:    "Critical",
		Description:  "Elasticsearch默认无认证，数据完全暴露",
		Recommendations: []string{
			"启用X-Pack安全认证",
			"绑定localhost",
			"配置HTTPS加密",
			"设置用户角色权限",
			"配置Nginx反向代理加认证",
		},
	},
	3389: {
		RiskLevel:    "High",
		Description:  "RDP远程桌面暴露存在被暴力破解风险",
		Recommendations: []string{
			"使用强密码策略",
			"配置账户锁定策略",
			"启用网络级别认证(NLA)",
			"使用VPN接入后再连接RDP",
			"更改默认端口",
		},
	},
}

func AssessRisk(port int, service string) RiskAssessment {
	assessment := RiskAssessment{
		Port:        port,
		Service:     service,
		RiskLevel:   "Info",
		Description: "常规服务端口",
		Recommendations: []string{
			"确保服务保持最新版本",
			"根据业务需要开放端口",
		},
	}

	if profile, ok := riskProfiles[port]; ok {
		assessment.RiskLevel = profile.RiskLevel
		assessment.Description = profile.Description
		assessment.Recommendations = profile.Recommendations
	}

	return assessment
}

func AssessAllRisks(ports []PortResult) []RiskAssessment {
	assessments := make([]RiskAssessment, 0, len(ports))
	for _, port := range ports {
		assessment := AssessRisk(port.Port, port.Service)
		assessments = append(assessments, assessment)
	}
	return assessments
}

func GetRiskColor(level string) string {
	switch level {
	case "Critical":
		return "\033[31m"
	case "High":
		return "\033[35m"
	case "Medium":
		return "\033[33m"
	case "Low":
		return "\033[32m"
	default:
		return "\033[36m"
	}
}
