package store

import (
	"context"
	"fmt"
	"scheduler/internal/models"
	"time"

	"github.com/jackc/pgx/v4/pgxpool"
)

type PostgresStore struct {
	pool *pgxpool.Pool
}

func NewPostgresStore(host string, port int, user, password, dbname string, maxConns int) (*PostgresStore, error) {
	connStr := fmt.Sprintf("host=%s port=%d user=%s password=%s dbname=%s pool_max_conns=%d",
		host, port, user, password, dbname, maxConns)

	config, err := pgxpool.ParseConfig(connStr)
	if err != nil {
		return nil, err
	}

	pool, err := pgxpool.ConnectConfig(context.Background(), config)
	if err != nil {
		return nil, err
	}

	return &PostgresStore{pool: pool}, nil
}

func (s *PostgresStore) Close() {
	s.pool.Close()
}

func (s *PostgresStore) CreateTask(ctx context.Context, task *models.Task) error {
	query := `
		INSERT INTO tasks (id, name, cron_expr, task_type, payload, status, shard_key, shard_total,
			shard_index, next_run_time, priority, max_retries, created_at, updated_at)
		VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, NOW(), NOW())
	`
	_, err := s.pool.Exec(ctx, query,
		task.ID, task.Name, task.CronExpr, task.TaskType, task.Payload, task.Status,
		task.ShardKey, task.ShardTotal, task.ShardIndex, task.NextRunTime,
		task.Priority, task.MaxRetries)
	return err
}

func (s *PostgresStore) UpdateTask(ctx context.Context, task *models.Task) error {
	query := `
		UPDATE tasks SET name=$1, cron_expr=$2, task_type=$3, payload=$4, status=$5,
			next_run_time=$6, last_run_time=$7, last_run_status=$8, last_error=$9,
			run_count=$10, priority=$12, max_retries=$13, retry_count=$14, node_id=$15, updated_at=NOW()
		WHERE id=$11
	`
	_, err := s.pool.Exec(ctx, query,
		task.Name, task.CronExpr, task.TaskType, task.Payload, task.Status,
		task.NextRunTime, task.LastRunTime, task.LastRunStatus, task.LastError,
		task.RunCount, task.ID, task.Priority, task.MaxRetries, task.RetryCount, task.NodeID)
	return err
}

func (s *PostgresStore) UpdateTaskStatus(ctx context.Context, taskID, status string) error {
	query := `UPDATE tasks SET status=$1, updated_at=NOW() WHERE id=$2`
	_, err := s.pool.Exec(ctx, query, status, taskID)
	return err
}

func (s *PostgresStore) UpdateTaskNode(ctx context.Context, taskID, nodeID string) error {
	query := `UPDATE tasks SET node_id=$1, updated_at=NOW() WHERE id=$2`
	_, err := s.pool.Exec(ctx, query, nodeID, taskID)
	return err
}

func (s *PostgresStore) UpdateTaskNextRunTime(ctx context.Context, taskID string, nextRunTime time.Time) error {
	query := `UPDATE tasks SET next_run_time=$1, updated_at=NOW() WHERE id=$2`
	_, err := s.pool.Exec(ctx, query, nextRunTime, taskID)
	return err
}

func (s *PostgresStore) MarkTaskDeleted(ctx context.Context, taskID string) error {
	query := `UPDATE tasks SET is_deleted=true, status=$1, updated_at=NOW() WHERE id=$2`
	_, err := s.pool.Exec(ctx, query, models.TaskStatusDeleted, taskID)
	return err
}

func (s *PostgresStore) GetTask(ctx context.Context, taskID string) (*models.Task, error) {
	query := `
		SELECT id, name, cron_expr, task_type, payload, status, shard_key, shard_total,
			shard_index, node_id, next_run_time, last_run_time, last_run_status, last_error,
			run_count, priority, max_retries, retry_count, is_deleted, created_at, updated_at
		FROM tasks WHERE id=$1 AND is_deleted=false
	`
	task := &models.Task{}
	err := s.pool.QueryRow(ctx, query, taskID).Scan(
		&task.ID, &task.Name, &task.CronExpr, &task.TaskType, &task.Payload, &task.Status,
		&task.ShardKey, &task.ShardTotal, &task.ShardIndex, &task.NodeID, &task.NextRunTime,
		&task.LastRunTime, &task.LastRunStatus, &task.LastError, &task.RunCount,
		&task.Priority, &task.MaxRetries, &task.RetryCount, &task.IsDeleted, &task.CreatedAt, &task.UpdatedAt)
	if err != nil {
		return nil, err
	}
	return task, nil
}

