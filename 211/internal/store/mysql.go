package store

import (
	"context"
	"time"

	"scheduler/internal/models"
	"scheduler/pkg/lock"

	"gorm.io/driver/mysql"
	"gorm.io/gorm"
)

type ExecutionStore interface {
	CreateExecution(ctx context.Context, exec *models.TaskExecution) error
	GetExecution(ctx context.Context, id string) (*models.TaskExecution, error)
	ListExecutions(ctx context.Context, taskID string, offset, limit int) ([]models.TaskExecution, int64, error)
	UpdateExecution(ctx context.Context, exec *models.TaskExecution) error
	UpdateExecutionStatus(ctx context.Context, id string, status models.ExecutionStatus, result, errMsg string) error
}

type MySQLStore struct {
	db              *gorm.DB
	usePartitioning bool
}

func NewMySQLStore(dsn string) (*MySQLStore, error) {
	return NewMySQLStoreWithPartitioning(dsn, true)
}

func NewMySQLStoreWithPartitioning(dsn string, usePartitioning bool) (*MySQLStore, error) {
	db, err := gorm.Open(mysql.Open(dsn), &gorm.Config{})
	if err != nil {
		return nil, err
	}

	sqlDB, err := db.DB()
	if err != nil {
		return nil, err
	}
	sqlDB.SetMaxOpenConns(100)
	sqlDB.SetMaxIdleConns(10)
	sqlDB.SetConnMaxLifetime(time.Hour)

	if err := db.AutoMigrate(&models.Task{}, &models.AuditLog{}, &models.WorkerNode{}); err != nil {
		return nil, err
	}

	store := &MySQLStore{
		db:              db,
		usePartitioning: usePartitioning,
	}

	if usePartitioning {
		if err := CreateExecutionPartitions(db, 3); err != nil {
			return nil, err
		}
	} else {
		if err := db.AutoMigrate(&models.TaskExecution{}); err != nil {
			return nil, err
		}
	}

	return store, nil
}

func (s *MySQLStore) getExecutionTable(t time.Time) (string, error) {
	if !s.usePartitioning {
		return "task_executions", nil
	}
	return EnsureExecutionPartition(s.db, t)
}

func (s *MySQLStore) CreateTask(ctx context.Context, task *models.Task) error {
	return s.db.WithContext(ctx).Create(task).Error
}

func (s *MySQLStore) GetTask(ctx context.Context, id string) (*models.Task, error) {
	var task models.Task
	if err := s.db.WithContext(ctx).Where("id = ?", id).First(&task).Error; err != nil {
		return nil, err
	}
	return &task, nil
}

func (s *MySQLStore) ListTasks(ctx context.Context, offset, limit int) ([]models.Task, int64, error) {
	var tasks []models.Task
	var count int64

	if err := s.db.WithContext(ctx).Model(&models.Task{}).Count(&count).Error; err != nil {
		return nil, 0, err
	}

	if err := s.db.WithContext(ctx).Offset(offset).Limit(limit).Find(&tasks).Error; err != nil {
		return nil, 0, err
	}

	return tasks, count, nil
}

func (s *MySQLStore) UpdateTask(ctx context.Context, task *models.Task) error {
	return s.db.WithContext(ctx).Save(task).Error
}

func (s *MySQLStore) UpdateTaskStatus(ctx context.Context, id string, status models.TaskStatus) error {
	return s.db.WithContext(ctx).Model(&models.Task{}).Where("id = ?", id).Update("status", status).Error
}

func (s *MySQLStore) GetPendingTasks(ctx context.Context) ([]models.Task, error) {
	var tasks []models.Task
	now := time.Now()
	err := s.db.WithContext(ctx).Where(
		"status = ? AND next_run_at <= ?",
		models.TaskStatusPending,
		now,
	).Find(&tasks).Error
	return tasks, err
}

func (s *MySQLStore) GetTasksByDependency(ctx context.Context, taskID string) ([]models.Task, error) {
	var tasks []models.Task
	err := s.db.WithContext(ctx).Where(
		"status = ? AND FIND_IN_SET(?, dependencies) > 0",
		models.TaskStatusPending,
		taskID,
	).Find(&tasks).Error
	return tasks, err
}

