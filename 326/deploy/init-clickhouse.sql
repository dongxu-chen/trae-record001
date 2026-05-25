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

SELECT 'Tables created successfully!' AS status;