func (s *PostgresStore) GetTasksToRun(ctx context.Context, now time.Time, limit int) ([]*models.Task, error) {
	query := `
		SELECT id, name, cron_expr, task_type, payload, status, shard_key, shard_total,
			shard_index, node_id, next_run_time, last_run_time, priority, max_retries, retry_count
		FROM tasks
		WHERE status IN ($1, $2) AND next_run_time <= $3 AND is_deleted=false
		ORDER BY priority DESC, next_run_time ASC
		LIMIT $4
	`
	rows, err := s.pool.Query(ctx, query, models.TaskStatusPending, models.TaskStatusRunning, now, limit)
	if err != nil {
		return nil, err
	}
	defer rows.Close()

	var tasks []*models.Task
	for rows.Next() {
		task := &models.Task{}
		err := rows.Scan(
			&task.ID, &task.Name, &task.CronExpr, &task.TaskType, &task.Payload, &task.Status,
			&task.ShardKey, &task.ShardTotal, &task.ShardIndex, &task.NodeID, &task.NextRunTime,
			&task.LastRunTime, &task.Priority, &task.MaxRetries, &task.RetryCount)
		if err != nil {
			return nil, err
		}
		tasks = append(tasks, task)
	}
	return tasks, nil
}

func (s *PostgresStore) GetMissedTasks(ctx context.Context, threshold time.Duration, limit int) ([]*models.Task, error) {
	cutoffTime := time.Now().Add(-threshold)
	query := `
		SELECT id, name, cron_expr, task_type, payload, status, shard_key, shard_total,
			shard_index, node_id, next_run_time, last_run_time, priority, max_retries, retry_count
		FROM tasks
		WHERE status IN ($1, $2) AND next_run_time <= $3 AND is_deleted=false
		ORDER BY next_run_time ASC
		LIMIT $4
	`
	rows, err := s.pool.Query(ctx, query, models.TaskStatusPending, models.TaskStatusRunning, cutoffTime, limit)
	if err != nil {
		return nil, err
	}
	defer rows.Close()

	var tasks []*models.Task
	for rows.Next() {
		task := &models.Task{}
		err := rows.Scan(
			&task.ID, &task.Name, &task.CronExpr, &task.TaskType, &task.Payload, &task.Status,
			&task.ShardKey, &task.ShardTotal, &task.ShardIndex, &task.NodeID, &task.NextRunTime,
			&task.LastRunTime, &task.Priority, &task.MaxRetries, &task.RetryCount)
		if err != nil {
			return nil, err
		}
		tasks = append(tasks, task)
	}
	return tasks, nil
}

func (s *PostgresStore) GetTasksByNode(ctx context.Context, nodeID string) ([]*models.Task, error) {
	query := `
		SELECT id, name, cron_expr, task_type, status, next_run_time, priority
		FROM tasks
		WHERE node_id=$1 AND is_deleted=false
		ORDER BY next_run_time ASC
	`
	rows, err := s.pool.Query(ctx, query, nodeID)
	if err != nil {
		return nil, err
	}
	defer rows.Close()

	var tasks []*models.Task
	for rows.Next() {
		task := &models.Task{}
		err := rows.Scan(
			&task.ID, &task.Name, &task.CronExpr, &task.TaskType, &task.Status,
			&task.NextRunTime, &task.Priority)
		if err != nil {
			return nil, err
		}
		tasks = append(tasks, task)
	}
	return tasks, nil
}

func (s *PostgresStore) ReassignTasksFromNode(ctx context.Context, nodeID string) error {
	query := `
		UPDATE tasks SET node_id=NULL, updated_at=NOW()
		WHERE node_id=$1 AND status=$2 AND is_deleted=false
	`
	_, err := s.pool.Exec(ctx, query, nodeID, models.TaskStatusPending)
	return err
}

func (s *PostgresStore) CountTasksByStatus(ctx context.Context, status string) (int64, error) {
	query := `SELECT COUNT(*) FROM tasks WHERE status=$1 AND is_deleted=false`
	var count int64
	err := s.pool.QueryRow(ctx, query, status).Scan(&count)
	return count, err
}

