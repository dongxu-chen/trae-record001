package service

import (
	"fmt"
	"log"
	"strings"
	"sync"
	"time"

	"nacos-audit-tool/models"
	"nacos-audit-tool/pkg/compliance"
	"nacos-audit-tool/pkg/diff"
	"nacos-audit-tool/pkg/email"
	"nacos-audit-tool/pkg/ldap"
	"nacos-audit-tool/pkg/nacos"
	"nacos-audit-tool/pkg/structdiff"
	"nacos-audit-tool/repository"
)

type AuditService struct {
	nacosClient       *nacos.NacosClient
	repo              *repository.AuditRepository
	emailNotifier     *email.Notifier
	complianceChecker *compliance.Checker
	ldapClient        *ldap.LDAPClient
	defaultEmails     []string
	ldapEnabled       bool
	listeners         map[string]bool
	listenerMutex     sync.RWMutex
}

func NewAuditService(
	nacosClient *nacos.NacosClient,
	repo *repository.AuditRepository,
	emailNotifier *email.Notifier,
	defaultEmails []string,
	ldapConfig *ldap.LDAPConfig,
) *AuditService {
	service := &AuditService{
		nacosClient:       nacosClient,
		repo:              repo,
		emailNotifier:     emailNotifier,
		complianceChecker: compliance.NewChecker(),
		defaultEmails:     defaultEmails,
		ldapEnabled:       ldapConfig != nil,
		listeners:         make(map[string]bool),
	}

	if ldapConfig != nil {
		service.ldapClient = ldap.NewLDAPClient(*ldapConfig)
		log.Println("LDAP client initialized")
	}

	return service
}

func (s *AuditService) RecordChange(namespaceID, group, dataID, operator, operatorIP, oldContent, newContent, desc string) (*models.AuditLog, error) {
	contentType := "text"
	
	_, contentType, _ = s.nacosClient.GetConfig(namespaceID, group, dataID)

	auditLog := &models.AuditLog{
		NamespaceID: namespaceID,
		Group:       group,
		DataID:      dataID,
		Operator:    operator,
		OperatorIP:  operatorIP,
		Action:      "UPDATE",
		OldContent:  oldContent,
		NewContent:  newContent,
		ContentType: contentType,
		Desc:        desc,
	}

	if oldContent == "" {
		auditLog.Action = "CREATE"
	} else if newContent == "" {
		auditLog.Action = "DELETE"
	}

	rules, _ := s.repo.GetAllComplianceRules()
	checkResults := s.complianceChecker.CheckContent(newContent, contentType, rules)
	
	compliancePass := true
	var complianceMsgs []string
	for _, result := range checkResults {
		if !result.Pass {
			compliancePass = false
			complianceMsgs = append(complianceMsgs, result.Message)
		}
	}
	auditLog.CompliancePass = &compliancePass
	if len(complianceMsgs) > 0 {
		auditLog.ComplianceMsg = joinStrings(complianceMsgs, "; ")
	}

	err := s.repo.CreateAuditLog(auditLog)
	if err != nil {
		return nil, err
	}

	go s.sendChangeNotifications(auditLog, checkResults)

	if !compliancePass {
		go s.checkAutoRollback(auditLog, checkResults)
	}

	return auditLog, nil
}

