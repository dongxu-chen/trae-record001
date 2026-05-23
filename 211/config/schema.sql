CREATE DATABASE IF NOT EXISTS scheduler DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

USE scheduler;

CREATE TABLE IF NOT EXISTS tasks (
    id VARCHAR(36) PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    description VARCHAR(500),
    task_type VARCHAR(50) NOT NULL,
    payload TEXT,
    trigger_type VARCHAR(20) NOT NULL,
    cron_expr VARCHAR(100),
    interval_sec INT DEFAULT 0,
    status VARCHAR(20) DEFAULT 'pending',
    max_retries INT DEFAULT 3,
    retry_delay INT DEFAULT 5,
    timeout_sec INT DEFAULT 300,
    dependencies VARCHAR(500),
    next_run_at DATETIME,
    last_run_at DATETIME,
    created_at DATETIME NOT NULL,
    updated_at DATETIME NOT NULL,
    deleted_at DATETIME,
    INDEX idx_status_next_run (status, next_run_at),
    INDEX idx_dependencies (dependencies)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS task_executions (
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
    INDEX idx_created_at (created_at DESC),
    FOREIGN KEY (task_id) REFERENCES tasks(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