func (s *PostgresStore) CountTasksByNode(ctx context.Context) (map[string]int64, error) {
	query := `
		SELECT node_id, COUNT(*)
		FROM tasks
		WHERE node_id IS NOT NULL AND status=$1 AND is_deleted=false
		GROUP BY node_id
	`
	rows, err := s.pool.Query(ctx, query, models.TaskStatusPending)
	if err != nil {
		return nil, err
	}
	defer rows.Close()

	result := make(map[string]int64)
	for rows.Next() {
		var nodeID string
		var count int64
		if err := rows.Scan(&nodeID, &count); err != nil {
			return nil, err
		}
		result[nodeID] = count
	}
	return result, nil
}

func (s *PostgresStore) CreateExecution(ctx context.Context, exec *models.TaskExecution) error {
	query := `
		INSERT INTO task_executions (task_id, node_id, start_time, status, shard_index, created_at)
		VALUES ($1, $2, $3, $4, $5, NOW())
		RETURNING id
	`
	err := s.pool.QueryRow(ctx, query,
		exec.TaskID, exec.NodeID, exec.StartTime, exec.Status, exec.ShardIndex).Scan(&exec.ID)
	return err
}

func (s *PostgresStore) UpdateExecution(ctx context.Context, exec *models.TaskExecution) error {
	query := `
		UPDATE task_executions
		SET end_time=$1, status=$2, error=$3, duration_ms=$4
		WHERE id=$5
	`
	_, err := s.pool.Exec(ctx, query,
		exec.EndTime, exec.Status, exec.Error, exec.DurationMs, exec.ID)
	return err
}

func (s *PostgresStore) RegisterNode(ctx context.Context, node *models.Node) error {
	query := `
		INSERT INTO nodes (id, host, port, status, task_count, last_heartbeat, registered_at, updated_at)
		VALUES ($1, $2, $3, $4, $5, NOW(), NOW(), NOW())
		ON CONFLICT (id) DO UPDATE SET
			host=EXCLUDED.host, port=EXCLUDED.port, status=EXCLUDED.status,
			last_heartbeat=NOW(), updated_at=NOW()
	`
	_, err := s.pool.Exec(ctx, query,
		node.ID, node.Host, node.Port, node.Status, node.TaskCount)
	return err
}

func (s *PostgresStore) UpdateNodeHeartbeat(ctx context.Context, nodeID string) error {
	query := `
		UPDATE nodes SET last_heartbeat=NOW(), updated_at=NOW() WHERE id=$1
	`
	_, err := s.pool.Exec(ctx, query, nodeID)
	return err
}

func (s *PostgresStore) UpdateNodeTaskCount(ctx context.Context, nodeID string, taskCount int) error {
	query := `
		UPDATE nodes SET task_count=$1, updated_at=NOW() WHERE id=$2
	`
	_, err := s.pool.Exec(ctx, query, taskCount, nodeID)
	return err
}

func (s *PostgresStore) GetAllNodes(ctx context.Context) ([]*models.Node, error) {
	query := `
		SELECT id, host, port, status, task_count, last_heartbeat, registered_at, updated_at
		FROM nodes
		ORDER BY id
	`
	rows, err := s.pool.Query(ctx, query)
	if err != nil {
		return nil, err
	}
	defer rows.Close()

	var nodes []*models.Node
	for rows.Next() {
		node := &models.Node{}
		err := rows.Scan(
			&node.ID, &node.Host, &node.Port, &node.Status, &node.TaskCount,
			&node.LastHeartbeat, &node.RegisteredAt, &node.UpdatedAt)
		if err != nil {
			return nil, err
		}
		nodes = append(nodes, node)
	}
	return nodes, nil
}

func (s *PostgresStore) MarkNodesOffline(ctx context.Context, timeout time.Duration) error {
	cutoffTime := time.Now().Add(-timeout)
	query := `
		UPDATE nodes SET status=$1, updated_at=NOW()
		WHERE last_heartbeat < $2 AND status=$3
	`
	_, err := s.pool.Exec(ctx, query, models.NodeStatusOffline, cutoffTime, models.NodeStatusOnline)
	return err
}

func (s *PostgresStore) CheckTaskExecutionExists(ctx context.Context, taskID string, since time.Time) (bool, error) {
	query := `
		SELECT EXISTS(
			SELECT 1 FROM task_executions
			WHERE task_id=$1 AND start_time >= $2 AND status=$3
		)
	`
	var exists bool
	err := s.pool.QueryRow(ctx, query, taskID, since, models.ExecutionStatusSuccess).Scan(&exists)
	return exists, err
}

