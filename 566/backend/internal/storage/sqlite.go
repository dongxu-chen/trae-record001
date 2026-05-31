package storage

import (
	"fault-injection-platform/internal/model"
	"os"
	"path/filepath"

	"gorm.io/driver/sqlite"
	"gorm.io/gorm"
)

type SQLiteDB struct {
	db *gorm.DB
}

func NewSQLiteDB(dbPath string) (*SQLiteDB, error) {
	dir := filepath.Dir(dbPath)
	if err := os.MkdirAll(dir, 0755); err != nil {
		return nil, err
	}

	db, err := gorm.Open(sqlite.Open(dbPath), &gorm.Config{})
	if err != nil {
		return nil, err
	}

	if err := db.AutoMigrate(
		&model.Fault{},
		&model.FaultScenario{},
		&model.ScenarioExecution{},
		&model.MetricData{},
	); err != nil {
		return nil, err
	}

	return &SQLiteDB{db: db}, nil
}

func (s *SQLiteDB) Close() error {
	sqlDB, err := s.db.DB()
	if err != nil {
		return err
	}
	return sqlDB.Close()
}

func (s *SQLiteDB) CreateFault(fault *model.Fault) error {
	return s.db.Create(fault).Error
}

func (s *SQLiteDB) GetFault(id string) (*model.Fault, error) {
	var fault model.Fault
	if err := s.db.First(&fault, "id = ?", id).Error; err != nil {
		return nil, err
	}
	return &fault, nil
}

func (s *SQLiteDB) ListFaults() ([]*model.Fault, error) {
	var faults []*model.Fault
	if err := s.db.Order("created_at desc").Find(&faults).Error; err != nil {
		return nil, err
	}
	return faults, nil
}

func (s *SQLiteDB) UpdateFault(fault *model.Fault) error {
	return s.db.Save(fault).Error
}

func (s *SQLiteDB) DeleteFault(id string) error {
	return s.db.Delete(&model.Fault{}, "id = ?", id).Error
}

func (s *SQLiteDB) CreateScenario(scenario *model.FaultScenario) error {
	return s.db.Create(scenario).Error
}

func (s *SQLiteDB) GetScenario(id string) (*model.FaultScenario, error) {
	var scenario model.FaultScenario
	if err := s.db.First(&scenario, "id = ?", id).Error; err != nil {
		return nil, err
	}
	return &scenario, nil
}

func (s *SQLiteDB) ListScenarios() ([]*model.FaultScenario, error) {
	var scenarios []*model.FaultScenario
	if err := s.db.Order("created_at desc").Find(&scenarios).Error; err != nil {
		return nil, err
	}
	return scenarios, nil
}

func (s *SQLiteDB) UpdateScenario(scenario *model.FaultScenario) error {
	return s.db.Save(scenario).Error
}

func (s *SQLiteDB) DeleteScenario(id string) error {
	return s.db.Delete(&model.FaultScenario{}, "id = ?", id).Error
}

func (s *SQLiteDB) CreateExecution(exec *model.ScenarioExecution) error {
	return s.db.Create(exec).Error
}

func (s *SQLiteDB) GetExecution(id string) (*model.ScenarioExecution, error) {
	var exec model.ScenarioExecution
	if err := s.db.First(&exec, "id = ?", id).Error; err != nil {
		return nil, err
	}
	return &exec, nil
}

func (s *SQLiteDB) UpdateExecution(exec *model.ScenarioExecution) error {
	return s.db.Save(exec).Error
}

func (s *SQLiteDB) ListExecutions(scenarioID string) ([]*model.ScenarioExecution, error) {
	var execs []*model.ScenarioExecution
	query := s.db.Order("created_at desc")
	if scenarioID != "" {
		query = query.Where("scenario_id = ?", scenarioID)
	}
	if err := query.Find(&execs).Error; err != nil {
		return nil, err
	}
	return execs, nil
}

func (s *SQLiteDB) SaveMetric(metric *model.MetricData) error {
	return s.db.Create(metric).Error
}

func (s *SQLiteDB) GetMetrics(faultID string, metricType string) ([]*model.MetricData, error) {
	var metrics []*model.MetricData
	query := s.db.Where("fault_id = ?", faultID)
	if metricType != "" {
		query = query.Where("metric_type = ?", metricType)
	}
	if err := query.Order("timestamp desc").Find(&metrics).Error; err != nil {
		return nil, err
	}
	return metrics, nil
}
