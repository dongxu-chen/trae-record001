package compare

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

func (s *Store) Save(result *types.ComparisonResult) error {
	diffsJSON, _ := json.Marshal(result.Differences)
	protoDiffsJSON, _ := json.Marshal(result.ProtoDifferences)

	dbResult := model.ComparisonResult{
		RequestID:        result.RequestID,
		Timestamp:        result.Timestamp,
		Path:             result.Path,
		Method:           result.Method,
		ProdStatus:       result.ProdStatus,
		TestStatus:       result.TestStatus,
		StatusMatch:      result.StatusMatch,
		BodyMatch:        result.BodyMatch,
		HeaderMatch:      result.HeaderMatch,
		HasDiff:          result.HasDiff,
		Severity:         result.Severity,
		ProdBodyHash:     result.ProdBodyHash,
		TestBodyHash:     result.TestBodyHash,
		ProdBodyLen:      result.ProdBodyLen,
		TestBodyLen:      result.TestBodyLen,
		Differences:      string(diffsJSON),
		ProdHeaders:      result.ProdHeaders,
		TestHeaders:      result.TestHeaders,
		ProdBody:         result.ProdBody,
		TestBody:         result.TestBody,
		IsProto:          result.IsProto,
		ProtoMessageType: result.ProtoMessageType,
		ProtoDifferences: string(protoDiffsJSON),
		Anomaly:          result.Anomaly,
	}

	return s.db.Create(&dbResult).Error
}

func (s *Store) Query(query types.ComparisonQuery) ([]types.ComparisonResult, int64, error) {
	var dbResults []model.ComparisonResult
	var total int64

	db := s.db.Model(&model.ComparisonResult{})

	if query.Path != "" {
		db = db.Where("path LIKE ?", "%"+query.Path+"%")
	}
	if query.Method != "" {
		db = db.Where("method = ?", query.Method)
	}
	if query.Severity != "" {
		db = db.Where("severity = ?", query.Severity)
	}
	if query.HasDiff != nil {
		db = db.Where("has_diff = ?", *query.HasDiff)
	}
	if query.IsProto != nil {
		db = db.Where("is_proto = ?", *query.IsProto)
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
	if err := db.Order("timestamp DESC").Offset(offset).Limit(pageSize).Find(&dbResults).Error; err != nil {
		return nil, total, err
	}

	results := make([]types.ComparisonResult, 0, len(dbResults))
	for _, r := range dbResults {
		result := convertDBResult(r)
		results = append(results, result)
	}

	return results, total, nil
}

func (s *Store) GetByID(id int64) (types.ComparisonResult, error) {
	var dbResult model.ComparisonResult
	err := s.db.First(&dbResult, id).Error
	if err != nil {
		return types.ComparisonResult{}, err
	}
	return convertDBResult(dbResult), nil
}

func (s *Store) GetStats() (types.ComparisonStats, error) {
	var stats types.ComparisonStats
	stats.SeverityCount = make(map[string]int64)

	if err := s.db.Model(&model.ComparisonResult{}).Count(&stats.TotalCount).Error; err != nil {
		return stats, err
	}

	if err := s.db.Model(&model.ComparisonResult{}).Where("has_diff = ?", false).Count(&stats.MatchCount).Error; err != nil {
		return stats, err
	}

	stats.MismatchCount = stats.TotalCount - stats.MatchCount

	if err := s.db.Model(&model.ComparisonResult{}).Where("is_proto = ?", true).Count(&stats.ProtoCount).Error; err != nil {
		return stats, err
	}

	type SeverityCount struct {
		Severity string
		Count    int64
	}
	var counts []SeverityCount
	if err := s.db.Model(&model.ComparisonResult{}).
		Select("severity, count(*) as count").
		Where("severity != ?", "none").
		Group("severity").
		Scan(&counts).Error; err != nil {
		return stats, err
	}

	for _, c := range counts {
		stats.SeverityCount[c.Severity] = c.Count
	}

	type TopDiffRow struct {
		Path     string
		Count    int64
		Severity string
	}
	var topDiffs []TopDiffRow
	if err := s.db.Model(&model.ComparisonResult{}).
		Select("path, count(*) as count, max(severity) as severity").
		Where("has_diff = ?", true).
		Group("path").
		Order("count DESC").
		Limit(10).
		Scan(&topDiffs).Error; err != nil {
		return stats, err
	}

	for _, td := range topDiffs {
		stats.TopDiffs = append(stats.TopDiffs, types.TopDiff{
			Path:     td.Path,
			Count:    td.Count,
			Severity: td.Severity,
		})
	}

	var topProtoDiffs []TopDiffRow
	if err := s.db.Model(&model.ComparisonResult{}).
		Select("path, count(*) as count, max(severity) as severity").
		Where("has_diff = ? AND is_proto = ?", true, true).
		Group("path").
		Order("count DESC").
		Limit(10).
		Scan(&topProtoDiffs).Error; err != nil {
		return stats, err
	}

	for _, td := range topProtoDiffs {
		stats.TopProtoDiffs = append(stats.TopProtoDiffs, types.TopDiff{
			Path:     td.Path,
			Count:    td.Count,
			Severity: td.Severity,
		})
	}

	return stats, nil
}

func (s *Store) DeleteOlderThan(days int) (int64, error) {
	cutoff := time.Now().AddDate(0, 0, -days).UnixNano()
	result := s.db.Where("timestamp < ?", cutoff).Delete(&model.ComparisonResult{})
	return result.RowsAffected, result.Error
}

func (s *Store) GetRecent(limit int) ([]types.ComparisonResult, error) {
	var dbResults []model.ComparisonResult
	if err := s.db.Order("timestamp DESC").Limit(limit).Find(&dbResults).Error; err != nil {
		return nil, err
	}

	results := make([]types.ComparisonResult, 0, len(dbResults))
	for _, r := range dbResults {
		results = append(results, convertDBResult(r))
	}
	return results, nil
}

func convertDBResult(r model.ComparisonResult) types.ComparisonResult {
	result := types.ComparisonResult{
		ID:               r.ID,
		RequestID:        r.RequestID,
		Timestamp:        r.Timestamp,
		Path:             r.Path,
		Method:           r.Method,
		ProdStatus:       r.ProdStatus,
		TestStatus:       r.TestStatus,
		StatusMatch:      r.StatusMatch,
		BodyMatch:        r.BodyMatch,
		HeaderMatch:      r.HeaderMatch,
		HasDiff:          r.HasDiff,
		Severity:         r.Severity,
		ProdBodyHash:     r.ProdBodyHash,
		TestBodyHash:     r.TestBodyHash,
		ProdBodyLen:      r.ProdBodyLen,
		TestBodyLen:      r.TestBodyLen,
		ProdHeaders:      r.ProdHeaders,
		TestHeaders:      r.TestHeaders,
		ProdBody:         r.ProdBody,
		TestBody:         r.TestBody,
		IsProto:          r.IsProto,
		ProtoMessageType: r.ProtoMessageType,
	}

	if r.Differences != "" {
		var diffs []types.Difference
		if err := json.Unmarshal([]byte(r.Differences), &diffs); err == nil {
			result.Differences = diffs
		}
	}

	if r.ProtoDifferences != "" {
		var protoDiffs []types.ProtoFieldDiff
		if err := json.Unmarshal([]byte(r.ProtoDifferences), &protoDiffs); err == nil {
			result.ProtoDifferences = protoDiffs
		}
	}

	if r.Anomaly != "" {
		result.Anomaly = r.Anomaly
	}

	return result
}
