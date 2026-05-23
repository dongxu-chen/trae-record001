-- ============================================
-- ClickHouse 日志表建表脚本
-- ============================================

-- 创建数据库
CREATE DATABASE IF NOT EXISTS logs_db
    COMMENT '日志数据库'
    ENGINE = Atomic;

USE logs_db;

-- ============================================
-- 应用日志表 (MergeTree引擎)
-- ============================================
CREATE TABLE IF NOT EXISTS application_logs
(
    `timestamp`          DateTime64(3) COMMENT '日志时间戳',
    `dt`                 Date MATERIALIZED toDate(timestamp) COMMENT '日期分区字段',
    `level`              LowCardinality(String) COMMENT '日志级别: DEBUG/INFO/WARN/ERROR',
    `service`            LowCardinality(String) COMMENT '服务名称',
    `host`               String COMMENT '主机名/IP',
    `trace_id`           String COMMENT '链路追踪ID',
    `message`            String COMMENT '日志消息摘要',
    `body`               String COMMENT '完整日志内容',
    `topic`              String COMMENT 'Kafka主题',
    `partition`          Int32 COMMENT 'Kafka分区',
    `offset`             Int64 COMMENT 'Kafka偏移量',
    `parse_status`       LowCardinality(String) COMMENT '解析状态',
    `collect_timestamp`  DateTime64(3) COMMENT '采集时间戳',
    `hostname`           String COMMENT '采集器主机名',
    `agent_id`           String COMMENT '采集器ID',
    `kafka_topic`        String COMMENT 'Kafka主题(注入)',
    `kafka_partition`    Int32 COMMENT 'Kafka分区(注入)',
    `kafka_offset`       Int64 COMMENT 'Kafka偏移量(注入)',
    `collector_ip`       String COMMENT '采集器IP',
    `sampled`            String COMMENT '是否采样',
    `sample_rate`        Float64 COMMENT '采样率',
    `ingest_time`        DateTime64(3) DEFAULT now64() COMMENT '入库时间'
)
ENGINE = MergeTree
PARTITION BY toYYYYMM(dt)
ORDER BY (service, level, timestamp)
TTL dt + INTERVAL 90 DAY
SETTINGS index_granularity = 8192,
         ttl_only_drop_parts = 1;

-- ============================================
-- 死信队列表
-- ============================================
CREATE TABLE IF NOT EXISTS dlq_logs
(
    `timestamp`      DateTime64(3) COMMENT '原始日志时间',
    `dlq_timestamp`  DateTime64(3) DEFAULT now64() COMMENT '进入DLQ时间',
    `dlq_reason`     String COMMENT '失败原因',
    `dlq_sink`       LowCardinality(String) COMMENT '失败的Sink类型',
    `topic`          String COMMENT 'Kafka主题',
    `partition`      Int32 COMMENT 'Kafka分区',
    `offset`         Int64 COMMENT 'Kafka偏移量',
    `body`           String COMMENT '完整日志内容'
)
ENGINE = MergeTree
PARTITION BY toYYYYMM(toDate(dlq_timestamp))
ORDER BY (dlq_sink, dlq_timestamp)
TTL toDate(dlq_timestamp) + INTERVAL 180 DAY;

-- ============================================
-- 日志统计物化视图
-- ============================================
CREATE MATERIALIZED VIEW IF NOT EXISTS logs_stats_mv
ENGINE = SummingMergeTree
PARTITION BY toYYYYMM(dt)
ORDER BY (dt, service, level)
AS
SELECT
    dt,
    service,
    level,
    count() as count
FROM application_logs
GROUP BY dt, service, level;

-- ============================================
-- 端到端延迟统计表
-- ============================================
CREATE TABLE IF NOT EXISTS latency_stats
(
    `dt`             Date COMMENT '统计日期',
    `service`        LowCardinality(String) COMMENT '服务名称',
    `level`          LowCardinality(String) COMMENT '日志级别',
    `bucket`         LowCardinality(String) COMMENT '延迟桶: <10ms, 10-50ms, etc',
    `count`          UInt64 COMMENT '数量',
    `total_latency`  UInt64 COMMENT '总延迟(ms)',
    `min_latency`    UInt32 COMMENT '最小延迟(ms)',
    `max_latency`    UInt32 COMMENT '最大延迟(ms)'
)
ENGINE = SummingMergeTree(count, total_latency)
PARTITION BY toYYYYMM(dt)
ORDER BY (dt, service, level, bucket);

-- ============================================
-- 端到端延迟物化视图
-- ============================================
CREATE MATERIALIZED VIEW IF NOT EXISTS latency_stats_mv
TO latency_stats
AS
SELECT
    toDate(timestamp) as dt,
    service,
    level,
    multiIf(
        ingest_time - timestamp < 0.010, '<10ms',
        ingest_time - timestamp < 0.050, '10-50ms',
        ingest_time - timestamp < 0.100, '50-100ms',
        ingest_time - timestamp < 0.500, '100-500ms',
        ingest_time - timestamp < 1.000, '500ms-1s',
        ingest_time - timestamp < 5.000, '1-5s',
        ingest_time - timestamp < 10.000, '5-10s',
        ingest_time - timestamp < 30.000, '10-30s',
        ingest_time - timestamp < 60.000, '30-60s',
        '>60s'
    ) as bucket,
    count() as count,
    toUInt64(sum(ingest_time - timestamp) * 1000) as total_latency,
    toUInt32(min(ingest_time - timestamp) * 1000) as min_latency,
    toUInt32(max(ingest_time - timestamp) * 1000) as max_latency
FROM application_logs
WHERE ingest_time > timestamp
GROUP BY dt, service, level, bucket;

-- ============================================
-- 示例查询
-- ============================================

-- 查询最近1小时错误日志
SELECT
    timestamp,
    service,
    level,
    message,
    trace_id
FROM application_logs
WHERE level = 'ERROR'
  AND timestamp >= now() - INTERVAL 1 HOUR
ORDER BY timestamp DESC
LIMIT 100;

-- 按服务统计日志量
SELECT
    service,
    level,
    count() as cnt
FROM application_logs
WHERE timestamp >= today()
GROUP BY service, level
ORDER BY cnt DESC;