func (s *MySQLStore) CreateExecution(ctx context.Context, exec *models.TaskExecution) error {
	table, err := s.getExecutionTable(exec.CreatedAt)
	if err != nil {
		return err
	}
	return s.db.WithContext(ctx).Table(table).Create(exec).Error
}

func (s *MySQLStore) GetExecution(ctx context.Context, id string) (*models.TaskExecution, error) {
	if !s.usePartitioning {
		var exec models.TaskExecution
		if err := s.db.WithContext(ctx).Where("id = ?", id).First(&exec).Error; err != nil {
			return nil, err
		}
		return &exec, nil
	}

	endTime := time.Now()
	startTime := endTime.AddDate(0, -6, 0)
	tables := GetPartitionTablesInRange(startTime, endTime)

	for _, table := range tables {
		var exec models.TaskExecution
		if err := s.db.WithContext(ctx).Table(table).Where("id = ?", id).First(&exec).Error; err != nil {
			continue
		}
		return &exec, nil
	}

	return nil, gorm.ErrRecordNotFound
}

func (s *MySQLStore) ListExecutions(ctx context.Context, taskID string, offset, limit int) ([]models.TaskExecution, int64, error) {
	if !s.usePartitioning {
		var executions []models.TaskExecution
		var count int64

		query := s.db.WithContext(ctx).Model(&models.TaskExecution{})
		if taskID != "" {
			query = query.Where("task_id = ?", taskID)
		}

		if err := query.Count(&count).Error; err != nil {
			return nil, 0, err
		}

		if err := query.Offset(offset).Limit(limit).Order("created_at DESC").Find(&executions).Error; err != nil {
			return nil, 0, err
		}

		return executions, count, nil
	}

	return s.listExecutionsPartitioned(ctx, taskID, offset, limit)
}

func (s *MySQLStore) listExecutionsPartitioned(ctx context.Context, taskID string, offset, limit int) ([]models.TaskExecution, int64, error) {
	endTime := time.Now()
	startTime := endTime.AddDate(0, -6, 0)
	tables := GetPartitionTablesInRange(startTime, endTime)

	if len(tables) == 0 {
		return []models.TaskExecution{}, 0, nil
	}

	var whereClause string
	var args []interface{}
	if taskID != "" {
		whereClause = "task_id = ?"
		args = append(args, taskID)
	}

	var allExecutions []models.TaskExecution
	for _, table := range tables {
		var execs []models.TaskExecution
		query := s.db.WithContext(ctx).Table(table)
		if taskID != "" {
			query = query.Where("task_id = ?", taskID)
		}
		if err := query.Order("created_at DESC").Find(&execs).Error; err != nil {
			continue
		}
		allExecutions = append(allExecutions, execs...)
	}

	count := int64(len(allExecutions))

	if offset >= len(allExecutions) {
		return []models.TaskExecution{}, count, nil
	}

	endIdx := offset + limit
	if endIdx > len(allExecutions) {
		endIdx = len(allExecutions)
	}

	return allExecutions[offset:endIdx], count, nil
}

func (s *MySQLStore) UpdateExecution(ctx context.Context, exec *models.TaskExecution) error {
	if !s.usePartitioning {
		return s.db.WithContext(ctx).Save(exec).Error
	}

	table, err := s.findExecutionTable(ctx, exec.ID)
	if err != nil {
		return err
	}

	return s.db.WithContext(ctx).Table(table).Save(exec).Error
}

func (s *MySQLStore) UpdateExecutionStatus(ctx context.Context, id string, status models.ExecutionStatus, result, errMsg string) error {
	updates := map[string]interface{}{
		"status": status,
		"result": result,
		"error":  errMsg,
	}
	if status == models.ExecutionStatusSuccess || status == models.ExecutionStatusFailed || status == models.ExecutionStatusTimeout {
		updates["end_time"] = time.Now()
	}

	if !s.usePartitioning {
		return s.db.WithContext(ctx).Model(&models.TaskExecution{}).Where("id = ?", id).Updates(updates).Error
	}

	table, err := s.findExecutionTable(ctx, id)
	if err != nil {
		return err
	}

	return s.db.WithContext(ctx).Table(table).Where("id = ?", id).Updates(updates).Error
}

