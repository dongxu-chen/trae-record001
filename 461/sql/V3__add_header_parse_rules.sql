-- Header解析规则表
CREATE TABLE IF NOT EXISTS header_parse_rule (
    id BIGINT PRIMARY KEY AUTO_INCREMENT COMMENT '规则ID',
    routing_rule_id BIGINT NOT NULL COMMENT '关联的路由规则ID',
    header_name VARCHAR(64) NOT NULL COMMENT 'Header名称',
    parse_strategy VARCHAR(32) NOT NULL DEFAULT 'DIRECT' COMMENT '解析策略:DIRECT,REGEX,PREFIX,DELIMITER,SEMVER',
    pattern VARCHAR(256) COMMENT '匹配模式(正则、前缀、分隔符等)',
    default_value VARCHAR(64) COMMENT '默认值',
    priority INT DEFAULT 100 COMMENT '优先级，数字越小优先级越高',
    enabled TINYINT NOT NULL DEFAULT 1 COMMENT '是否启用',
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    deleted TINYINT DEFAULT 0 COMMENT '是否删除',
    INDEX idx_routing_rule_id (routing_rule_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='Header解析规则配置表';

-- 插入示例Header解析规则
INSERT INTO header_parse_rule (routing_rule_id, header_name, parse_strategy, pattern, default_value, priority) VALUES
(1, 'X-API-Version', 'DIRECT', NULL, 'v1', 1),
(1, 'Accept', 'REGEX', 'version=([^;]+)', 'v1', 2),
(1, 'User-Agent', 'SEMVER', NULL, 'v1', 3),
(2, 'X-API-Version', 'DIRECT', NULL, 'v1', 1),
(2, 'X-Client-Version', 'PREFIX', 'v', 'v1', 2);
