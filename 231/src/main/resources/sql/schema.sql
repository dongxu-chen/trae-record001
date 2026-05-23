CREATE DATABASE IF NOT EXISTS email_marketing DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

USE email_marketing;

CREATE TABLE IF NOT EXISTS email_template (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(200) NOT NULL COMMENT '模板名称',
    subject VARCHAR(500) NOT NULL COMMENT '邮件主题',
    content TEXT NOT NULL COMMENT '邮件内容(富文本)',
    status TINYINT DEFAULT 1 COMMENT '状态: 1启用 0禁用',
    deleted TINYINT DEFAULT 0,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_name (name),
    INDEX idx_status (status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='邮件模板表';

CREATE TABLE IF NOT EXISTS recipient_group (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(200) NOT NULL COMMENT '分组名称',
    description VARCHAR(500) COMMENT '描述',
    recipient_count INT DEFAULT 0 COMMENT '收件人数',
    deleted TINYINT DEFAULT 0,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_name (name)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='收件人分组表';

CREATE TABLE IF NOT EXISTS recipient (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    group_id BIGINT NOT NULL COMMENT '分组ID',
    email VARCHAR(200) NOT NULL COMMENT '邮箱地址',
    name VARCHAR(100) COMMENT '姓名',
    phone VARCHAR(20) COMMENT '手机号',
    status TINYINT DEFAULT 1 COMMENT '状态: 1有效 0无效',
    unsubscribed TINYINT DEFAULT 0 COMMENT '是否退订: 1是 0否',
    deleted TINYINT DEFAULT 0,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY uk_group_email (group_id, email),
    INDEX idx_group_id (group_id),
    INDEX idx_email (email),
    INDEX idx_status (status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='收件人表';

CREATE TABLE IF NOT EXISTS email_task (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(200) NOT NULL COMMENT '任务名称',
    template_id BIGINT NOT NULL COMMENT '模板ID',
    group_id BIGINT NOT NULL COMMENT '收件人分组ID',
    task_type TINYINT NOT NULL COMMENT '任务类型: 1立即发送 2定时发送',
    schedule_time DATETIME COMMENT '定时发送时间',
    status TINYINT DEFAULT 0 COMMENT '状态: 0待发送 1发送中 2已完成 3已取消 4失败',
    total_count INT DEFAULT 0 COMMENT '总收件人数',
    sent_count INT DEFAULT 0 COMMENT '已发送数',
    success_count INT DEFAULT 0 COMMENT '成功数',
    fail_count INT DEFAULT 0 COMMENT '失败数',
    unsubscribe_count INT DEFAULT 0 COMMENT '退订数',
    deleted TINYINT DEFAULT 0,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_status (status),
    INDEX idx_schedule_time (schedule_time),
    INDEX idx_template_id (template_id),
    INDEX idx_group_id (group_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='邮件发送任务表';

CREATE TABLE IF NOT EXISTS email_send_log (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    task_id BIGINT NOT NULL COMMENT '任务ID',
    recipient_id BIGINT NOT NULL COMMENT '收件人ID',
    email VARCHAR(200) NOT NULL COMMENT '邮箱地址',
    send_status TINYINT DEFAULT 0 COMMENT '发送状态: 0待发送 1发送成功 2发送失败',
    error_msg VARCHAR(500) COMMENT '错误信息',
    opened TINYINT DEFAULT 0 COMMENT '是否打开: 1是 0否',
    open_time DATETIME COMMENT '打开时间',
    clicked TINYINT DEFAULT 0 COMMENT '是否点击: 1是 0否',
    click_time DATETIME COMMENT '点击时间',
    unsubscribed TINYINT DEFAULT 0 COMMENT '是否退订: 1是 0否',
    unsubscribe_time DATETIME COMMENT '退订时间',
    sent_at DATETIME COMMENT '发送时间',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_task_id (task_id),
    INDEX idx_recipient_id (recipient_id),
    INDEX idx_email (email),
    INDEX idx_send_status (send_status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='邮件发送日志表';

CREATE TABLE IF NOT EXISTS domain_rate_limit (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    domain VARCHAR(100) NOT NULL COMMENT '域名',
    limit_per_minute INT NOT NULL DEFAULT 10 COMMENT '每分钟发送限制',
    status TINYINT DEFAULT 1 COMMENT '状态: 1启用 0禁用',
    deleted TINYINT DEFAULT 0,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY uk_domain (domain)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='域名限流配置表';

CREATE TABLE IF NOT EXISTS email_statistics (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    task_id BIGINT NOT NULL COMMENT '任务ID',
    total_sent INT DEFAULT 0 COMMENT '总发送数',
    total_opened INT DEFAULT 0 COMMENT '总打开数',
    total_clicked INT DEFAULT 0 COMMENT '总点击数',
    total_unsubscribed INT DEFAULT 0 COMMENT '总退订数',
    open_rate DECIMAL(5,2) DEFAULT 0 COMMENT '打开率',
    click_rate DECIMAL(5,2) DEFAULT 0 COMMENT '点击率',
    unsubscribe_rate DECIMAL(5,2) DEFAULT 0 COMMENT '退订率',
    statistics_date DATE NOT NULL COMMENT '统计日期',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY uk_task_date (task_id, statistics_date),
    INDEX idx_task_id (task_id),
    INDEX idx_statistics_date (statistics_date)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='邮件统计表';

INSERT INTO domain_rate_limit (domain, limit_per_minute, status, created_at, updated_at) VALUES
('gmail.com', 5, 1, NOW(), NOW()),
('outlook.com', 5, 1, NOW(), NOW()),
('hotmail.com', 5, 1, NOW(), NOW()),
('yahoo.com', 5, 1, NOW(), NOW()),
('163.com', 10, 1, NOW(), NOW()),
('126.com', 10, 1, NOW(), NOW()),
('qq.com', 10, 1, NOW(), NOW()),
('sina.com', 8, 1, NOW(), NOW()),
('sohu.com', 8, 1, NOW(), NOW()),
('aliyun.com', 10, 1, NOW(), NOW())
ON DUPLICATE KEY UPDATE updated_at = NOW();

CREATE TABLE IF NOT EXISTS ab_test (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(200) NOT NULL COMMENT '测试名称',
    template_id BIGINT NOT NULL COMMENT '基础模板ID',
    group_id BIGINT NOT NULL COMMENT '目标分组ID',
    test_type TINYINT NOT NULL COMMENT '测试类型: 1标题测试 2内容测试 3混合测试',
    sample_size INT DEFAULT 0 COMMENT '样本量(每个变体)',
    total_size INT DEFAULT 0 COMMENT '总发送量',
    winner_id BIGINT COMMENT '胜出变体ID',
    status TINYINT DEFAULT 0 COMMENT '状态: 0草稿 1测试中 2已完成 3已取消',
    metric_type TINYINT DEFAULT 1 COMMENT '评估指标: 1打开率 2点击率 3转化率',
    confidence_level DECIMAL(4,2) DEFAULT 95.00 COMMENT '置信度',
    start_time DATETIME COMMENT '开始时间',
    end_time DATETIME COMMENT '结束时间',
    deleted TINYINT DEFAULT 0,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_status (status),
    INDEX idx_template_id (template_id),
    INDEX idx_group_id (group_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='A/B测试表';

CREATE TABLE IF NOT EXISTS ab_test_variant (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    test_id BIGINT NOT NULL COMMENT '测试ID',
    variant_name VARCHAR(100) NOT NULL COMMENT '变体名称',
    subject VARCHAR(500) COMMENT '邮件标题',
    content TEXT COMMENT '邮件内容',
    weight INT DEFAULT 1 COMMENT '权重',
    sent_count INT DEFAULT 0 COMMENT '发送数',
    open_count INT DEFAULT 0 COMMENT '打开数',
    click_count INT DEFAULT 0 COMMENT '点击数',
    conversion_count INT DEFAULT 0 COMMENT '转化数',
    open_rate DECIMAL(5,2) DEFAULT 0 COMMENT '打开率',
    click_rate DECIMAL(5,2) DEFAULT 0 COMMENT '点击率',
    conversion_rate DECIMAL(5,2) DEFAULT 0 COMMENT '转化率',
    is_winner TINYINT DEFAULT 0 COMMENT '是否胜出: 0否 1是',
    deleted TINYINT DEFAULT 0,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_test_id (test_id),
    INDEX idx_is_winner (is_winner)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='A/B测试变体表';

CREATE TABLE IF NOT EXISTS user_behavior (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    recipient_id BIGINT NOT NULL COMMENT '收件人ID',
    email VARCHAR(200) NOT NULL COMMENT '邮箱',
    task_id BIGINT COMMENT '任务ID',
    behavior_type TINYINT NOT NULL COMMENT '行为类型: 1接收 2打开 3点击 4退订 5转化',
    item_category VARCHAR(100) COMMENT '相关产品类别',
    item_id VARCHAR(100) COMMENT '相关产品ID',
    behavior_time DATETIME COMMENT '行为时间',
    stay_duration INT DEFAULT 0 COMMENT '停留时长(秒)',
    click_count INT DEFAULT 1 COMMENT '点击次数',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_recipient_id (recipient_id),
    INDEX idx_email (email),
    INDEX idx_task_id (task_id),
    INDEX idx_behavior_type (behavior_type),
    INDEX idx_behavior_time (behavior_time)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='用户行为表';

CREATE TABLE IF NOT EXISTS product_category (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    category_code VARCHAR(50) NOT NULL COMMENT '类别编码',
    category_name VARCHAR(100) NOT NULL COMMENT '类别名称',
    parent_id BIGINT DEFAULT 0 COMMENT '父类别ID',
    keywords TEXT COMMENT '关键词(逗号分隔)',
    status TINYINT DEFAULT 1 COMMENT '状态: 0禁用 1启用',
    deleted TINYINT DEFAULT 0,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY uk_category_code (category_code),
    INDEX idx_parent_id (parent_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='产品类别表';

CREATE TABLE IF NOT EXISTS recipient_segment (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    segment_name VARCHAR(100) NOT NULL COMMENT '分群名称',
    segment_desc VARCHAR(500) COMMENT '分群描述',
    segment_type TINYINT NOT NULL COMMENT '分群类型: 1行为分群 2属性分群 3推荐分群',
    criteria TEXT COMMENT '筛选条件(JSON)',
    recipient_count INT DEFAULT 0 COMMENT '人数',
    status TINYINT DEFAULT 1 COMMENT '状态: 0禁用 1启用',
    auto_refresh TINYINT DEFAULT 1 COMMENT '是否自动刷新: 0否 1是',
    last_refresh_time DATETIME COMMENT '最后刷新时间',
    deleted TINYINT DEFAULT 0,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_segment_type (segment_type),
    INDEX idx_status (status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='收件人分群表';

CREATE TABLE IF NOT EXISTS recipient_segment_member (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    segment_id BIGINT NOT NULL COMMENT '分群ID',
    recipient_id BIGINT NOT NULL COMMENT '收件人ID',
    email VARCHAR(200) NOT NULL COMMENT '邮箱',
    score DECIMAL(5,2) DEFAULT 0 COMMENT '匹配度评分',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY uk_segment_recipient (segment_id, recipient_id),
    INDEX idx_segment_id (segment_id),
    INDEX idx_recipient_id (recipient_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='分群成员表';

CREATE TABLE IF NOT EXISTS delivery_report (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    task_id BIGINT COMMENT '任务ID',
    domain VARCHAR(100) NOT NULL COMMENT '邮箱域名',
    total_sent INT DEFAULT 0 COMMENT '总发送',
    delivered INT DEFAULT 0 COMMENT '成功送达',
    bounced INT DEFAULT 0 COMMENT '退信',
    complained INT DEFAULT 0 COMMENT '投诉',
    opened INT DEFAULT 0 COMMENT '已打开',
    clicked INT DEFAULT 0 COMMENT '已点击',
    delivery_rate DECIMAL(5,2) DEFAULT 0 COMMENT '送达率',
    open_rate DECIMAL(5,2) DEFAULT 0 COMMENT '打开率',
    click_rate DECIMAL(5,2) DEFAULT 0 COMMENT '点击率',
    avg_delay_seconds INT DEFAULT 0 COMMENT '平均延迟(秒)',
    delay_distribution TEXT COMMENT '延迟分布(JSON)',
    report_date DATE NOT NULL COMMENT '报告日期',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY uk_task_domain_date (task_id, domain, report_date),
    INDEX idx_task_id (task_id),
    INDEX idx_domain (domain),
    INDEX idx_report_date (report_date)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='送达报告表';

CREATE TABLE IF NOT EXISTS category_preference (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    recipient_id BIGINT NOT NULL COMMENT '收件人ID',
    email VARCHAR(200) NOT NULL COMMENT '邮箱',
    category_code VARCHAR(50) NOT NULL COMMENT '类别编码',
    preference_score DECIMAL(5,2) DEFAULT 0 COMMENT '偏好分数',
    view_count INT DEFAULT 0 COMMENT '浏览次数',
    click_count INT DEFAULT 0 COMMENT '点击次数',
    conversion_count INT DEFAULT 0 COMMENT '转化次数',
    last_behavior_time DATETIME COMMENT '最后行为时间',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY uk_recipient_category (recipient_id, category_code),
    INDEX idx_recipient_id (recipient_id),
    INDEX idx_email (email),
    INDEX idx_preference_score (preference_score)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='类别偏好表';

INSERT INTO product_category (category_code, category_name, parent_id, keywords, status) VALUES
('ELECTRONICS', '电子产品', 0, '手机,电脑,平板,数码,电子', 1),
('CLOTHING', '服装服饰', 0, '衣服,裤子,鞋子,包包,配饰', 1),
('FOOD', '食品饮料', 0, '零食,饮料,生鲜,美食', 1),
('HOME', '家居生活', 0, '家具,家居,日用品,装饰', 1),
('BEAUTY', '美妆个护', 0, '化妆品,护肤品,美容,香水', 1),
('SPORTS', '运动户外', 0, '运动,健身,户外,旅游', 1),
('BOOKS', '图书音像', 0, '书籍,图书,音像,电子书', 1),
('BABY', '母婴用品', 0, '婴儿,母婴,孕妇,儿童', 1)
ON DUPLICATE KEY UPDATE updated_at = NOW();
