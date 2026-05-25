CREATE DATABASE IF NOT EXISTS tracking;

USE tracking;

CREATE TABLE IF NOT EXISTS tracking_events (
    id String,
    event String,
    timestamp UInt64,
    receive_time UInt64,
    anonymous_id String,
    user_id String,
    session_id String,
    platform String,
    app_id String,
    app_version String,
    channel String,
    os String,
    os_version String,
    device_id String,
    device_model String,
    ip String,
    user_agent String,
    referrer String,
    url String,
    title String,
    screen_width Int32,
    screen_height Int32,
    network_type String,
    carrier String,
    properties String,
    source String,
    country String,
    province String,
    city String,
    event_date Date MATERIALIZED toDate(timestamp / 1000)
) ENGINE = MergeTree()
PARTITION BY toYYYYMM(event_date)
ORDER BY (timestamp, user_id, session_id)
SETTINGS index_granularity = 8192;

CREATE TABLE IF NOT EXISTS tracking_sessions (
    session_id String,
    anonymous_id String,
    user_id String,
    device_id String,
    start_time UInt64,
    end_time UInt64,
    duration UInt64,
    event_count Int32,
    first_page String,
    last_page String,
    entry_source String,
    session_date Date MATERIALIZED toDate(start_time / 1000)
) ENGINE = MergeTree()
PARTITION BY toYYYYMM(session_date)
ORDER BY (start_time, user_id, session_id)
SETTINGS index_granularity = 8192;

CREATE TABLE IF NOT EXISTS tracking_user_mapping (
    anonymous_id String,
    user_id String,
    device_id String,
    create_time UInt64,
    update_time UInt64,
    mapping_date Date MATERIALIZED toDate(create_time / 1000)
) ENGINE = ReplacingMergeTree(update_time)
PARTITION BY toYYYYMM(mapping_date)
ORDER BY (anonymous_id, user_id)
SETTINGS index_granularity = 8192;

CREATE TABLE IF NOT EXISTS tracking_event_summary (
    event_date Date,
    event String,
    platform String,
    app_id String,
    pv UInt64,
    uv UInt64,
    sv UInt64
) ENGINE = SummingMergeTree((pv, uv, sv))
PARTITION BY toYYYYMM(event_date)
ORDER BY (event_date, event, platform, app_id)
SETTINGS index_granularity = 8192;

CREATE MATERIALIZED VIEW IF NOT EXISTS tracking_event_summary_mv
TO tracking_event_summary
AS SELECT
    event_date,
    event,
    platform,
    app_id,
    count() AS pv,
    uniqExact(user_id) AS uv,
    uniqExact(session_id) AS sv
FROM tracking_events
GROUP BY event_date, event, platform, app_id;

CREATE TABLE IF NOT EXISTS tracking_device_binding (
    id String,
    user_id String,
    device_id String,
    anonymous_id String,
    platform String,
    device_model String,
    os String,
    os_version String,
    app_id String,
    app_version String,
    bind_time UInt64,
    last_active_time UInt64,
    event_count UInt32,
    status String,
    source String,
    ip String,
    country String,
    province String,
    city String,
    bind_date Date MATERIALIZED toDate(bind_time / 1000)
) ENGINE = MergeTree()
PARTITION BY toYYYYMM(bind_date)
ORDER BY (bind_time, user_id, device_id)
SETTINGS index_granularity = 8192;

CREATE TABLE IF NOT EXISTS tracking_merge_request (
    request_id String,
    target_user_id String,
    source_user_ids Array(String),
    device_ids Array(String),
    reason String,
    confidence Float64,
    evidence String,
    status String,
    reviewed_by String,
    reviewed_time UInt64,
    review_comment String,
    create_time UInt64,
    expire_time UInt64,
    source String,
    create_date Date MATERIALIZED toDate(create_time / 1000)
) ENGINE = MergeTree()
PARTITION BY toYYYYMM(create_date)
ORDER BY (create_time, request_id, target_user_id)
SETTINGS index_granularity = 8192;

