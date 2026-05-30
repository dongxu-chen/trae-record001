package com.tracing.staining.constant;

public class TraceConstant {

    public static final String TRACE_ID = "traceId";

    public static final String SPAN_ID = "spanId";

    public static final String PARENT_SPAN_ID = "parentSpanId";

    public static final String STAINING_FLAG = "X-Staining-Flag";

    public static final String STAINING_COLOR = "X-Staining-Color";

    public static final String STAINING_USER_ID = "X-Staining-User-Id";

    public static final String STAINING_BIZ_TYPE = "X-Staining-Biz-Type";

    public static final String STAINING_BIZ_TAG = "X-Staining-Biz-Tag";

    public static final String STAINING_BIZ_TAG_VERSION = "X-Staining-Biz-Tag-Version";

    public static final String SAMPLED = "X-Sampled";

    public static final String REQUEST_ID = "X-Request-Id";

    public static final String STAINING_CONTEXT_KEY = "staining-context";

    public static final String CLOUD_PROVIDER = "X-Cloud-Provider";

    public static final String CLOUD_REGION = "X-Cloud-Region";

    public static final String CLOUD_AVAILABILITY_ZONE = "X-Cloud-AZ";

    public static final String CLOUD_ACCOUNT_ID = "X-Cloud-Account-Id";

    public static final String CLOUD_SERVICE_NAME = "X-Cloud-Service-Name";

    public static final String ORIGIN_TRACE_ID = "X-Origin-Trace-Id";

    public static final String CROSS_CLOUD_TRACE_ID = "X-Cross-Cloud-Trace-Id";

    private TraceConstant() {
    }
}
