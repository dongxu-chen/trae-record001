-- 创建数据库
CREATE DATABASE IF NOT EXISTS points_db DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

USE points_db;

-- 用户积分表
CREATE TABLE IF NOT EXISTS user_points (
    id BIGINT AUTO_INCREMENT PRIMARY KEY COMMENT '主键ID',
    user_id BIGINT NOT NULL COMMENT '用户ID',
    total_points INT NOT NULL DEFAULT 0 COMMENT '累计总积分',
    available_points INT NOT NULL DEFAULT 0 COMMENT '可用积分',
    frozen_points INT NOT NULL DEFAULT 0 COMMENT '冻结积分',
    version INT NOT NULL DEFAULT 0 COMMENT '乐观锁版本号',
    create_time DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    update_time DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    deleted TINYINT NOT NULL DEFAULT 0 COMMENT '逻辑删除: 0-未删除 1-已删除',
    UNIQUE KEY uk_user_id (user_id),
    KEY idx_user_id (user_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='用户积分表';

-- 积分流水记录表
CREATE TABLE IF NOT EXISTS points_record (
    id BIGINT AUTO_INCREMENT PRIMARY KEY COMMENT '主键ID',
    user_id BIGINT NOT NULL COMMENT '用户ID',
    order_no VARCHAR(64) NOT NULL COMMENT '业务单号',
    points_type TINYINT NOT NULL COMMENT '积分类型: 1-发放 2-扣减',
    points_source TINYINT NOT NULL COMMENT '积分来源: 1-签到 2-消费 3-活动 4-兑换 5-过期',
    points INT NOT NULL COMMENT '积分变动数量',
    balance_before INT NOT NULL COMMENT '变动前余额',
    balance_after INT NOT NULL COMMENT '变动后余额',
    description VARCHAR(256) DEFAULT NULL COMMENT '描述',
    remark VARCHAR(256) DEFAULT NULL COMMENT '备注',
    create_time DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    update_time DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    deleted TINYINT NOT NULL DEFAULT 0 COMMENT '逻辑删除: 0-未删除 1-已删除',
    KEY idx_user_id (user_id),
    KEY idx_order_no (order_no),
    KEY idx_create_time (create_time),
    KEY idx_user_type (user_id, points_type)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='积分流水记录表';

-- 积分过期记录表
CREATE TABLE IF NOT EXISTS points_expire (
    id BIGINT AUTO_INCREMENT PRIMARY KEY COMMENT '主键ID',
    user_id BIGINT NOT NULL COMMENT '用户ID',
    points INT NOT NULL COMMENT '原始积分',
    remaining_points INT NOT NULL COMMENT '剩余积分',
    source TINYINT NOT NULL COMMENT '来源: 1-签到 2-消费 3-活动',
    source_order_no VARCHAR(64) DEFAULT NULL COMMENT '来源业务单号',
    expire_time DATETIME NOT NULL COMMENT '过期时间',
    status TINYINT NOT NULL DEFAULT 0 COMMENT '状态: 0-正常 1-已过期 2-已使用',
    create_time DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    update_time DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    deleted TINYINT NOT NULL DEFAULT 0 COMMENT '逻辑删除: 0-未删除 1-已删除',
    KEY idx_user_id (user_id),
    KEY idx_expire_time (expire_time),
    KEY idx_status (status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='积分过期记录表';

-- 积分商城商品表
CREATE TABLE IF NOT EXISTS points_mall_product (
    id BIGINT AUTO_INCREMENT PRIMARY KEY COMMENT '主键ID',
    product_name VARCHAR(128) NOT NULL COMMENT '商品名称',
    product_image VARCHAR(512) DEFAULT NULL COMMENT '商品图片',
    product_desc VARCHAR(512) DEFAULT NULL COMMENT '商品描述',
    points_required INT NOT NULL COMMENT '所需积分',
    stock INT NOT NULL DEFAULT 0 COMMENT '库存',
    status TINYINT NOT NULL DEFAULT 1 COMMENT '状态: 0-下架 1-上架',
    create_time DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    update_time DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    deleted TINYINT NOT NULL DEFAULT 0 COMMENT '逻辑删除: 0-未删除 1-已删除',
    KEY idx_status (status),
    KEY idx_points_required (points_required)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='积分商城商品表';

-- 积分商城订单表
CREATE TABLE IF NOT EXISTS points_mall_order (
    id BIGINT AUTO_INCREMENT PRIMARY KEY COMMENT '主键ID',
    order_no VARCHAR(64) NOT NULL COMMENT '订单号',
    user_id BIGINT NOT NULL COMMENT '用户ID',
    product_id BIGINT NOT NULL COMMENT '商品ID',
    product_name VARCHAR(128) NOT NULL COMMENT '商品名称',
    points_required INT NOT NULL COMMENT '单件所需积分',
    quantity INT NOT NULL DEFAULT 1 COMMENT '数量',
    total_points INT NOT NULL COMMENT '总消耗积分',
    status TINYINT NOT NULL DEFAULT 1 COMMENT '状态: 0-取消 1-待发货 2-已发货 3-已完成',
    receiver_name VARCHAR(64) DEFAULT NULL COMMENT '收货人姓名',
    receiver_phone VARCHAR(20) DEFAULT NULL COMMENT '收货人电话',
    receiver_address VARCHAR(256) DEFAULT NULL COMMENT '收货地址',
    create_time DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    update_time DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    deleted TINYINT NOT NULL DEFAULT 0 COMMENT '逻辑删除: 0-未删除 1-已删除',
    UNIQUE KEY uk_order_no (order_no),
    KEY idx_user_id (user_id),
    KEY idx_create_time (create_time)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='积分商城订单表';

-- 初始化测试商品数据
INSERT INTO points_mall_product (product_name, product_image, product_desc, points_required, stock, status) VALUES
('10元话费券', 'https://example.com/images/phone_10.jpg', '可兑换10元话费', 1000, 100, 1),
('30元话费券', 'https://example.com/images/phone_30.jpg', '可兑换30元话费', 2800, 50, 1),
('50元话费券', 'https://example.com/images/phone_50.jpg', '可兑换50元话费', 4500, 30, 1),
('精美马克杯', 'https://example.com/images/mug.jpg', '品牌定制马克杯', 2000, 200, 1),
('精美笔记本', 'https://example.com/images/notebook.jpg', '商务笔记本', 1500, 150, 1),
('品牌雨伞', 'https://example.com/images/umbrella.jpg', '折叠晴雨伞', 3000, 80, 1),
('蓝牙耳机', 'https://example.com/images/earphone.jpg', '无线蓝牙耳机', 8000, 20, 1),
('智能手环', 'https://example.com/images/bracelet.jpg', '运动智能手环', 15000, 10, 1);
