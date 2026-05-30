package com.replay.detector.service;

import com.replay.detector.config.ReplayDetectionProperties;
import com.replay.detector.model.AttackTrace;
import com.replay.detector.model.RequestFingerprint;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.data.redis.core.StringRedisTemplate;
import org.springframework.data.redis.core.script.DefaultRedisScript;
import org.springframework.stereotype.Service;

import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.time.Instant;
import java.util.*;
import java.util.concurrent.TimeUnit;
import java.util.stream.Collectors;

@Slf4j
@Service
@RequiredArgsConstructor
public class AttackTracingService {

    private static final String IP_TRACE_PREFIX = "replay:trace:ip:";
    private static final String DEVICE_TRACE_PREFIX = "replay:trace:device:";
    private static final String IP_PATH_PREFIX = "replay:trace:ip:path:";
    private static final String IP_TIMELINE_PREFIX = "replay:trace:ip:timeline:";

    private static final long TRACE_TTL_SECONDS = 86400;

    private static final String RECORD_IP_SCRIPT =
            "local ipKey = KEYS[1] " +
            "local pathKey = KEYS[2] " +
            "local timelineKey = KEYS[3] " +
            "local now = tonumber(ARGV[1]) " +
            "local path = ARGV[2] " +
            "local fpHash = ARGV[3] " +
            "local ttl = tonumber(ARGV[4]) " +
            "redis.call('HINCRBY', ipKey, 'totalCount', 1) " +
            "redis.call('HSET', ipKey, 'lastSeenAt', now) " +
            "redis.call('HSET', ipKey, 'lastFpHash', fpHash) " +
            "if redis.call('HEXISTS', ipKey, 'firstSeenAt') == 0 then " +
            "  redis.call('HSET', ipKey, 'firstSeenAt', now) " +
            "end " +
            "redis.call('EXPIRE', ipKey, ttl) " +
            "redis.call('HINCRBY', pathKey, path, 1) " +
            "redis.call('EXPIRE', pathKey, ttl) " +
            "redis.call('ZADD', timelineKey, now, fpHash .. ':' .. now) " +
            "redis.call('EXPIRE', timelineKey, ttl) " +
            "return 1 ";

    private final StringRedisTemplate redisTemplate;
    private final ReplayDetectionProperties properties;

    public void recordAttack(RequestFingerprint fingerprint, int replayCount) {
        String clientIp = fingerprint.getClientIp();
        if (clientIp == null || clientIp.isEmpty()) {
            return;
        }

        long now = System.currentTimeMillis();
        String ipKey = IP_TRACE_PREFIX + clientIp;
        String pathKey = IP_PATH_PREFIX + clientIp;
        String timelineKey = IP_TIMELINE_PREFIX + clientIp;

        DefaultRedisScript<Long> script = new DefaultRedisScript<>(RECORD_IP_SCRIPT, Long.class);
        redisTemplate.execute(
                script,
                List.of(ipKey, pathKey, timelineKey),
                String.valueOf(now),
                fingerprint.getPath() != null ? fingerprint.getPath() : "/",
                fingerprint.getFingerprintHash(),
                String.valueOf(TRACE_TTL_SECONDS)
        );

        log.debug("Recorded attack trace: ip={}, path={}, fpHash={}", clientIp, fingerprint.getPath(), fingerprint.getFingerprintHash());
    }

    public AttackTrace getTrace(String clientIp) {
        String ipKey = IP_TRACE_PREFIX + clientIp;
        Map<Object, Object> ipData = redisTemplate.opsForHash().entries(ipKey);

        if (ipData == null || ipData.isEmpty()) {
            return null;
        }

        String pathKey = IP_PATH_PREFIX + clientIp;
        Map<Object, Object> pathData = redisTemplate.opsForHash().entries(pathKey);

        Map<String, Integer> pathHitCount = new HashMap<>();
        List<String> targetPaths = new ArrayList<>();
        if (pathData != null) {
            pathData.forEach((k, v) -> {
                String path = k.toString();
                int count = Integer.parseInt(v.toString());
                pathHitCount.put(path, count);
                targetPaths.add(path);
            });
            targetPaths.sort((a, b) -> pathHitCount.getOrDefault(b, 0) - pathHitCount.getOrDefault(a, 0));
        }

        String userAgentHash = (String) ipData.get("lastFpHash");
        AttackTrace.DeviceFingerprint deviceFp = buildDeviceFingerprint(clientIp, userAgentHash);

        AttackTrace.AttackPattern pattern = analyzePattern(clientIp);

        int totalCount = parseIntSafe(ipData.get("totalCount"), 0);
        long firstSeen = parseLongSafe(ipData.get("firstSeenAt"), 0L);
        long lastSeen = parseLongSafe(ipData.get("lastSeenAt"), 0L);

        return AttackTrace.builder()
                .traceId(UUID.randomUUID().toString())
                .sourceIp(clientIp)
                .deviceFingerprint(deviceFp)
                .attackPattern(pattern)
                .totalReplayCount(totalCount)
                .firstSeenAt(firstSeen)
                .lastSeenAt(lastSeen)
                .targetPaths(targetPaths)
                .pathHitCount(pathHitCount)
                .riskLevel(determineRiskLevel(totalCount, pattern))
                .build();
    }

