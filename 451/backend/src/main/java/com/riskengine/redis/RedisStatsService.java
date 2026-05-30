package com.riskengine.redis;

import com.riskengine.model.HitStats;
import com.riskengine.model.RiskDecision;
import com.riskengine.model.RiskEvent;
import lombok.extern.slf4j.Slf4j;
import org.springframework.data.redis.core.StringRedisTemplate;
import org.springframework.stereotype.Service;

import java.time.LocalDate;
import java.time.LocalDateTime;
import java.time.format.DateTimeFormatter;
import java.util.*;
import java.util.concurrent.TimeUnit;
import java.util.stream.Collectors;

@Slf4j
@Service
public class RedisStatsService {

    private static final String KEY_PREFIX = "risk:stats:";
    private static final String KEY_EVENT_TOTAL = KEY_PREFIX + "event:total";
    private static final String KEY_EVENT_TYPE = KEY_PREFIX + "event:type:";
    private static final String KEY_RULE_HIT = KEY_PREFIX + "rule:hit:";
    private static final String KEY_ACTION_COUNT = KEY_PREFIX + "action:";
    private static final String KEY_LATENCY = KEY_PREFIX + "latency:";
    private static final String KEY_ERROR = KEY_PREFIX + "error:";

    public enum Granularity {
        MINUTE("minute", "yyyy-MM-dd:HH:mm", 2, TimeUnit.HOURS),
        HOUR("hour", "yyyy-MM-dd:HH", 24, TimeUnit.DAYS),
        DAY("day", "yyyy-MM-dd", 30, TimeUnit.DAYS);

        public final String code;
        public final String pattern;
        public final int keepCount;
        public final TimeUnit ttlUnit;

        Granularity(String code, String pattern, int keepCount, TimeUnit ttlUnit) {
            this.code = code;
            this.pattern = pattern;
            this.keepCount = keepCount;
            this.ttlUnit = ttlUnit;
        }

        public String format(LocalDateTime time) {
            return time.format(DateTimeFormatter.ofPattern(pattern));
        }

        public static Granularity fromCode(String code) {
            for (Granularity g : values()) {
                if (g.code.equals(code)) return g;
            }
            return HOUR;
        }
    }

    private static class TimeSeriesKey {
        static String forMinute(LocalDateTime time) {
            return time.format(DateTimeFormatter.ofPattern("yyyy-MM-dd:HH:mm"));
        }
        static String forHour(LocalDateTime time) {
            return time.format(DateTimeFormatter.ofPattern("yyyy-MM-dd:HH"));
        }
        static String forDay(LocalDateTime time) {
            return time.format(DateTimeFormatter.ofPattern("yyyy-MM-dd"));
        }
    }

    private final StringRedisTemplate redisTemplate;

    public RedisStatsService(StringRedisTemplate redisTemplate) {
        this.redisTemplate = redisTemplate;
    }

    public void recordHitStats(RiskEvent event, RiskDecision decision) {
        try {
            LocalDateTime now = LocalDateTime.now();

            String minKey = TimeSeriesKey.forMinute(now);
            String hourKey = TimeSeriesKey.forHour(now);
            String dayKey = TimeSeriesKey.forDay(now);

            incr(KEY_EVENT_TOTAL);
            incr(KEY_EVENT_TYPE + event.getEventType());

            String action = decision.getAction();
            incr(KEY_ACTION_COUNT + action);
            incr(KEY_ACTION_COUNT + "minute:" + minKey + ":" + action);
            incr(KEY_ACTION_COUNT + "hour:" + hourKey + ":" + action);
            incr(KEY_ACTION_COUNT + "day:" + dayKey + ":" + action);

            expire(KEY_ACTION_COUNT + "minute:" + minKey + ":" + action, 2, TimeUnit.HOURS);
            expire(KEY_ACTION_COUNT + "hour:" + hourKey + ":" + action, 24, TimeUnit.HOURS);
            expire(KEY_ACTION_COUNT + "day:" + dayKey + ":" + action, 30, TimeUnit.DAYS);

            if (decision.getHitRules() != null) {
                for (String ruleCode : decision.getHitRules()) {
                    incr(KEY_RULE_HIT + ruleCode);
                    incr(KEY_RULE_HIT + ruleCode + ":minute:" + minKey);
                    incr(KEY_RULE_HIT + ruleCode + ":hour:" + hourKey);
                    incr(KEY_RULE_HIT + ruleCode + ":day:" + dayKey);
                    incrBy(KEY_RULE_HIT + ruleCode + ":score", decision.getRiskScore());

                    expire(KEY_RULE_HIT + ruleCode + ":minute:" + minKey, 2, TimeUnit.HOURS);
                    expire(KEY_RULE_HIT + ruleCode + ":hour:" + hourKey, 24, TimeUnit.HOURS);
                    expire(KEY_RULE_HIT + ruleCode + ":day:" + dayKey, 30, TimeUnit.DAYS);
                }
            }

            String today = TimeSeriesKey.forDay(now);
            String dailyKey = KEY_PREFIX + "daily:" + today;
            incrHash(dailyKey, "total", 1);
            if (!decision.getHitRules().isEmpty()) {
                incrHash(dailyKey, "hit", 1);
            }
            expire(dailyKey, 30, TimeUnit.DAYS);

        } catch (Exception e) {
            log.error("Failed to record hit stats to Redis", e);
        }
    }

