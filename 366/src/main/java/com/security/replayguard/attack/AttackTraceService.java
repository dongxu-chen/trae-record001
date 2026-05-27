package com.security.replayguard.attack;

import com.alibaba.fastjson2.JSON;
import com.security.replayguard.config.ReplayGuardProperties;
import com.security.replayguard.core.RequestHasher;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.data.redis.core.StringRedisTemplate;
import org.springframework.stereotype.Component;

import java.util.*;
import java.util.concurrent.TimeUnit;
import java.util.stream.Collectors;

@Slf4j
@Component
@RequiredArgsConstructor
public class AttackTraceService {

    private static final String ATTACK_LOG_PREFIX = "replay:attack:log:";
    private static final String IP_ATTACK_COUNT_PREFIX = "replay:attack:ip:";
    private static final String USER_ATTACK_COUNT_PREFIX = "replay:attack:user:";
    private static final String ATTACK_PATTERN_PREFIX = "replay:attack:pattern:";
    private static final String ATTACK_SOURCE_SET = "replay:attack:sources";

    private final StringRedisTemplate redisTemplate;
    private final ReplayGuardProperties properties;
    private final RequestHasher requestHasher;

    public void recordAttack(AttackEvent event) {
        String attackId = generateAttackId();
        event.setAttackId(attackId);
        event.setTimestamp(System.currentTimeMillis() / 1000);

        saveAttackLog(event);
        incrementIpAttackCount(event.getIpAddress(), event.getAttackType());
        incrementUserAttackCount(event.getUserId(), event.getAttackType());
        recordAttackPattern(event);
        addAttackSource(event.getIpAddress());

        log.warn("Attack recorded: type={}, ip={}, user={}, path={}, id={}",
                event.getAttackType(), event.getIpAddress(),
                event.getUserId(), event.getRequestPath(), attackId);
    }

    private String generateAttackId() {
        return "ATT-" + System.currentTimeMillis() + "-" +
                UUID.randomUUID().toString().substring(0, 8).toUpperCase();
    }

    private void saveAttackLog(AttackEvent event) {
        String logKey = ATTACK_LOG_PREFIX + event.getAttackId();
        Map<String, String> logData = new HashMap<>();
        logData.put("attackId", event.getAttackId());
        logData.put("attackType", event.getAttackType());
        logData.put("ipAddress", event.getIpAddress());
        logData.put("userId", event.getUserId() != null ? event.getUserId() : "");
        logData.put("deviceFingerprint", event.getDeviceFingerprint() != null ? event.getDeviceFingerprint() : "");
        logData.put("requestPath", event.getRequestPath());
        logData.put("requestHash", event.getRequestHash() != null ? event.getRequestHash() : "");
        logData.put("timestamp", String.valueOf(event.getTimestamp()));
        logData.put("reason", event.getReason() != null ? event.getReason() : "");
        logData.put("sourceNode", event.getSourceNode() != null ? event.getSourceNode() : "");

        redisTemplate.opsForHash().putAll(logKey, logData);
        redisTemplate.expire(logKey, 7, TimeUnit.DAYS);
    }

    private void incrementIpAttackCount(String ip, String attackType) {
        if (ip == null || ip.isEmpty()) {
            return;
        }

        String ipKey = IP_ATTACK_COUNT_PREFIX + ip;
        redisTemplate.opsForHash().increment(ipKey, attackType, 1);
        redisTemplate.opsForHash().increment(ipKey, "total", 1);
        redisTemplate.opsForHash().put(ipKey, "lastAttackTime", String.valueOf(System.currentTimeMillis() / 1000));
        redisTemplate.expire(ipKey, 7, TimeUnit.DAYS);
    }

    private void incrementUserAttackCount(String userId, String attackType) {
        if (userId == null || userId.isEmpty()) {
            return;
        }

        String userKey = USER_ATTACK_COUNT_PREFIX + userId;
        redisTemplate.opsForHash().increment(userKey, attackType, 1);
        redisTemplate.opsForHash().increment(userKey, "total", 1);
        redisTemplate.opsForHash().put(userKey, "lastAttackTime", String.valueOf(System.currentTimeMillis() / 1000));
        redisTemplate.expire(userKey, 7, TimeUnit.DAYS);
    }

    private void recordAttackPattern(AttackEvent event) {
        String patternKey = ATTACK_PATTERN_PREFIX + event.getAttackType();
        long hourBucket = (System.currentTimeMillis() / 1000) / 3600;

        redisTemplate.opsForZSet().incrementScore(patternKey, String.valueOf(hourBucket), 1);
        redisTemplate.expire(patternKey, 7, TimeUnit.DAYS);

        String pathKey = ATTACK_PATTERN_PREFIX + "path:" + event.getAttackType();
        redisTemplate.opsForZSet().incrementScore(pathKey, event.getRequestPath(), 1);
        redisTemplate.expire(pathKey, 7, TimeUnit.DAYS);
    }

    private void addAttackSource(String ip) {
        if (ip == null || ip.isEmpty()) {
            return;
        }
        redisTemplate.opsForZSet().add(ATTACK_SOURCE_SET, ip, System.currentTimeMillis() / 1000);
    }

    public AttackSourceStats getIpAttackStats(String ip) {
        AttackSourceStats stats = new AttackSourceStats();
        stats.setIpAddress(ip);

        String ipKey = IP_ATTACK_COUNT_PREFIX + ip;
        Map<Object, Object> data = redisTemplate.opsForHash().entries(ipKey);

        if (data.isEmpty()) {
            stats.setTotalAttacks(0);
            return stats;
        }

        stats.setTotalAttacks(parseLong(data.get("total")));
        stats.setLastAttackTime(parseLong(data.get("lastAttackTime")));

        Map<String, Long> attackBreakdown = new HashMap<>();
        for (AttackEvent.AttackType type : AttackEvent.AttackType.values()) {
            long count = parseLong(data.get(type.getCode()));
            if (count > 0) {
                attackBreakdown.put(type.getCode(), count);
            }
        }
        stats.setAttackBreakdown(attackBreakdown);

        return stats;
    }