    public List<AttackTrace> getTopAttackers(int limit) {
        Set<String> keys = redisTemplate.keys(IP_TRACE_PREFIX + "*");
        if (keys == null || keys.isEmpty()) {
            return Collections.emptyList();
        }

        List<Map.Entry<String, Integer>> ipCounts = new ArrayList<>();
        for (String key : keys) {
            String countStr = (String) redisTemplate.opsForHash().get(key, "totalCount");
            int count = parseIntSafe(countStr, 0);
            String ip = key.substring(IP_TRACE_PREFIX.length());
            ipCounts.add(Map.entry(ip, count));
        }

        ipCounts.sort((a, b) -> b.getValue() - a.getValue());

        return ipCounts.stream()
                .limit(limit)
                .map(entry -> getTrace(entry.getKey()))
                .filter(Objects::nonNull)
                .collect(Collectors.toList());
    }

    private AttackTrace.DeviceFingerprint buildDeviceFingerprint(String clientIp, String userAgentHash) {
        String deviceKey = DEVICE_TRACE_PREFIX + clientIp;
        Map<Object, Object> deviceData = redisTemplate.opsForHash().entries(deviceKey);

        String userAgent = deviceData != null ? (String) deviceData.get("userAgent") : null;

        return AttackTrace.DeviceFingerprint.builder()
                .userAgent(userAgent)
                .userAgentHash(userAgentHash != null ? userAgentHash : sha256(clientIp))
                .browserType(classifyBrowser(userAgent))
                .osType(classifyOs(userAgent))
                .isBot(isBot(userAgent))
                .isProxy(isProxyHeaders(deviceData))
                .build();
    }

    public void recordDeviceFingerprint(String clientIp, String userAgent) {
        if (clientIp == null || userAgent == null) {
            return;
        }
        String deviceKey = DEVICE_TRACE_PREFIX + clientIp;
        redisTemplate.opsForHash().put(deviceKey, "userAgent", userAgent);
        redisTemplate.opsForHash().put(deviceKey, "userAgentHash", sha256(userAgent));
        redisTemplate.expire(deviceKey, TRACE_TTL_SECONDS, TimeUnit.SECONDS);
    }

    private AttackTrace.AttackPattern analyzePattern(String clientIp) {
        String pathKey = IP_PATH_PREFIX + clientIp;
        String timelineKey = IP_TIMELINE_PREFIX + clientIp;

        Map<Object, Object> pathData = redisTemplate.opsForHash().entries(pathKey);
        int pathCount = pathData != null ? pathData.size() : 0;

        String ipKey = IP_TRACE_PREFIX + clientIp;
        String totalCountStr = (String) redisTemplate.opsForHash().get(ipKey, "totalCount");
        int totalCount = parseIntSafe(totalCountStr, 0);

        long now = System.currentTimeMillis();
        long oneHourAgo = now - 3600000;
        Long recentCount = redisTemplate.opsForZSet().count(timelineKey, oneHourAgo, now);
        int recent = recentCount != null ? recentCount.intValue() : 0;

        AttackTrace.PatternType patternType;
        double confidence;
        String description;

        if (pathCount == 1 && recent >= 10) {
            patternType = AttackTrace.PatternType.SINGLE_PATH_BURST;
            confidence = Math.min(0.95, 0.6 + recent * 0.02);
            description = "Single path burst attack: concentrated on one endpoint";
        } else if (pathCount >= 5 && recent >= 5) {
            patternType = AttackTrace.PatternType.MULTI_PATH_SCAN;
            confidence = Math.min(0.9, 0.5 + pathCount * 0.05);
            description = "Multi-path scan: probing multiple endpoints";
        } else if (recent >= 3 && recent <= 8 && pathCount <= 2) {
            patternType = AttackTrace.PatternType.SLOW_DRIP;
            confidence = 0.7;
            description = "Slow drip attack: low frequency sustained replay";
        } else if (recent >= 5 && checkPeriodicity(timelineKey)) {
            patternType = AttackTrace.PatternType.PERIODIC_PULSE;
            confidence = 0.8;
            description = "Periodic pulse: time-regular replay bursts";
        } else if (totalCount >= 20 && pathCount >= 3) {
            patternType = AttackTrace.PatternType.DISTRIBUTED_COORDINATED;
            confidence = 0.65;
            description = "Possible coordinated distributed attack";
        } else {
            patternType = AttackTrace.PatternType.UNKNOWN;
            confidence = 0.3;
            description = "Unrecognized attack pattern";
        }

        return AttackTrace.AttackPattern.builder()
                .patternType(patternType)
                .confidence(confidence)
                .description(description)
                .burstCount(recent)
                .avgIntervalMs(computeAvgInterval(timelineKey, oneHourAgo, now))
                .build();
    }

