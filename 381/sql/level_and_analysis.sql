-- 积分等级配置表
CREATE TABLE IF NOT EXISTS points_level_config (
    id BIGINT AUTO_INCREMENT PRIMARY KEY COMMENT '主键ID',
    level_name VARCHAR(64) NOT NULL COMMENT '等级名称',
    level_code VARCHAR(32) NOT NULL COMMENT '等级编码',
    level_order INT NOT NULL COMMENT '等级排序（数字越大等级越高）',
    min_points INT NOT NULL DEFAULT 0 COMMENT '最小积分',
    max_points INT NOT NULL DEFAULT 999999999 COMMENT '最大积分',
    level_icon VARCHAR(512) DEFAULT NULL COMMENT '等级图标',
    level_privileges TEXT COMMENT '等级权益JSON',
    discount_rate DECIMAL(3,2) DEFAULT 1.00 COMMENT '折扣率（如0.95代表95折）',
    status TINYINT NOT NULL DEFAULT 1 COMMENT '状态: 0-禁用 1-启用',
    create_time DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    update_time DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    deleted TINYINT NOT NULL DEFAULT 0 COMMENT '逻辑删除',
    UNIQUE KEY uk_level_code (level_code),
    UNIQUE KEY uk_level_order (level_order)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='积分等级配置表';

-- 用户等级表
CREATE TABLE IF NOT EXISTS user_level (
    id BIGINT AUTO_INCREMENT PRIMARY KEY COMMENT '主键ID',
    user_id BIGINT NOT NULL COMMENT '用户ID',
    current_level_id BIGINT NOT NULL COMMENT '当前等级ID',
    current_level_code VARCHAR(32) NOT NULL COMMENT '当前等级编码',
    current_level_name VARCHAR(64) NOT NULL COMMENT '当前等级名称',
    current_level_order INT NOT NULL COMMENT '当前等级排序',
    total_points INT NOT NULL DEFAULT 0 COMMENT '累计总积分',
    level_points INT NOT NULL DEFAULT 0 COMMENT '当前等级已获得积分',
    next_level_points INT DEFAULT NULL COMMENT '下一等级所需积分',
    next_level_name VARCHAR(64) DEFAULT NULL COMMENT '下一等级名称',
    level_up_time DATETIME DEFAULT NULL COMMENT '最近升级时间',
    create_time DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    update_time DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    deleted TINYINT NOT NULL DEFAULT 0 COMMENT '逻辑删除',
    UNIQUE KEY uk_user_id (user_id),
    KEY idx_level_id (current_level_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='用户等级表';

-- 用户等级变更记录表
CREATE TABLE IF NOT EXISTS user_level_log (
    id BIGINT AUTO_INCREMENT PRIMARY KEY COMMENT '主键ID',
    user_id BIGINT NOT NULL COMMENT '用户ID',
    before_level_id BIGINT DEFAULT NULL COMMENT '变更前等级ID',
    before_level_code VARCHAR(32) DEFAULT NULL COMMENT '变更前等级编码',
    before_level_name VARCHAR(64) DEFAULT NULL COMMENT '变更前等级名称',
    after_level_id BIGINT NOT NULL COMMENT '变更后等级ID',
    after_level_code VARCHAR(32) NOT NULL COMMENT '变更后等级编码',
    after_level_name VARCHAR(64) NOT NULL COMMENT '变更后等级名称',
    change_type TINYINT NOT NULL DEFAULT 1 COMMENT '变更类型: 1-升级 2-降级 3-初始化',
    change_reason VARCHAR(256) DEFAULT NULL COMMENT '变更原因',
    trigger_points INT DEFAULT NULL COMMENT '触发变更时的积分',
    create_time DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    deleted TINYINT NOT NULL DEFAULT 0 COMMENT '逻辑删除',
    KEY idx_user_id (user_id),
    KEY idx_create_time (create_time)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='用户等级变更记录表';

-- 初始化会员等级配置
INSERT INTO points_level_config (level_name, level_code, level_order, min_points, max_points, level_icon, level_privileges, discount_rate, status) VALUES
('普通会员', 'BRONZE', 1, 0, 1000, 'https://example.com/icons/bronze.png', '{"signInPoints":10, "discount":100, "birthdayPoints":50}', 1.00, 1),
('白银会员', 'SILVER', 2, 1000, 5000, 'https://example.com/icons/silver.png', '{"signInPoints":20, "discount":95, "birthdayPoints":100}', 0.95, 1),
('黄金会员', 'GOLD', 3, 5000, 20000, 'https://example.com/icons/gold.png', '{"signInPoints":30, "discount":90, "birthdayPoints":200}', 0.90, 1),
('铂金会员', 'PLATINUM', 4, 20000, 50000, 'https://example.com/icons/platinum.png', '{"signInPoints":50, "discount":85, "birthdayPoints":500}', 0.85, 1),
('钻石会员', 'DIAMOND', 5, 50000, 100000, 'https://example.com/icons/diamond.png', '{"signInPoints":80, "discount":80, "birthdayPoints":1000}', 0.80, 1),
('皇冠会员', 'CROWN', 6, 100000, 999999999, 'https://example.com/icons/crown.png', '{"signInPoints":100, "discount":75, "birthdayPoints":2000}', 0.75, 1);
