package com.alert.util;

import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.security.NoSuchAlgorithmException;
import java.util.Arrays;
import java.util.stream.Collectors;

public class AggregationFingerprint {

    public static String generate(String source, String host, String service, String tags) {
        StringBuilder sb = new StringBuilder();
        sb.append(normalize(source)).append("|");
        sb.append(normalize(host)).append("|");
        sb.append(normalize(service)).append("|");
        sb.append(normalizeTags(tags));
        
        return md5Hash(sb.toString());
    }

    private static String normalize(String value) {
        if (value == null || value.trim().isEmpty()) {
            return "*";
        }
        return value.trim().toLowerCase();
    }

    private static String normalizeTags(String tags) {
        if (tags == null || tags.trim().isEmpty()) {
            return "*";
        }
        return Arrays.stream(tags.split(","))
                .map(String::trim)
                .filter(s -> !s.isEmpty())
                .map(String::toLowerCase)
                .sorted()
                .collect(Collectors.joining(","));
    }

    private static String md5Hash(String input) {
        try {
            MessageDigest md = MessageDigest.getInstance("MD5");
            byte[] hashBytes = md.digest(input.getBytes(StandardCharsets.UTF_8));
            StringBuilder sb = new StringBuilder();
            for (byte b : hashBytes) {
                sb.append(String.format("%02x", b));
            }
            return "agg_" + sb.toString();
        } catch (NoSuchAlgorithmException e) {
            return "agg_" + Math.abs(input.hashCode());
        }
    }

    public static String getFingerprintDetails(String source, String host, String service, String tags) {
        return String.format("source:%s | host:%s | service:%s | tags:%s",
                normalize(source), normalize(host), normalize(service), normalizeTags(tags));
    }
}