    private boolean checkPeriodicity(String timelineKey) {
        List<String> entries = redisTemplate.opsForZSet().range(timelineKey, -20, -1);
        if (entries == null || entries.size() < 4) {
            return false;
        }

        List<Long> timestamps = entries.stream()
                .map(e -> {
                    String[] parts = e.split(":");
                    return parts.length >= 2 ? parseLongSafe(parts[parts.length - 1], 0L) : 0L;
                })
                .filter(t -> t > 0)
                .sorted()
                .collect(Collectors.toList());

        if (timestamps.size() < 4) return false;

        List<Long> intervals = new ArrayList<>();
        for (int i = 1; i < timestamps.size(); i++) {
            intervals.add(timestamps.get(i) - timestamps.get(i - 1));
        }

        if (intervals.isEmpty()) return false;

        double avg = intervals.stream().mapToLong(Long::longValue).average().orElse(0);
        if (avg == 0) return false;

        long consistentCount = intervals.stream()
                .filter(i -> Math.abs(i - avg) < avg * 0.3)
                .count();

        return (double) consistentCount / intervals.size() > 0.6;
    }

    private long computeAvgInterval(String timelineKey, long from, long to) {
        List<String> entries = redisTemplate.opsForZSet().rangeByScore(timelineKey, from, to);
        if (entries == null || entries.size() < 2) return 0;

        List<Long> timestamps = entries.stream()
                .map(e -> {
                    String[] parts = e.split(":");
                    return parts.length >= 2 ? parseLongSafe(parts[parts.length - 1], 0L) : 0L;
                })
                .filter(t -> t > 0)
                .sorted()
                .collect(Collectors.toList());

        if (timestamps.size() < 2) return 0;

        long totalInterval = timestamps.get(timestamps.size() - 1) - timestamps.get(0);
        return totalInterval / (timestamps.size() - 1);
    }

    private String determineRiskLevel(int totalCount, AttackTrace.AttackPattern pattern) {
        if (totalCount >= 50 || (pattern.getPatternType() == AttackTrace.PatternType.DISTRIBUTED_COORDINATED && pattern.getConfidence() > 0.7)) {
            return "CRITICAL";
        } else if (totalCount >= 20 || pattern.getConfidence() > 0.8) {
            return "HIGH";
        } else if (totalCount >= 10 || pattern.getConfidence() > 0.6) {
            return "MEDIUM";
        }
        return "LOW";
    }

    private String classifyBrowser(String ua) {
        if (ua == null) return "UNKNOWN";
        String lower = ua.toLowerCase();
        if (lower.contains("edg/")) return "Edge";
        if (lower.contains("chrome/")) return "Chrome";
        if (lower.contains("firefox/")) return "Firefox";
        if (lower.contains("safari/") && !lower.contains("chrome")) return "Safari";
        if (lower.contains("curl")) return "curl";
        if (lower.contains("python")) return "Python";
        if (lower.contains("java")) return "Java";
        if (lower.contains("postman")) return "Postman";
        return "OTHER";
    }

    private String classifyOs(String ua) {
        if (ua == null) return "UNKNOWN";
        String lower = ua.toLowerCase();
        if (lower.contains("windows")) return "Windows";
        if (lower.contains("mac os") || lower.contains("macos")) return "macOS";
        if (lower.contains("linux")) return "Linux";
        if (lower.contains("android")) return "Android";
        if (lower.contains("iphone") || lower.contains("ipad")) return "iOS";
        return "OTHER";
    }

    private boolean isBot(String ua) {
        if (ua == null) return true;
        String lower = ua.toLowerCase();
        return lower.contains("bot") || lower.contains("crawler") || lower.contains("spider")
                || lower.contains("curl") || lower.contains("wget") || lower.contains("python")
                || lower.contains("java/") || lower.contains("httpclient") || ua.length() < 10;
    }

    private boolean isProxyHeaders(Map<Object, Object> deviceData) {
        if (deviceData == null) return false;
        return deviceData.containsKey("via") || deviceData.containsKey("x-forwarded")
                || deviceData.containsKey("forwarded");
    }

    private String sha256(String input) {
        try {
            MessageDigest digest = MessageDigest.getInstance("SHA-256");
            byte[] hash = digest.digest(input.getBytes(StandardCharsets.UTF_8));
            return HexFormat.of().formatHex(hash);
        } catch (Exception e) {
            return Integer.toHexString(input.hashCode());
        }
    }

    private int parseIntSafe(Object obj, int defaultValue) {
        if (obj == null) return defaultValue;
        try { return Integer.parseInt(obj.toString()); } catch (NumberFormatException e) { return defaultValue; }
    }

    private long parseLongSafe(Object obj, long defaultValue) {
        if (obj == null) return defaultValue;
        try { return Long.parseLong(obj.toString()); } catch (NumberFormatException e) { return defaultValue; }
    }
}
