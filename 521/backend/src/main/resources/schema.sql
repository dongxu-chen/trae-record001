CREATE DATABASE IF NOT EXISTS taskflow DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

USE taskflow;

CREATE TABLE tf_workflow (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(128) NOT NULL,
    description VARCHAR(512),
    dag_json TEXT NOT NULL,
    status VARCHAR(32) NOT NULL DEFAULT 'DRAFT',
    version INT NOT NULL DEFAULT 1,
    created_by VARCHAR(64),
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_workflow_status (status),
    INDEX idx_workflow_name (name)
) ENGINE=InnoDB;

CREATE TABLE tf_task (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    workflow_id BIGINT NOT NULL,
    task_key VARCHAR(128) NOT NULL,
    task_name VARCHAR(128) NOT NULL,
    task_type VARCHAR(64) NOT NULL,
    task_config JSON,
    task_priority INT NOT NULL DEFAULT 5,
    retry_count INT NOT NULL DEFAULT 0,
    retry_interval INT NOT NULL DEFAULT 30,
    retry_strategy VARCHAR(32) DEFAULT 'FIXED',
    timeout_seconds INT NOT NULL DEFAULT 3600,
    upstream_keys JSON,
    data_products JSON,
    position_x DOUBLE DEFAULT 0,
    position_y DOUBLE DEFAULT 0,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE INDEX uk_workflow_task_key (workflow_id, task_key),
    INDEX idx_task_workflow (workflow_id),
    INDEX idx_task_priority (task_priority)
) ENGINE=InnoDB;

CREATE TABLE tf_workflow_execution (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    workflow_id BIGINT NOT NULL,
    execution_id VARCHAR(64) NOT NULL,
    status VARCHAR(32) NOT NULL DEFAULT 'PENDING',
    trigger_type VARCHAR(32) NOT NULL DEFAULT 'MANUAL',
    trigger_id BIGINT,
    started_at DATETIME,
    finished_at DATETIME,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE INDEX uk_execution_id (execution_id),
    INDEX idx_wf_exec_workflow (workflow_id),
    INDEX idx_wf_exec_status (status)
) ENGINE=InnoDB;

CREATE TABLE tf_task_execution (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    workflow_execution_id BIGINT NOT NULL,
    task_id BIGINT NOT NULL,
    task_key VARCHAR(128) NOT NULL,
    status VARCHAR(32) NOT NULL DEFAULT 'PENDING',
    attempt INT NOT NULL DEFAULT 1,
    worker_node VARCHAR(128),
    started_at DATETIME,
    finished_at DATETIME,
    duration_ms BIGINT,
    log_text TEXT,
    error_message TEXT,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_task_exec_wf_exec (workflow_execution_id),
    INDEX idx_task_exec_task (task_id),
    INDEX idx_task_exec_status (status)
) ENGINE=InnoDB;

CREATE TABLE tf_trigger (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    workflow_id BIGINT NOT NULL,
    trigger_type VARCHAR(32) NOT NULL,
    cron_expression VARCHAR(128),
    event_topic VARCHAR(256),
    event_filter JSON,
    webhook_path VARCHAR(128),
    webhook_secret VARCHAR(256),
    enabled TINYINT NOT NULL DEFAULT 1,
    last_trigger_time DATETIME,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_trigger_workflow (workflow_id),
    INDEX idx_trigger_type (trigger_type),
    INDEX idx_trigger_enabled (enabled),
    UNIQUE INDEX uk_webhook_path (webhook_path)
) ENGINE=InnoDB;

CREATE TABLE tf_task_lineage (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    data_product VARCHAR(256) NOT NULL,
    source_workflow_id BIGINT,
    source_task_key VARCHAR(128),
    target_workflow_id BIGINT NOT NULL,
    target_task_key VARCHAR(128),
    lineage_type VARCHAR(32) NOT NULL DEFAULT 'DATA',
    enabled TINYINT NOT NULL DEFAULT 1,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_lineage_data_product (data_product),
    INDEX idx_lineage_source (source_workflow_id, source_task_key),
    INDEX idx_lineage_target (target_workflow_id)
) ENGINE=InnoDB;