func (s *AuditService) sendChangeNotifications(log *models.AuditLog, checkResults []compliance.CheckResult) {
	emails := s.getNotifyEmails(log.NamespaceID)
	
	if s.ldapEnabled && log.Operator != "" && log.Operator != "system" {
		ldapEmails := s.ldapClient.GetResponsibleEmails(log.Operator)
		emailSet := make(map[string]bool)
		for _, e := range emails {
			emailSet[e] = true
		}
		for _, e := range ldapEmails {
			if !emailSet[e] {
				emails = append(emails, e)
				emailSet[e] = true
			}
		}
		log.Printf("Added %d LDAP responsible emails for operator %s", len(ldapEmails), log.Operator)
	}

	if len(emails) == 0 {
		return
	}

	var diffSummary string
	if log.ContentType == "json" || log.ContentType == "yaml" || log.ContentType == "yml" {
		structDiff, err := structdiff.CompareStructured(log.OldContent, log.NewContent, log.ContentType)
		if err == nil {
			diffSummary = structDiff.GetSummary()
		} else {
			diffResult := diff.Compare(log.OldContent, log.NewContent)
			diffSummary = diffResult.GetSummary()
		}
	} else {
		diffResult := diff.Compare(log.OldContent, log.NewContent)
		diffSummary = diffResult.GetSummary()
	}
	
	err := s.emailNotifier.SendConfigChangeNotification(
		emails,
		log.NamespaceID,
		log.Group,
		log.DataID,
		log.Operator,
		log.OldContent,
		log.NewContent,
		diffSummary,
	)
	if err != nil {
		log.Printf("Failed to send change notification: %v", err)
	}

	for _, result := range checkResults {
		if !result.Pass {
			err := s.emailNotifier.SendComplianceAlert(
				emails,
				log.NamespaceID,
				log.Group,
				log.DataID,
				log.Operator,
				result.RuleName,
				result.Severity,
				result.Message,
			)
			if err != nil {
				log.Printf("Failed to send compliance alert: %v", err)
			}
		}
	}
}

func (s *AuditService) Rollback(auditLogID, operator string) (*models.AuditLog, error) {
	targetLog, err := s.repo.GetAuditLogByID(auditLogID)
	if err != nil {
		return nil, err
	}

	currentContent, _, err := s.nacosClient.GetConfig(targetLog.NamespaceID, targetLog.Group, targetLog.DataID)
	if err != nil {
		return nil, err
	}

	err = s.nacosClient.PublishConfig(
		targetLog.NamespaceID,
		targetLog.Group,
		targetLog.DataID,
		targetLog.OldContent,
		operator,
	)
	if err != nil {
		return nil, err
	}

	rollbackLog := &models.AuditLog{
		NamespaceID: targetLog.NamespaceID,
		Group:       targetLog.Group,
		DataID:      targetLog.DataID,
		Operator:    operator,
		Action:      "ROLLBACK",
		OldContent:  currentContent,
		NewContent:  targetLog.OldContent,
		ContentType: targetLog.ContentType,
		Desc:        "回滚到历史版本",
	}

	pass := true
	rollbackLog.CompliancePass = &pass

	err = s.repo.CreateAuditLog(rollbackLog)
	if err != nil {
		return nil, err
	}

	go func() {
		emails := s.getNotifyEmails(targetLog.NamespaceID)
		_ = s.emailNotifier.SendRollbackNotification(
			emails,
			targetLog.NamespaceID,
			targetLog.Group,
			targetLog.DataID,
			operator,
			auditLogID,
			"历史版本",
		)
	}()

	return rollbackLog, nil
}

func (s *AuditService) GetDiff(auditLogID string) (*diff.DiffResult, error) {
	log, err := s.repo.GetAuditLogByID(auditLogID)
	if err != nil {
		return nil, err
	}

	return diff.Compare(log.OldContent, log.NewContent), nil
}

func (s *AuditService) GetStructDiff(auditLogID string) (*structdiff.DiffResult, error) {
	log, err := s.repo.GetAuditLogByID(auditLogID)
	if err != nil {
		return nil, err
	}

	return structdiff.CompareStructured(log.OldContent, log.NewContent, log.ContentType)
}

func (s *AuditService) GetAuditLogs(namespaceID, group, dataID string, page, pageSize int) ([]models.AuditLog, int64, error) {
	return s.repo.GetAuditLogs(namespaceID, group, dataID, page, pageSize)
}

func (s *AuditService) GetAuditLog(id string) (*models.AuditLog, error) {
	return s.repo.GetAuditLogByID(id)
}

func (s *AuditService) getNotifyEmails(namespaceID string) []string {
	config, err := s.repo.GetNamespaceConfig(namespaceID)
	if err != nil || config == nil || config.NotifyEmails == "" {
		return s.defaultEmails
	}
	return splitEmails(config.NotifyEmails)
}