    public void recordDecisionLatency(String eventType, long durationMs) {
        try {
            String latencyKey = KEY_LATENCY + eventType;
            redisTemplate.opsForList().rightPush(latencyKey, String.valueOf(durationMs));
            redisTemplate.opsForList().trim(latencyKey, -1000, -1);
        } catch (Exception e) {
            log.error("Failed to record latency to Redis", e);
        }
    }

    public void recordError(String eventType) {
        try {
            incr(KEY_ERROR + eventType);
        } catch (Exception e) {
            log.error("Failed to record error to Redis", e);
        }
    }

    public List<HitStats> getHitStats(List<String> ruleCodes) {
        List<HitStats> result = new ArrayList<>();
        Long totalEvents = getLong(KEY_EVENT_TOTAL, 0L);

        for (String ruleCode : ruleCodes) {
            HitStats stats = new HitStats();
            stats.setRuleCode(ruleCode);
            stats.setTotalEvents(totalEvents);
            stats.setHitCount(getLong(KEY_RULE_HIT + ruleCode, 0L));
            stats.setHitRate(totalEvents > 0 ? (double) stats.getHitCount() / totalEvents * 100 : 0.0);

            String scoreKey = KEY_RULE_HIT + ruleCode + ":score";
            Long scoreSum = getLong(scoreKey, 0L);
            stats.setAvgRiskScore(stats.getHitCount() > 0 ? (double) scoreSum / stats.getHitCount() : 0.0);

            result.add(stats);
        }
        return result;
    }

    public Map<String, Object> getHitStatsByGranularity(String granularityCode) {
        Granularity g = Granularity.fromCode(granularityCode);
        LocalDateTime now = LocalDateTime.now();

        List<String> timeKeys = new ArrayList<>();
        for (int i = g.keepCount - 1; i >= 0; i--) {
            LocalDateTime time = now.minus(i,
                g == Granularity.MINUTE ? java.time.temporal.ChronoUnit.MINUTES :
                g == Granularity.HOUR ? java.time.temporal.ChronoUnit.HOURS :
                java.time.temporal.ChronoUnit.DAYS);
            timeKeys.add(g.format(time));
        }

        Set<String> ruleCodes = redisTemplate.keys(KEY_RULE_HIT + "*:minute:*")
            .stream()
            .map(k -> k.replace(KEY_RULE_HIT, "").split(":")[0])
            .filter(k -> !k.contains(":"))
            .collect(Collectors.toSet());

        if (ruleCodes.isEmpty()) {
            return Map.of(
                "granularity", g.code,
                "timeKeys", timeKeys,
                "series", Collections.emptyList(),
                "totals", Collections.emptyMap()
            );
        }

        List<Map<String, Object>> series = new ArrayList<>();
        for (String ruleCode : ruleCodes) {
            List<Long> values = new ArrayList<>();
            long total = 0;
            for (String tk : timeKeys) {
                String key = KEY_RULE_HIT + ruleCode + ":" + g.code + ":" + tk;
                long v = getLong(key, 0L);
                values.add(v);
                total += v;
            }
            series.add(Map.of(
                "ruleCode", ruleCode,
                "values", values,
                "total", total
            ));
        }

        Map<String, Long> totals = new HashMap<>();
        for (String action : new String[]{"PASS", "REVIEW", "REJECT", "BLOCK"}) {
            long count = 0;
            for (String tk : timeKeys) {
                String key = KEY_ACTION_COUNT + g.code + ":" + tk + ":" + action;
                count += getLong(key, 0L);
            }
            totals.put(action, count);
        }

        return Map.of(
            "granularity", g.code,
            "timeKeys", timeKeys,
            "series", series,
            "totals", totals
        );
    }

    public Map<String, Long> getActionCounts() {
        Map<String, Long> counts = new HashMap<>();
        for (RiskDecision.Action action : RiskDecision.Action.values()) {
            String key = KEY_ACTION_COUNT + action.name();
            counts.put(action.name(), getLong(key, 0L));
        }
        return counts;
    }

