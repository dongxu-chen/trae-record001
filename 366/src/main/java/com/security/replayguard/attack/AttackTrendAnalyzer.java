package com.security.replayguard.attack;

import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.data.redis.core.StringRedisTemplate;
import org.springframework.stereotype.Component;

import java.util.*;
import java.util.stream.Collectors;

@Slf4j
@Component
@RequiredArgsConstructor
public class AttackTrendAnalyzer {

    private static final String TREND_HOURLY_PREFIX = "replay:trend:hourly:";
    private static final String TREND_DAILY_PREFIX = "replay:trend:daily:";
    private static final String STAT_SUMMARY_KEY = "replay:trend:summary";

    private final StringRedisTemplate redisTemplate;
    private final AttackTraceService attackTraceService;

    public void recordAttackEvent(String attackType, String ip, String userId) {
        long now = System.currentTimeMillis() / 1000;
        long hourBucket = now / 3600;
        long dayBucket = now / 86400;

        recordHourlyStat(hourBucket, attackType, ip, userId);
        recordDailyStat(dayBucket, attackType, ip, userId);
        updateSummary(attackType);
    }

    private void recordHourlyStat(long hourBucket, String attackType, String ip, String userId) {
        String hourKey = TREND_HOURLY_PREFIX + hourBucket;

        redisTemplate.opsForHash().increment(hourKey, attackType, 1);
        redisTemplate.opsForHash().increment(hourKey, "total", 1);

        String ipKey = hourKey + ":ips";
        redisTemplate.opsForHyperLogLog().add(ipKey, ip);

        if (userId != null && !userId.isEmpty()) {
            String userKey = hourKey + ":users";
            redisTemplate.opsForHyperLogLog().add(userKey, userId);
        }

        redisTemplate.expire(hourKey, 7, java.util.concurrent.TimeUnit.DAYS);
    }

    private void recordDailyStat(long dayBucket, String attackType, String ip, String userId) {
        String dayKey = TREND_DAILY_PREFIX + dayBucket;

        redisTemplate.opsForHash().increment(dayKey, attackType, 1);
        redisTemplate.opsForHash().increment(dayKey, "total", 1);

        String ipKey = dayKey + ":ips";
        redisTemplate.opsForHyperLogLog().add(ipKey, ip);

        if (userId != null && !userId.isEmpty()) {
            String userKey = dayKey + ":users";
            redisTemplate.opsForHyperLogLog().add(userKey, userId);
        }

        redisTemplate.expire(dayKey, 30, java.util.concurrent.TimeUnit.DAYS);
    }

    private void updateSummary(String attackType) {
        redisTemplate.opsForHash().increment(STAT_SUMMARY_KEY, attackType, 1);
        redisTemplate.opsForHash().increment(STAT_SUMMARY_KEY, "total", 1);
        redisTemplate.opsForHash().put(STAT_SUMMARY_KEY, "lastUpdate", String.valueOf(System.currentTimeMillis() / 1000));
    }

    public HourlyTrend getHourlyTrend(int hours) {
        HourlyTrend trend = new HourlyTrend();
        long now = System.currentTimeMillis() / 1000;
        long currentHour = now / 3600;

        Map<Long, HourlyStats> hourlyStats = new LinkedHashMap<>();

        for (int i = hours - 1; i >= 0; i--) {
            long hourBucket = currentHour - i;
            String hourKey = TREND_HOURLY_PREFIX + hourBucket;

            HourlyStats stats = new HourlyStats();
            stats.setHour(hourBucket);
            stats.setHourStart(hourBucket * 3600);

            Map<Object, Object> data = redisTemplate.opsForHash().entries(hourKey);
            stats.setTotalAttacks(parseLong(data.get("total")));

            Map<String, Long> attackBreakdown = new HashMap<>();
            for (AttackEvent.AttackType type : AttackEvent.AttackType.values()) {
                long count = parseLong(data.get(type.getCode()));
                if (count > 0) {
                    attackBreakdown.put(type.getCode(), count);
                }
            }
            stats.setAttackBreakdown(attackBreakdown);

            String ipKey = hourKey + ":ips";
            Long uniqueIps = redisTemplate.opsForHyperLogLog().size(ipKey);
            stats.setUniqueIpCount(uniqueIps != null ? uniqueIps : 0);

            String userKey = hourKey + ":users";
            Long uniqueUsers = redisTemplate.opsForHyperLogLog().size(userKey);
            stats.setUniqueUserCount(uniqueUsers != null ? uniqueUsers : 0);

            hourlyStats.put(hourBucket, stats);
        }

        trend.setHours(hours);
        trend.setHourlyStats(hourlyStats);

        List<HourlyStats> statsList = new ArrayList<>(hourlyStats.values());
        if (!statsList.isEmpty()) {
            long total = statsList.stream().mapToLong(HourlyStats::getTotalAttacks).sum();
            trend.setTotalAttacks(total);
            trend.setAveragePerHour((double) total / hours);
            trend.setPeakHourAttacks(statsList.stream()
                    .mapToLong(HourlyStats::getTotalAttacks)
                    .max().orElse(0));

            double sum = 0;
            double mean = (double) total / hours;
            for (HourlyStats s : statsList) {
                sum += Math.pow(s.getTotalAttacks() - mean, 2);
            }
            trend.setStdDeviation(Math.sqrt(sum / hours));
        }

        return trend;
    }

