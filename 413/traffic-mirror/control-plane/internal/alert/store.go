package alert

import (
	"encoding/json"
	"time"

	"github.com/traffic-mirror/control-plane/internal/model"
	"github.com/traffic-mirror/control-plane/pkg/types"
	"gorm.io/gorm"
)

type Store struct {
	db *gorm.DB
}

func NewStore(db *gorm.DB) *Store {
	return &Store{db: db}
}

func (s *Store) Create(alert *types.AnomalyAlert) error {
	detailsJSON, _ := json.Marshal(alert.Details)

	dbAlert := model.AnomalyAlert{
		Timestamp:    alert.Timestamp,
		RequestID:    alert.RequestID,
		Path:         alert.Path,
		Method:       alert.Method,
		AnomalyType:  alert.AnomalyType,
		Severity:     alert.Severity,
		Message:      alert.Message,
		Details:      string(detailsJSON),
		Acknowledged: alert.Acknowledged,
	}

	if err := s.db.Create(&dbAlert).Error; err != nil {
		return err
	}

	alert.ID = dbAlert.ID
	alert.CreatedAt = dbAlert.CreatedAt
	return nil
}

func (s *Store) GetByID(id int64) (types.AnomalyAlert, error) {
	var dbAlert model.AnomalyAlert
	if err := s.db.First(&dbAlert, id).Error; err != nil {
		return types.AnomalyAlert{}, err
	}
	return convertAlert(dbAlert), nil
}

func (s *Store) Query(query types.AnomalyQuery) ([]types.AnomalyAlert, int64, error) {
	var dbAlerts []model.AnomalyAlert
	var total int64

	db := s.db.Model(&model.AnomalyAlert{})

	if query.AnomalyType != "" {
		db = db.Where("anomaly_type = ?", query.AnomalyType)
	}
	if query.Severity != "" {
		db = db.Where("severity = ?", query.Severity)
	}
	if query.Acknowledged != nil {
		db = db.Where("acknowledged = ?", *query.Acknowledged)
	}
	if query.StartTime > 0 {
		db = db.Where("timestamp >= ?", query.StartTime)
	}
	if query.EndTime > 0 {
		db = db.Where("timestamp <= ?", query.EndTime)
	}

	if err := db.Count(&total).Error; err != nil {
		return nil, 0, err
	}

	page := query.Page
	if page < 1 {
		page = 1
	}
	pageSize := query.PageSize
	if pageSize < 1 {
		pageSize = 20
	}
	if pageSize > 100 {
		pageSize = 100
	}

	offset := (page - 1) * pageSize
	if err := db.Order("timestamp DESC").Offset(offset).Limit(pageSize).Find(&dbAlerts).Error; err != nil {
		return nil, total, err
	}

	alerts := make([]types.AnomalyAlert, 0, len(dbAlerts))
	for _, a := range dbAlerts {
		alerts = append(alerts, convertAlert(a))
	}

	return alerts, total, nil
}

func (s *Store) Acknowledge(id int64) error {
	return s.db.Model(&model.AnomalyAlert{}).Where("id = ?", id).Update("acknowledged", true).Error
}

func (s *Store) AcknowledgeAll() error {
	return s.db.Model(&model.AnomalyAlert{}).Where("acknowledged = ?", false).Update("acknowledged", true).Error
}

func (s *Store) Delete(id int64) error {
	return s.db.Delete(&model.AnomalyAlert{}, id).Error
}

func (s *Store) DeleteOlderThan(days int) (int64, error) {
	cutoff := time.Now().AddDate(0, 0, -days).UnixNano()
	result := s.db.Where("timestamp < ?", cutoff).Delete(&model.AnomalyAlert{})
	return result.RowsAffected, result.Error
}

func (s *Store) GetStats() (types.AnomalyStats, error) {
	var stats types.AnomalyStats
	stats.TypeCount = make(map[string]int64)
	stats.SeverityCount = make(map[string]int64)

	if err := s.db.Model(&model.AnomalyAlert{}).Count(&stats.TotalCount).Error; err != nil {
		return stats, err
	}

	if err := s.db.Model(&model.AnomalyAlert{}).Where("acknowledged = ?", true).Count(&stats.AckCount).Error; err != nil {
		return stats, err
	}

	stats.UnackCount = stats.TotalCount - stats.AckCount

	type TypeCount struct {
		AnomalyType string
		Count       int64
	}
	var typeCounts []TypeCount
	if err := s.db.Model(&model.AnomalyAlert{}).
		Select("anomaly_type, count(*) as count").
		Group("anomaly_type").
		Scan(&typeCounts).Error; err == nil {
		for _, tc := range typeCounts {
			stats.TypeCount[tc.AnomalyType] = tc.Count
		}
	}

	type SeverityCount struct {
		Severity string
		Count    int64
	}
	var sevCounts []SeverityCount
	if err := s.db.Model(&model.AnomalyAlert{}).
		Select("severity, count(*) as count").
		Group("severity").
		Scan(&sevCounts).Error; err == nil {
		for _, sc := range sevCounts {
			stats.SeverityCount[sc.Severity] = sc.Count
		}
	}

	return stats, nil
}

func convertAlert(a model.AnomalyAlert) types.AnomalyAlert {
	alert := types.AnomalyAlert{
		ID:           a.ID,
		Timestamp:    a.Timestamp,
		RequestID:    a.RequestID,
		Path:         a.Path,
		Method:       a.Method,
		AnomalyType:  a.AnomalyType,
		Severity:     a.Severity,
		Message:      a.Message,
		Acknowledged: a.Acknowledged,
		CreatedAt:    a.CreatedAt,
	}

	if a.Details != "" {
		var details map[string]string
		if err := json.Unmarshal([]byte(a.Details), &details); err == nil {
			alert.Details = details
		}
	}

	return alert
}
