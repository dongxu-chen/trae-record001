CREATE DATABASE IF NOT EXISTS alert_system DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE alert_system;

CREATE TABLE IF NOT EXISTS alert_event (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    alert_id VARCHAR(64) NOT NULL UNIQUE COMMENT '告警唯一标识',
    title VARCHAR(255) NOT NULL COMMENT '告警标题',
    content TEXT COMMENT '告警内容',
    severity VARCHAR(20) NOT NULL COMMENT '告警级别: CRITICAL, MAJOR, MINOR, WARNING, INFO',
    status VARCHAR(20) NOT NULL DEFAULT 'NEW' COMMENT '状态: NEW, ACKNOWLEDGED, PROCESSING, RESOLVED, CLOSED',
    source VARCHAR(100) COMMENT '告警来源',
    host VARCHAR(100) COMMENT '主机',
    service VARCHAR(100) COMMENT '服务',
    tags VARCHAR(500) COMMENT '标签，逗号分隔',
    aggregation_key VARCHAR(255) COMMENT '聚合键，用于相似告警合并',
    parent_alert_id VARCHAR(64) COMMENT '父告警ID，用于告警抑制',
    assignee VARCHAR(50) COMMENT '处理人',
    acknowledge_time DATETIME COMMENT '认领时间',
    resolve_time DATETIME COMMENT '解决时间',
    close_time DATETIME COMMENT '关闭时间',
    upgrade_count INT DEFAULT 0 COMMENT '升级次数',
    next_upgrade_time DATETIME COMMENT '下次升级时间',
    create_time DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    update_time DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_alert_id (alert_id),
    INDEX idx_status (status),
    INDEX idx_severity (severity),
    INDEX idx_create_time (create_time),
    INDEX idx_aggregation_key (aggregation_key),
    INDEX idx_parent_alert_id (parent_alert_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='告警事件表';

CREATE TABLE IF NOT EXISTS alert_aggregation (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    aggregation_key VARCHAR(255) NOT NULL UNIQUE COMMENT '聚合键',
    title VARCHAR(255) NOT NULL COMMENT '聚合告警标题',
    severity VARCHAR(20) NOT NULL COMMENT '最高告警级别',
    count INT NOT NULL DEFAULT 1 COMMENT '聚合数量',
    status VARCHAR(20) NOT NULL DEFAULT 'ACTIVE' COMMENT '状态: ACTIVE, RESOLVED',
    first_alert_time DATETIME NOT NULL COMMENT '首次告警时间',
    last_alert_time DATETIME NOT NULL COMMENT '最后告警时间',
    create_time DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    update_time DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_aggregation_key (aggregation_key),
    INDEX idx_status (status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='告警聚合表';

CREATE TABLE IF NOT EXISTS alert_rule (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    rule_name VARCHAR(100) NOT NULL UNIQUE COMMENT '规则名称',
    rule_type VARCHAR(50) NOT NULL COMMENT '规则类型: AGGREGATION, SUPPRESSION, ESCALATION',
    enabled TINYINT(1) DEFAULT 1 COMMENT '是否启用',
    rule_content TEXT NOT NULL COMMENT '规则内容（Drools规则）',
    description VARCHAR(500) COMMENT '规则描述',
    create_time DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    update_time DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='告警规则表';

CREATE TABLE IF NOT EXISTS alert_history (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    alert_id VARCHAR(64) NOT NULL COMMENT '告警ID',
    operation_type VARCHAR(50) NOT NULL COMMENT '操作类型: CREATE, ACKNOWLEDGE, PROCESS, RESOLVE, CLOSE, UPGRADE, AGGREGATE',
    operator VARCHAR(50) COMMENT '操作人',
    remark VARCHAR(500) COMMENT '备注',
    create_time DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_alert_id (alert_id),
    INDEX idx_create_time (create_time)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='告警历史记录表';

CREATE TABLE IF NOT EXISTS alert_suppression_rule (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    rule_name VARCHAR(100) NOT NULL UNIQUE COMMENT '规则名称',
    parent_condition VARCHAR(500) NOT NULL COMMENT '父告警条件（依赖告警）',
    child_condition VARCHAR(500) NOT NULL COMMENT '子告警条件（被抑制告警）',
    enabled TINYINT(1) DEFAULT 1 COMMENT '是否启用',
    description VARCHAR(500) COMMENT '规则描述',
    position_x INT DEFAULT 0 COMMENT '画布X坐标',
    position_y INT DEFAULT 0 COMMENT '画布Y坐标',
    create_time DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    update_time DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='告警抑制依赖规则表';

INSERT INTO alert_rule (rule_name, rule_type, enabled, rule_content, description) VALUES
('default_aggregation', 'AGGREGATION', 1, 'rule "DefaultAggregation" when $alert: AlertEvent(status == "NEW", aggregationKey != null) then alertService.aggregateAlert($alert); end', '默认告警聚合规则'),
('default_suppression', 'SUPPRESSION', 1, 'rule "DefaultSuppression" when $child: AlertEvent(status == "NEW", parentAlertId != null) $parent: AlertEvent(alertId == $child.parentAlertId, status in ("NEW", "ACKNOWLEDGED", "PROCESSING")) then alertService.suppressAlert($child); end', '默认告警抑制规则'),
('default_escalation', 'ESCALATION', 1, 'rule "DefaultEscalation" when $alert: AlertEvent(status in ("NEW", "ACKNOWLEDGED"), nextUpgradeTime != null) then alertService.checkAndEscalate($alert); end', '默认告警升级规则');

INSERT INTO alert_suppression_rule (rule_name, parent_condition, child_condition, enabled, description, position_x, position_y) VALUES
('网络故障告警抑制', 'service=network;severity=CRITICAL', 'service=app', 1, '核心网络故障时，抑制应用层告警', 100, 100),
('数据库故障告警抑制', 'service=mysql;severity=MAJOR', 'tag=database-dependent', 1, 'MySQL故障时，抑制依赖数据库的服务告警', 550, 100);

CREATE TABLE IF NOT EXISTS alert_root_cause (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    root_cause_id VARCHAR(64) NOT NULL UNIQUE COMMENT '根因ID',
    title VARCHAR(255) NOT NULL COMMENT '根因标题',
    description TEXT COMMENT '根因描述',
    root_alert_id VARCHAR(64) COMMENT '根源告警ID',
    confidence_score DOUBLE COMMENT '置信度',
    status VARCHAR(50) DEFAULT 'ANALYZING' COMMENT '状态: ANALYZING, CONFIRMED, REJECTED',
    analysis_time DATETIME COMMENT '分析时间',
    tags VARCHAR(500) COMMENT '标签',
    affected_count INT DEFAULT 0 COMMENT '影响告警数量',
    create_time DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_root_cause_id (root_cause_id),
    INDEX idx_status (status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='告警根因分析表';

CREATE TABLE IF NOT EXISTS alert_prediction (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    prediction_id VARCHAR(64) NOT NULL UNIQUE COMMENT '预测ID',
    title VARCHAR(255) NOT NULL COMMENT '预测标题',
    description TEXT COMMENT '预测描述',
    predicted_severity VARCHAR(20) COMMENT '预测告警级别',
    prediction_probability DOUBLE COMMENT '预测概率',
    predicted_time DATETIME COMMENT '预测发生时间',
    prediction_window_minutes INT COMMENT '预测时间窗口(分钟)',
    source_pattern VARCHAR(255) COMMENT '来源模式',
    host_pattern VARCHAR(255) COMMENT '主机模式',
    status VARCHAR(50) DEFAULT 'PREDICTED' COMMENT '状态: PREDICTED, CONFIRMED, DISMISSED',
    actual_alert_id VARCHAR(64) COMMENT '实际告警ID',
    create_time DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_prediction_id (prediction_id),
    INDEX idx_predicted_time (predicted_time),
    INDEX idx_status (status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='告警预测表';
