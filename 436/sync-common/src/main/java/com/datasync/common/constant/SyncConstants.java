package com.datasync.common.constant;

public class SyncConstants {
    private SyncConstants() {
    }

    public static final String KAFKA_TOPIC_PREFIX = "datasync_";

    public static final String KAFKA_CONSUMER_GROUP_PREFIX = "datsync-group-";

    public static final String ZK_ROOT_PATH = "/datasync";

    public static final String ZK_NODES_PATH = ZK_ROOT_PATH + "/nodes";

    public static final String ZK_LEADER_PATH = ZK_ROOT_PATH + "/leader";

    public static final String ZK_CONFIG_PATH = ZK_ROOT_PATH + "/config";

    public static final String ZK_TOPOLOGY_PATH = ZK_ROOT_PATH + "/topology";

    public static final String ZK_HEARTBEAT_PATH = ZK_ROOT_PATH + "/heartbeat";

    public static final int HEARTBEAT_INTERVAL_MS = 5000;

    public static final int SESSION_TIMEOUT_MS = 30000;

    public static final int MAX_RETRY_COUNT = 3;

    public static final long RETRY_INTERVAL_MS = 1000;

    public static final long DEFAULT_CONFLICT_WINDOW_MS = 60000;

    public static final int DEFAULT_BATCH_SIZE = 100;

    public static final long DEFAULT_POLL_TIMEOUT_MS = 1000;

    public static final String COLUMN_TIMESTAMP = "update_time";

    public static final String COLUMN_VERSION = "version";

    public static final String COLUMN_BUSINESS_KEY = "business_key";

    public static final String DEFAULT_DATACENTER_ID = "dc-default";

    public static final String ENV_DATACENTER_ID = "DATACENTER_ID";

    public static final String METRIC_SYNC_LATENCY = "sync_latency_ms";

    public static final String METRIC_SYNC_COUNT = "sync_count";

    public static final String METRIC_CONFLICT_COUNT = "conflict_count";

    public static final String METRIC_ERROR_COUNT = "error_count";
}
