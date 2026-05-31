package main

import (
	"log"

	"gorm.io/driver/sqlite"
	"gorm.io/gorm"
	"nacos-audit-tool/api"
	"nacos-audit-tool/config"
	"nacos-audit-tool/models"
	"nacos-audit-tool/pkg/email"
	"nacos-audit-tool/pkg/ldap"
	"nacos-audit-tool/pkg/nacos"
	"nacos-audit-tool/repository"
	"nacos-audit-tool/service"
)

func main() {
	cfg := config.Load()

	db, err := gorm.Open(sqlite.Open(cfg.DBPath), &gorm.Config{})
	if err != nil {
		log.Fatalf("Failed to connect to database: %v", err)
	}

	if err := models.Migrate(db); err != nil {
		log.Fatalf("Failed to migrate database: %v", err)
	}

	nacosClient, err := nacos.NewNacosClient(
		cfg.NacosHost,
		cfg.NacosPort,
		cfg.NacosUser,
		cfg.NacosPassword,
	)
	if err != nil {
		log.Fatalf("Failed to create Nacos client: %v", err)
	}

	emailNotifier := email.NewNotifier(
		cfg.SMTPHost,
		cfg.SMTPPort,
		cfg.SMTPUser,
		cfg.SMTPPassword,
		cfg.SMTPFrom,
	)

	var ldapConfig *ldap.LDAPConfig
	if cfg.LDAPEnabled {
		ldapConfig = &ldap.LDAPConfig{
			Host:         cfg.LDAPHost,
			Port:         cfg.LDAPPort,
			UseSSL:       cfg.LDAPUseSSL,
			BindDN:       cfg.LDAPBindDN,
			BindPassword: cfg.LDAPBindPass,
			BaseDN:       cfg.LDAPBaseDN,
			UserFilter:   cfg.LDAPUserFilter,
			EmailAttr:    cfg.LDAPEmailAttr,
			NameAttr:     cfg.LDAPNameAttr,
			DeptAttr:     cfg.LDAPDeptAttr,
		}
		log.Println("LDAP integration enabled")
	}

	repo := repository.NewAuditRepository(db)
	auditService := service.NewAuditService(nacosClient, repo, emailNotifier, cfg.NotifyEmails, ldapConfig)
	handler := api.NewHandler(auditService)
	router := api.SetupRouter(handler)

	initDefaultData(repo)

	log.Printf("Server starting on port %s...", cfg.ServerPort)
	log.Printf("API Documentation:")
	log.Printf("  GET    /api/audit/logs              - List audit logs")
	log.Printf("  GET    /api/audit/logs/:id          - Get audit log detail")
	log.Printf("  GET    /api/audit/logs/:id/diff     - Get line diff of audit log")
	log.Printf("  GET    /api/audit/logs/:id/struct-diff - Get structured diff of audit log")
	log.Printf("  POST   /api/audit/logs/:id/rollback - Rollback to this version")
	log.Printf("  POST   /api/audit/record            - Manually record a change")
	log.Printf("  GET    /api/namespaces              - List Nacos namespaces")
	log.Printf("  GET    /api/namespaces/configs      - List namespace audit configs")
	log.Printf("  POST   /api/namespaces/configs      - Save namespace audit config")
	log.Printf("  GET    /api/compliance/rules        - List compliance rules")
	log.Printf("  POST   /api/compliance/rules        - Save compliance rule")
	log.Printf("  DELETE /api/compliance/rules/:id    - Delete compliance rule")
	log.Printf("  POST   /api/listener/start          - Start config listener")
	log.Printf("  POST   /api/listener/stop           - Stop config listener")

	if cfg.LDAPEnabled {
		log.Println("LDAP Integration: ENABLED (Responsible person auto-lookup)")
	} else {
		log.Println("LDAP Integration: DISABLED")
	}

	if err := router.Run(":" + cfg.ServerPort); err != nil {
		log.Fatalf("Failed to start server: %v", err)
	}
}

func initDefaultData(repo *repository.AuditRepository) {
	rules, _ := repo.GetAllComplianceRules()
	if len(rules) == 0 {
		defaultRules := []*models.ComplianceRule{
			{
				Name:        "密码强度检查",
				Description: "检查配置中是否存在弱密码",
				RuleType:    "password_strength",
				Pattern:     "",
				IsEnabled:   true,
				Severity:    "HIGH",
			},
			{
				Name:        "禁止明文密码",
				Description: "禁止在配置中使用明文密码",
				RuleType:    "forbidden_key",
				Pattern:     "database.password",
				IsEnabled:   false,
				Severity:    "MEDIUM",
			},
			{
				Name:        "AK/SK敏感数据检测",
				Description: "检测配置中的AccessKey/SecretKey等敏感凭证",
				RuleType:    "sensitive_data",
				Pattern:     "(LTAI|AKIA|AKID)[a-zA-Z0-9]{16,32}",
				IsEnabled:   true,
				Severity:    "CRITICAL",
			},
			{
				Name:        "私钥文件检测",
				Description: "禁止在配置中包含私钥文件内容",
				RuleType:    "sensitive_data",
				Pattern:     "-----BEGIN (RSA |EC |DSA |OPENSSH )?PRIVATE KEY-----",
				IsEnabled:   true,
				Severity:    "CRITICAL",
			},
			{
				Name:        "手机号敏感检测",
				Description: "检测配置中的明文手机号",
				RuleType:    "sensitive_data",
				Pattern:     "1[3-9]\\d{9}",
				IsEnabled:   false,
				Severity:    "MEDIUM",
			},
		}

		for _, rule := range defaultRules {
			_ = repo.CreateComplianceRule(rule)
		}
		log.Println("Initialized default compliance rules (including sensitive data detection)")
	}
}
