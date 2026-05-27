-- =============================================
-- 医疗药品库存预警系统 数据库DDL
-- =============================================

CREATE DATABASE IF NOT EXISTS medicine_stock
    DEFAULT CHARACTER SET utf8mb4
    DEFAULT COLLATE utf8mb4_unicode_ci;

USE medicine_stock;

-- 仓库表
DROP TABLE IF EXISTS t_warehouse;
CREATE TABLE t_warehouse (
    id              BIGINT          NOT NULL AUTO_INCREMENT COMMENT '仓库ID',
    warehouse_code  VARCHAR(32)     NOT NULL COMMENT '仓库编码',
    warehouse_name  VARCHAR(100)    NOT NULL COMMENT '仓库名称',
    location        VARCHAR(200)    NOT NULL COMMENT '仓库位置/地址',
    capacity        INT             DEFAULT 0 COMMENT '容量(件数)',
    status          TINYINT         DEFAULT 1 COMMENT '状态: 1-启用 0-停用',
    is_main         TINYINT         DEFAULT 0 COMMENT '是否主仓库: 1-是 0-否',
    create_time     DATETIME        DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    update_time     DATETIME        DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    PRIMARY KEY (id),
    UNIQUE KEY uk_warehouse_code (warehouse_code)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='仓库表';

-- 药品表
DROP TABLE IF EXISTS t_medicine;
CREATE TABLE t_medicine (
    id                  BIGINT          NOT NULL AUTO_INCREMENT COMMENT '药品ID',
    medicine_code       VARCHAR(32)     NOT NULL COMMENT '药品编码',
    medicine_name       VARCHAR(200)    NOT NULL COMMENT '药品名称',
    generic_name        VARCHAR(200)    COMMENT '通用名',
    specification       VARCHAR(100)    COMMENT '规格',
    manufacturer        VARCHAR(200)    COMMENT '生产厂家',
    unit                VARCHAR(20)     NOT NULL COMMENT '单位(盒/瓶/支等)',
    category            VARCHAR(50)     COMMENT '药品分类',
    dosage_form         VARCHAR(50)     COMMENT '剂型',
    is_prescription     TINYINT         DEFAULT 0 COMMENT '是否处方药: 1-是 0-否',
    is_active           TINYINT         DEFAULT 1 COMMENT '是否启用: 1-是 0-否',
    create_time         DATETIME        DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    update_time         DATETIME        DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    PRIMARY KEY (id),
    UNIQUE KEY uk_medicine_code (medicine_code)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='药品表';

-- 药品库存表
DROP TABLE IF EXISTS t_stock;
CREATE TABLE t_stock (
    id                      BIGINT          NOT NULL AUTO_INCREMENT COMMENT '库存ID',
    warehouse_id            BIGINT          NOT NULL COMMENT '仓库ID',
    medicine_id             BIGINT          NOT NULL COMMENT '药品ID',
    batch_no                VARCHAR(64)     NOT NULL COMMENT '批次号',
    quantity                INT             NOT NULL DEFAULT 0 COMMENT '当前库存数量',
    locked_quantity         INT             NOT NULL DEFAULT 0 COMMENT '锁定数量(已分配未出库)',
    available_quantity      INT             GENERATED ALWAYS AS (quantity - locked_quantity) VIRTUAL COMMENT '可用数量',
    unit_price              DECIMAL(12,2)   NOT NULL DEFAULT 0.00 COMMENT '单价',
    production_date         DATE            COMMENT '生产日期',
    expiry_date             DATE            NOT NULL COMMENT '有效期',
    supplier_id             BIGINT          COMMENT '供应商ID',
    inbound_date            DATETIME        COMMENT '入库时间',
    is_expired              TINYINT         DEFAULT 0 COMMENT '是否已过期: 1-是 0-否',
    is_blocked              TINYINT         DEFAULT 0 COMMENT '是否拦截(近效期): 1-是 0-否',
    create_time             DATETIME        DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    update_time             DATETIME        DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    PRIMARY KEY (id),
    KEY idx_warehouse_medicine (warehouse_id, medicine_id),
    KEY idx_expiry_date (expiry_date),
    KEY idx_batch_no (batch_no)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='药品库存表';

-- 药品消耗历史表
DROP TABLE IF EXISTS t_consumption_history;
CREATE TABLE t_consumption_history (
    id                  BIGINT          NOT NULL AUTO_INCREMENT COMMENT '记录ID',
    warehouse_id        BIGINT          NOT NULL COMMENT '仓库ID',
    medicine_id         BIGINT          NOT NULL COMMENT '药品ID',
    quantity            INT             NOT NULL COMMENT '消耗数量',
    consumption_date    DATE            NOT NULL COMMENT '消耗日期',
    unit_price          DECIMAL(12,2)   COMMENT '单价',
    total_amount        DECIMAL(14,2)   COMMENT '总金额',
    department          VARCHAR(100)    COMMENT '领用科室',
    remark              VARCHAR(500)    COMMENT '备注',
    create_time         DATETIME        DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    PRIMARY KEY (id),
    KEY idx_medicine_date (medicine_id, consumption_date),
    KEY idx_warehouse_date (warehouse_id, consumption_date)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='药品消耗历史表';

-- 供应商表
DROP TABLE IF EXISTS t_supplier;
CREATE TABLE t_supplier (
    id                  BIGINT          NOT NULL AUTO_INCREMENT COMMENT '供应商ID',
    supplier_code       VARCHAR(32)     NOT NULL COMMENT '供应商编码',
    supplier_name       VARCHAR(200)    NOT NULL COMMENT '供应商名称',
    contact_person      VARCHAR(50)     COMMENT '联系人',
    contact_phone       VARCHAR(30)     COMMENT '联系电话',
    address             VARCHAR(300)    COMMENT '地址',
    lead_time_days      INT             DEFAULT 14 COMMENT '供货周期(天)',
    min_order_quantity  INT             DEFAULT 1 COMMENT '最小订货量',
    is_active           TINYINT         DEFAULT 1 COMMENT '是否启用: 1-是 0-否',
    create_time         DATETIME        DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    update_time         DATETIME        DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    PRIMARY KEY (id),
    UNIQUE KEY uk_supplier_code (supplier_code)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='供应商表';

-- 采购计划表
DROP TABLE IF EXISTS t_purchase_plan;
CREATE TABLE t_purchase_plan (
    id                  BIGINT          NOT NULL AUTO_INCREMENT COMMENT '采购计划ID',
    plan_no             VARCHAR(32)     NOT NULL COMMENT '计划编号',
    medicine_id         BIGINT          NOT NULL COMMENT '药品ID',
    supplier_id         BIGINT          COMMENT '供应商ID',
    warehouse_id        BIGINT          NOT NULL COMMENT '目标仓库ID',
    plan_quantity       INT             NOT NULL COMMENT '计划采购数量',
    actual_quantity     INT             DEFAULT 0 COMMENT '实际入库数量',
    unit_price          DECIMAL(12,2)   COMMENT '单价',
    total_amount        DECIMAL(14,2)   COMMENT '总金额',
    expected_date       DATE            COMMENT '预计到货日期',
    reorder_point       INT             COMMENT '补货点',
    safety_stock        INT             COMMENT '安全库存',
    avg_consumption     DECIMAL(10,2)   COMMENT '日均消耗量',
    lead_time_days      INT             COMMENT '供货周期(天)',
    status              VARCHAR(20)     DEFAULT 'PENDING' COMMENT '状态: PENDING-待处理 APPROVED-已批准 ORDERED-已订购 IN_TRANSIT-运输中 RECEIVED-已入库 CANCELLED-已取消',
    approval_status     VARCHAR(20)     DEFAULT 'PENDING' COMMENT '审批状态: PENDING-待审批 APPROVED-已批准 REJECTED-已拒绝',
    plan_date           DATE            COMMENT '计划生成日期',
    order_date          DATETIME        COMMENT '下单日期',
    receipt_date        DATETIME        COMMENT '入库日期',
    approver            VARCHAR(50)     COMMENT '审批人',
    approval_time       DATETIME        COMMENT '审批时间',
    remark              VARCHAR(500)    COMMENT '备注',
    create_time         DATETIME        DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    update_time         DATETIME        DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    PRIMARY KEY (id),
    UNIQUE KEY uk_plan_no (plan_no),
    KEY idx_medicine_status (medicine_id, status),
    KEY idx_warehouse_status (warehouse_id, status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='采购计划表';

-- 库存调拨单表
DROP TABLE IF EXISTS t_allocation;
CREATE TABLE t_allocation (
    id                  BIGINT          NOT NULL AUTO_INCREMENT COMMENT '调拨ID',
    allocation_no       VARCHAR(32)     NOT NULL COMMENT '调拨单号',
    medicine_id         BIGINT          NOT NULL COMMENT '药品ID',
    from_warehouse_id   BIGINT          NOT NULL COMMENT '源仓库ID',
    to_warehouse_id     BIGINT          NOT NULL COMMENT '目标仓库ID',
    quantity            INT             NOT NULL COMMENT '调拨数量',
    unit_price          DECIMAL(12,2)   COMMENT '单价',
    total_amount        DECIMAL(14,2)   COMMENT '总金额',
    reason              VARCHAR(500)    COMMENT '调拨原因',
    status              VARCHAR(20)     DEFAULT 'PENDING' COMMENT '状态: PENDING-待出库 OUT-已出库 IN_TRANSIT-运输中 IN-已入库 CANCELLED-已取消',
    allocation_date     DATETIME        COMMENT '调拨日期',
    create_time         DATETIME        DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    update_time         DATETIME        DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    PRIMARY KEY (id),
    UNIQUE KEY uk_allocation_no (allocation_no),
    KEY idx_medicine_status (medicine_id, status),
    KEY idx_from_warehouse (from_warehouse_id, status),
    KEY idx_to_warehouse (to_warehouse_id, status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='库存调拨单表';

-- 预警记录表
DROP TABLE IF EXISTS t_warning_log;
CREATE TABLE t_warning_log (
    id                  BIGINT          NOT NULL AUTO_INCREMENT COMMENT '预警ID',
    warning_type        VARCHAR(30)     NOT NULL COMMENT '预警类型: LOW_STOCK-低库存 NEAR_EXPIRY-近效期 EXPIRED-已过期 ALLOCATION-待调拨',
    severity            VARCHAR(20)     DEFAULT 'WARNING' COMMENT '严重级别: INFO-提示 WARNING-警告 CRITICAL-严重',
    warehouse_id        BIGINT          COMMENT '仓库ID',
    medicine_id         BIGINT          COMMENT '药品ID',
    batch_no            VARCHAR(64)     COMMENT '批次号',
    current_value       INT             COMMENT '当前值',
    threshold_value     INT             COMMENT '阈值',
    message             VARCHAR(500)    COMMENT '预警消息',
    is_resolved         TINYINT         DEFAULT 0 COMMENT '是否已处理: 1-是 0-否',
    resolve_time        DATETIME        COMMENT '处理时间',
    resolve_by          VARCHAR(50)     COMMENT '处理人',
    resolve_note        VARCHAR(500)    COMMENT '处理说明',
    create_time         DATETIME        DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    PRIMARY KEY (id),
    KEY idx_type_created (warning_type, create_time),
    KEY idx_medicine (medicine_id),
    KEY idx_warehouse (warehouse_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='预警记录表';

-- =============================================
-- 初始数据
-- =============================================

INSERT INTO t_warehouse (warehouse_code, warehouse_name, location, capacity, is_main, status) VALUES
('WH001', '中心仓库', '北京市朝阳区中心库1号', 100000, 1, 1),
('WH002', '东城分库', '北京市东城区分库2号', 50000, 0, 1),
('WH003', '西城分库', '北京市西城区分库3号', 50000, 0, 1),
('WH004', '海淀分库', '北京市海淀区分库4号', 40000, 0, 1);

INSERT INTO t_medicine (medicine_code, medicine_name, generic_name, specification, manufacturer, unit, category, dosage_form, is_prescription) VALUES
('MED001', '阿莫西林胶囊', '阿莫西林', '0.25g*24粒', '华北制药', '盒', '抗生素', '胶囊剂', 1),
('MED002', '布洛芬缓释胶囊', '布洛芬', '0.3g*20粒', '中美史克', '盒', '解热镇痛', '缓释胶囊', 0),
('MED003', '头孢克肟分散片', '头孢克肟', '0.1g*12片', '广州白云山', '盒', '抗生素', '片剂', 1),
('MED004', '蒙脱石散', '蒙脱石', '3g*10袋', '博福-益普生', '盒', '消化系统', '散剂', 0),
('MED005', '维生素C片', '维生素C', '0.1g*100片', '东北制药', '瓶', '维生素类', '片剂', 0);

INSERT INTO t_supplier (supplier_code, supplier_name, contact_person, contact_phone, address, lead_time_days, min_order_quantity) VALUES
('SUP001', '华北制药股份有限公司', '张经理', '010-12345678', '河北省石家庄市', 14, 10),
('SUP002', '中美天津史克制药', '李经理', '022-87654321', '天津市', 10, 20),
('SUP003', '广州白云山医药集团', '王经理', '020-11223344', '广东省广州市', 12, 15);