    public DailyTrend getDailyTrend(int days) {
        DailyTrend trend = new DailyTrend();
        long now = System.currentTimeMillis() / 1000;
        long currentDay = now / 86400;

        Map<Long, DailyStats> dailyStats = new LinkedHashMap<>();

        for (int i = days - 1; i >= 0; i--) {
            long dayBucket = currentDay - i;
            String dayKey = TREND_DAILY_PREFIX + dayBucket;

            DailyStats stats = new DailyStats();
            stats.setDay(dayBucket);
            stats.setDayStart(dayBucket * 86400);

            Map<Object, Object> data = redisTemplate.opsForHash().entries(dayKey);
            stats.setTotalAttacks(parseLong(data.get("total")));

            Map<String, Long> attackBreakdown = new HashMap<>();
            for (AttackEvent.AttackType type : AttackEvent.AttackType.values()) {
                long count = parseLong(data.get(type.getCode()));
                if (count > 0) {
                    attackBreakdown.put(type.getCode(), count);
                }
            }
            stats.setAttackBreakdown(attackBreakdown);

            String ipKey = dayKey + ":ips";
            Long uniqueIps = redisTemplate.opsForHyperLogLog().size(ipKey);
            stats.setUniqueIpCount(uniqueIps != null ? uniqueIps : 0);

            String userKey = dayKey + ":users";
            Long uniqueUsers = redisTemplate.opsForHyperLogLog().size(userKey);
            stats.setUniqueUserCount(uniqueUsers != null ? uniqueUsers : 0);

            dailyStats.put(dayBucket, stats);
        }

        trend.setDays(days);
        trend.setDailyStats(dailyStats);

        List<DailyStats> statsList = new ArrayList<>(dailyStats.values());
        if (!statsList.isEmpty()) {
            long total = statsList.stream().mapToLong(DailyStats::getTotalAttacks).sum();
            trend.setTotalAttacks(total);
            trend.setAveragePerDay((double) total / days);
        }

        return trend;
    }