func (s *AuditService) StartConfigListener(namespaceID, group, dataID string) error {
	key := namespaceID + ":" + group + ":" + dataID
	
	s.listenerMutex.RLock()
	if s.listeners[key] {
		s.listenerMutex.RUnlock()
		return nil
	}
	s.listenerMutex.RUnlock()

	s.listenerMutex.Lock()
	s.listeners[key] = true
	s.listenerMutex.Unlock()

	oldContent, _, _ := s.nacosClient.GetConfig(namespaceID, group, dataID)

	err := s.nacosClient.ListenConfig(namespaceID, group, dataID, func(ns, g, d, content string) {
		log.Printf("Config changed: %s/%s/%s", ns, g, d)
		
		_, _ = s.RecordChange(ns, g, d, "system", "", oldContent, content, "自动监听到的配置变更")
		oldContent = content
	})

	if err != nil {
		s.listenerMutex.Lock()
		delete(s.listeners, key)
		s.listenerMutex.Unlock()
		return err
	}

	log.Printf("Started listener for %s/%s/%s", namespaceID, group, dataID)
	return nil
}

func (s *AuditService) StopConfigListener(namespaceID, group, dataID string) error {
	key := namespaceID + ":" + group + ":" + dataID
	
	s.listenerMutex.Lock()
	defer s.listenerMutex.Unlock()
	
	if !s.listeners[key] {
		return nil
	}

	err := s.nacosClient.CancelListenConfig(namespaceID, group, dataID)
	if err != nil {
		return err
	}

	delete(s.listeners, key)
	log.Printf("Stopped listener for %s/%s/%s", namespaceID, group, dataID)
	return nil
}

func (s *AuditService) GetNamespaces() ([]map[string]string, error) {
	namespaces, err := s.nacosClient.GetNamespaces()
	if err != nil {
		return nil, err
	}

	result := make([]map[string]string, len(namespaces))
	for i, ns := range namespaces {
		result[i] = map[string]string{
			"id":   ns.Namespace,
			"name": ns.NamespaceShowName,
		}
	}

	return result, nil
}

func (s *AuditService) GetNamespaceConfigs() ([]models.NamespaceConfig, error) {
	return s.repo.GetAllNamespaceConfigs()
}

func (s *AuditService) SaveNamespaceConfig(config *models.NamespaceConfig) error {
	existing, _ := s.repo.GetNamespaceConfig(config.NamespaceID)
	if existing != nil {
		config.ID = existing.ID
		config.CreatedAt = existing.CreatedAt
		return s.repo.UpdateNamespaceConfig(config)
	}
	return s.repo.CreateNamespaceConfig(config)
}

func (s *AuditService) GetComplianceRules() ([]models.ComplianceRule, error) {
	return s.repo.GetAllComplianceRules()
}

func (s *AuditService) SaveComplianceRule(rule *models.ComplianceRule) error {
	if rule.ID != "" {
		return s.repo.UpdateComplianceRule(rule)
	}
	return s.repo.CreateComplianceRule(rule)
}

func (s *AuditService) DeleteComplianceRule(id string) error {
	return s.repo.DeleteComplianceRule(id)
}

func joinStrings(strs []string, sep string) string {
	result := ""
	for i, s := range strs {
		if i > 0 {
			result += sep
		}
		result += s
	}
	return result
}

func splitEmails(s string) []string {
	var result []string
	var current string
	for _, c := range s {
		if c == ',' {
			if current != "" {
				result = append(result, current)
				current = ""
			}
		} else {
			current += string(c)
		}
	}
	if current != "" {
		result = append(result, current)
	}
	return result
}

type ImpactAnalysis struct {
	ConfigKey    string                   `json:"config_key"`
	NamespaceID  string                   `json:"namespace_id"`
	Group        string                   `json:"group"`
	DataID       string                   `json:"data_id"`
	AffectedServices []AffectedService    `json:"affected_services"`
	TotalServices int                      `json:"total_services"`
	RiskLevel    string                   `json:"risk_level"`
	Warnings     []string                 `json:"warnings"`
}

type AffectedService struct {
	ServiceName string `json:"service_name"`
	Environment string `json:"environment"`
	Owner       string `json:"owner"`
	OwnerEmail  string `json:"owner_email"`
	Desc        string `json:"desc"`
}

