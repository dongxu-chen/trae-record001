CREATE DATABASE IF NOT EXISTS payment_reconciliation DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

USE payment_reconciliation;

CREATE TABLE IF NOT EXISTS transaction (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    transaction_no VARCHAR(64) NOT NULL COMMENT '交易流水号',
    order_no VARCHAR(64) NOT NULL COMMENT '订单号',
    channel_code VARCHAR(32) NOT NULL COMMENT '渠道编码',
    merchant_no VARCHAR(64) COMMENT '商户号',
    amount DECIMAL(18,2) NOT NULL COMMENT '交易金额',
    fee DECIMAL(18,2) DEFAULT 0 COMMENT '手续费',
    status TINYINT DEFAULT 1 COMMENT '状态',
    pay_method VARCHAR(32) COMMENT '支付方式',
    trans_time DATETIME NOT NULL COMMENT '交易时间',
    create_time DATETIME DEFAULT CURRENT_TIMESTAMP,
    update_time DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY uk_transaction_no (transaction_no),
    KEY idx_order_no (order_no),
    KEY idx_channel_code (channel_code),
    KEY idx_trans_time (trans_time)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='交易流水表';

CREATE TABLE IF NOT EXISTS channel_reconciliation (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    reconciliation_no VARCHAR(64) NOT NULL COMMENT '对账编号',
    channel_code VARCHAR(32) NOT NULL COMMENT '渠道编码',
    reconciliation_date DATE NOT NULL COMMENT '对账日期',
    file_name VARCHAR(255) COMMENT '文件名',
    file_path VARCHAR(512) COMMENT '文件路径',
    file_type TINYINT COMMENT '文件类型',
    total_count INT DEFAULT 0 COMMENT '总笔数',
    total_amount DECIMAL(18,2) DEFAULT 0 COMMENT '总金额',
    parsed_count INT DEFAULT 0 COMMENT '解析笔数',
    status TINYINT DEFAULT 0 COMMENT '状态',
    error_msg TEXT COMMENT '错误信息',
    create_time DATETIME DEFAULT CURRENT_TIMESTAMP,
    update_time DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY uk_reconciliation_no (reconciliation_no),
    KEY idx_channel_date (channel_code, reconciliation_date),
    KEY idx_status (status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='渠道对账记录表';

CREATE TABLE IF NOT EXISTS channel_transaction (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    reconciliation_id BIGINT NOT NULL COMMENT '对账记录ID',
    channel_trans_no VARCHAR(64) NOT NULL COMMENT '渠道交易流水号',
    channel_code VARCHAR(32) NOT NULL COMMENT '渠道编码',
    merchant_no VARCHAR(64) COMMENT '商户号',
    order_no VARCHAR(64) COMMENT '订单号',
    amount DECIMAL(18,2) NOT NULL COMMENT '交易金额',
    fee DECIMAL(18,2) DEFAULT 0 COMMENT '手续费',
    status TINYINT DEFAULT 1 COMMENT '状态',
    trans_time DATETIME NOT NULL COMMENT '交易时间',
    matched TINYINT DEFAULT 0 COMMENT '是否匹配',
    create_time DATETIME DEFAULT CURRENT_TIMESTAMP,
    KEY idx_reconciliation_id (reconciliation_id),
    KEY idx_order_no (order_no),
    KEY idx_matched (matched)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='渠道交易明细表';

CREATE TABLE IF NOT EXISTS reconciliation_result (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    result_no VARCHAR(64) NOT NULL COMMENT '结果编号',
    channel_code VARCHAR(32) NOT NULL COMMENT '渠道编码',
    reconciliation_date DATE NOT NULL COMMENT '对账日期',
    sys_total_count INT DEFAULT 0 COMMENT '系统总笔数',
    sys_total_amount DECIMAL(18,2) DEFAULT 0 COMMENT '系统总金额',
    channel_total_count INT DEFAULT 0 COMMENT '渠道总笔数',
    channel_total_amount DECIMAL(18,2) DEFAULT 0 COMMENT '渠道总金额',
    matched_count INT DEFAULT 0 COMMENT '匹配笔数',
    matched_amount DECIMAL(18,2) DEFAULT 0 COMMENT '匹配金额',
    long_count INT DEFAULT 0 COMMENT '长款笔数',
    long_amount DECIMAL(18,2) DEFAULT 0 COMMENT '长款金额',
    short_count INT DEFAULT 0 COMMENT '短款笔数',
    short_amount DECIMAL(18,2) DEFAULT 0 COMMENT '短款金额',
    status TINYINT DEFAULT 1 COMMENT '状态',
    create_time DATETIME DEFAULT CURRENT_TIMESTAMP,
    update_time DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY uk_result_no (result_no),
    KEY idx_channel_date (channel_code, reconciliation_date)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='对账结果表';

CREATE TABLE IF NOT EXISTS discrepancy (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    discrepancy_no VARCHAR(64) NOT NULL COMMENT '差错编号',
    result_id BIGINT NOT NULL COMMENT '对账结果ID',
    channel_code VARCHAR(32) NOT NULL COMMENT '渠道编码',
    reconciliation_date DATE NOT NULL COMMENT '对账日期',
    type TINYINT NOT NULL COMMENT '差错类型:1-长款,2-短款,3-金额不符',
    order_no VARCHAR(64) COMMENT '订单号',
    transaction_no VARCHAR(64) COMMENT '系统交易流水号',
    channel_trans_no VARCHAR(64) COMMENT '渠道交易流水号',
    sys_amount DECIMAL(18,2) DEFAULT 0 COMMENT '系统金额',
    channel_amount DECIMAL(18,2) DEFAULT 0 COMMENT '渠道金额',
    difference_amount DECIMAL(18,2) DEFAULT 0 COMMENT '差额',
    status TINYINT DEFAULT 0 COMMENT '处理状态',
    handle_remark TEXT COMMENT '处理备注',
    handle_time DATETIME COMMENT '处理时间',
    handler VARCHAR(64) COMMENT '处理人',
    create_time DATETIME DEFAULT CURRENT_TIMESTAMP,
    update_time DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY uk_discrepancy_no (discrepancy_no),
    KEY idx_result_id (result_id),
    KEY idx_type (type),
    KEY idx_status (status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='差错记录表';

CREATE TABLE IF NOT EXISTS fund_transfer (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    transfer_no VARCHAR(64) NOT NULL COMMENT '调拨编号',
    request_id VARCHAR(128) NOT NULL COMMENT '唯一请求ID,用于幂等',
    discrepancy_id BIGINT COMMENT '差错记录ID',
    channel_code VARCHAR(32) NOT NULL COMMENT '渠道编码',
    transfer_type TINYINT NOT NULL COMMENT '调拨类型',
    amount DECIMAL(18,2) NOT NULL COMMENT '调拨金额',
    from_account VARCHAR(128) COMMENT '出款账户',
    to_account VARCHAR(128) COMMENT '入款账户',
    bank_order_no VARCHAR(128) COMMENT '银行流水号',
    status TINYINT DEFAULT 0 COMMENT '状态',
    remark TEXT COMMENT '备注',
    transfer_time DATETIME COMMENT '调拨时间',
    operator VARCHAR(64) COMMENT '操作人',
    create_time DATETIME DEFAULT CURRENT_TIMESTAMP,
    update_time DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY uk_transfer_no (transfer_no),
    UNIQUE KEY uk_request_id (request_id),
    KEY idx_discrepancy_id (discrepancy_id),
    KEY idx_status (status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='资金调拨记录表';

CREATE TABLE IF NOT EXISTS transaction_log (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    transaction_id VARCHAR(128) NOT NULL COMMENT '事务ID',
    business_type VARCHAR(64) NOT NULL COMMENT '业务类型:RECONCILIATION,DISCREPANCY,FUND_TRANSFER',
    business_id VARCHAR(128) COMMENT '业务ID',
    status TINYINT DEFAULT 0 COMMENT '状态:0-待处理,1-已提交,2-已回滚',
    retry_count INT DEFAULT 0 COMMENT '重试次数',
    next_retry_time DATETIME COMMENT '下次重试时间',
    error_msg TEXT COMMENT '错误信息',
    create_time DATETIME DEFAULT CURRENT_TIMESTAMP,
    update_time DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY uk_transaction_id (transaction_id),
    KEY idx_business_type (business_type),
    KEY idx_status (status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='本地事务记录表';

CREATE TABLE IF NOT EXISTS reversal_task (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    task_no VARCHAR(64) NOT NULL COMMENT '任务编号',
    discrepancy_id BIGINT NOT NULL COMMENT '差错记录ID',
    channel_code VARCHAR(32) NOT NULL COMMENT '渠道编码',
    task_type TINYINT NOT NULL COMMENT '任务类型:1-长款补登,2-短款冲正,3-金额调整',
    amount DECIMAL(18,2) NOT NULL COMMENT '金额',
    order_no VARCHAR(64) COMMENT '订单号',
    status TINYINT DEFAULT 0 COMMENT '状态:0-待处理,1-处理中,2-成功,3-失败',
    retry_count INT DEFAULT 0 COMMENT '重试次数',
    max_retry INT DEFAULT 3 COMMENT '最大重试次数',
    error_msg TEXT COMMENT '错误信息',
    handle_time DATETIME COMMENT '处理时间',
    operator VARCHAR(64) COMMENT '操作人',
    create_time DATETIME DEFAULT CURRENT_TIMESTAMP,
    update_time DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY uk_task_no (task_no),
    KEY idx_discrepancy_id (discrepancy_id),
    KEY idx_status (status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='自动冲正补账任务表';

CREATE TABLE IF NOT EXISTS channel_fee_config (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    channel_code VARCHAR(32) NOT NULL COMMENT '渠道编码',
    merchant_no VARCHAR(64) COMMENT '商户号',
    fee_type TINYINT NOT NULL COMMENT '费率类型:1-百分比,2-固定金额,3-阶梯费率',
    fee_rate DECIMAL(10,6) COMMENT '费率',
    fixed_fee DECIMAL(18,2) COMMENT '固定费用',
    min_fee DECIMAL(18,2) COMMENT '最低手续费',
    max_fee DECIMAL(18,2) COMMENT '最高手续费',
    start_amount DECIMAL(18,2) COMMENT '阶梯起始金额',
    end_amount DECIMAL(18,2) COMMENT '阶梯结束金额',
    status TINYINT DEFAULT 1 COMMENT '状态',
    effective_date DATETIME COMMENT '生效日期',
    expire_date DATETIME COMMENT '失效日期',
    create_time DATETIME DEFAULT CURRENT_TIMESTAMP,
    update_time DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    KEY idx_channel_merchant (channel_code, merchant_no),
    KEY idx_status (status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='渠道费率配置表';

CREATE TABLE IF NOT EXISTS transaction_fee (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    fee_no VARCHAR(64) NOT NULL COMMENT '手续费编号',
    channel_code VARCHAR(32) NOT NULL COMMENT '渠道编码',
    merchant_no VARCHAR(64) COMMENT '商户号',
    transaction_no VARCHAR(64) COMMENT '交易流水号',
    order_no VARCHAR(64) COMMENT '订单号',
    settlement_date DATE COMMENT '结算日期',
    trans_amount DECIMAL(18,2) NOT NULL COMMENT '交易金额',
    fee_amount DECIMAL(18,2) NOT NULL COMMENT '手续费金额',
    fee_rate DECIMAL(10,6) COMMENT '费率',
    fee_type TINYINT COMMENT '费率类型',
    status TINYINT DEFAULT 1 COMMENT '状态',
    remark TEXT COMMENT '备注',
    create_time DATETIME DEFAULT CURRENT_TIMESTAMP,
    update_time DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY uk_fee_no (fee_no),
    KEY idx_transaction_no (transaction_no),
    KEY idx_settlement_date (settlement_date),
    KEY idx_channel_code (channel_code)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='交易手续费表';

CREATE TABLE IF NOT EXISTS settlement_monitor (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    monitor_no VARCHAR(64) NOT NULL COMMENT '监控编号',
    channel_code VARCHAR(32) NOT NULL COMMENT '渠道编码',
    settlement_date DATE NOT NULL COMMENT '结算日期',
    status TINYINT DEFAULT 0 COMMENT '状态:0-待结算,1-结算中,2-已完成,3-已延迟,4-结算失败',
    expected_arrival_time DATETIME COMMENT '预计到账时间',
    actual_arrival_time DATETIME COMMENT '实际到账时间',
    expected_amount DECIMAL(18,2) COMMENT '预计结算金额',
    actual_amount DECIMAL(18,2) COMMENT '实际结算金额',
    delay_minutes BIGINT COMMENT '延迟分钟数',
    alert_level TINYINT DEFAULT 0 COMMENT '告警级别:0-无告警,1-警告,2-严重,3-紧急',
    alert_message TEXT COMMENT '告警信息',
    create_time DATETIME DEFAULT CURRENT_TIMESTAMP,
    update_time DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY uk_monitor_no (monitor_no),
    KEY idx_channel_settlement (channel_code, settlement_date),
    KEY idx_status (status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='结算监控表';

CREATE TABLE IF NOT EXISTS discrepancy_trend (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    trend_no VARCHAR(64) NOT NULL COMMENT '趋势编号',
    channel_code VARCHAR(32) NOT NULL COMMENT '渠道编码',
    statistics_date DATE NOT NULL COMMENT '统计日期',
    total_count INT DEFAULT 0 COMMENT '差异总笔数',
    total_amount DECIMAL(18,2) DEFAULT 0 COMMENT '差异总金额',
    long_count INT DEFAULT 0 COMMENT '长款笔数',
    long_amount DECIMAL(18,2) DEFAULT 0 COMMENT '长款金额',
    short_count INT DEFAULT 0 COMMENT '短款笔数',
    short_amount DECIMAL(18,2) DEFAULT 0 COMMENT '短款金额',
    amount_mismatch_count INT DEFAULT 0 COMMENT '金额不符笔数',
    amount_mismatch_amount DECIMAL(18,2) DEFAULT 0 COMMENT '金额不符金额',
    resolved_count INT DEFAULT 0 COMMENT '已解决笔数',
    resolved_amount DECIMAL(18,2) DEFAULT 0 COMMENT '已解决金额',
    create_time DATETIME DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY uk_trend_no (trend_no),
    UNIQUE KEY uk_date_channel (statistics_date, channel_code)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='对账差异趋势统计表';
