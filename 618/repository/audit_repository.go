package repository

import (
	"time"

	"github.com/google/uuid"
	"gorm.io/gorm"
	"nacos-audit-tool/models"
)

type AuditRepository struct {
	db *gorm.DB
}

func NewAuditRepository(db *gorm.DB) *AuditRepository {
	return &AuditRepository{db: db}
}

func (r *AuditRepository) GetDB() *gorm.DB {
	return r.db
}

func (r *AuditRepository) UpdateAuditLogAutoRollback(id string, isAutoRollback bool, reason string) error {
	return r.db.Model(&models.AuditLog{}).
		Where("id = ?", id).
		Updates(map[string]interface{}{
			"is_auto_rollback": isAutoRollback,
			"rollback_reason":  reason,
		}).Error
}

func (r *AuditRepository) CreateAuditLog(log *models.AuditLog) error {
	log.ID = uuid.New().String()
	log.CreatedAt = time.Now()
	return r.db.Create(log).Error
}

func (r *AuditRepository) GetAuditLogs(namespaceID, group, dataID string, page, pageSize int) ([]models.AuditLog, int64, error) {
	var logs []models.AuditLog
	var total int64

	query := r.db.Model(&models.AuditLog{}).Order("created_at DESC")

	if namespaceID != "" {
		query = query.Where("namespace_id = ?", namespaceID)
	}
	if group != "" {
		query = query.Where("`group` = ?", group)
	}
	if dataID != "" {
		query = query.Where("data_id = ?", dataID)
	}

	query.Count(&total)

	offset := (page - 1) * pageSize
	err := query.Offset(offset).Limit(pageSize).Find(&logs).Error
	return logs, total, err
}

func (r *AuditRepository) GetAuditLogByID(id string) (*models.AuditLog, error) {
	var log models.AuditLog
	err := r.db.Where("id = ?", id).First(&log).Error
	if err != nil {
		return nil, err
	}
	return &log, nil
}

func (r *AuditRepository) GetPreviousAuditLog(namespaceID, group, dataID string, beforeTime time.Time) (*models.AuditLog, error) {
	var log models.AuditLog
	err := r.db.Where("namespace_id = ? AND `group` = ? AND data_id = ? AND created_at < ?",
		namespaceID, group, dataID, beforeTime).
		Order("created_at DESC").
		First(&log).Error
	if err != nil {
		return nil, err
	}
	return &log, nil
}

func (r *AuditRepository) CreateNamespaceConfig(config *models.NamespaceConfig) error {
	config.ID = uuid.New().String()
	config.CreatedAt = time.Now()
	config.UpdatedAt = time.Now()
	return r.db.Create(config).Error
}

func (r *AuditRepository) UpdateNamespaceConfig(config *models.NamespaceConfig) error {
	config.UpdatedAt = time.Now()
	return r.db.Save(config).Error
}

func (r *AuditRepository) GetNamespaceConfig(namespaceID string) (*models.NamespaceConfig, error) {
	var config models.NamespaceConfig
	err := r.db.Where("namespace_id = ?", namespaceID).First(&config).Error
	if err != nil {
		return nil, err
	}
	return &config, nil
}

func (r *AuditRepository) GetAllNamespaceConfigs() ([]models.NamespaceConfig, error) {
	var configs []models.NamespaceConfig
	err := r.db.Find(&configs).Error
	return configs, err
}

func (r *AuditRepository) CreateComplianceRule(rule *models.ComplianceRule) error {
	rule.ID = uuid.New().String()
	rule.CreatedAt = time.Now()
	rule.UpdatedAt = time.Now()
	return r.db.Create(rule).Error
}

func (r *AuditRepository) UpdateComplianceRule(rule *models.ComplianceRule) error {
	rule.UpdatedAt = time.Now()
	return r.db.Save(rule).Error
}

func (r *AuditRepository) GetAllComplianceRules() ([]models.ComplianceRule, error) {
	var rules []models.ComplianceRule
	err := r.db.Where("is_enabled = ?", true).Find(&rules).Error
	return rules, err
}

func (r *AuditRepository) DeleteComplianceRule(id string) error {
	return r.db.Delete(&models.ComplianceRule{}, "id = ?", id).Error
}

func (r *AuditRepository) CreateServiceRegistry(svc *models.ServiceRegistry) error {
	svc.ID = uuid.New().String()
	svc.CreatedAt = time.Now()
	svc.UpdatedAt = time.Now()
	return r.db.Create(svc).Error
}

func (r *AuditRepository) UpdateServiceRegistry(svc *models.ServiceRegistry) error {
	svc.UpdatedAt = time.Now()
	return r.db.Save(svc).Error
}

func (r *AuditRepository) DeleteServiceRegistry(id string) error {
	return r.db.Delete(&models.ServiceRegistry{}, "id = ?", id).Error
}

func (r *AuditRepository) GetServiceRegistries(namespaceID, group, dataID string) ([]models.ServiceRegistry, error) {
	var services []models.ServiceRegistry
	query := r.db.Model(&models.ServiceRegistry{})
	if namespaceID != "" {
		query = query.Where("namespace_id = ?", namespaceID)
	}
	if group != "" {
		query = query.Where("`group` = ?", group)
	}
	if dataID != "" {
		query = query.Where("data_id = ?", dataID)
	}
	err := query.Find(&services).Error
	return services, err
}