    public Map<String, Long> getActionCountsByGranularity(String granularityCode) {
        Granularity g = Granularity.fromCode(granularityCode);
        LocalDateTime now = LocalDateTime.now();

        Map<String, Long> counts = new HashMap<>();
        for (RiskDecision.Action action : RiskDecision.Action.values()) {
            long total = 0;
            for (int i = g.keepCount - 1; i >= 0; i--) {
                LocalDateTime time = now.minus(i,
                    g == Granularity.MINUTE ? java.time.temporal.ChronoUnit.MINUTES :
                    g == Granularity.HOUR ? java.time.temporal.ChronoUnit.HOURS :
                    java.time.temporal.ChronoUnit.DAYS);
                String key = KEY_ACTION_COUNT + g.code + ":" + g.format(time) + ":" + action.name();
                total += getLong(key, 0L);
            }
            counts.put(action.name(), total);
        }
        return counts;
    }

    public Map<String, Object> getDashboardStats() {
        Map<String, Object> dashboard = new HashMap<>();

        dashboard.put("totalEvents", getLong(KEY_EVENT_TOTAL, 0L));
        dashboard.put("actionCounts", getActionCounts());

        String today = TimeSeriesKey.forDay(LocalDateTime.now());
        String dailyKey = KEY_PREFIX + "daily:" + today;
        Map<Object, Object> dailyData = redisTemplate.opsForHash().entries(dailyKey);
        dashboard.put("todayTotal", Long.valueOf(dailyData.getOrDefault("total", "0").toString()));
        dashboard.put("todayHit", Long.valueOf(dailyData.getOrDefault("hit", "0").toString()));

        return dashboard;
    }

    public Map<String, Object> getTimeSeriesData(String granularityCode, List<String> ruleCodes) {
        Granularity g = Granularity.fromCode(granularityCode);
        LocalDateTime now = LocalDateTime.now();

        List<String> labels = new ArrayList<>();
        List<Map<String, Object>> datasets = new ArrayList<>();

        String[] colors = {"#1677ff", "#52c41a", "#faad14", "#ff4d4f", "#722ed1", "#13c2c2", "#eb2f96", "#fa8c16"};

        for (int i = 0; i < ruleCodes.size(); i++) {
            String ruleCode = ruleCodes.get(i);
            List<Long> data = new ArrayList<>();

            for (int j = g.keepCount - 1; j >= 0; j--) {
                LocalDateTime time = now.minus(j,
                    g == Granularity.MINUTE ? java.time.temporal.ChronoUnit.MINUTES :
                    g == Granularity.HOUR ? java.time.temporal.ChronoUnit.HOURS :
                    java.time.temporal.ChronoUnit.DAYS);

                if (i == 0) {
                    labels.add(g.format(time));
                }

                String key = KEY_RULE_HIT + ruleCode + ":" + g.code + ":" + g.format(time);
                data.add(getLong(key, 0L));
            }

            datasets.add(Map.of(
                "ruleCode", ruleCode,
                "color", colors[i % colors.length],
                "data", data
            ));
        }

        return Map.of(
            "labels", labels,
            "granularity", g.code,
            "keepCount", g.keepCount,
            "datasets", datasets
        );
    }

    private long getLong(String key, long defaultValue) {
        try {
            String val = redisTemplate.opsForValue().get(key);
            return val != null ? Long.parseLong(val) : defaultValue;
        } catch (Exception e) {
            return defaultValue;
        }
    }

    private void incr(String key) {
        try {
            redisTemplate.opsForValue().increment(key);
        } catch (Exception e) {
            log.warn("Failed to incr key: {}", key, e);
        }
    }

    private void incrBy(String key, long value) {
        try {
            redisTemplate.opsForValue().increment(key, value);
        } catch (Exception e) {
            log.warn("Failed to incrBy key: {}", key, e);
        }
    }

    private void incrHash(String key, String hashKey, long value) {
        try {
            redisTemplate.opsForHash().increment(key, hashKey, value);
        } catch (Exception e) {
            log.warn("Failed to incrHash key: {}, hashKey: {}", key, hashKey, e);
        }
    }

    private void expire(String key, long timeout, TimeUnit unit) {
        try {
            redisTemplate.expire(key, timeout, unit);
        } catch (Exception e) {
            log.warn("Failed to set expire on key: {}", key, e);
        }
    }

    public void incrByRaw(String key, long value) {
        incrBy(key, value);
    }

    public long getRawLong(String key, long defaultValue) {
        return getLong(key, defaultValue);
    }
}