func (s *AuditService) AnalyzeImpact(namespaceID, group, dataID string) (*ImpactAnalysis, error) {
	services, err := s.repo.GetAffectedServices(namespaceID, group, dataID)
	if err != nil {
		return nil, err
	}

	analysis := &ImpactAnalysis{
		ConfigKey:    fmt.Sprintf("%s/%s/%s", namespaceID, group, dataID),
		NamespaceID:  namespaceID,
		Group:        group,
		DataID:       dataID,
		AffectedServices: make([]AffectedService, 0, len(services)),
		TotalServices: len(services),
		Warnings:     make([]string, 0),
	}

	for _, svc := range services {
		analysis.AffectedServices = append(analysis.AffectedServices, AffectedService{
			ServiceName: svc.ServiceName,
			Environment: svc.Environment,
			Owner:       svc.Owner,
			OwnerEmail:  svc.OwnerEmail,
			Desc:        svc.Desc,
		})
	}

	if analysis.TotalServices == 0 {
		analysis.RiskLevel = "LOW"
		analysis.Warnings = append(analysis.Warnings, "未注册关联服务，影响范围未知")
	} else if analysis.TotalServices <= 3 {
		analysis.RiskLevel = "MEDIUM"
	} else if analysis.TotalServices <= 10 {
		analysis.RiskLevel = "HIGH"
	} else {
		analysis.RiskLevel = "CRITICAL"
		analysis.Warnings = append(analysis.Warnings, fmt.Sprintf("影响%d个服务，变更风险极高", analysis.TotalServices))
	}

	hasProd := false
	for _, svc := range analysis.AffectedServices {
		if svc.Environment == "production" || svc.Environment == "prod" {
			hasProd = true
			break
		}
	}
	if hasProd {
		analysis.Warnings = append(analysis.Warnings, "影响生产环境服务，请谨慎操作")
		if analysis.RiskLevel != "CRITICAL" {
			analysis.RiskLevel = "HIGH"
		}
	}

	return analysis, nil
}

func (s *AuditService) checkAutoRollback(auditLog *models.AuditLog, checkResults []compliance.CheckResult) {
	policy, err := s.repo.GetRollbackPolicyForConfig(auditLog.NamespaceID, auditLog.Group, auditLog.DataID)
	if err != nil || policy == nil {
		return
	}

	shouldRollback := false
	var reasons []string

	if policy.AutoRollbackOnComplianceFail {
		for _, result := range checkResults {
			if !result.Pass {
				shouldRollback = true
				reasons = append(reasons, fmt.Sprintf("合规检查失败: %s", result.RuleName))
				break
			}
		}
	}

	if policy.AutoRollbackOnSensitiveData {
		for _, result := range checkResults {
			if !result.Pass && (result.Severity == "CRITICAL" || strings.Contains(strings.ToLower(result.RuleName), "key") || strings.Contains(strings.ToLower(result.RuleName), "ak") || strings.Contains(strings.ToLower(result.RuleName), "sk") || strings.Contains(strings.ToLower(result.RuleName), "secret") || strings.Contains(strings.ToLower(result.RuleName), "private")) {
				shouldRollback = true
				reasons = append(reasons, fmt.Sprintf("检测到敏感数据泄露: %s", result.RuleName))
				break
			}
		}
	}

	if policy.AutoRollbackOnCriticalChange && auditLog.Action == "DELETE" {
		shouldRollback = true
		reasons = append(reasons, "配置被删除，自动回滚")
	}

	if policy.MaxChangeLines > 0 {
		diffResult := diff.Compare(auditLog.OldContent, auditLog.NewContent)
		if diffResult.ChangedCount > policy.MaxChangeLines {
			shouldRollback = true
			reasons = append(reasons, fmt.Sprintf("变更行数(%d)超过限制(%d)", diffResult.ChangedCount, policy.MaxChangeLines))
		}
	}

	if shouldRollback {
		log.Printf("Auto-rollback triggered for %s/%s/%s, reasons: %s",
			auditLog.NamespaceID, auditLog.Group, auditLog.DataID, joinStrings(reasons, "; "))

		_, err := s.Rollback(auditLog.ID, "system-auto-rollback")
		if err != nil {
			log.Printf("Auto-rollback failed: %v", err)
			return
		}

		auditLog.IsAutoRollback = true
		auditLog.RollbackReason = joinStrings(reasons, "; ")
		s.repo.UpdateAuditLogAutoRollback(auditLog.ID, true, joinStrings(reasons, "; "))

		log.Printf("Auto-rollback completed for audit log %s", auditLog.ID)
	}
}