func (s *PostgresStore) GetLastTaskExecution(ctx context.Context, taskID string) (*models.TaskExecution, error) {
	query := `
		SELECT id, task_id, node_id, start_time, end_time, status, error, duration_ms, shard_index, created_at
		FROM task_executions
		WHERE task_id=$1
		ORDER BY start_time DESC
		LIMIT 1
	`
	exec := &models.TaskExecution{}
	err := s.pool.QueryRow(ctx, query, taskID).Scan(
		&exec.ID, &exec.TaskID, &exec.NodeID, &exec.StartTime, &exec.EndTime,
		&exec.Status, &exec.Error, &exec.DurationMs, &exec.ShardIndex, &exec.CreatedAt)
	if err != nil {
		return nil, err
	}
	return exec, nil
}

func (s *PostgresStore) GetTaskExecutionsInTimeRange(ctx context.Context, taskID string, startTime, endTime time.Time) ([]*models.TaskExecution, error) {
	query := `
		SELECT id, task_id, node_id, start_time, end_time, status, error, duration_ms, shard_index, created_at
		FROM task_executions
		WHERE task_id=$1 AND start_time >= $2 AND start_time <= $3
		ORDER BY start_time DESC
	`
	rows, err := s.pool.Query(ctx, query, taskID, startTime, endTime)
	if err != nil {
		return nil, err
	}
	defer rows.Close()

	var executions []*models.TaskExecution
	for rows.Next() {
		exec := &models.TaskExecution{}
		err := rows.Scan(
			&exec.ID, &exec.TaskID, &exec.NodeID, &exec.StartTime, &exec.EndTime,
			&exec.Status, &exec.Error, &exec.DurationMs, &exec.ShardIndex, &exec.CreatedAt)
		if err != nil {
			return nil, err
		}
		executions = append(executions, exec)
	}
	return executions, nil
}

func (s *PostgresStore) CreateDAG(ctx context.Context, dag *models.DAG) error {
	query := `
		INSERT INTO dags (id, name, description, status, cron_expr, task_ids, next_run_time, created_at, updated_at)
		VALUES ($1, $2, $3, $4, $5, $6, $7, NOW(), NOW())
	`
	_, err := s.pool.Exec(ctx, query,
		dag.ID, dag.Name, dag.Description, dag.Status, dag.CronExpr, dag.TaskIDs, dag.NextRunTime)
	return err
}

func (s *PostgresStore) GetDAG(ctx context.Context, dagID string) (*models.DAG, error) {
	query := `
		SELECT id, name, description, status, cron_expr, task_ids, next_run_time, last_run_time, is_deleted, created_at, updated_at
		FROM dags WHERE id=$1 AND is_deleted=false
	`
	dag := &models.DAG{}
	err := s.pool.QueryRow(ctx, query, dagID).Scan(
		&dag.ID, &dag.Name, &dag.Description, &dag.Status, &dag.CronExpr, &dag.TaskIDs,
		&dag.NextRunTime, &dag.LastRunTime, &dag.IsDeleted, &dag.CreatedAt, &dag.UpdatedAt)
	if err != nil {
		return nil, err
	}
	return dag, nil
}

func (s *PostgresStore) UpdateDAGStatus(ctx context.Context, dagID, status string) error {
	query := `UPDATE dags SET status=$1, updated_at=NOW() WHERE id=$2`
	_, err := s.pool.Exec(ctx, query, status, dagID)
	return err
}

func (s *PostgresStore) AddDependency(ctx context.Context, dep *models.DAGDependency) error {
	query := `
		INSERT INTO dag_dependencies (dag_id, task_id, depends_on_task_id, dependency_type)
		VALUES ($1, $2, $3, $4)
		ON CONFLICT (dag_id, task_id, depends_on_task_id) DO NOTHING
	`
	_, err := s.pool.Exec(ctx, query,
		dep.DagID, dep.TaskID, dep.DependsOnTaskID, dep.DependencyType)
	return err
}