func (s *MySQLStore) findExecutionTable(ctx context.Context, id string) (string, error) {
	endTime := time.Now()
	startTime := endTime.AddDate(0, -6, 0)
	tables := GetPartitionTablesInRange(startTime, endTime)

	for _, table := range tables {
		var count int64
		if err := s.db.WithContext(ctx).Table(table).Where("id = ?", id).Count(&count).Error; err != nil {
			continue
		}
		if count > 0 {
			return table, nil
		}
	}

	return "", gorm.ErrRecordNotFound
}

func (s *MySQLStore) CreateNextMonthPartition() error {
	nextMonth := time.Now().AddDate(0, 1, 0)
	return CreateExecutionPartition(s.db, nextMonth)
}

func (s *MySQLStore) IsPartitioningEnabled() bool {
	return s.usePartitioning
}

func (s *MySQLStore) GetDB() *gorm.DB {
	return s.db
}

func (s *MySQLStore) UpsertWorkerNode(ctx context.Context, node *models.WorkerNode) error {
	var existing models.WorkerNode
	err := s.db.WithContext(ctx).Where("id = ?", node.ID).First(&existing).Error
	if err == gorm.ErrRecordNotFound {
		return s.db.WithContext(ctx).Create(node).Error
	}
	return s.db.WithContext(ctx).Save(node).Error
}

func (s *MySQLStore) UpdateWorkerStatus(ctx context.Context, workerID string, status string) error {
	return s.db.WithContext(ctx).Model(&models.WorkerNode{}).
		Where("id = ?", workerID).
		Updates(map[string]interface{}{
			"status":     status,
			"updated_at": time.Now(),
		}).Error
}

func (s *MySQLStore) UpdateHeartbeat(ctx context.Context, workerID string, heartbeat time.Time) error {
	return s.db.WithContext(ctx).Model(&models.WorkerNode{}).
		Where("id = ?", workerID).
		Updates(map[string]interface{}{
			"last_heartbeat": heartbeat,
			"updated_at":     time.Now(),
		}).Error
}

func (s *MySQLStore) GetFailedWorkerNodes(ctx context.Context, threshold time.Time) ([]models.WorkerNode, error) {
	var nodes []models.WorkerNode
	err := s.db.WithContext(ctx).
		Where("status = ? AND last_heartbeat < ?", models.WorkerStatusOnline, threshold).
		Find(&nodes).Error
	return nodes, err
}

func (s *MySQLStore) GetRunningExecutionsByWorker(ctx context.Context, workerID string) ([]models.TaskExecution, error) {
	var executions []models.TaskExecution
	err := s.db.WithContext(ctx).
		Where("worker_id = ? AND status = ?", workerID, models.ExecutionStatusRunning).
		Find(&executions).Error
	return executions, err
}

func (s *MySQLStore) RecordAuditLog(ctx context.Context, log *models.AuditLog) error {
	return s.db.WithContext(ctx).Create(log).Error
}

func (s *MySQLStore) ListAuditLogs(ctx context.Context, taskID, event string, offset, limit int) ([]models.AuditLog, int64, error) {
	var logs []models.AuditLog
	var count int64

	query := s.db.WithContext(ctx).Model(&models.AuditLog{})
	if taskID != "" {
		query = query.Where("task_id = ?", taskID)
	}
	if event != "" {
		query = query.Where("event = ?", event)
	}

	if err := query.Count(&count).Error; err != nil {
		return nil, 0, err
	}

	if err := query.Order("created_at DESC").Offset(offset).Limit(limit).Find(&logs).Error; err != nil {
		return nil, 0, err
	}

	return logs, count, nil
}

func (s *MySQLStore) ListWorkerNodes(ctx context.Context) ([]models.WorkerNode, error) {
	var nodes []models.WorkerNode
	err := s.db.WithContext(ctx).Find(&nodes).Error
	return nodes, err
}

var redisLocker *lock.RedisLock

func (s *MySQLStore) SetRedisLocker(locker *lock.RedisLock) {
	redisLocker = locker
}

func (s *MySQLStore) GetRedisLocker() *lock.RedisLock {
	return redisLocker
}
