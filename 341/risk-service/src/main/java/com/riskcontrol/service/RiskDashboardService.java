package com.riskcontrol.service;

import com.riskcontrol.common.enums.EventType;
import com.riskcontrol.common.enums.RiskLevel;
import com.riskcontrol.common.model.RiskAssessmentResult;
import com.riskcontrol.common.model.RiskEvent;
import org.redisson.api.RDeque;
import org.redisson.api.RMap;
import org.redisson.api.RScoredSortedSet;
import org.redisson.api.RedissonClient;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;

import java.time.LocalDate;
import java.time.LocalDateTime;
import java.time.LocalTime;
import java.time.ZoneId;
import java.time.format.DateTimeFormatter;
import java.util.*;
import java.util.concurrent.TimeUnit;

@Service
public class RiskDashboardService {

    private static final Logger logger = LoggerFactory.getLogger(RiskDashboardService.class);

    private static final String DASHBOARD_PREFIX = "risk:dashboard:";
    private static final String EVENT_TOTAL = DASHBOARD_PREFIX + "event:total";
    private static final String EVENT_BY_TYPE = DASHBOARD_PREFIX + "event:by_type:";
    private static final String EVENT_BY_LEVEL = DASHBOARD_PREFIX + "event:by_level:";
    private static final String EVENT_BY_HOUR = DASHBOARD_PREFIX + "event:by_hour:";
    private static final String ACTION_STATS = DASHBOARD_PREFIX + "action:stats";
    private static final String RECENT_EVENTS = DASHBOARD_PREFIX + "events:recent";

    private static final int MAX_RECENT_EVENTS = 1000;
    private static final int HOURS_TO_KEEP = 24;

    private final RedissonClient redissonClient;

    @Autowired
    public RiskDashboardService(RedissonClient redissonClient) {
        this.redissonClient = redissonClient;
    }

    public void recordEvent(RiskEvent event, RiskAssessmentResult result) {
        try {
            String hourKey = getCurrentHourKey();

            redissonClient.getAtomicLong(EVENT_TOTAL).incrementAndGet();
            redissonClient.getAtomicLong(EVENT_BY_TYPE + event.getEventType()).incrementAndGet();
            redissonClient.getAtomicLong(EVENT_BY_LEVEL + result.getRiskLevel()).incrementAndGet();
            redissonClient.getAtomicLong(EVENT_BY_HOUR + hourKey).incrementAndGet();

            recordActionStats(result);
            recordRecentEvent(event, result);
            recordTrendData(event, result, hourKey);

        } catch (Exception e) {
            logger.error("Failed to record event to dashboard", e);
        }
    }

    private void recordActionStats(RiskAssessmentResult result) {
        RMap<String, Long> actionMap = redissonClient.getMap(ACTION_STATS);

        actionMap.merge("total", 1L, Long::sum);

        if (!result.isAllowed()) {
            actionMap.merge("blocked", 1L, Long::sum);
            if (result.isBlockAccount()) {
                actionMap.merge("account_blocked", 1L, Long::sum);
            }
        } else {
            actionMap.merge("allowed", 1L, Long::sum);
        }

        if (result.isRequireMfa()) {
            actionMap.merge("mfa_required", 1L, Long::sum);
        }
        if (result.isRequireCaptcha()) {
            actionMap.merge("captcha_required", 1L, Long::sum);
        }

        if (result.getRiskLevel() != null) {
            actionMap.merge("level_" + result.getRiskLevel().name().toLowerCase(), 1L, Long::sum);
        }
    }

    private void recordRecentEvent(RiskEvent event, RiskAssessmentResult result) {
        RDeque<String> recentEvents = redissonClient.getDeque(RECENT_EVENTS);

        Map<String, Object> eventData = new HashMap<>();
        eventData.put("eventId", event.getEventId());
        eventData.put("userId", event.getUserId());
        eventData.put("eventType", event.getEventType() != null ? event.getEventType().name() : "UNKNOWN");
        eventData.put("ipAddress", event.getIpAddress());
        eventData.put("riskLevel", result.getRiskLevel() != null ? result.getRiskLevel().name() : "UNKNOWN");
        eventData.put("finalScore", result.getFinalScore());
        eventData.put("isAllowed", result.isAllowed());
        eventData.put("timestamp", event.getEventTimestamp());

        String json = toJson(eventData);
        recentEvents.addFirst(json);

        while (recentEvents.size() > MAX_RECENT_EVENTS) {
            recentEvents.removeLast();
        }

        recentEvents.expire(1, TimeUnit.HOURS);
    }

