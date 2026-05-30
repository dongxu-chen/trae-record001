-- API版本表
CREATE TABLE api_version (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    name VARCHAR(128) NOT NULL COMMENT 'API名称',
    version VARCHAR(32) NOT NULL COMMENT '版本号如v1,v2',
    status VARCHAR(16) NOT NULL DEFAULT 'DRAFT' COMMENT '状态:DRAFT/ACTIVE/DEPRECATED/RETIRED',
    description VARCHAR(512) COMMENT '描述',
    base_path VARCHAR(128) NOT NULL COMMENT '基础路径如/api/v1',
    openapi_spec LONGTEXT COMMENT 'OpenAPI规范JSON',
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    deprecated_at DATETIME COMMENT '废弃时间',
    retire_at DATETIME COMMENT '计划下线时间',
    UNIQUE KEY uk_name_version (name, version)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- API端点表
CREATE TABLE api_endpoint (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    version_id BIGINT NOT NULL COMMENT '版本ID',
    method VARCHAR(8) NOT NULL COMMENT 'HTTP方法',
    path VARCHAR(256) NOT NULL COMMENT '接口路径',
    summary VARCHAR(256) COMMENT '接口说明',
    request_schema LONGTEXT COMMENT '请求Schema',
    response_schema LONGTEXT COMMENT '响应Schema',
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_version_id (version_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 路由规则表
CREATE TABLE routing_rule (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    api_name VARCHAR(128) NOT NULL COMMENT 'API名称',
    strategy VARCHAR(16) NOT NULL DEFAULT 'PATH' COMMENT '路由策略:PATH/HEADER/QUERY/WEIGHTED',
    match_expression VARCHAR(256) COMMENT '匹配表达式',
    weight_v1 INT DEFAULT 0 COMMENT 'v1权重',
    weight_v2 INT DEFAULT 100 COMMENT 'v2权重',
    enabled TINYINT NOT NULL DEFAULT 1 COMMENT '是否启用',
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY uk_api_name (api_name)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 灰度策略表
CREATE TABLE gray_policy (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    rule_id BIGINT NOT NULL COMMENT '路由规则ID',
    type VARCHAR(16) NOT NULL COMMENT '灰度类型:USER_ID/IP/WEIGHT/CUSTOM',
    include_list TEXT COMMENT '包含列表JSON',
    exclude_list TEXT COMMENT '排除列表JSON',
    weight_percent INT DEFAULT 0 COMMENT '流量百分比',
    custom_rule TEXT COMMENT '自定义规则',
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_rule_id (rule_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 差异对比结果表
CREATE TABLE diff_result (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    base_version_id BIGINT NOT NULL COMMENT '基准版本ID',
    target_version_id BIGINT NOT NULL COMMENT '目标版本ID',
    diff_content LONGTEXT COMMENT '差异内容JSON',
    breaking_changes INT DEFAULT 0 COMMENT '破坏性变更数',
    warning_changes INT DEFAULT 0 COMMENT '警告变更数',
    is_compatible TINYINT NOT NULL DEFAULT 1 COMMENT '是否兼容',
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_versions (base_version_id, target_version_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
