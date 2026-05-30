package com.loganalytics.model;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.io.Serializable;

@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class TraceSpan implements Serializable {
    private String spanId;
    private String serviceName;
    private String operation;
    private double duration;
    private String status;
    private long startOffset;
    private long endOffset;

    public static TraceSpan fromUpstream(String upstreamStatus, double upstreamResponseTime) {
        return TraceSpan.builder()
                .spanId("upstream-0")
                .serviceName("upstream")
                .operation("proxy_pass")
                .duration(upstreamResponseTime)
                .status(upstreamStatus != null && !upstreamStatus.isEmpty() ? upstreamStatus : "-")
                .startOffset(0)
                .endOffset((long) (upstreamResponseTime * 1000))
                .build();
    }

    public static TraceSpan fromSelfProcess(double selfProcessTime) {
        return TraceSpan.builder()
                .spanId("self-0")
                .serviceName("nginx")
                .operation("internal_processing")
                .duration(selfProcessTime)
                .status("200")
                .startOffset(0)
                .endOffset((long) (selfProcessTime * 1000))
                .build();
    }
}
