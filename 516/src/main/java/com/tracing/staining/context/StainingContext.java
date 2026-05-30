package com.tracing.staining.context;

import com.tracing.staining.constant.TraceConstant;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.io.Serializable;
import java.util.HashMap;
import java.util.Map;

@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class StainingContext implements Serializable {

    private static final long serialVersionUID = 1L;

    private String traceId;

    private String spanId;

    private String parentSpanId;

    private Boolean stainingFlag;

    private String stainingColor;

    private String userId;

    private String bizType;

    private String bizTag;

    private String bizTagVersion;

    private Boolean sampled;

    private String requestId;

    private Long timestamp;

    private String cloudProvider;

    private String cloudRegion;

    private String cloudAZ;

    private String cloudAccountId;

    private String cloudServiceName;

    private String originTraceId;

    private String crossCloudTraceId;

    @Builder.Default
    private Map<String, String> bizTags = new HashMap<>();

    @Builder.Default
    private Map<String, String> extraAttributes = new HashMap<>();

    public void addExtraAttribute(String key, String value) {
        if (this.extraAttributes == null) {
            this.extraAttributes = new HashMap<>();
        }
        this.extraAttributes.put(key, value);
    }

    public String getExtraAttribute(String key) {
        return this.extraAttributes != null ? this.extraAttributes.get(key) : null;
    }

    public void addBizTag(String key, String value) {
        if (this.bizTags == null) {
            this.bizTags = new HashMap<>();
        }
        this.bizTags.put(key, value);
    }

    public String getBizTag(String key) {
        return this.bizTags != null ? this.bizTags.get(key) : null;
    }

    public void setCloudInfo(String provider, String region, String az,
                            String accountId, String serviceName) {
        this.cloudProvider = provider;
        this.cloudRegion = region;
        this.cloudAZ = az;
        this.cloudAccountId = accountId;
        this.cloudServiceName = serviceName;
    }

    public Map<String, String> toHeadersMap() {
        Map<String, String> headers = new HashMap<>();
        if (traceId != null) {
            headers.put("traceId", traceId);
        }
        if (spanId != null) {
            headers.put("spanId", spanId);
        }
        if (parentSpanId != null) {
            headers.put("parentSpanId", parentSpanId);
        }
        if (stainingFlag != null) {
            headers.put("X-Staining-Flag", stainingFlag.toString());
        }
        if (stainingColor != null) {
            headers.put("X-Staining-Color", stainingColor);
        }
        if (userId != null) {
            headers.put("X-Staining-User-Id", userId);
        }
        if (bizType != null) {
            headers.put("X-Staining-Biz-Type", bizType);
        }
        if (bizTag != null) {
            headers.put(TraceConstant.STAINING_BIZ_TAG, bizTag);
        }
        if (bizTagVersion != null) {
            headers.put(TraceConstant.STAINING_BIZ_TAG_VERSION, bizTagVersion);
        }
        if (sampled != null) {
            headers.put("X-Sampled", sampled.toString());
        }
        if (requestId != null) {
            headers.put("X-Request-Id", requestId);
        }
        if (cloudProvider != null) {
            headers.put(TraceConstant.CLOUD_PROVIDER, cloudProvider);
        }
        if (cloudRegion != null) {
            headers.put(TraceConstant.CLOUD_REGION, cloudRegion);
        }
        if (cloudAZ != null) {
            headers.put(TraceConstant.CLOUD_AVAILABILITY_ZONE, cloudAZ);
        }
        if (cloudAccountId != null) {
            headers.put(TraceConstant.CLOUD_ACCOUNT_ID, cloudAccountId);
        }
        if (cloudServiceName != null) {
            headers.put(TraceConstant.CLOUD_SERVICE_NAME, cloudServiceName);
        }
        if (originTraceId != null) {
            headers.put(TraceConstant.ORIGIN_TRACE_ID, originTraceId);
        }
        if (crossCloudTraceId != null) {
            headers.put(TraceConstant.CROSS_CLOUD_TRACE_ID, crossCloudTraceId);
        }
        if (bizTags != null && !bizTags.isEmpty()) {
            headers.putAll(bizTags);
        }
        if (extraAttributes != null) {
            headers.putAll(extraAttributes);
        }
        return headers;
    }

    public Map<String, Object> toAnalysisMap() {
        Map<String, Object> analysis = new HashMap<>();
        analysis.put("traceId", traceId);
        analysis.put("spanId", spanId);
        analysis.put("parentSpanId", parentSpanId);
        analysis.put("stainingFlag", stainingFlag);
        analysis.put("stainingColor", stainingColor);
        analysis.put("userId", userId);
        analysis.put("bizType", bizType);
        analysis.put("bizTag", bizTag);
        analysis.put("bizTagVersion", bizTagVersion);
        analysis.put("bizTags", bizTags);
        analysis.put("timestamp", timestamp);
        analysis.put("cloudProvider", cloudProvider);
        analysis.put("cloudRegion", cloudRegion);
        analysis.put("cloudAZ", cloudAZ);
        analysis.put("cloudAccountId", cloudAccountId);
        analysis.put("cloudServiceName", cloudServiceName);
        analysis.put("originTraceId", originTraceId);
        analysis.put("crossCloudTraceId", crossCloudTraceId);
        analysis.put("sampled", sampled);
        analysis.put("requestId", requestId);
        return analysis;
    }
}
