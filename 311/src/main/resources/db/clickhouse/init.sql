CREATE DATABASE IF NOT EXISTS coupon_db;

USE coupon_db;

CREATE TABLE IF NOT EXISTS coupon_distribution (
    distribution_id String COMMENT '发放记录ID',
    user_id String COMMENT '用户ID',
    coupon_id String COMMENT '优惠券ID',
    coupon_code String COMMENT '券码',
    denomination Decimal(10,2) COMMENT '面额',
    coupon_type Int32 COMMENT '券类型 1:满减 2:折扣 3:免邮 4:新人专享 5:品类券',
    scene_code Int32 COMMENT '场景 1:新人 2:复购 3:唤醒',
    min_order_amount Decimal(10,2) COMMENT '最低使用金额',
    status Int32 COMMENT '状态 0:已发放 1:已使用 2:已过期 3:已撤回',
    experiment_id String COMMENT '实验ID',
    group_id String COMMENT '实验组ID',
    rl_action_index Int32 COMMENT 'RL动作索引',
    rl_reward Float64 COMMENT 'RL奖励',
    state_vector String COMMENT '状态向量JSON',
    issue_time DateTime COMMENT '发放时间',
    expire_time DateTime COMMENT '过期时间',
    use_time DateTime COMMENT '使用时间',
    order_id String COMMENT '订单ID',
    order_amount Decimal(10,2) COMMENT '订单金额',
    discount_amount Decimal(10,2) COMMENT '优惠金额',
    create_time DateTime DEFAULT now() COMMENT '创建时间',
    update_time DateTime DEFAULT now() COMMENT '更新时间'
) ENGINE = MergeTree()
PARTITION BY toYYYYMM(issue_time)
ORDER BY (experiment_id, group_id, issue_time, user_id)
TTL issue_time + INTERVAL 1 YEAR
SETTINGS index_granularity = 8192;

CREATE TABLE IF NOT EXISTS coupon_actions (
    action_id Int32 COMMENT '动作索引',
    coupon_type Int32 COMMENT '券类型',
    denomination Decimal(10,2) COMMENT '面额',
    min_order_amount Decimal(10,2) COMMENT '最低使用金额',
    valid_days Int32 COMMENT '有效天数',
    description String COMMENT '描述',
    create_time DateTime DEFAULT now()
) ENGINE = ReplacingMergeTree()
ORDER BY action_id
SETTINGS index_granularity = 8192;

CREATE TABLE IF NOT EXISTS user_profile_log (
    user_id String COMMENT '用户ID',
    consumption_frequency Float64 COMMENT '消费频次',
    avg_order_value Float64 COMMENT '客单价',
    activity_score Float64 COMMENT '活跃度',
    total_spend Float64 COMMENT '总消费',
    order_count_30d Int32 COMMENT '30天订单数',
    days_since_last_order Int32 COMMENT '距上次订单天数',
    coupon_usage_rate Float64 COMMENT '券使用率',
    avg_discount_sensitivity Float64 COMMENT '折扣敏感度',
    is_new_user UInt8 COMMENT '是否新用户',
    user_level Int32 COMMENT '用户等级',
    state_vector Array(Float64) COMMENT '状态向量',
    log_time DateTime DEFAULT now() COMMENT '日志时间'
) ENGINE = MergeTree()
PARTITION BY toYYYYMM(log_time)
ORDER BY (user_id, log_time)
TTL log_time + INTERVAL 1 YEAR
SETTINGS index_granularity = 8192;

CREATE TABLE IF NOT EXISTS abtest_events (
    event_id String COMMENT '事件ID',
    event_type String COMMENT '事件类型 exposure/conversion/coupon_issue/coupon_use',
    user_id String COMMENT '用户ID',
    experiment_id String COMMENT '实验ID',
    group_id String COMMENT '实验组ID',
    action String COMMENT '动作',
    scene String COMMENT '场景',
    source String COMMENT '来源',
    properties String COMMENT '属性JSON',
    event_time DateTime COMMENT '事件时间',
    create_time DateTime DEFAULT now()
) ENGINE = MergeTree()
PARTITION BY toYYYYMM(event_time)
ORDER BY (experiment_id, group_id, event_time, user_id)
TTL event_time + INTERVAL 1 YEAR
SETTINGS index_granularity = 8192;

CREATE MATERIALIZED VIEW IF NOT EXISTS mv_coupon_stats_daily
ENGINE = SummingMergeTree()
PARTITION BY toYYYYMM(stat_date)
ORDER BY (stat_date, experiment_id, group_id, coupon_type, scene_code)
AS SELECT
    toDate(issue_time) AS stat_date,
    experiment_id,
    group_id,
    coupon_type,
    scene_code,
    count() AS issue_count,
    countIf(status = 1) AS used_count,
    countIf(status = 2) AS expired_count,
    sum(denomination) AS total_denomination,
    sumIf(discount_amount, status = 1) AS total_discount,
    sumIf(order_amount, status = 1) AS total_order_amount
FROM coupon_distribution
GROUP BY stat_date, experiment_id, group_id, coupon_type, scene_code;

INSERT INTO coupon_actions (action_id, coupon_type, denomination, min_order_amount, valid_days, description) VALUES
(0, 1, 5, 15, 7, '满15减5满减券'),
(1, 1, 10, 30, 7, '满30减10满减券'),
(2, 1, 20, 60, 7, '满60减20满减券'),
(3, 1, 50, 150, 7, '满150减50满减券'),
(4, 2, 5, 30, 7, '满30享95折折扣券'),
(5, 2, 10, 30, 7, '满30享9折折扣券'),
(6, 2, 20, 60, 7, '满60享8折折扣券'),
(7, 2, 50, 150, 7, '满150享5折折扣券'),
(8, 3, 5, 0, 7, '免邮券'),
(9, 3, 10, 0, 7, '高额免邮券'),
(10, 4, 10, 0, 7, '新人专享10元券'),
(11, 4, 20, 0, 7, '新人专享20元券');
