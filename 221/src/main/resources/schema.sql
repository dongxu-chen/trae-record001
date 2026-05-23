CREATE DATABASE IF NOT EXISTS shortlink DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

USE shortlink;

CREATE TABLE IF NOT EXISTS short_link (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    origin_url VARCHAR(2048) NOT NULL COMMENT '原始URL',
    short_code VARCHAR(16) NOT NULL COMMENT '短码',
    description VARCHAR(255) DEFAULT NULL COMMENT '描述',
    expire_time DATETIME DEFAULT NULL COMMENT '过期时间',
    enabled TINYINT(1) NOT NULL DEFAULT 1 COMMENT '是否启用',
    pv_count BIGINT NOT NULL DEFAULT 0 COMMENT 'PV数',
    uv_count BIGINT NOT NULL DEFAULT 0 COMMENT 'UV数',
    create_time DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    update_time DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    UNIQUE KEY idx_short_code (short_code),
    KEY idx_origin_url (origin_url(255)),
    KEY idx_expire_time (expire_time)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='短链接表';

CREATE TABLE IF NOT EXISTS access_log (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    short_code VARCHAR(16) NOT NULL COMMENT '短码',
    ip VARCHAR(64) DEFAULT NULL COMMENT 'IP地址',
    user_agent VARCHAR(512) DEFAULT NULL COMMENT '用户代理',
    device_type VARCHAR(64) DEFAULT NULL COMMENT '设备类型',
    browser VARCHAR(64) DEFAULT NULL COMMENT '浏览器',
    os VARCHAR(64) DEFAULT NULL COMMENT '操作系统',
    country VARCHAR(128) DEFAULT NULL COMMENT '国家',
    province VARCHAR(128) DEFAULT NULL COMMENT '省份',
    city VARCHAR(128) DEFAULT NULL COMMENT '城市',
    referer VARCHAR(255) DEFAULT NULL COMMENT '来源',
    access_time DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '访问时间',
    KEY idx_short_code (short_code),
    KEY idx_access_time (access_time),
    KEY idx_ip (ip)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='访问日志表';