    public UserAttackStats getUserAttackStats(String userId) {
        UserAttackStats stats = new UserAttackStats();
        stats.setUserId(userId);

        String userKey = USER_ATTACK_COUNT_PREFIX + userId;
        Map<Object, Object> data = redisTemplate.opsForHash().entries(userKey);

        if (data.isEmpty()) {
            stats.setTotalAttacks(0);
            return stats;
        }

        stats.setTotalAttacks(parseLong(data.get("total")));
        stats.setLastAttackTime(parseLong(data.get("lastAttackTime")));

        Map<String, Long> attackBreakdown = new HashMap<>();
        for (AttackEvent.AttackType type : AttackEvent.AttackType.values()) {
            long count = parseLong(data.get(type.getCode()));
            if (count > 0) {
                attackBreakdown.put(type.getCode(), count);
            }
        }
        stats.setAttackBreakdown(attackBreakdown);

        return stats;
    }

    public List<AttackSourceStats> getTopAttackIps(int limit) {
        Set<String> recentIps = redisTemplate.opsForZSet()
                .reverseRange(ATTACK_SOURCE_SET, 0, limit - 1);

        if (recentIps == null) {
            return Collections.emptyList();
        }

        return recentIps.stream()
                .map(this::getIpAttackStats)
                .sorted((a, b) -> Long.compare(b.getTotalAttacks(), a.getTotalAttacks()))
                .limit(limit)
                .collect(Collectors.toList());
    }

    public AttackPatternAnalysis getPatternAnalysis(String attackType, int hours) {
        AttackPatternAnalysis analysis = new AttackPatternAnalysis();
        analysis.setAttackType(attackType);

        String patternKey = ATTACK_PATTERN_PREFIX + attackType;
        long currentHour = (System.currentTimeMillis() / 1000) / 3600;
        long startHour = currentHour - hours;

        Map<Long, Long> hourlyDistribution = new LinkedHashMap<>();
        for (long hour = startHour; hour <= currentHour; hour++) {
            Double score = redisTemplate.opsForZSet().score(patternKey, String.valueOf(hour));
            hourlyDistribution.put(hour, score != null ? score.longValue() : 0L);
        }
        analysis.setHourlyDistribution(hourlyDistribution);

        String pathKey = ATTACK_PATTERN_PREFIX + "path:" + attackType;
        Set<String> topPaths = redisTemplate.opsForZSet().reverseRange(pathKey, 0, 9);

        Map<String, Long> topTargetPaths = new LinkedHashMap<>();
        if (topPaths != null) {
            for (String path : topPaths) {
                Double score = redisTemplate.opsForZSet().score(pathKey, path);
                topTargetPaths.put(path, score != null ? score.longValue() : 0L);
            }
        }
        analysis.setTopTargetPaths(topTargetPaths);

        long totalAttacks = hourlyDistribution.values().stream().mapToLong(Long::longValue).sum();
        analysis.setTotalAttacks(totalAttacks);

        List<Long> values = new ArrayList<>(hourlyDistribution.values());
        if (!values.isEmpty()) {
            analysis.setPeakHour(values.stream().max(Long::compareTo).orElse(0L));
            analysis.setAveragePerHour((double) totalAttacks / hours);
        }

        return analysis;
    }

    public List<AttackEvent> getRecentAttacks(int limit) {
        Set<String> keys = redisTemplate.keys(ATTACK_LOG_PREFIX + "ATT-*");
        if (keys == null || keys.isEmpty()) {
            return Collections.emptyList();
        }

        List<AttackEvent> events = new ArrayList<>();
        for (String key : keys.stream().limit(limit).collect(Collectors.toList())) {
            try {
                Map<Object, Object> data = redisTemplate.opsForHash().entries(key);
                AttackEvent event = AttackEvent.builder()
                        .attackId((String) data.get("attackId"))
                        .attackType((String) data.get("attackType"))
                        .ipAddress((String) data.get("ipAddress"))
                        .userId((String) data.get("userId"))
                        .deviceFingerprint((String) data.get("deviceFingerprint"))
                        .requestPath((String) data.get("requestPath"))
                        .requestHash((String) data.get("requestHash"))
                        .timestamp(parseLong(data.get("timestamp")))
                        .reason((String) data.get("reason"))
                        .sourceNode((String) data.get("sourceNode"))
                        .build();
                events.add(event);
            } catch (Exception e) {
                log.debug("Error parsing attack log", e);
            }
        }

        events.sort((a, b) -> Long.compare(b.getTimestamp(), a.getTimestamp()));
        return events;
    }

    private long parseLong(Object value) {
        if (value == null) {
            return 0;
        }
        try {
            return Long.parseLong(value.toString());
        } catch (NumberFormatException e) {
            return 0;
        }
    }

    @lombok.Data
    public static class AttackSourceStats {
        private String ipAddress;
        private long totalAttacks;
        private long lastAttackTime;
        private Map<String, Long> attackBreakdown;
    }

    @lombok.Data
    public static class UserAttackStats {
        private String userId;
        private long totalAttacks;
        private long lastAttackTime;
        private Map<String, Long> attackBreakdown;
    }

    @lombok.Data
    public static class AttackPatternAnalysis {
        private String attackType;
        private long totalAttacks;
        private long peakHour;
        private double averagePerHour;
        private Map<Long, Long> hourlyDistribution;
        private Map<String, Long> topTargetPaths;
    }
}