    public TimePatternAnalysis analyzeTimePatterns(int hours) {
        TimePatternAnalysis analysis = new TimePatternAnalysis();

        HourlyTrend trend = getHourlyTrend(hours);
        List<HourlyStats> statsList = new ArrayList<>(trend.getHourlyStats().values());

        Map<Integer, Long> hourOfDayDistribution = new HashMap<>();
        for (HourlyStats stats : statsList) {
            int hourOfDay = (int) ((stats.getHourStart() % 86400) / 3600);
            hourOfDayDistribution.merge(hourOfDay, stats.getTotalAttacks(), Long::sum);
        }
        analysis.setHourOfDayDistribution(hourOfDayDistribution);

        if (!hourOfDayDistribution.isEmpty()) {
            List<Map.Entry<Integer, Long>> sortedHours = hourOfDayDistribution.entrySet()
                    .stream()
                    .sorted(Map.Entry.<Integer, Long>comparingByValue().reversed())
                    .collect(Collectors.toList());

            analysis.setPeakHours(sortedHours.stream()
                    .limit(3)
                    .map(Map.Entry::getKey)
                    .collect(Collectors.toList()));

            analysis.setQuietHours(sortedHours.stream()
                    .skip(Math.max(0, sortedHours.size() - 3))
                    .limit(3)
                    .map(Map.Entry::getKey)
                    .collect(Collectors.toList()));
        }

        long consecutiveIncreases = 0;
        long maxIncrease = 0;
        for (int i = 1; i < statsList.size(); i++) {
            long prev = statsList.get(i - 1).getTotalAttacks();
            long curr = statsList.get(i).getTotalAttacks();
            if (curr > prev) {
                consecutiveIncreases++;
                maxIncrease = Math.max(maxIncrease, consecutiveIncreases);
            } else {
                consecutiveIncreases = 0;
            }
        }
        analysis.setMaxConsecutiveIncreases(maxIncrease);

        long totalAttacks = trend.getTotalAttacks();
        if (totalAttacks > 0) {
            analysis.setAttackRatePerHour(trend.getAveragePerHour());

            List<HourlyStats> recentHours = statsList.stream()
                    .skip(Math.max(0, statsList.size() - 6))
                    .collect(Collectors.toList());
            long recentTotal = recentHours.stream().mapToLong(HourlyStats::getTotalAttacks).sum();
            double recentAverage = (double) recentTotal / recentHours.size();

            double trendDirection = recentAverage / Math.max(1, trend.getAveragePerHour());
            analysis.setTrendDirection(trendDirection);
            analysis.setTrendingUp(trendDirection > 1.2);
            analysis.setTrendingDown(trendDirection < 0.8);
        }

        return analysis;
    }

    public AttackSummary getSummary() {
        AttackSummary summary = new AttackSummary();

        Map<Object, Object> data = redisTemplate.opsForHash().entries(STAT_SUMMARY_KEY);
        summary.setTotalAttacks(parseLong(data.get("total")));
        summary.setLastUpdateTime(parseLong(data.get("lastUpdate")));

        Map<String, Long> attackBreakdown = new HashMap<>();
        for (AttackEvent.AttackType type : AttackEvent.AttackType.values()) {
            long count = parseLong(data.get(type.getCode()));
            if (count > 0) {
                attackBreakdown.put(type.getCode(), count);
            }
        }
        summary.setAttackBreakdown(attackBreakdown);

        HourlyTrend hourlyTrend = getHourlyTrend(24);
        summary.setLast24hAttacks(hourlyTrend.getTotalAttacks());

        DailyTrend dailyTrend = getDailyTrend(7);
        summary.setLast7dAttacks(dailyTrend.getTotalAttacks());

        return summary;
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
    public static class HourlyStats {
        private long hour;
        private long hourStart;
        private long totalAttacks;
        private long uniqueIpCount;
        private long uniqueUserCount;
        private Map<String, Long> attackBreakdown;
    }

    @lombok.Data
    public static class HourlyTrend {
        private int hours;
        private long totalAttacks;
        private double averagePerHour;
        private long peakHourAttacks;
        private double stdDeviation;
        private Map<Long, HourlyStats> hourlyStats;
    }

    @lombok.Data
    public static class DailyStats {
        private long day;
        private long dayStart;
        private long totalAttacks;
        private long uniqueIpCount;
        private long uniqueUserCount;
        private Map<String, Long> attackBreakdown;
    }

    @lombok.Data
    public static class DailyTrend {
        private int days;
        private long totalAttacks;
        private double averagePerDay;
        private Map<Long, DailyStats> dailyStats;
    }

    @lombok.Data
    public static class TimePatternAnalysis {
        private Map<Integer, Long> hourOfDayDistribution;
        private List<Integer> peakHours;
        private List<Integer> quietHours;
        private long maxConsecutiveIncreases;
        private double attackRatePerHour;
        private double trendDirection;
        private boolean trendingUp;
        private boolean trendingDown;
    }

    @lombok.Data
    public static class AttackSummary {
        private long totalAttacks;
        private long last24hAttacks;
        private long last7dAttacks;
        private long lastUpdateTime;
        private Map<String, Long> attackBreakdown;
    }
}
