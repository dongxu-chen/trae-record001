package com.ratelimit.center.common;

public interface RateLimitConstants {

    String RULE_TYPE_FLOW = "flow";
    String RULE_TYPE_DEGRADE = "degrade";
    String RULE_TYPE_PARAM_FLOW = "param_flow";
    String RULE_TYPE_SYSTEM = "system";
    String RULE_TYPE_AUTHORITY = "authority";

    int GRADE_QPS = 1;
    int GRADE_THREAD_COUNT = 0;

    int STRATEGY_DIRECT = 0;
    int STRATEGY_RELATE = 1;
    int STRATEGY_CHAIN = 2;

    int CONTROL_BEHAVIOR_DEFAULT = 0;
    int CONTROL_BEHAVIOR_WARM_UP = 1;
    int CONTROL_BEHAVIOR_RATE_LIMITER = 2;
    int CONTROL_BEHAVIOR_WARM_UP_RATE_LIMITER = 3;

    int DEGRADE_GRADE_RT = 0;
    int DEGRADE_GRADE_EXCEPTION_RATIO = 1;
    int DEGRADE_GRADE_EXCEPTION_COUNT = 2;

    int STATUS_ENABLE = 1;
    int STATUS_DISABLE = 0;

    String REDIS_KEY_PREFIX = "sentinel:";
    String REDIS_FLOW_RULES_KEY = REDIS_KEY_PREFIX + "flow:rules";
    String REDIS_DEGRADE_RULES_KEY = REDIS_KEY_PREFIX + "degrade:rules";
    String REDIS_PARAM_FLOW_RULES_KEY = REDIS_KEY_PREFIX + "param:flow:rules";
    String REDIS_SYSTEM_RULES_KEY = REDIS_KEY_PREFIX + "system:rules";
    String REDIS_FLOW_CHANNEL = REDIS_KEY_PREFIX + "flow:channel";
    String REDIS_DEGRADE_CHANNEL = REDIS_KEY_PREFIX + "degrade:channel";
    String REDIS_PARAM_FLOW_CHANNEL = REDIS_KEY_PREFIX + "param:flow:channel";
    String REDIS_SYSTEM_CHANNEL = REDIS_KEY_PREFIX + "system:channel";
    String REDIS_CLUSTER_STATE_KEY = REDIS_KEY_PREFIX + "cluster:state";
    String REDIS_LOG_QUEUE_KEY = REDIS_KEY_PREFIX + "log:queue";

    String METRIC_PASS_COUNT = "sentinel_pass_total";
    String METRIC_BLOCK_COUNT = "sentinel_block_total";
    String METRIC_EXCEPTION_COUNT = "sentinel_exception_total";
    String METRIC_RT = "sentinel_rt_seconds";

    // 集群数据中心常量
    String REDIS_CLUSTER_DC_KEY = REDIS_KEY_PREFIX + "cluster:dc";
    String REDIS_CLUSTER_DC_QUOTA_KEY = REDIS_KEY_PREFIX + "cluster:dc:quota";
    String REDIS_CLUSTER_DC_USAGE_KEY = REDIS_KEY_PREFIX + "cluster:dc:usage";
    String DEFAULT_DC = "default";
    int CLUSTER_QUOTA_BORROW_PERCENT = 30;

    // 预热曲线类型
    int WARM_UP_CURVE_LINEAR = 0;
    int WARM_UP_CURVE_EXPONENTIAL = 1;

    // 预聚合常量
    String REDIS_METRIC_AGGREGATE_MINUTE = REDIS_KEY_PREFIX + "metric:minute";
    String REDIS_METRIC_AGGREGATE_HOUR = REDIS_KEY_PREFIX + "metric:hour";
    int AGGREGATE_WINDOW_MINUTE = 60;
    int AGGREGATE_WINDOW_HOUR = 3600;
}