CREATE TABLE IF NOT EXISTS tracking_user_session_stats (
    user_id String,
    anonymous_id String,
    total_sessions UInt32,
    avg_session_interval UInt64,
    median_session_interval UInt64,
    p75_session_interval UInt64,
    p90_session_interval UInt64,
    p95_session_interval UInt64,
    min_session_interval UInt64,
    max_session_interval UInt64,
    dynamic_session_timeout UInt64,
    sample_size UInt32,
    last_update_time UInt64,
    platform String,
    app_id String,
    update_date Date MATERIALIZED toDate(last_update_time / 1000)
) ENGINE = ReplacingMergeTree(last_update_time)
PARTITION BY toYYYYMM(update_date)
ORDER BY (user_id, anonymous_id, platform, app_id)
SETTINGS index_granularity = 8192;

ALTER TABLE tracking_events ADD COLUMN IF NOT EXISTS session_dynamic_timeout UInt64 AFTER session_id;
ALTER TABLE tracking_events ADD COLUMN IF NOT EXISTS session_timeout_minutes UInt32 AFTER session_dynamic_timeout;

ALTER TABLE tracking_sessions ADD COLUMN IF NOT EXISTS dynamic_timeout UInt64 AFTER duration;
ALTER TABLE tracking_sessions ADD COLUMN IF NOT EXISTS timeout_minutes UInt32 AFTER dynamic_timeout;

CREATE TABLE IF NOT EXISTS tracking_anomaly_detection (
    alert_id String,
    anomaly_type String,
    severity String,
    metric_name String,
    dimension String,
    dimension_value String,
    current_value Float64,
    baseline_value Float64,
    deviation_percent Float64,
    z_score Float64,
    window_start_time UInt64,
    window_end_time UInt64,
    detection_time UInt64,
    description String,
    details String,
    status String,
    acknowledged_by String,
    acknowledged_time UInt64,
    comment String,
    detection_date Date MATERIALIZED toDate(detection_time / 1000)
) ENGINE = MergeTree()
PARTITION BY toYYYYMM(detection_date)
ORDER BY (detection_date, severity, alert_id)
SETTINGS index_granularity = 8192;

CREATE TABLE IF NOT EXISTS tracking_user_path (
    path_id String,
    session_id String,
    user_id String,
    platform String,
    app_id String,
    path_events Array(String),
    path_urls Array(String),
    path_length UInt32,
    event_count UInt32,
    start_time UInt64,
    end_time UInt64,
    start_date Date MATERIALIZED toDate(start_time / 1000)
) ENGINE = MergeTree()
PARTITION BY toYYYYMM(start_date)
ORDER BY (start_date, platform, app_id, path_length)
SETTINGS index_granularity = 8192;

CREATE TABLE IF NOT EXISTS tracking_retention (
    retention_id String,
    retention_type String,
    initial_event String,
    return_event String,
    platform String,
    app_id String,
    channel String,
    cohort_date Date,
    retention_day UInt32,
    initial_users UInt64,
    return_users UInt64,
    retention_rate Float64,
    group_value String,
    calculate_time UInt64,
    calculate_date Date MATERIALIZED toDate(calculate_time / 1000)
) ENGINE = MergeTree()
PARTITION BY toYYYYMM(calculate_date)
ORDER BY (calculate_date, retention_type, initial_event, return_event, cohort_date)
SETTINGS index_granularity = 8192;

CREATE TABLE IF NOT EXISTS tracking_retention_cohort (
    cohort_date Date,
    user_id String,
    initial_event_time UInt64,
    platform String,
    app_id String,
    channel String,
    return_events Array(Tuple(String, UInt64)),
    create_time UInt64,
    create_date Date MATERIALIZED toDate(create_time / 1000)
) ENGINE = MergeTree()
PARTITION BY toYYYYMM(create_date)
ORDER BY (cohort_date, platform, app_id, user_id)
SETTINGS index_granularity = 8192;