func (s *PostgresStore) GetTaskDependencies(ctx context.Context, dagID, taskID string) ([]*models.DAGDependency, error) {
	query := `
		SELECT id, dag_id, task_id, depends_on_task_id, dependency_type
		FROM dag_dependencies
		WHERE dag_id=$1 AND task_id=$2
	`
	rows, err := s.pool.Query(ctx, query, dagID, taskID)
	if err != nil {
		return nil, err
	}
	defer rows.Close()

	var deps []*models.DAGDependency
	for rows.Next() {
		dep := &models.DAGDependency{}
		err := rows.Scan(&dep.ID, &dep.DagID, &dep.TaskID, &dep.DependsOnTaskID, &dep.DependencyType)
		if err != nil {
			return nil, err
		}
		deps = append(deps, dep)
	}
	return deps, nil
}

func (s *PostgresStore) GetDAGDependencies(ctx context.Context, dagID string) ([]*models.DAGDependency, error) {
	query := `
		SELECT id, dag_id, task_id, depends_on_task_id, dependency_type
		FROM dag_dependencies
		WHERE dag_id=$1
	`
	rows, err := s.pool.Query(ctx, query, dagID)
	if err != nil {
		return nil, err
	}
	defer rows.Close()

	var deps []*models.DAGDependency
	for rows.Next() {
		dep := &models.DAGDependency{}
		err := rows.Scan(&dep.ID, &dep.DagID, &dep.TaskID, &dep.DependsOnTaskID, &dep.DependencyType)
		if err != nil {
			return nil, err
		}
		deps = append(deps, dep)
	}
	return deps, nil
}

func (s *PostgresStore) CreateDAGExecution(ctx context.Context, exec *models.DAGExecution) error {
	query := `
		INSERT INTO dag_executions (dag_id, start_time, status, triggered_by, completed_tasks, failed_tasks, created_at)
		VALUES ($1, $2, $3, $4, $5, $6, NOW())
		RETURNING id
	`
	err := s.pool.QueryRow(ctx, query,
		exec.DagID, exec.StartTime, exec.Status, exec.TriggeredBy, exec.CompletedTasks, exec.FailedTasks).Scan(&exec.ID)
	return err
}

func (s *PostgresStore) UpdateDAGExecution(ctx context.Context, exec *models.DAGExecution) error {
	query := `
		UPDATE dag_executions
		SET end_time=$1, status=$2, completed_tasks=$3, failed_tasks=$4
		WHERE id=$5
	`
	_, err := s.pool.Exec(ctx, query,
		exec.EndTime, exec.Status, exec.CompletedTasks, exec.FailedTasks, exec.ID)
	return err
}

func (s *PostgresStore) GetResourcePool(ctx context.Context, name string) (*models.ResourcePool, error) {
	query := `
		SELECT name, worker_count, max_worker_count, cpu_quota, memory_quota_mb, description
		FROM resource_pools WHERE name=$1
	`
	pool := &models.ResourcePool{}
	err := s.pool.QueryRow(ctx, query, name).Scan(
		&pool.Name, &pool.WorkerCount, &pool.MaxWorkerCount, &pool.CPUQuota, &pool.MemoryQuotaMB, &pool.Description)
	if err != nil {
		return nil, err
	}
	return pool, nil
}

func (s *PostgresStore) GetAllResourcePools(ctx context.Context) ([]*models.ResourcePool, error) {
	query := `
		SELECT name, worker_count, max_worker_count, cpu_quota, memory_quota_mb, description
		FROM resource_pools ORDER BY name
	`
	rows, err := s.pool.Query(ctx, query)
	if err != nil {
		return nil, err
	}
	defer rows.Close()

	var pools []*models.ResourcePool
	for rows.Next() {
		pool := &models.ResourcePool{}
		err := rows.Scan(
			&pool.Name, &pool.WorkerCount, &pool.MaxWorkerCount, &pool.CPUQuota, &pool.MemoryQuotaMB, &pool.Description)
		if err != nil {
			return nil, err
		}
		pools = append(pools, pool)
	}
	return pools, nil
}

func (s *PostgresStore) CreateResourcePool(ctx context.Context, pool *models.ResourcePool) error {
	query := `
		INSERT INTO resource_pools (name, worker_count, max_worker_count, cpu_quota, memory_quota_mb, description)
		VALUES ($1, $2, $3, $4, $5, $6)
		ON CONFLICT (name) DO UPDATE SET
			worker_count=EXCLUDED.worker_count,
			max_worker_count=EXCLUDED.max_worker_count,
			cpu_quota=EXCLUDED.cpu_quota,
			memory_quota_mb=EXCLUDED.memory_quota_mb,
			description=EXCLUDED.description,
			updated_at=NOW()
	`
	_, err := s.pool.Exec(ctx, query,
		pool.Name, pool.WorkerCount, pool.MaxWorkerCount, pool.CPUQuota, pool.MemoryQuotaMB, pool.Description)
	return err
}

