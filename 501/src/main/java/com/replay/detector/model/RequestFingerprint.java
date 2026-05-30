package com.replay.detector.model;

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
public class RequestFingerprint implements Serializable {

    private static final long serialVersionUID = 1L;

    private String requestId;

    private String path;

    private Map<String, String> params;

    private String userAgent;

    private String clientIp;

    private long timestamp;

    private String httpMethod;

    private String fingerprintHash;

    public String computeKey() {
        return "replay:fp:" + fingerprintHash;
    }
}