    private void recordTrendData(RiskEvent event, RiskAssessmentResult result, String hourKey) {
        String trendKey = DASHBOARD_PREFIX + "trend:" + hourKey;
        RMap<String, Long> trendMap = redissonClient.getMap(trendKey);

        trendMap.merge("total", 1L, Long::sum);

        if (result.getRiskLevel() != null) {
            trendMap.merge(result.getRiskLevel().name(), 1L, Long::sum);
        }

        if (event.getEventType() != null) {
            trendMap.merge(event.getEventType().name(), 1L, Long::sum);
        }

        if (!result.isAllowed()) {
            trendMap.merge("blocked", 1L, Long::sum);
        }
        if (result.isRequireMfa()) {
            trendMap.merge("mfa", 1L, Long::sum);
        }

        trendMap.expire(HOURS_TO_KEEP + 1, TimeUnit.HOURS);
    }

    public Map<String, Object> getDashboardSummary() {
        Map<String, Object> summary = new HashMap<>();

        summary.put("totalEvents", redissonClient.getAtomicLong(EVENT_TOTAL).get());

        Map<String, Long> byType = new HashMap<>();
        for (EventType type : EventType.values()) {
            byType.put(type.name(), redissonClient.getAtomicLong(EVENT_BY_TYPE + type).get());
        }
        summary.put("eventsByType", byType);

        Map<String, Long> byLevel = new HashMap<>();
        for (RiskLevel level : RiskLevel.values()) {
            byLevel.put(level.name(), redissonClient.getAtomicLong(EVENT_BY_LEVEL + level).get());
        }
        summary.put("eventsByLevel", byLevel);

        RMap<String, Long> actionStats = redissonClient.getMap(ACTION_STATS);
        Map<String, Object> actions = new HashMap<>();
        actions.putAll(actionStats);

        long total = actionStats.getOrDefault("total", 1L);
        actions.put("blockRate", calculateRate(actionStats.get("blocked"), total));
        actions.put("mfaRate", calculateRate(actionStats.get("mfa_required"), total));
        actions.put("captchaRate", calculateRate(actionStats.get("captcha_required"), total));
        actions.put("allowRate", calculateRate(actionStats.get("allowed"), total));

        summary.put("actionStats", actions);

        return summary;
    }

    public Map<String, Object> getTrendData(int hours) {
        Map<String, Object> trend = new LinkedHashMap<>();
        List<Map<String, Object>> hourlyData = new ArrayList<>();

        LocalDateTime now = LocalDateTime.now();
        for (int i = hours - 1; i >= 0; i--) {
            LocalDateTime hourTime = now.minusHours(i);
            String hourKey = getHourKey(hourTime);

            Map<String, Object> hourData = new HashMap<>();
            hourData.put("hour", hourTime.format(DateTimeFormatter.ofPattern("HH:00")));
            hourData.put("timestamp", hourTime.atZone(ZoneId.systemDefault()).toInstant().toEpochMilli());

            RMap<String, Long> trendMap = redissonClient.getMap(DASHBOARD_PREFIX + "trend:" + hourKey);
            if (!trendMap.isEmpty()) {
                hourData.putAll(trendMap);
            } else {
                hourData.put("total", 0);
                for (RiskLevel level : RiskLevel.values()) {
                    hourData.put(level.name(), 0);
                }
            }

            hourlyData.add(hourData);
        }

        trend.put("hourlyData", hourlyData);
        trend.put("totalPeriod", calculatePeriodTotal(hourlyData));

        return trend;
    }

    public List<Map<String, Object>> getRecentEvents(int limit) {
        RDeque<String> recentEvents = redissonClient.getDeque(RECENT_EVENTS);
        List<Map<String, Object>> events = new ArrayList<>();

        int count = 0;
        for (String json : recentEvents) {
            if (count >= limit) break;
            Map<String, Object> eventData = fromJson(json);
            if (eventData != null) {
                events.add(eventData);
            }
            count++;
        }

        return events;
    }

    public Map<String, Object> getRiskDistribution() {
        Map<String, Object> distribution = new HashMap<>();

        long low = redissonClient.getAtomicLong(EVENT_BY_LEVEL + RiskLevel.LOW).get();
        long medium = redissonClient.getAtomicLong(EVENT_BY_LEVEL + RiskLevel.MEDIUM).get();
        long high = redissonClient.getAtomicLong(EVENT_BY_LEVEL + RiskLevel.HIGH).get();
        long critical = redissonClient.getAtomicLong(EVENT_BY_LEVEL + RiskLevel.CRITICAL).get();
        long total = low + medium + high + critical;

        distribution.put("total", total);
        distribution.put("low", low);
        distribution.put("medium", medium);
        distribution.put("high", high);
        distribution.put("critical", critical);

        if (total > 0) {
            distribution.put("lowPercent", Math.round((low * 100.0 / total) * 100) / 100.0);
            distribution.put("mediumPercent", Math.round((medium * 100.0 / total) * 100) / 100.0);
            distribution.put("highPercent", Math.round((high * 100.0 / total) * 100) / 100.0);
            distribution.put("criticalPercent", Math.round((critical * 100.0 / total) * 100) / 100.0);
        }

        return distribution;
    }

