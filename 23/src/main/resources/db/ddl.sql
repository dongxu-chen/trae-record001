-- ============================================
-- 商品中心数据库 DDL
-- ============================================

-- 商品表
CREATE TABLE IF NOT EXISTS products (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    version BIGINT DEFAULT 0 NOT NULL,
    name VARCHAR(200) NOT NULL COMMENT '商品名称',
    description TEXT COMMENT '商品描述',
    price DECIMAL(10,2) NOT NULL COMMENT '商品价格',
    stock INT NOT NULL DEFAULT 0 COMMENT '总库存（冗余字段，可由各SKU汇总）',
    category VARCHAR(100) COMMENT '商品分类',
    image_url VARCHAR(500) COMMENT '商品主图',
    active BOOLEAN NOT NULL DEFAULT TRUE COMMENT '是否上架',
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_category (category),
    INDEX idx_active (active),
    INDEX idx_created_at (created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='商品表';

-- SKU表（商品规格）
CREATE TABLE IF NOT EXISTS skus (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    version BIGINT DEFAULT 0 NOT NULL,
    product_id BIGINT NOT NULL COMMENT '关联商品ID',
    sku_code VARCHAR(64) NOT NULL UNIQUE COMMENT 'SKU编码',
    specs VARCHAR(500) NOT NULL COMMENT '规格JSON，如 {"颜色":"红色","尺码":"M"}',
    price DECIMAL(10,2) NOT NULL COMMENT 'SKU价格',
    stock INT NOT NULL DEFAULT 0 COMMENT 'SKU库存',
    image_url VARCHAR(500) COMMENT 'SKU图片',
    active BOOLEAN NOT NULL DEFAULT TRUE COMMENT '是否启用',
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_product_id (product_id),
    INDEX idx_sku_code (sku_code),
    INDEX idx_active (active),
    FOREIGN KEY (product_id) REFERENCES products(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='SKU表';

-- 库存流水表（记录库存变更，用于审计和补偿）
CREATE TABLE IF NOT EXISTS stock_logs (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    sku_id BIGINT NOT NULL COMMENT 'SKU ID',
    order_no VARCHAR(64) COMMENT '关联订单号',
    type VARCHAR(32) NOT NULL COMMENT '流水类型：DEDUCT-扣减, FREEZE-冻结, RELEASE-释放, INCREASE-增加, INIT-初始化',
    quantity INT NOT NULL COMMENT '变更数量（正数为增加，负数为扣减）',
    before_stock INT NOT NULL COMMENT '变更前库存',
    after_stock INT NOT NULL COMMENT '变更后库存',
    remark VARCHAR(500) COMMENT '备注',
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_sku_id (sku_id),
    INDEX idx_order_no (order_no),
    INDEX idx_type (type),
    INDEX idx_created_at (created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='库存流水表';