func (s *PostgresStore) GetTasksByResourcePool(ctx context.Context, poolName string) ([]*models.Task, error) {
	query := `
		SELECT id, name, cron_expr, task_type, status, next_run_time, priority
		FROM tasks
		WHERE resource_pool=$1 AND status IN ($2, $3) AND is_deleted=false
		ORDER BY next_run_time ASC
	`
	rows, err := s.pool.Query(ctx, query, poolName, models.TaskStatusPending, models.TaskStatusRunning)
	if err != nil {
		return nil, err
	}
	defer rows.Close()

	var tasks []*models.Task
	for rows.Next() {
		task := &models.Task{}
		err := rows.Scan(&task.ID, &task.Name, &task.CronExpr, &task.TaskType, &task.Status, &task.NextRunTime, &task.Priority)
		if err != nil {
			return nil, err
		}
		tasks = append(tasks, task)
	}
	return tasks, nil
}

func (s *PostgresStore) RecordLoadMetrics(ctx context.Context, nodeID string, totalTasks, runningTasks, queuedTasks int, avgDurationMs int64, cpuUsage, memUsage float64) error {
	query := `
		INSERT INTO load_metrics (node_id, timestamp, total_tasks, running_tasks, queued_tasks, avg_duration_ms, cpu_usage_pct, memory_usage_pct)
		VALUES ($1, NOW(), $2, $3, $4, $5, $6, $7)
	`
	_, err := s.pool.Exec(ctx, query, nodeID, totalTasks, runningTasks, queuedTasks, avgDurationMs, cpuUsage, memUsage)
	return err
}

func (s *PostgresStore) GetHistoricalLoadData(ctx context.Context, nodeID string, hours int) ([]map[string]interface{}, error) {
	query := `
		SELECT timestamp, total_tasks, running_tasks, queued_tasks, avg_duration_ms
		FROM load_metrics
		WHERE ($1 = '' OR node_id=$1) AND timestamp >= NOW() - INTERVAL '1 hour' * $2
		ORDER BY timestamp ASC
	`
	rows, err := s.pool.Query(ctx, query, nodeID, hours)
	if err != nil {
		return nil, err
	}
	defer rows.Close()

	var data []map[string]interface{}
	for rows.Next() {
		var timestamp time.Time
		var totalTasks, runningTasks, queuedTasks int
		var avgDurationMs int64
		err := rows.Scan(&timestamp, &totalTasks, &runningTasks, &queuedTasks, &avgDurationMs)
		if err != nil {
			return nil, err
		}
		data = append(data, map[string]interface{}{
			"timestamp":      timestamp,
			"total_tasks":    totalTasks,
			"running_tasks":  runningTasks,
			"queued_tasks":   queuedTasks,
			"avg_duration_ms": avgDurationMs,
		})
	}
	return data, nil
}

func (s *PostgresStore) GetDAGsToRun(ctx context.Context, now time.Time, limit int) ([]*models.DAG, error) {
	query := `
		SELECT id, name, description, status, cron_expr, task_ids, next_run_time, last_run_time
		FROM dags
		WHERE status IN ($1, $2) AND next_run_time <= $3 AND is_deleted=false AND cron_expr != ''
		ORDER BY next_run_time ASC
		LIMIT $4
	`
	rows, err := s.pool.Query(ctx, query, models.DagStatusPending, models.DagStatusRunning, now, limit)
	if err != nil {
		return nil, err
	}
	defer rows.Close()

	var dags []*models.DAG
	for rows.Next() {
		dag := &models.DAG{}
		err := rows.Scan(
			&dag.ID, &dag.Name, &dag.Description, &dag.Status, &dag.CronExpr, &dag.TaskIDs,
			&dag.NextRunTime, &dag.LastRunTime)
		if err != nil {
			return nil, err
		}
		dags = append(dags, dag)
	}
	return dags, nil
}

func (s *PostgresStore) UpdateDAGNextRunTime(ctx context.Context, dagID string, nextRunTime time.Time) error {
	query := `UPDATE dags SET next_run_time=$1, updated_at=NOW() WHERE id=$2`
	_, err := s.pool.Exec(ctx, query, nextRunTime, dagID)
	return err
}