    public Map<String, Object> getDispositionStats() {
        Map<String, Object> stats = new HashMap<>();
        RMap<String, Long> actionStats = redissonClient.getMap(ACTION_STATS);

        long total = actionStats.getOrDefault("total", 0L);
        long allowed = actionStats.getOrDefault("allowed", 0L);
        long blocked = actionStats.getOrDefault("blocked", 0L);
        long mfa = actionStats.getOrDefault("mfa_required", 0L);
        long captcha = actionStats.getOrDefault("captcha_required", 0L);
        long accountBlocked = actionStats.getOrDefault("account_blocked", 0L);

        stats.put("totalAssessments", total);
        stats.put("allowed", allowed);
        stats.put("blocked", blocked);
        stats.put("mfaRequired", mfa);
        stats.put("captchaRequired", captcha);
        stats.put("accountsBlocked", accountBlocked);

        if (total > 0) {
            stats.put("allowRate", Math.round((allowed * 100.0 / total) * 100) / 100.0);
            stats.put("blockRate", Math.round((blocked * 100.0 / total) * 100) / 100.0);
            stats.put("mfaRate", Math.round((mfa * 100.0 / total) * 100) / 100.0);
            stats.put("captchaRate", Math.round((captcha * 100.0 / total) * 100) / 100.0);
        }

        Map<String, Long> levelCounts = new HashMap<>();
        for (RiskLevel level : RiskLevel.values()) {
            levelCounts.put(level.name(), actionStats.getOrDefault("level_" + level.name().toLowerCase(), 0L));
        }
        stats.put("riskLevelCounts", levelCounts);

        return stats;
    }

    public void resetDashboard() {
        logger.warn("Resetting dashboard statistics");

        redissonClient.getAtomicLong(EVENT_TOTAL).set(0);

        for (EventType type : EventType.values()) {
            redissonClient.getAtomicLong(EVENT_BY_TYPE + type).delete();
        }
        for (RiskLevel level : RiskLevel.values()) {
            redissonClient.getAtomicLong(EVENT_BY_LEVEL + level).delete();
        }

        redissonClient.getMap(ACTION_STATS).delete();
        redissonClient.getDeque(RECENT_EVENTS).delete();

        for (int i = 0; i <= HOURS_TO_KEEP; i++) {
            String hourKey = getHourKey(LocalDateTime.now().minusHours(i));
            redissonClient.getMap(DASHBOARD_PREFIX + "trend:" + hourKey).delete();
            redissonClient.getAtomicLong(EVENT_BY_HOUR + hourKey).delete();
        }
    }

    private String getCurrentHourKey() {
        return getHourKey(LocalDateTime.now());
    }

    private String getHourKey(LocalDateTime dateTime) {
        return dateTime.format(DateTimeFormatter.ofPattern("yyyyMMddHH"));
    }

    private double calculateRate(Long value, long total) {
        if (value == null || total == 0) return 0.0;
        return Math.round((value * 100.0 / total) * 100) / 100.0;
    }

    private long calculatePeriodTotal(List<Map<String, Object>> hourlyData) {
        long total = 0;
        for (Map<String, Object> hour : hourlyData) {
            Object t = hour.get("total");
            if (t instanceof Number) {
                total += ((Number) t).longValue();
            }
        }
        return total;
    }

    private String toJson(Map<String, Object> data) {
        StringBuilder sb = new StringBuilder("{");
        boolean first = true;
        for (Map.Entry<String, Object> entry : data.entrySet()) {
            if (!first) sb.append(",");
            first = false;
            sb.append("\"").append(entry.getKey()).append("\":");
            Object value = entry.getValue();
            if (value instanceof String) {
                sb.append("\"").append(value).append("\"");
            } else {
                sb.append(value);
            }
        }
        sb.append("}");
        return sb.toString();
    }

    @SuppressWarnings("unchecked")
    private Map<String, Object> fromJson(String json) {
        try {
            Map<String, Object> map = new HashMap<>();
            json = json.trim();
            if (json.startsWith("{") && json.endsWith("}")) {
                json = json.substring(1, json.length() - 1);
                String[] pairs = json.split(",(?=(?:[^\"]*\"[^\"]*\")*[^\"]*$)");
                for (String pair : pairs) {
                    String[] kv = pair.split(":", 2);
                    if (kv.length == 2) {
                        String key = kv[0].trim().replaceAll("^\"|\"$", "");
                        String value = kv[1].trim();
                        if (value.startsWith("\"") && value.endsWith("\"")) {
                            map.put(key, value.substring(1, value.length() - 1));
                        } else if ("true".equals(value) || "false".equals(value)) {
                            map.put(key, Boolean.parseBoolean(value));
                        } else {
                            try {
                                if (value.contains(".")) {
                                    map.put(key, Double.parseDouble(value));
                                } else {
                                    map.put(key, Long.parseLong(value));
                                }
                            } catch (NumberFormatException e) {
                                map.put(key, value);
                            }
                        }
                    }
                }
            }
            return map;
        } catch (Exception e) {
            logger.warn("Failed to parse event JSON: {}", e.getMessage());
            return null;
        }
    }
}
