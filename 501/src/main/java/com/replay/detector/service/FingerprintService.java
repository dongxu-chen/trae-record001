package com.replay.detector.service;

import com.replay.detector.config.ReplayDetectionProperties;
import com.replay.detector.model.RequestFingerprint;
import org.apache.commons.lang3.StringUtils;
import org.springframework.stereotype.Service;

import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.security.NoSuchAlgorithmException;
import java.util.HexFormat;
import java.util.Map;
import java.util.TreeMap;
import java.util.stream.Collectors;

@Service
public class FingerprintService {

    private final ReplayDetectionProperties properties;

    public FingerprintService(ReplayDetectionProperties properties) {
        this.properties = properties;
    }

    public RequestFingerprint buildFingerprint(String requestId, String path, Map<String, String> params,
                                                String userAgent, String clientIp, String httpMethod, long timestamp) {
        String hash = computeHash(path, params, userAgent, timestamp);
        return RequestFingerprint.builder()
                .requestId(requestId)
                .path(path)
                .params(params)
                .userAgent(userAgent)
                .clientIp(clientIp)
                .httpMethod(httpMethod)
                .timestamp(timestamp)
                .fingerprintHash(hash)
                .build();
    }

    String computeHash(String path, Map<String, String> params, String userAgent, long timestamp) {
        StringBuilder sb = new StringBuilder();

        ReplayDetectionProperties.Fingerprint fp = properties.getFingerprint();

        if (fp.isIncludePath() && StringUtils.isNotBlank(path)) {
            sb.append("PATH:").append(path).append(";");
        }

        if (fp.isIncludeParams() && params != null && !params.isEmpty()) {
            Map<String, String> sorted = new TreeMap<>(params);
            String paramStr = sorted.entrySet().stream()
                    .map(e -> e.getKey() + "=" + e.getValue())
                    .collect(Collectors.joining("&"));
            sb.append("PARAMS:").append(paramStr).append(";");
        }

        if (fp.isIncludeUserAgent() && StringUtils.isNotBlank(userAgent)) {
            sb.append("UA:").append(userAgent).append(";");
        }

        if (fp.isIncludeTimestamp()) {
            long windowBucket = timestamp / fp.getTimestampToleranceSeconds();
            sb.append("TS:").append(windowBucket).append(";");
        }

        return sha256(sb.toString());
    }

    private String sha256(String input) {
        try {
            MessageDigest digest = MessageDigest.getInstance("SHA-256");
            byte[] hash = digest.digest(input.getBytes(StandardCharsets.UTF_8));
            return HexFormat.of().formatHex(hash);
        } catch (NoSuchAlgorithmException e) {
            throw new RuntimeException("SHA-256 algorithm not available", e);
        }
    }
}
