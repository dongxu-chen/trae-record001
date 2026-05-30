package audit

import (
	"context"
	"time"

	"github.com/google/uuid"
	"github.com/sirupsen/logrus"
	"gorm.io/gorm"

	"github.com/keymgmt/service/backend/internal/audit/async"
	"github.com/keymgmt/service/backend/internal/models"
)

type AuditServiceInterface interface {
	Log(ctx context.Context, entry AuditEntry) error
	GetLogsBySecret(ctx context.Context, secretID uuid.UUID, limit, offset int) ([]models.AuditLog, int64, error)
	GetLogsByUser(ctx context.Context, user string, limit, offset int) ([]models.AuditLog, int64, error)
	GetLogsByTimeRange(ctx context.Context, startTime, endTime time.Time, limit, offset int) ([]models.AuditLog, int64, error)
	GetAllLogs(ctx context.Context, limit, offset int) ([]models.AuditLog, int64, error)
	GetRecentLogs(ctx context.Context, minutes int) ([]models.AuditLog, error)
	GetActionStats(ctx context.Context) (map[string]int64, error)
	CleanupOldLogs(ctx context.Context, retentionDays int) (int64, error)
}

type AuditServiceWithAsync struct {
	syncService  *AuditService
	asyncService *async.AsyncAuditService
	useAsync     bool
}

func NewAuditServiceWithAsync(db *gorm.DB, log *logrus.Logger, useAsync bool, asyncCfg async.Config) *AuditServiceWithAsync {
	syncService := NewAuditService(db, log)

	var asyncService *async.AsyncAuditService
	if useAsync {
		asyncService = async.NewAsyncAuditService(db, log, asyncCfg)
		asyncService.Start()
	}

	return &AuditServiceWithAsync{
		syncService:  syncService,
		asyncService: asyncService,
		useAsync:     useAsync,
	}
}

func (s *AuditServiceWithAsync) Log(ctx context.Context, entry AuditEntry) error {
	if s.useAsync && s.asyncService != nil {
		s.asyncService.LogEntry(async.AuditEntry{
			SecretID:  entry.SecretID.String(),
			Action:    entry.Action,
			User:      entry.User,
			IPAddress: entry.IPAddress,
			UserAgent: entry.UserAgent,
			Success:   entry.Success,
			Message:   entry.Message,
		})
		return nil
	}
	return s.syncService.Log(ctx, entry)
}

func (s *AuditServiceWithAsync) GetLogsBySecret(ctx context.Context, secretID uuid.UUID, limit, offset int) ([]models.AuditLog, int64, error) {
	return s.syncService.GetLogsBySecret(ctx, secretID, limit, offset)
}

func (s *AuditServiceWithAsync) GetLogsByUser(ctx context.Context, user string, limit, offset int) ([]models.AuditLog, int64, error) {
	return s.syncService.GetLogsByUser(ctx, user, limit, offset)
}

func (s *AuditServiceWithAsync) GetLogsByTimeRange(ctx context.Context, startTime, endTime time.Time, limit, offset int) ([]models.AuditLog, int64, error) {
	return s.syncService.GetLogsByTimeRange(ctx, startTime, endTime, limit, offset)
}

func (s *AuditServiceWithAsync) GetAllLogs(ctx context.Context, limit, offset int) ([]models.AuditLog, int64, error) {
	return s.syncService.GetAllLogs(ctx, limit, offset)
}

func (s *AuditServiceWithAsync) GetRecentLogs(ctx context.Context, minutes int) ([]models.AuditLog, error) {
	return s.syncService.GetRecentLogs(ctx, minutes)
}

func (s *AuditServiceWithAsync) GetActionStats(ctx context.Context) (map[string]int64, error) {
	return s.syncService.GetActionStats(ctx)
}

func (s *AuditServiceWithAsync) CleanupOldLogs(ctx context.Context, retentionDays int) (int64, error) {
	return s.syncService.CleanupOldLogs(ctx, retentionDays)
}

func (s *AuditServiceWithAsync) Stop() {
	if s.asyncService != nil {
		s.asyncService.Stop()
	}
}

func (s *AuditServiceWithAsync) GetAsyncMetrics() *async.Metrics {
	if s.asyncService == nil {
		return nil
	}
	m := s.asyncService.GetMetrics()
	return &m
}
