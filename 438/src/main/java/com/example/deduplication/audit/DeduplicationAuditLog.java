package com.example.deduplication.audit;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.io.Serializable;
import java.util.Map;

@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class DeduplicationAuditLog implements Serializable {

    private static final long serialVersionUID = 1L;

    private String auditId;
    private String requestHash;
    private String requestFingerprint;
    private long timestamp;
    private String userId;
    private String clientIp;
    private String method;
    private String path;
    private Map<String, String> requestHeaders;
    private String requestBody;
    private String responseBody;
    private int responseStatus;
    private boolean isDuplicate;
    private String source;
    private String matchedPattern;
    private long processingTimeMs;
    private Map<String, Object> additionalInfo;
}
