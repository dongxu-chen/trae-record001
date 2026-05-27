package com.security.replayguard.model;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.util.Map;

@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class RequestFeature {

    private String requestPath;

    private String method;

    private Map<String, String> queryParams;

    private String bodyHash;

    private String timestamp;

    private String nonce;

    private String deviceFingerprint;

    private String ipAddress;

    private String userAgent;

    private String userId;
}
