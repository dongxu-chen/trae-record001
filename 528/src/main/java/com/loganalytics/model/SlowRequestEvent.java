package com.loganalytics.model;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.io.Serializable;
import java.util.List;

@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class SlowRequestEvent implements Serializable {
    private String traceId;
    private String dimension;
    private String value;
    private String method;
    private String path;
    private String uri;
    private int status;
    private double requestTime;
    private double upstreamResponseTime;
    private double selfProcessTime;
    private String remoteAddr;
    private String host;
    private String upstreamStatus;
    private List<TraceSpan> downstreamSpans;
    private boolean isUpstreamSlow;
    private boolean isSelfSlow;
    private String slowReason;
    private long timestamp;

    public enum SlowReason {
        SELF_SLOW,
        UPSTREAM_SLOW,
        BOTH_SLOW,
        UNKNOWN
    }
}
