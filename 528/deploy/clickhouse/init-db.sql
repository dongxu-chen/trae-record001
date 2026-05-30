CREATE TABLE IF NOT EXISTS nginx_metrics (
    dimension String,
    value String,
    window_start DateTime,
    window_end DateTime,
    total_requests UInt64,
    error_requests UInt64,
    error_rate Float64,
    qps Float64,
    avg_latency Float64,
    min_latency Float64,
    max_latency Float64,
    stddev_latency Float64,
    variance_latency Float64,
    p50_latency Float64,
    p95_latency Float64,
    p99_latency Float64,
    p999_latency Float64,
    error_rate_mean Float64,
    error_rate_stddev Float64,
    latency_mean Float64,
    latency_stddev Float64,
    qps_mean Float64,
    qps_stddev Float64,
    timestamp DateTime
) ENGINE = MergeTree()
ORDER BY (dimension, value, window_start)
PARTITION BY toDate(window_start)
TTL window_start + INTERVAL 30 DAY;

CREATE TABLE IF NOT EXISTS nginx_alerts (
    alert_type String,
    dimension String,
    value String,
    current_value Float64,
    threshold Float64,
    severity String,
    message String,
    timestamp DateTime
) ENGINE = MergeTree()
ORDER BY (timestamp, severity, alert_type)
PARTITION BY toDate(timestamp)
TTL timestamp + INTERVAL 7 DAY;

CREATE TABLE IF NOT EXISTS slow_requests (
    trace_id String,
    dimension String,
    value String,
    method String,
    path String,
    uri String,
    status Int32,
    request_time Float64,
    upstream_response_time Float64,
    self_process_time Float64,
    remote_addr String,
    host String,
    upstream_status String,
    is_upstream_slow UInt8,
    is_self_slow UInt8,
    slow_reason String,
    downstream_spans String,
    timestamp DateTime
) ENGINE = MergeTree()
ORDER BY (trace_id, timestamp)
PARTITION BY toDate(timestamp)
TTL timestamp + INTERVAL 7 DAY;

CREATE TABLE IF NOT EXISTS traffic_forecasts (
    dimension String,
    value String,
    current_qps Float64,
    predicted_qps Float64,
    predicted_qps_next Float64,
    predicted_qps_next2 Float64,
    confidence Float64,
    trend_slope Float64,
    trend_intercept Float64,
    trend_direction String,
    moving_avg5 Float64,
    moving_avg10 Float64,
    deviation_from_predicted Float64,
    window_start DateTime,
    window_end DateTime,
    timestamp DateTime
) ENGINE = MergeTree()
ORDER BY (dimension, value, window_start)
PARTITION BY toDate(window_start)
TTL window_start + INTERVAL 30 DAY;

CREATE TABLE IF NOT EXISTS custom_metrics (
    metric_name String,
    expression String,
    dimension String,
    value String,
    result Float64,
    variables String,
    timestamp DateTime
) ENGINE = MergeTree()
ORDER BY (metric_name, dimension, value, timestamp)
PARTITION BY toDate(timestamp)
TTL timestamp + INTERVAL 30 DAY;
