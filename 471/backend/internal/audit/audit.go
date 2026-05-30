package audit

import (
	"context"
	"time"

	"github.com/google/uuid"
	"github.com/sirupsen/logrus"
	"gorm.io/gorm"

	"github.com/keymgmt/service/backend/internal/models"
)

type AuditService struct {
	db  *gorm.DB
	log *logrus.Logger
}

type AuditEntry struct {
	SecretID  uuid.UUID
	Action    string
	User      string
	IPAddress string
	UserAgent string
	Success   bool
	Message   string
}

func NewAuditService(db *gorm.DB, log *logrus.Logger) *AuditService {
	return &AuditService{
		db:  db,
		log: log,
	}
}

func (as *AuditService) Log(ctx context.Context, entry AuditEntry) error {
	auditLog := &models.AuditLog{
		SecretID:  entry.SecretID,
		Action:    entry.Action,
		User:      entry.User,
		IPAddress: entry.IPAddress,
		UserAgent: entry.UserAgent,
		Success:   entry.Success,
		Message:   entry.Message,
		CreatedAt: time.Now(),
	}

	if err := as.db.Create(auditLog).Error; err != nil {
		as.log.Errorf("Failed to create audit log: %v", err)
		return err
	}

	as.log.WithFields(logrus.Fields{
		"action":    entry.Action,
		"user":      entry.User,
		"secret_id": entry.SecretID,
		"success":   entry.Success,
	}).Info("Audit log created")

	return nil
}

func (as *AuditService) GetLogsBySecret(ctx context.Context, secretID uuid.UUID, limit, offset int) ([]models.AuditLog, int64, error) {
	var logs []models.AuditLog
	var total int64

	query := as.db.Model(&models.AuditLog{}).Where("secret_id = ?", secretID)

	if err := query.Count(&total).Error; err != nil {
		as.log.Errorf("Failed to count audit logs: %v", err)
		return nil, 0, err
	}

	if err := query.Order("created_at DESC").Limit(limit).Offset(offset).Find(&logs).Error; err != nil {
		as.log.Errorf("Failed to fetch audit logs: %v", err)
		return nil, 0, err
	}

	return logs, total, nil
}

func (as *AuditService) GetLogsByUser(ctx context.Context, user string, limit, offset int) ([]models.AuditLog, int64, error) {
	var logs []models.AuditLog
	var total int64

	query := as.db.Model(&models.AuditLog{}).Where("user = ?", user)

	if err := query.Count(&total).Error; err != nil {
		as.log.Errorf("Failed to count audit logs: %v", err)
		return nil, 0, err
	}

	if err := query.Order("created_at DESC").Limit(limit).Offset(offset).Find(&logs).Error; err != nil {
		as.log.Errorf("Failed to fetch audit logs: %v", err)
		return nil, 0, err
	}

	return logs, total, nil
}

func (as *AuditService) GetLogsByTimeRange(ctx context.Context, startTime, endTime time.Time, limit, offset int) ([]models.AuditLog, int64, error) {
	var logs []models.AuditLog
	var total int64

	query := as.db.Model(&models.AuditLog{}).Where("created_at BETWEEN ? AND ?", startTime, endTime)

	if err := query.Count(&total).Error; err != nil {
		as.log.Errorf("Failed to count audit logs: %v", err)
		return nil, 0, err
	}

	if err := query.Order("created_at DESC").Limit(limit).Offset(offset).Find(&logs).Error; err != nil {
		as.log.Errorf("Failed to fetch audit logs: %v", err)
		return nil, 0, err
	}

	return logs, total, nil
}

func (as *AuditService) GetAllLogs(ctx context.Context, limit, offset int) ([]models.AuditLog, int64, error) {
	var logs []models.AuditLog
	var total int64

	if err := as.db.Model(&models.AuditLog{}).Count(&total).Error; err != nil {
		as.log.Errorf("Failed to count audit logs: %v", err)
		return nil, 0, err
	}

	if err := as.db.Order("created_at DESC").Limit(limit).Offset(offset).Find(&logs).Error; err != nil {
		as.log.Errorf("Failed to fetch audit logs: %v", err)
		return nil, 0, err
	}

	return logs, total, nil
}

func (as *AuditService) GetRecentLogs(ctx context.Context, minutes int) ([]models.AuditLog, error) {
	var logs []models.AuditLog
	startTime := time.Now().Add(-time.Duration(minutes) * time.Minute)

	if err := as.db.Where("created_at > ?", startTime).Order("created_at DESC").Find(&logs).Error; err != nil {
		as.log.Errorf("Failed to fetch recent audit logs: %v", err)
		return nil, err
	}

	return logs, nil
}

func (as *AuditService) GetActionStats(ctx context.Context) (map[string]int64, error) {
	type ActionCount struct {
		Action string
		Count  int64
	}

	var results []ActionCount
	if err := as.db.Model(&models.AuditLog{}).Select("action, count(*) as count").Group("action").Scan(&results).Error; err != nil {
		as.log.Errorf("Failed to get action stats: %v", err)
		return nil, err
	}

	stats := make(map[string]int64)
	for _, r := range results {
		stats[r.Action] = r.Count
	}

	return stats, nil
}

func (as *AuditService) CleanupOldLogs(ctx context.Context, retentionDays int) (int64, error) {
	cutoffTime := time.Now().AddDate(0, 0, -retentionDays)

	result := as.db.Where("created_at < ?", cutoffTime).Delete(&models.AuditLog{})
	if result.Error != nil {
		as.log.Errorf("Failed to cleanup old audit logs: %v", result.Error)
		return 0, result.Error
	}

	as.log.Infof("Cleaned up %d old audit logs", result.RowsAffected)
	return result.RowsAffected, nil
}