func (s *AuditService) QuickRollback(namespaceID, group, dataID, operator string) (*models.AuditLog, error) {
	var latestLog models.AuditLog
	err := s.repo.(*repository.AuditRepository).GetDB().
		Where("namespace_id = ? AND `group` = ? AND data_id = ? AND action != 'ROLLBACK'",
			namespaceID, group, dataID).
		Order("created_at DESC").
		First(&latestLog).Error
	if err != nil {
		return nil, fmt.Errorf("no rollback target found: %v", err)
	}

	return s.Rollback(latestLog.ID, operator)
}

type DashboardStats struct {
	TotalChanges     int64                     `json:"total_changes"`
	ComplianceFailCount int64                  `json:"compliance_fail_count"`
	AutoRollbackCount int64                    `json:"auto_rollback_count"`
	ActionStats      []repository.ActionStat   `json:"action_stats"`
	DailyStats       []repository.DailyStat    `json:"daily_stats"`
	NamespaceStats   []repository.NamespaceStat `json:"namespace_stats"`
	RecentChanges    []models.AuditLog         `json:"recent_changes"`
}

func (s *AuditService) GetDashboardStats(days int) (*DashboardStats, error) {
	now := time.Now()
	startTime := now.AddDate(0, 0, -days)

	stats := &DashboardStats{}

	total, err := s.repo.GetTotalCount()
	if err == nil {
		stats.TotalChanges = total
	}

	failCount, err := s.repo.GetComplianceFailCount(startTime, now)
	if err == nil {
		stats.ComplianceFailCount = failCount
	}

	rollbackCount, err := s.repo.GetAutoRollbackCount(startTime, now)
	if err == nil {
		stats.AutoRollbackCount = rollbackCount
	}

	actionStats, err := s.repo.GetActionStats(startTime, now)
	if err == nil {
		stats.ActionStats = actionStats
	}

	dailyStats, err := s.repo.GetDailyStats(startTime, now)
	if err == nil {
		stats.DailyStats = dailyStats
	}

	nsStats, err := s.repo.GetNamespaceStats(startTime, now)
	if err == nil {
		stats.NamespaceStats = nsStats
	}

	recentLogs, _, err := s.repo.GetAuditLogs("", "", "", 1, 10)
	if err == nil {
		stats.RecentChanges = recentLogs
	}

	return stats, nil
}

func (s *AuditService) GetServiceRegistries(namespaceID, group, dataID string) ([]models.ServiceRegistry, error) {
	return s.repo.GetServiceRegistries(namespaceID, group, dataID)
}

func (s *AuditService) CreateServiceRegistry(svc *models.ServiceRegistry) error {
	return s.repo.CreateServiceRegistry(svc)
}

func (s *AuditService) UpdateServiceRegistry(svc *models.ServiceRegistry) error {
	return s.repo.UpdateServiceRegistry(svc)
}

func (s *AuditService) DeleteServiceRegistry(id string) error {
	return s.repo.DeleteServiceRegistry(id)
}

func (s *AuditService) GetRollbackPolicies(namespaceID string) ([]models.RollbackPolicy, error) {
	return s.repo.GetRollbackPolicies(namespaceID)
}

func (s *AuditService) CreateRollbackPolicy(policy *models.RollbackPolicy) error {
	return s.repo.CreateRollbackPolicy(policy)
}

func (s *AuditService) UpdateRollbackPolicy(policy *models.RollbackPolicy) error {
	return s.repo.UpdateRollbackPolicy(policy)
}

func (s *AuditService) DeleteRollbackPolicy(id string) error {
	return s.repo.DeleteRollbackPolicy(id)
}
