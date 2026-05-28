CREATE DATABASE IF NOT EXISTS `rate_limit_center` DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

USE `rate_limit_center`;

DROP TABLE IF EXISTS `flow_rule`;
CREATE TABLE `flow_rule` (
    `id` BIGINT NOT NULL AUTO_INCREMENT,
    `service_name` VARCHAR(128) NOT NULL DEFAULT '' COMMENT '服务名称',
    `resource` VARCHAR(256) NOT NULL DEFAULT '' COMMENT '资源名称',
    `grade` TINYINT NOT NULL DEFAULT 1 COMMENT '限流阈值类型: 0-线程数, 1-QPS',
    `count` DOUBLE NOT NULL DEFAULT 0 COMMENT '限流阈值',
    `strategy` TINYINT NOT NULL DEFAULT 0 COMMENT '流量控制策略: 0-直接, 1-关联, 2-链路',
    `ref_resource` VARCHAR(256) DEFAULT NULL COMMENT '关联的资源名',
    `control_behavior` TINYINT NOT NULL DEFAULT 0 COMMENT '流量控制效果: 0-快速失败, 1-预热, 2-排队等待, 3-预热+排队等待',
    `warm_up_period_sec` INT NOT NULL DEFAULT 10 COMMENT '预热时长(秒)',
    `max_queueing_time_ms` INT NOT NULL DEFAULT 500 COMMENT '排队等待时长(毫秒)',
    `cluster_mode` TINYINT(1) NOT NULL DEFAULT 0 COMMENT '是否集群模式',
    `cluster_fallback` TINYINT(1) NOT NULL DEFAULT 1 COMMENT '集群失败是否降级到本地',
    `cluster_threshold_type` TINYINT NOT NULL DEFAULT 0 COMMENT '集群阈值类型: 0-单机均摊, 1-全局阈值',
    `cluster_threshold_config` INT DEFAULT NULL COMMENT '集群阈值配置',
    `param_flow_item` INT DEFAULT NULL COMMENT '热点参数项',
    `param_hot_items` TEXT DEFAULT NULL COMMENT '热点参数配置(JSON)',
    `limit_app` VARCHAR(128) NOT NULL DEFAULT 'default' COMMENT '调用来源',
    `status` TINYINT NOT NULL DEFAULT 1 COMMENT '状态: 0-禁用, 1-启用',
    `create_time` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    `update_time` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    `remark` VARCHAR(512) DEFAULT NULL COMMENT '备注',
    PRIMARY KEY (`id`),
    KEY `idx_service_name` (`service_name`),
    KEY `idx_resource` (`resource`),
    KEY `idx_status` (`status`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='限流规则表';

DROP TABLE IF EXISTS `degrade_rule`;
CREATE TABLE `degrade_rule` (
    `id` BIGINT NOT NULL AUTO_INCREMENT,
    `service_name` VARCHAR(128) NOT NULL DEFAULT '' COMMENT '服务名称',
    `resource` VARCHAR(256) NOT NULL DEFAULT '' COMMENT '资源名称',
    `grade` TINYINT NOT NULL DEFAULT 1 COMMENT '熔断策略: 0-慢调用比例, 1-异常比例, 2-异常数',
    `count` DOUBLE NOT NULL DEFAULT 0 COMMENT '阈值',
    `time_window` INT NOT NULL DEFAULT 10 COMMENT '熔断时长(秒)',
    `min_request_amount` INT NOT NULL DEFAULT 5 COMMENT '最小请求数',
    `slow_ratio_threshold` INT DEFAULT NULL COMMENT '慢调用比例阈值',
    `stat_interval_ms` INT NOT NULL DEFAULT 1000 COMMENT '统计时长(毫秒)',
    `limit_app` VARCHAR(128) NOT NULL DEFAULT 'default' COMMENT '调用来源',
    `status` TINYINT NOT NULL DEFAULT 1 COMMENT '状态: 0-禁用, 1-启用',
    `create_time` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    `update_time` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    `remark` VARCHAR(512) DEFAULT NULL COMMENT '备注',
    PRIMARY KEY (`id`),
    KEY `idx_service_name` (`service_name`),
    KEY `idx_resource` (`resource`),
    KEY `idx_status` (`status`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='降级熔断规则表';

DROP TABLE IF EXISTS `param_flow_rule`;
CREATE TABLE `param_flow_rule` (
    `id` BIGINT NOT NULL AUTO_INCREMENT,
    `service_name` VARCHAR(128) NOT NULL DEFAULT '' COMMENT '服务名称',
    `resource` VARCHAR(256) NOT NULL DEFAULT '' COMMENT '资源名称',
    `grade` TINYINT NOT NULL DEFAULT 1 COMMENT '限流阈值类型',
    `param_idx` INT NOT NULL DEFAULT 0 COMMENT '参数索引',
    `count` DOUBLE NOT NULL DEFAULT 0 COMMENT '限流阈值',
    `param_flow_item` INT DEFAULT NULL COMMENT '参数流控项',
    `param_hot_items` TEXT DEFAULT NULL COMMENT '热点参数配置(JSON)',
    `burst_count` INT DEFAULT NULL COMMENT '突发流量次数',
    `duration_in_sec` BIGINT DEFAULT NULL COMMENT '流控效果持续时间(秒)',
    `status` TINYINT NOT NULL DEFAULT 1 COMMENT '状态: 0-禁用, 1-启用',
    `create_time` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    `update_time` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    `remark` VARCHAR(512) DEFAULT NULL COMMENT '备注',
    PRIMARY KEY (`id`),
    KEY `idx_service_name` (`service_name`),
    KEY `idx_resource` (`resource`),
    KEY `idx_status` (`status`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='热点参数限流规则表';

DROP TABLE IF EXISTS `system_rule`;
CREATE TABLE `system_rule` (
    `id` BIGINT NOT NULL AUTO_INCREMENT,
    `service_name` VARCHAR(128) NOT NULL DEFAULT '' COMMENT '服务名称',
    `grade` TINYINT NOT NULL DEFAULT 0 COMMENT '系统保护阈值类型: 0-LOAD, 1-CPU使用率, 2-平均RT, 3-QPS, 4-线程数',
    `count` DOUBLE NOT NULL DEFAULT 0 COMMENT '阈值',
    `status` TINYINT NOT NULL DEFAULT 1 COMMENT '状态: 0-禁用, 1-启用',
    `create_time` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    `update_time` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    `remark` VARCHAR(512) DEFAULT NULL COMMENT '备注',
    PRIMARY KEY (`id`),
    KEY `idx_service_name` (`service_name`),
    KEY `idx_status` (`status`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='系统自适应限流规则表';

DROP TABLE IF EXISTS `authority_rule`;
CREATE TABLE `authority_rule` (
    `id` BIGINT NOT NULL AUTO_INCREMENT,
    `service_name` VARCHAR(128) NOT NULL DEFAULT '' COMMENT '服务名称',
    `resource` VARCHAR(256) NOT NULL DEFAULT '' COMMENT '资源名称',
    `limit_app` VARCHAR(128) NOT NULL DEFAULT 'default' COMMENT '调用来源',
    `strategy` TINYINT NOT NULL DEFAULT 0 COMMENT '鉴权策略: 0-白名单, 1-黑名单',
    `status` TINYINT NOT NULL DEFAULT 1 COMMENT '状态: 0-禁用, 1-启用',
    `create_time` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    `update_time` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    `remark` VARCHAR(512) DEFAULT NULL COMMENT '备注',
    PRIMARY KEY (`id`),
    KEY `idx_service_name` (`service_name`),
    KEY `idx_resource` (`resource`),
    KEY `idx_status` (`status`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='黑白名单规则表';

DROP TABLE IF EXISTS `rate_limit_log`;
CREATE TABLE `rate_limit_log` (
    `id` BIGINT NOT NULL AUTO_INCREMENT,
    `service_name` VARCHAR(128) NOT NULL DEFAULT '' COMMENT '服务名称',
    `resource` VARCHAR(512) NOT NULL DEFAULT '' COMMENT '资源名称',
    `origin` VARCHAR(128) DEFAULT NULL COMMENT '调用来源',
    `rule_type` VARCHAR(32) NOT NULL DEFAULT '' COMMENT '规则类型: flow, degrade, param_flow, system, authority',
    `pass_count` INT NOT NULL DEFAULT 0 COMMENT '通过数量',
    `block_count` INT NOT NULL DEFAULT 0 COMMENT '拦截数量',
    `rt` BIGINT DEFAULT NULL COMMENT '响应时间(毫秒)',
    `exception` VARCHAR(512) DEFAULT NULL COMMENT '异常信息',
    `client_ip` VARCHAR(64) DEFAULT NULL COMMENT '客户端IP',
    `request_path` VARCHAR(512) DEFAULT NULL COMMENT '请求路径',
    `request_method` VARCHAR(16) DEFAULT NULL COMMENT '请求方法',
    `request_params` TEXT DEFAULT NULL COMMENT '请求参数(JSON)',
    `occur_time` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '发生时间',
    `create_time` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    PRIMARY KEY (`id`),
    KEY `idx_service_name` (`service_name`),
    KEY `idx_resource` (`resource`),
    KEY `idx_rule_type` (`rule_type`),
    KEY `idx_occur_time` (`occur_time`),
    KEY `idx_client_ip` (`client_ip`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='限流拦截日志表';

INSERT INTO `flow_rule` (`service_name`, `resource`, `grade`, `count`, `strategy`, `control_behavior`, `warm_up_period_sec`, `max_queueing_time_ms`, `cluster_mode`, `status`, `remark`) VALUES
('rate-limit-center', 'GET:/api/flow-rules', 1, 100, 0, 0, 10, 500, 0, 1, '测试限流规则-查询流控规则列表'),
('rate-limit-center', 'POST:/api/flow-rules', 1, 50, 0, 0, 10, 500, 0, 1, '测试限流规则-创建流控规则');

INSERT INTO `degrade_rule` (`service_name`, `resource`, `grade`, `count`, `time_window`, `min_request_amount`, `stat_interval_ms`, `status`, `remark`) VALUES
('rate-limit-center', 'GET:/api/metrics/all', 1, 0.5, 30, 5, 1000, 1, '测试降级规则-指标查询异常比例50%时熔断30秒');
