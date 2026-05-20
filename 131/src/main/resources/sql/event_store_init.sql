-- Event Sourcing 事件存储表
CREATE TABLE IF NOT EXISTS event_store (
    id BIGINT AUTO_INCREMENT PRIMARY KEY COMMENT '主键ID',
    event_id VARCHAR(64) NOT NULL COMMENT '事件ID',
    aggregate_id VARCHAR(64) NOT NULL COMMENT '聚合根ID',
    aggregate_type VARCHAR(64) NOT NULL COMMENT '聚合根类型',
    version BIGINT NOT NULL COMMENT '事件版本号',
    event_type VARCHAR(128) NOT NULL COMMENT '事件类型',
    event_data TEXT NOT NULL COMMENT '事件数据(JSON格式)',
    occurred_on DATETIME NOT NULL COMMENT '事件发生时间',
    create_time DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    UNIQUE KEY uk_aggregate_version (aggregate_id, version),
    KEY idx_aggregate_id (aggregate_id),
    KEY idx_event_type (event_type),
    KEY idx_occurred_on (occurred_on)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='事件存储表';

-- 账户流水快照表（用于优化聚合重建性能）
CREATE TABLE IF NOT EXISTS account_snapshot (
    id BIGINT AUTO_INCREMENT PRIMARY KEY COMMENT '主键ID',
    aggregate_id VARCHAR(64) NOT NULL COMMENT '聚合根ID',
    aggregate_type VARCHAR(64) NOT NULL COMMENT '聚合根类型',
    version BIGINT NOT NULL COMMENT '快照版本号',
    snapshot_data TEXT NOT NULL COMMENT '快照数据(JSON格式)',
    create_time DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    UNIQUE KEY uk_aggregate_version (aggregate_id, version),
    KEY idx_aggregate_id (aggregate_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='聚合根快照表';
