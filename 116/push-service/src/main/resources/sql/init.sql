CREATE DATABASE IF NOT EXISTS push_center DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

USE push_center;

DROP TABLE IF EXISTS push_template;
CREATE TABLE push_template (
    id BIGINT AUTO_INCREMENT PRIMARY KEY COMMENT '主键ID',
    template_code VARCHAR(64) NOT NULL UNIQUE COMMENT '模板编码',
    template_name VARCHAR(128) NOT NULL COMMENT '模板名称',
    channel VARCHAR(32) NOT NULL COMMENT '推送通道: apns/fcm/websocket',
    title VARCHAR(256) COMMENT '消息标题',
    content TEXT NOT NULL COMMENT '消息内容模板',
    ext_params JSON COMMENT '扩展参数',
    status TINYINT DEFAULT 1 COMMENT '状态: 0-禁用, 1-启用',
    remark VARCHAR(512) COMMENT '备注',
    create_time DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    update_time DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    deleted TINYINT DEFAULT 0 COMMENT '删除标记: 0-未删除, 1-已删除',
    INDEX idx_template_code (template_code),
    INDEX idx_channel (channel)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='消息模板表';

DROP TABLE IF EXISTS push_task;
CREATE TABLE push_task (
    id BIGINT AUTO_INCREMENT PRIMARY KEY COMMENT '主键ID',
    task_no VARCHAR(64) NOT NULL UNIQUE COMMENT '任务编号',
    template_id BIGINT COMMENT '模板ID',
    channel VARCHAR(32) NOT NULL COMMENT '推送通道',
    title VARCHAR(256) COMMENT '消息标题',
    content TEXT NOT NULL COMMENT '消息内容',
    target_type VARCHAR(32) COMMENT '目标类型: single-单用户, batch-批量',
    targets TEXT COMMENT '目标用户列表(JSON)',
    ext_params JSON COMMENT '扩展参数',
    schedule_time DATETIME COMMENT '定时推送时间',
    status TINYINT DEFAULT 0 COMMENT '状态: 0-待推送, 1-推送成功, 2-推送失败',
    total_count INT DEFAULT 0 COMMENT '总推送数',
    success_count INT DEFAULT 0 COMMENT '成功数',
    fail_count INT DEFAULT 0 COMMENT '失败数',
    remark VARCHAR(512) COMMENT '备注',
    create_time DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    update_time DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    deleted TINYINT DEFAULT 0 COMMENT '删除标记',
    INDEX idx_task_no (task_no),
    INDEX idx_status (status),
    INDEX idx_create_time (create_time)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='推送任务表';

DROP TABLE IF EXISTS push_record;
CREATE TABLE push_record (
    id BIGINT AUTO_INCREMENT PRIMARY KEY COMMENT '主键ID',
    task_id BIGINT NOT NULL COMMENT '任务ID',
    task_no VARCHAR(64) NOT NULL COMMENT '任务编号',
    channel VARCHAR(32) NOT NULL COMMENT '推送通道',
    target VARCHAR(256) NOT NULL COMMENT '推送目标',
    title VARCHAR(256) COMMENT '消息标题',
    content TEXT COMMENT '消息内容',
    status TINYINT DEFAULT 0 COMMENT '状态: 0-待推送, 1-成功, 2-失败',
    error_msg TEXT COMMENT '错误信息',
    message_id VARCHAR(128) COMMENT '第三方消息ID',
    callback_time DATETIME COMMENT '回调时间',
    callback_result JSON COMMENT '回调结果',
    click_count INT DEFAULT 0 COMMENT '点击次数',
    ab_test_id BIGINT COMMENT 'A/B测试ID',
    ab_group VARCHAR(16) COMMENT 'A/B测试分组: A/B',
    create_time DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    update_time DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    deleted TINYINT DEFAULT 0 COMMENT '删除标记',
    INDEX idx_task_id (task_id),
    INDEX idx_target (target),
    INDEX idx_status (status),
    INDEX idx_ab_test_id (ab_test_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='推送记录表';

DROP TABLE IF EXISTS user_tag;
CREATE TABLE user_tag (
    id BIGINT AUTO_INCREMENT PRIMARY KEY COMMENT '主键ID',
    user_id VARCHAR(64) NOT NULL COMMENT '用户ID',
    tag_code VARCHAR(64) NOT NULL COMMENT '标签编码',
    tag_name VARCHAR(128) COMMENT '标签名称',
    tag_value VARCHAR(256) COMMENT '标签值',
    create_time DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    update_time DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    deleted TINYINT DEFAULT 0 COMMENT '删除标记',
    UNIQUE KEY uk_user_tag (user_id, tag_code),
    INDEX idx_tag_code (tag_code)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='用户标签表';

DROP TABLE IF EXISTS tag_group;
CREATE TABLE tag_group (
    id BIGINT AUTO_INCREMENT PRIMARY KEY COMMENT '主键ID',
    group_code VARCHAR(64) NOT NULL UNIQUE COMMENT '分群编码',
    group_name VARCHAR(128) NOT NULL COMMENT '分群名称',
    tag_conditions JSON COMMENT '标签筛选条件',
    user_count INT DEFAULT 0 COMMENT '用户数量',
    status TINYINT DEFAULT 1 COMMENT '状态: 0-禁用, 1-启用',
    remark VARCHAR(512) COMMENT '备注',
    create_time DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    update_time DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    deleted TINYINT DEFAULT 0 COMMENT '删除标记'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='用户分群表';

DROP TABLE IF EXISTS ab_test;
CREATE TABLE ab_test (
    id BIGINT AUTO_INCREMENT PRIMARY KEY COMMENT '主键ID',
    test_code VARCHAR(64) NOT NULL UNIQUE COMMENT '测试编码',
    test_name VARCHAR(128) NOT NULL COMMENT '测试名称',
    channel VARCHAR(32) NOT NULL COMMENT '推送通道',
    template_a_id BIGINT NOT NULL COMMENT 'A组模板ID',
    template_b_id BIGINT NOT NULL COMMENT 'B组模板ID',
    split_ratio INT DEFAULT 50 COMMENT '流量分配比例(1-99)',
    total_targets BIGINT DEFAULT 0 COMMENT '总目标数',
    a_targets BIGINT DEFAULT 0 COMMENT 'A组目标数',
    b_targets BIGINT DEFAULT 0 COMMENT 'B组目标数',
    a_clicks INT DEFAULT 0 COMMENT 'A组点击数',
    b_clicks INT DEFAULT 0 COMMENT 'B组点击数',
    a_click_rate DECIMAL(5,4) DEFAULT 0 COMMENT 'A组点击率',
    b_click_rate DECIMAL(5,4) DEFAULT 0 COMMENT 'B组点击率',
    status TINYINT DEFAULT 0 COMMENT '状态: 0-草稿, 1-进行中, 2-已结束',
    start_time DATETIME COMMENT '开始时间',
    end_time DATETIME COMMENT '结束时间',
    remark VARCHAR(512) COMMENT '备注',
    create_time DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    update_time DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    deleted TINYINT DEFAULT 0 COMMENT '删除标记',
    INDEX idx_test_code (test_code)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='A/B测试表';

DROP TABLE IF EXISTS message_aggregate;
CREATE TABLE message_aggregate (
    id BIGINT AUTO_INCREMENT PRIMARY KEY COMMENT '主键ID',
    user_id VARCHAR(64) NOT NULL COMMENT '用户ID',
    channel VARCHAR(32) NOT NULL COMMENT '推送通道',
    aggregate_type VARCHAR(32) DEFAULT 'time' COMMENT '聚合类型: time-时间窗口, count-数量',
    window_seconds INT DEFAULT 300 COMMENT '聚合窗口秒数',
    message_count INT DEFAULT 0 COMMENT '已聚合消息数',
    messages JSON COMMENT '聚合的消息列表',
    first_receive_time DATETIME COMMENT '首次接收时间',
    last_receive_time DATETIME COMMENT '最后接收时间',
    status TINYINT DEFAULT 0 COMMENT '状态: 0-聚集中, 1-已发送',
    create_time DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    update_time DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    UNIQUE KEY uk_user_channel (user_id, channel),
    INDEX idx_status (status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='消息聚合表';