func (r *AuditRepository) GetAffectedServices(namespaceID, group, dataID string) ([]models.ServiceRegistry, error) {
	var services []models.ServiceRegistry
	err := r.db.Where("namespace_id = ? AND `group` = ? AND data_id = ?", namespaceID, group, dataID).
		Find(&services).Error
	return services, err
}

func (r *AuditRepository) GetServiceByID(id string) (*models.ServiceRegistry, error) {
	var svc models.ServiceRegistry
	err := r.db.Where("id = ?", id).First(&svc).Error
	if err != nil {
		return nil, err
	}
	return &svc, nil
}

func (r *AuditRepository) CreateRollbackPolicy(policy *models.RollbackPolicy) error {
	policy.ID = uuid.New().String()
	policy.CreatedAt = time.Now()
	policy.UpdatedAt = time.Now()
	return r.db.Create(policy).Error
}

func (r *AuditRepository) UpdateRollbackPolicy(policy *models.RollbackPolicy) error {
	policy.UpdatedAt = time.Now()
	return r.db.Save(policy).Error
}

func (r *AuditRepository) DeleteRollbackPolicy(id string) error {
	return r.db.Delete(&models.RollbackPolicy{}, "id = ?", id).Error
}

func (r *AuditRepository) GetRollbackPolicies(namespaceID string) ([]models.RollbackPolicy, error) {
	var policies []models.RollbackPolicy
	query := r.db.Where("is_enabled = ?", true)
	if namespaceID != "" {
		query = query.Where("namespace_id = ? OR namespace_id = ''", namespaceID)
	}
	err := query.Find(&policies).Error
	return policies, err
}

func (r *AuditRepository) GetRollbackPolicyForConfig(namespaceID, group, dataID string) (*models.RollbackPolicy, error) {
	var policy models.RollbackPolicy
	err := r.db.Where("namespace_id = ? AND `group` = ? AND data_id = ? AND is_enabled = ?",
		namespaceID, group, dataID, true).First(&policy).Error
	if err != nil {
		err2 := r.db.Where("namespace_id = ? AND is_enabled = ?", namespaceID, true).First(&policy).Error
		if err2 != nil {
			return nil, err
		}
		return &policy, nil
	}
	return &policy, nil
}

func (r *AuditRepository) GetRollbackPolicyByID(id string) (*models.RollbackPolicy, error) {
	var policy models.RollbackPolicy
	err := r.db.Where("id = ?", id).First(&policy).Error
	if err != nil {
		return nil, err
	}
	return &policy, nil
}

type ActionStat struct {
	Action string `json:"action"`
	Count  int64  `json:"count"`
}

type DailyStat struct {
	Date  string `json:"date"`
	Count int64  `json:"count"`
}

type NamespaceStat struct {
	NamespaceID string `json:"namespace_id"`
	Count       int64  `json:"count"`
}

func (r *AuditRepository) GetActionStats(startTime, endTime time.Time) ([]ActionStat, error) {
	var stats []ActionStat
	err := r.db.Model(&models.AuditLog{}).
		Select("action, count(*) as count").
		Where("created_at BETWEEN ? AND ?", startTime, endTime).
		Group("action").
		Find(&stats).Error
	return stats, err
}

func (r *AuditRepository) GetDailyStats(startTime, endTime time.Time) ([]DailyStat, error) {
	var stats []DailyStat
	err := r.db.Model(&models.AuditLog{}).
		Select("date(created_at) as date, count(*) as count").
		Where("created_at BETWEEN ? AND ?", startTime, endTime).
		Group("date(created_at)").
		Order("date ASC").
		Find(&stats).Error
	return stats, err
}

func (r *AuditRepository) GetNamespaceStats(startTime, endTime time.Time) ([]NamespaceStat, error) {
	var stats []NamespaceStat
	err := r.db.Model(&models.AuditLog{}).
		Select("namespace_id, count(*) as count").
		Where("created_at BETWEEN ? AND ?", startTime, endTime).
		Group("namespace_id").
		Order("count DESC").
		Find(&stats).Error
	return stats, err
}

func (r *AuditRepository) GetTotalCount() (int64, error) {
	var count int64
	err := r.db.Model(&models.AuditLog{}).Count(&count).Error
	return count, err
}

func (r *AuditRepository) GetComplianceFailCount(startTime, endTime time.Time) (int64, error) {
	var count int64
	err := r.db.Model(&models.AuditLog{}).
		Where("compliance_pass = ? AND created_at BETWEEN ? AND ?", false, startTime, endTime).
		Count(&count).Error
	return count, err
}

func (r *AuditRepository) GetAutoRollbackCount(startTime, endTime time.Time) (int64, error) {
	var count int64
	err := r.db.Model(&models.AuditLog{}).
		Where("is_auto_rollback = ? AND created_at BETWEEN ? AND ?", true, startTime, endTime).
		Count(&count).Error
	return count, err
}

func (r *AuditRepository) GetTopChangedConfigs(startTime, endTime time.Time, limit int) ([]models.AuditLog, error) {
	var logs []models.AuditLog
	err := r.db.Model(&models.AuditLog{}).
		Select("namespace_id, `group`, data_id, count(*) as id").
		Where("created_at BETWEEN ? AND ?", startTime, endTime).
		Group("namespace_id, `group`, data_id").
		Order("id DESC").
		Limit(limit).
		Find(&logs).Error
	return logs, err
}
