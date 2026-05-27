package com.security.replayguard.core;

import com.alibaba.fastjson2.JSON;
import com.security.replayguard.model.RequestFeature;
import org.apache.commons.codec.digest.DigestUtils;
import org.apache.commons.lang3.StringUtils;
import org.springframework.stereotype.Component;

import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.security.NoSuchAlgorithmException;
import java.util.Map;
import java.util.TreeMap;

@Component
public class RequestHasher {

    private static final String SEPARATOR = "||";

    public String computeHash(RequestFeature feature) {
        StringBuilder sb = new StringBuilder();

        sb.append(normalizePath(feature.getRequestPath())).append(SEPARATOR);
        sb.append(StringUtils.defaultString(feature.getMethod())).append(SEPARATOR);
        sb.append(normalizeQueryParams(feature.getQueryParams())).append(SEPARATOR);
        sb.append(StringUtils.defaultString(feature.getBodyHash())).append(SEPARATOR);
        sb.append(StringUtils.defaultString(feature.getTimestamp())).append(SEPARATOR);
        sb.append(StringUtils.defaultString(feature.getNonce())).append(SEPARATOR);
        sb.append(StringUtils.defaultString(feature.getDeviceFingerprint())).append(SEPARATOR);
        sb.append(StringUtils.defaultString(feature.getIpAddress())).append(SEPARATOR);
        sb.append(StringUtils.defaultString(feature.getUserAgent()));

        return sha256Hex(sb.toString());
    }

    public String computeUniqueHash(RequestFeature feature) {
        StringBuilder sb = new StringBuilder();

        sb.append(normalizePath(feature.getRequestPath())).append(SEPARATOR);
        sb.append(normalizeQueryParams(feature.getQueryParams())).append(SEPARATOR);
        sb.append(StringUtils.defaultString(feature.getBodyHash())).append(SEPARATOR);
        sb.append(StringUtils.defaultString(feature.getDeviceFingerprint())).append(SEPARATOR);
        sb.append(StringUtils.defaultString(feature.getIpAddress()));

        return sha256Hex(sb.toString());
    }

    public String computeUniqueHashWithUser(RequestFeature feature) {
        StringBuilder sb = new StringBuilder();

        sb.append(normalizeUserId(feature.getUserId())).append(SEPARATOR);
        sb.append(normalizePath(feature.getRequestPath())).append(SEPARATOR);
        sb.append(normalizeQueryParams(feature.getQueryParams())).append(SEPARATOR);
        sb.append(StringUtils.defaultString(feature.getBodyHash()));

        return sha256Hex(sb.toString());
    }

    public String computeUserIdPartition(String userId) {
        return "user:" + sha256Hex(StringUtils.defaultString(userId)).substring(0, 8);
    }

    public String computePartitionKey(RequestFeature feature) {
        String userId = feature.getUserId();
        if (StringUtils.isNotBlank(userId)) {
            return computeUserIdPartition(userId);
        }
        
        String deviceFp = feature.getDeviceFingerprint();
        if (StringUtils.isNotBlank(deviceFp)) {
            return "device:" + sha256Hex(deviceFp).substring(0, 8);
        }
        
        String ip = feature.getIpAddress();
        if (StringUtils.isNotBlank(ip)) {
            return "ip:" + sha256Hex(ip).substring(0, 8);
        }
        
        return "unknown";
    }

    public String computeNonceHash(String deviceFingerprint, String nonce, String timestamp) {
        String content = StringUtils.defaultString(deviceFingerprint) + SEPARATOR +
                StringUtils.defaultString(nonce) + SEPARATOR +
                StringUtils.defaultString(timestamp);
        return sha256Hex(content);
    }

    public String computeRequestBodyHash(String body) {
        if (StringUtils.isBlank(body)) {
            return "";
        }
        String normalizedBody = normalizeJson(body);
        return sha256Hex(normalizedBody);
    }

    private String normalizePath(String path) {
        if (StringUtils.isBlank(path)) {
            return "";
        }
        path = path.trim();
        if (path.length() > 1 && path.endsWith("/")) {
            path = path.substring(0, path.length() - 1);
        }
        return path.toLowerCase();
    }

    private String normalizeUserId(String userId) {
        if (StringUtils.isBlank(userId)) {
            return "anonymous";
        }
        return userId.trim().toLowerCase();
    }

    private String normalizeQueryParams(Map<String, String> params) {
        if (params == null || params.isEmpty()) {
            return "";
        }
        TreeMap<String, String> sorted = new TreeMap<>(params);
        StringBuilder sb = new StringBuilder();
        sorted.forEach((key, value) -> {
            if (sb.length() > 0) {
                sb.append("&");
            }
            sb.append(key.toLowerCase()).append("=").append(StringUtils.defaultString(value));
        });
        return sb.toString();
    }

    private String normalizeJson(String json) {
        if (StringUtils.isBlank(json)) {
            return "";
        }
        try {
            Object obj = JSON.parse(json);
            return JSON.toJSONString(obj);
        } catch (Exception e) {
            return json.trim();
        }
    }

    private String sha256Hex(String input) {
        try {
            MessageDigest digest = MessageDigest.getInstance("SHA-256");
            byte[] hash = digest.digest(input.getBytes(StandardCharsets.UTF_8));
            return bytesToHex(hash);
        } catch (NoSuchAlgorithmException e) {
            return DigestUtils.sha256Hex(input);
        }
    }

    private String bytesToHex(byte[] bytes) {
        StringBuilder hexString = new StringBuilder();
        for (byte b : bytes) {
            String hex = Integer.toHexString(0xff & b);
            if (hex.length() == 1) {
                hexString.append('0');
            }
            hexString.append(hex);
        }
        return hexString.toString();
    }

    public String computeShortHash(String input) {
        return sha256Hex(input).substring(0, 16);
    }
}
