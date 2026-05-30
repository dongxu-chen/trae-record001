-- 版本扩展字段
ALTER TABLE api_version
ADD COLUMN planned_retire_time DATETIME COMMENT '计划下线时间' AFTER offline_time,
ADD COLUMN deprecation_message VARCHAR(512) COMMENT '废弃提示信息' AFTER planned_retire_time,
ADD COLUMN is_mock TINYINT DEFAULT 0 COMMENT '是否为Mock版本' AFTER deprecation_message;

-- 版本调用统计表
CREATE TABLE version_call_stats (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    service_name VARCHAR(128) NOT NULL COMMENT '服务名称',
    version VARCHAR(32) NOT NULL COMMENT '版本号',
    call_count BIGINT DEFAULT 0 COMMENT '调用次数',
    success_count BIGINT DEFAULT 0 COMMENT '成功次数',
    fail_count BIGINT DEFAULT 0 COMMENT '失败次数',
    avg_response_time INT DEFAULT 0 COMMENT '平均响应时间(ms)',
    stat_date DATE NOT NULL COMMENT '统计日期',
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY uk_service_version_date (service_name, version, stat_date),
    INDEX idx_stat_date (stat_date),
    INDEX idx_service_name (service_name)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='版本调用统计表';

-- Mock版本配置表
CREATE TABLE mock_version_config (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    version_id BIGINT NOT NULL COMMENT '版本ID',
    path VARCHAR(256) NOT NULL COMMENT '接口路径',
    method VARCHAR(16) NOT NULL COMMENT 'HTTP方法',
    mock_type VARCHAR(32) NOT NULL DEFAULT 'SUCCESS' COMMENT 'Mock类型:SUCCESS/DELAY/ERROR/CUSTOM',
    delay_ms INT DEFAULT 0 COMMENT '模拟延迟(ms)',
    error_code INT DEFAULT 200 COMMENT '模拟错误码',
    error_message VARCHAR(512) COMMENT '模拟错误信息',
    custom_response LONGTEXT COMMENT '自定义响应JSON',
    enabled TINYINT DEFAULT 1 COMMENT '是否启用',
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_version_id (version_id),
    INDEX idx_path (path)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='Mock版本配置表';

-- 废弃时间表示例数据
UPDATE api_version
SET planned_retire_time = DATE_ADD(NOW(), INTERVAL 30 DAY),
    deprecation_message = '该版本将于30天后下线，请尽快升级到v2.0.0版本'
WHERE status = 'DEPRECATED';

-- Mock版本示例数据
INSERT INTO api_version (service_name, version, description, status, is_default, publish_time, is_mock, created_at, updated_at)
VALUES
('用户服务', 'v1.0.0-mock', 'Mock版本-模拟旧版本用户服务', 'PUBLISHED', 0, NOW(), 1, NOW(), NOW()),
('订单服务', 'v1.0.0-mock', 'Mock版本-模拟旧版本订单服务', 'PUBLISHED', 0, NOW(), 1, NOW(), NOW());

-- Mock配置示例数据
INSERT INTO mock_version_config (version_id, path, method, mock_type, delay_ms, error_code, error_message, custom_response, enabled)
VALUES
(6, '/api/v1/users/{id}', 'GET', 'SUCCESS', 0, 200, NULL, '{"id":1,"name":"Mock User","email":"mock@example.com","createdAt":"2024-01-01T00:00:00"}', 1),
(6, '/api/v1/users', 'POST', 'DELAY', 2000, 200, NULL, '{"id":2,"name":"New User"}', 1),
(6, '/api/v1/users/{id}', 'PUT', 'ERROR', 0, 500, '服务器内部错误-Mock模拟', NULL, 1),
(7, '/api/v1/orders/{id}', 'GET', 'CUSTOM', 500, 200, NULL, '{"id":1,"orderNo":"ORD-MOCK-001","status":"PENDING","totalAmount":99.99}', 1);
