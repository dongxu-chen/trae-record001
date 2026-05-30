package com.tracing.staining.analysis;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.io.Serializable;
import java.time.LocalDateTime;
import java.util.Map;

@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class StainingRecord implements Serializable {

    private static final long serialVersionUID = 1L;

    private String traceId;

    private String spanId;

    private String parentSpanId;

    private String stainingColor;

    private String userId;

    private String bizType;

    private String bizTag;

    private String bizTagVersion;

    private Map<String, String> bizTags;

    private String requestUri;

    private String requestMethod;

    private Integer httpStatus;

    private Long durationMs;

    private String cloudProvider;

    private String cloudRegion;

    private String cloudAZ;

    private String cloudAccountId;

    private String cloudServiceName;

    private String originTraceId;

    private String crossCloudTraceId;

    private String requestId;

    private LocalDateTime requestTime;

    private LocalDateTime responseTime;

    private String errorMessage;

    private Map<String, String> extraAttributes;

    public boolean isCrossCloud() {
        return crossCloudTraceId != null && !crossCloudTraceId.isEmpty();
    }

    public String getUniqueKey() {
        return stainingColor + "|" + userId + "|" + bizType + "|" + bizTag;
    }
}
