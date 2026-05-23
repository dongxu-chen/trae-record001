package store

import (
	"fmt"
	"strings"
	"time"

	"gorm.io/gorm"
)

const (
	baseExecutionTable = "task_executions"
)

func GetPartitionSuffix(t time.Time) string {
	return t.Format("200601")
}

func GetPartitionTable(t time.Time) string {
	return fmt.Sprintf("%s_%s", baseExecutionTable, GetPartitionSuffix(t))
}

func GetCurrentPartitionTable() string {
	return GetPartitionTable(time.Now())
}

func GetPartitionTablesInRange(start, end time.Time) []string {
	tables := make([]string, 0)

	current := time.Date(start.Year(), start.Month(), 1, 0, 0, 0, 0, start.Location())
	endMonth := time.Date(end.Year(), end.Month(), 1, 0, 0, 0, 0, end.Location())

	for !current.After(endMonth) {
		tables = append(tables, GetPartitionTable(current))
		current = current.AddDate(0, 1, 0)
	}

	return tables
}

func CreateExecutionPartition(db *gorm.DB, t time.Time) error {
	tableName := GetPartitionTable(t)

	createTableSQL := fmt.Sprintf(`
		CREATE TABLE IF NOT EXISTS %s (
			id VARCHAR(36) PRIMARY KEY,
			task_id VARCHAR(36) NOT NULL,
			status VARCHAR(20) DEFAULT 'pending',
			retry_count INT DEFAULT 0,
			worker_id VARCHAR(100),
			start_time DATETIME,
			end_time DATETIME,
			result TEXT,
			error TEXT,
			duration_ms BIGINT DEFAULT 0,
			created_at DATETIME NOT NULL,
			updated_at DATETIME NOT NULL,
			INDEX idx_task_id (task_id),
			INDEX idx_status (status),
			INDEX idx_created_at (created_at DESC)
		) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
	`, tableName)

	return db.Exec(createTableSQL).Error
}

func CreateExecutionPartitions(db *gorm.DB, months int) error {
	now := time.Now()
	for i := 0; i < months; i++ {
		t := now.AddDate(0, i, 0)
		if err := CreateExecutionPartition(db, t); err != nil {
			return fmt.Errorf("failed to create partition for %s: %w", t.Format("2006-01"), err)
		}
	}
	return nil
}

func EnsureExecutionPartition(db *gorm.DB, t time.Time) (string, error) {
	tableName := GetPartitionTable(t)

	var count int64
	db.Raw("SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = DATABASE() AND table_name = ?", tableName).Scan(&count)

	if count == 0 {
		if err := CreateExecutionPartition(db, t); err != nil {
			return "", err
		}
	}

	return tableName, nil
}

func EnsureCurrentExecutionPartition(db *gorm.DB) (string, error) {
	return EnsureExecutionPartition(db, time.Now())
}

func UnionSelectFromPartitions(db *gorm.DB, start, end time.Time, whereClause string, args ...interface{}) *gorm.DB {
	tables := GetPartitionTablesInRange(start, end)
	if len(tables) == 0 {
		return db.Raw("SELECT 1 FROM DUAL WHERE 1=0")
	}

	var selects []string
	for _, table := range tables {
		selects = append(selects, fmt.Sprintf("SELECT * FROM %s WHERE 1=1", table))
	}

	unionSQL := strings.Join(selects, " UNION ALL ")
	if whereClause != "" {
		unionSQL = fmt.Sprintf("SELECT * FROM (%s) AS combined WHERE %s", unionSQL, whereClause)
	}

	return db.Raw(unionSQL, args...)
}
