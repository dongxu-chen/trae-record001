package com.tracking.common.constant;

public class TrackingConstants {

    public static final String KAFKA_TOPIC_RAW_EVENTS = "tracking_raw_events";
    public static final String KAFKA_TOPIC_CLEANED_EVENTS = "tracking_cleaned_events";
    public static final String KAFKA_TOPIC_SESSION_EVENTS = "tracking_session_events";
    public static final String KAFKA_TOPIC_DEVICE_BINDING = "tracking_device_binding_events";
    public static final String KAFKA_CONSUMER_GROUP_FLINK = "tracking_flink_group";
    public static final String KAFKA_CONSUMER_GROUP_COLLECTOR = "tracking_collector_group";

    public static final String REDIS_KEY_USER_MAPPING = "tracking:user:mapping:";
    public static final String REDIS_KEY_SESSION = "tracking:session:";
    public static final String REDIS_KEY_DEVICE_ANONYMOUS = "tracking:device:anonymous:";
    public static final String REDIS_KEY_USER_DEVICES = "tracking:user:devices:";
    public static final String REDIS_KEY_DEVICE_USER = "tracking:device:user:";
    public static final String REDIS_KEY_MERGE_PENDING = "tracking:merge:pending:";
    public static final String REDIS_KEY_USER_SESSION_STATS = "tracking:user:session:stats:";
    public static final int REDIS_EXPIRE_HOURS = 24 * 7;
    public static final int REDIS_SESSION_EXPIRE_MINUTES = 30;
    public static final int REDIS_MERGE_EXPIRE_HOURS = 24 * 3;

    public static final long SESSION_TIMEOUT_MILLIS = 30 * 60 * 1000L;
    public static final long SESSION_TIMEOUT_MIN_MILLIS = 5 * 60 * 1000L;
    public static final long SESSION_TIMEOUT_MAX_MILLIS = 120 * 60 * 1000L;
    public static final long EVENT_MAX_DELAY_HOURS = 24;

    public static final String PLATFORM_WEB = "web";
    public static final String PLATFORM_MINIAPP = "miniapp";
    public static final String PLATFORM_ANDROID = "android";
    public static final String PLATFORM_IOS = "ios";
    public static final String PLATFORM_SERVER = "server";

    public static final String SOURCE_FRONTEND = "frontend";
    public static final String SOURCE_BACKEND = "backend";
    public static final String SOURCE_SDK = "sdk";

    public static final String EVENT_PAGE_VIEW = "page_view";
    public static final String EVENT_CLICK = "click";
    public static final String EVENT_LOGIN = "login";
    public static final String EVENT_LOGOUT = "logout";
    public static final String EVENT_REGISTER = "register";
    public static final String EVENT_PURCHASE = "purchase";
    public static final String EVENT_ADD_TO_CART = "add_to_cart";
    public static final String EVENT_SEARCH = "search";
    public static final String EVENT_SESSION_START = "session_start";
    public static final String EVENT_SESSION_END = "session_end";
    public static final String EVENT_DEVICE_BIND = "device_bind";
    public static final String EVENT_CROSS_DEVICE_DETECTED = "cross_device_detected";
    public static final String EVENT_MERGE_CONFIRMED = "merge_confirmed";
    public static final String EVENT_MERGE_REJECTED = "merge_rejected";

    public static final String PROP_LOGIN_TYPE = "login_type";
    public static final String PROP_ORDER_ID = "order_id";
    public static final String PROP_ORDER_AMOUNT = "order_amount";
    public static final String PROP_PRODUCT_ID = "product_id";
    public static final String PROP_SEARCH_KEYWORD = "search_keyword";
    public static final String PROP_DURATION = "duration";

    public static final String CLICKHOUSE_DB = "tracking";
    public static final String CLICKHOUSE_TABLE_EVENTS = "tracking_events";
    public static final String CLICKHOUSE_TABLE_SESSIONS = "tracking_sessions";
    public static final String CLICKHOUSE_TABLE_USER_MAPPING = "tracking_user_mapping";
    public static final String CLICKHOUSE_TABLE_DEVICE_BINDING = "tracking_device_binding";
    public static final String CLICKHOUSE_TABLE_MERGE_REQUEST = "tracking_merge_request";
    public static final String CLICKHOUSE_TABLE_USER_SESSION_STATS = "tracking_user_session_stats";

    public static final String FUNNEL_WINDOW_HOURLY = "hourly";
    public static final String FUNNEL_WINDOW_DAILY = "daily";
    public static final String FUNNEL_WINDOW_WEEKLY = "weekly";
    public static final String FUNNEL_WINDOW_CUSTOM = "custom";

    public static final int DEVICE_MERGE_THRESHOLD = 3;
    public static final int SESSION_STATS_MIN_SAMPLES = 10;

    public static final String CLICKHOUSE_TABLE_ANOMALY_DETECTION = "tracking_anomaly_detection";
    public static final String CLICKHOUSE_TABLE_USER_PATH = "tracking_user_path";
    public static final String CLICKHOUSE_TABLE_RETENTION = "tracking_retention";

    public static final String KAFKA_TOPIC_ANOMALY_ALERT = "tracking_anomaly_alerts";

    public static final String REDIS_KEY_EVENT_COUNT = "tracking:event:count:";
    public static final String REDIS_KEY_PATH_COUNT = "tracking:path:count:";
    public static final String REDIS_KEY_RETENTION_CACHE = "tracking:retention:cache:";

    public static final String ANOMALY_TYPE_SPIKE = "spike";
    public static final String ANOMALY_TYPE_DROP = "drop";
    public static final String ANOMALY_SEVERITY_LOW = "low";
    public static final String ANOMALY_SEVERITY_MEDIUM = "medium";
    public static final String ANOMALY_SEVERITY_HIGH = "high";
    public static final String ANOMALY_SEVERITY_CRITICAL = "critical";

    public static final double ANOMALY_THRESHOLD_LOW = 2.0;
    public static final double ANOMALY_THRESHOLD_MEDIUM = 3.0;
    public static final double ANOMALY_THRESHOLD_HIGH = 4.0;
    public static final double ANOMALY_THRESHOLD_CRITICAL = 5.0;

    public static final int ANOMALY_WINDOW_MINUTES = 5;
    public static final int ANOMALY_BASELINE_MINUTES = 60;
    public static final int ANOMALY_MIN_EVENTS = 10;

    public static final String PATH_NODE_PAGE_VIEW = "page_view";
    public static final String PATH_NODE_CLICK = "click";
    public static final String PATH_NODE_CONVERSION = "conversion";
    public static final int PATH_MAX_LENGTH = 10;
    public static final int PATH_TOP_N = 20;

    public static final String RETENTION_TYPE_CLASSIC = "classic";
    public static final String RETENTION_TYPE_CUSTOM = "custom";
    public static final String[] RETENTION_DEFAULT_DAYS = {1, 3, 7, 14, 30};
}
