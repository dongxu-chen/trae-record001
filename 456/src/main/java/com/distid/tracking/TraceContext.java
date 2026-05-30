package com.distid.tracking;

import lombok.Builder;
import lombok.Getter;

@Getter
@Builder
public class TraceContext {

    private final String traceId;
    private final String spanId;
    private final String bizTag;
    private final String requestPath;
    private final String source;
    private final String dcCode;

    public static TraceContext empty() {
        return TraceContext.builder()
                .traceId("")
                .spanId("")
                .bizTag("")
                .requestPath("")
                .source("")
                .dcCode("")
                .build();
    }

    public boolean hasTrace() {
        return traceId != null && !traceId.isEmpty();
    }
}
