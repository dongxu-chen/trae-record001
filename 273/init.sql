CREATE TABLE IF NOT EXISTS tasks (
    id VARCHAR(64) PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    cron_expr VARCHAR(128) NOT NULL,
    task_type VARCHAR(64) NOT NULL,
    payload JSONB,
    status VARCHAR(32) NOT NULL DEFAULT 'pending',
    shard_key VARCHAR(128),
    shard_total INT DEFAULT 1,
    shard_index INT DEFAULT 0,
    node_id VARCHAR(128),
    resource_pool VARCHAR(64) DEFAULT 'default',
    dag_id VARCHAR(64),
    next_run_time TIMESTAMPTZ,
    last_run_time TIMESTAMPTZ,
    last_run_status VARCHAR(32),
    last_error TEXT,
    run_count INT DEFAULT 0,
    priority INT DEFAULT 0,
    max_retries INT DEFAULT 3,
    retry_count INT DEFAULT 0,
    avg_duration_ms BIGINT DEFAULT 0,
    is_deleted BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_tasks_status ON tasks(status);
CREATE INDEX IF NOT EXISTS idx_tasks_next_run_time ON tasks(next_run_time);
CREATE INDEX IF NOT EXISTS idx_tasks_node_id ON tasks(node_id);
CREATE INDEX IF NOT EXISTS idx_tasks_shard_key ON tasks(shard_key);
CREATE INDEX IF NOT EXISTS idx_tasks_status_next_run ON tasks(status, next_run_time);
CREATE INDEX IF NOT EXISTS idx_tasks_resource_pool ON tasks(resource_pool);
CREATE INDEX IF NOT EXISTS idx_tasks_dag_id ON tasks(dag_id);

CREATE TABLE IF NOT EXISTS task_executions (
    id BIGSERIAL PRIMARY KEY,
    task_id VARCHAR(64) NOT NULL,
    node_id VARCHAR(128) NOT NULL,
    start_time TIMESTAMPTZ NOT NULL,
    end_time TIMESTAMPTZ,
    status VARCHAR(32) NOT NULL,
    error TEXT,
    duration_ms BIGINT,
    shard_index INT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_executions_task_id ON task_executions(task_id);
CREATE INDEX IF NOT EXISTS idx_executions_node_id ON task_executions(node_id);
CREATE INDEX IF NOT EXISTS idx_executions_created_at ON task_executions(created_at);
CREATE INDEX IF NOT EXISTS idx_executions_start_time ON task_executions(start_time);

CREATE TABLE IF NOT EXISTS nodes (
    id VARCHAR(128) PRIMARY KEY,
    host VARCHAR(255) NOT NULL,
    port INT NOT NULL,
    status VARCHAR(32) NOT NULL,
    task_count INT DEFAULT 0,
    last_heartbeat TIMESTAMPTZ DEFAULT NOW(),
    registered_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS dags (
    id VARCHAR(64) PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    status VARCHAR(32) NOT NULL DEFAULT 'pending',
    cron_expr VARCHAR(128),
    task_ids TEXT[],
    next_run_time TIMESTAMPTZ,
    last_run_time TIMESTAMPTZ,
    is_deleted BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_dags_status ON dags(status);
CREATE INDEX IF NOT EXISTS idx_dags_next_run_time ON dags(next_run_time);

CREATE TABLE IF NOT EXISTS dag_dependencies (
    id BIGSERIAL PRIMARY KEY,
    dag_id VARCHAR(64) NOT NULL,
    task_id VARCHAR(64) NOT NULL,
    depends_on_task_id VARCHAR(64) NOT NULL,
    dependency_type VARCHAR(32) DEFAULT 'success',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(dag_id, task_id, depends_on_task_id)
);

CREATE INDEX IF NOT EXISTS idx_dag_deps_dag_id ON dag_dependencies(dag_id);
CREATE INDEX IF NOT EXISTS idx_dag_deps_task_id ON dag_dependencies(task_id);

CREATE TABLE IF NOT EXISTS dag_executions (
    id BIGSERIAL PRIMARY KEY,
    dag_id VARCHAR(64) NOT NULL,
    start_time TIMESTAMPTZ NOT NULL,
    end_time TIMESTAMPTZ,
    status VARCHAR(32) NOT NULL,
    triggered_by VARCHAR(128),
    completed_tasks TEXT[],
    failed_tasks TEXT[],
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_dag_execs_dag_id ON dag_executions(dag_id);
CREATE INDEX IF NOT EXISTS idx_dag_execs_status ON dag_executions(status);
CREATE INDEX IF NOT EXISTS idx_dag_execs_created_at ON dag_executions(created_at);

CREATE TABLE IF NOT EXISTS resource_pools (
    name VARCHAR(64) PRIMARY KEY,
    worker_count INT DEFAULT 10,
    max_worker_count INT DEFAULT 100,
    cpu_quota INT DEFAULT 100,
    memory_quota_mb INT DEFAULT 4096,
    description TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

INSERT INTO resource_pools (name, worker_count, max_worker_count, cpu_quota, memory_quota_mb, description)
VALUES 
    ('default', 20, 100, 100, 4096, 'Default resource pool'),
    ('cpu', 10, 50, 200, 2048, 'CPU intensive tasks'),
    ('io', 30, 100, 50, 1024, 'IO intensive tasks'),
    ('memory', 5, 20, 100, 8192, 'Memory intensive tasks')
ON CONFLICT (name) DO NOTHING;

CREATE TABLE IF NOT EXISTS load_metrics (
    id BIGSERIAL PRIMARY KEY,
    node_id VARCHAR(128),
    timestamp TIMESTAMPTZ NOT NULL,
    total_tasks INT DEFAULT 0,
    running_tasks INT DEFAULT 0,
    queued_tasks INT DEFAULT 0,
    avg_duration_ms BIGINT DEFAULT 0,
    cpu_usage_pct FLOAT DEFAULT 0,
    memory_usage_pct FLOAT DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_load_metrics_timestamp ON load_metrics(timestamp);
CREATE INDEX IF NOT EXISTS idx_load_metrics_node_time ON load_metrics(node_id, timestamp);
