package com.replay.detector.service;

import com.replay.detector.model.AttackTrace;
import com.replay.detector.model.TrendReport;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.data.redis.core.StringRedisTemplate;
import org.springframework.stereotype.Service;

import java.time.Instant;
import java.time.LocalDateTime;
import java.time.ZoneId;
import java.util.*;
import java.util.concurrent.TimeUnit;
import java.util.stream.Collectors;

@Slf4j
@Service
@RequiredArgsConstructor
public class TrendAnalysisService {

    private static final String ATTACK_EVENT_PREFIX = "replay:trend:event:";
    private static final String HOURLY_STATS_PREFIX = "replay:trend:hourly:";
    private static final String DAILY_STATS_KEY = "replay:trend:daily:";
    private static final String PREVIOUS_PERIOD_KEY = "replay:trend:prev:total";

    private final StringRedisTemplate redisTemplate;
    private final AttackTracingService attackTracingService;

    public void recordAttackEvent(String clientIp, String path, String fingerprintHash, int replayCount) {
        long now = System.currentTimeMillis();
        LocalDateTime ldt = LocalDateTime.ofInstant(Instant.ofEpochMilli(now), ZoneId.systemDefault());
        int hour = ldt.getHour();
        String dateKey = ldt.toLocalDate().toString();

        String eventKey = ATTACK_EVENT_PREFIX + dateKey;
        redisTemplate.opsForHash().increment(eventKey, "total", 1);

        String hourlyKey = HOURLY_STATS_PREFIX + dateKey;
        redisTemplate.opsForHash().increment(hourlyKey, "h:" + hour + ":attacks", 1);
        redisTemplate.opsForHash().increment(hourlyKey, "h:" + hour + ":ips:" + clientIp, 1);

        String ipField = "ip:" + clientIp;
        String currentCount = (String) redisTemplate.opsForHash().get(eventKey, ipField);
        if (currentCount == null) {
            redisTemplate.opsForHash().increment(eventKey, "uniqueIps", 1);
        }
        redisTemplate.opsForHash().increment(eventKey, ipField, 1);

        String pathField = "path:" + path;
        redisTemplate.opsForHash().increment(eventKey, pathField, 1);

        String fpField = "fp:" + fingerprintHash;
        String fpCount = (String) redisTemplate.opsForHash().get(eventKey, fpField);
        if (fpCount == null) {
            redisTemplate.opsForHash().increment(eventKey, "uniqueFps", 1);
        }
        redisTemplate.opsForHash().increment(eventKey, fpField, 1);

        redisTemplate.expire(eventKey, 7, TimeUnit.DAYS);
        redisTemplate.expire(hourlyKey, 7, TimeUnit.DAYS);
    }

    public TrendReport generateReport(long periodStartMs, long periodEndMs) {
        long now = System.currentTimeMillis();
        if (periodStartMs <= 0) periodStartMs = now - 86400000L;
        if (periodEndMs <= 0) periodEndMs = now;

        LocalDateTime start = LocalDateTime.ofInstant(Instant.ofEpochMilli(periodStartMs), ZoneId.systemDefault());
        LocalDateTime end = LocalDateTime.ofInstant(Instant.ofEpochMilli(periodEndMs), ZoneId.systemDefault());

        int totalAttacks = 0;
        Set<String> uniqueIps = new HashSet<>();
        Set<String> uniqueFps = new HashSet<>();
        Map<String, Integer> pathCounts = new HashMap<>();
        Map<String, Integer> ipCounts = new HashMap<>();
        Map<Integer, int[]> hourlyData = new HashMap<>();
        Map<String, Integer> patternDistribution = new HashMap<>();

        for (LocalDateTime date = start.toLocalDate().atStartOfDay();
             !date.isAfter(end.toLocalDate().atStartOfDay());
             date = date.plusDays(1)) {

            String dateKey = date.toLocalDate().toString();
            String eventKey = ATTACK_EVENT_PREFIX + dateKey;
            String hourlyKey = HOURLY_STATS_PREFIX + dateKey;

            Map<Object, Object> eventData = redisTemplate.opsForHash().entries(eventKey);
            if (eventData == null) continue;

            totalAttacks += parseIntSafe(eventData.get("total"), 0);

            for (Map.Entry<Object, Object> entry : eventData.entrySet()) {
                String field = entry.getKey().toString();
                int count = parseIntSafe(entry.getValue(), 0);

                if (field.startsWith("ip:")) {
                    String ip = field.substring(3);
                    uniqueIps.add(ip);
                    ipCounts.merge(ip, count, Integer::sum);
                } else if (field.startsWith("path:")) {
                    String path = field.substring(5);
                    pathCounts.merge(path, count, Integer::sum);
                } else if (field.startsWith("fp:")) {
                    uniqueFps.add(field.substring(3));
                }
            }

            Map<Object, Object> hourlyMap = redisTemplate.opsForHash().entries(hourlyKey);
            if (hourlyMap != null) {
                for (Map.Entry<Object, Object> entry : hourlyMap.entrySet()) {
                    String field = entry.getKey().toString();
                    if (field.startsWith("h:") && field.contains(":attacks")) {
                        int hour = Integer.parseInt(field.split(":")[1]);
                        int count = parseIntSafe(entry.getValue(), 0);
                        hourlyData.computeIfAbsent(hour, k -> new int[2])[0] += count;
                    } else if (field.startsWith("h:") && field.contains(":ips:")) {
                        String[] parts = field.split(":");
                        int hour = Integer.parseInt(parts[1]);
                        hourlyData.computeIfAbsent(hour, k -> new int[2])[1]++;
                    }
                }
            }
        }

        List<TrendReport.HourlyDistribution> hourlyList = new ArrayList<>();
        for (int h = 0; h < 24; h++) {
            int[] data = hourlyData.getOrDefault(h, new int[2]);
            hourlyList.add(TrendReport.HourlyDistribution.builder()
                    .hour(h)
                    .attackCount(data[0])
                    .uniqueIpCount(data[1])
                    .build());
        }

        List<TrendReport.IpAttackSummary> topIps = ipCounts.entrySet().stream()
                .sorted(Map.Entry.<String, Integer>comparingByValue().reversed())
                .limit(10)
                .map(entry -> {
                    AttackTrace trace = attackTracingService.getTrace(entry.getKey());
                    return TrendReport.IpAttackSummary.builder()
                            .ip(entry.getKey())
                            .attackCount(entry.getValue())
                            .riskLevel(trace != null ? trace.getRiskLevel() : "LOW")
                            .dominantPattern(trace != null ? trace.getAttackPattern().getPatternType() : AttackTrace.PatternType.UNKNOWN)
                            .build();
                })
                .collect(Collectors.toList());

        List<TrendReport.PathAttackSummary> topPaths = pathCounts.entrySet().stream()
                .sorted(Map.Entry.<String, Integer>comparingByValue().reversed())
                .limit(10)
                .map(entry -> TrendReport.PathAttackSummary.builder()
                        .path(entry.getKey())
                        .attackCount(entry.getValue())
                        .uniqueIpCount(0)
                        .build())
                .collect(Collectors.toList());

        long periodMinutes = Math.max(1, (periodEndMs - periodStartMs) / 60000);
        double attacksPerMinute = (double) totalAttacks / periodMinutes;

        TrendReport.TrendDirection direction = computeTrendDirection(totalAttacks, periodStartMs, periodEndMs);
        double trendChange = computeTrendChange(totalAttacks, periodStartMs, periodEndMs);

        return TrendReport.builder()
                .reportId(UUID.randomUUID().toString())
                .generatedAt(now)
                .periodStart(periodStartMs)
                .periodEnd(periodEndMs)
                .totalAttacks(totalAttacks)
                .uniqueSourceIps(uniqueIps.size())
                .uniqueFingerprints(uniqueFps.size())
                .hourlyDistribution(hourlyList)
                .topAttackIps(topIps)
                .topTargetPaths(topPaths)
                .patternTypeDistribution(patternDistribution)
                .attacksPerMinute(attacksPerMinute)
                .trendDirection(direction)
                .trendChangePercent(trendChange)
                .build();
    }

    private TrendReport.TrendDirection computeTrendDirection(int currentTotal, long periodStart, long periodEnd) {
        long periodLength = periodEnd - periodStart;
        long prevEnd = periodStart;
        long prevStart = prevEnd - periodLength;

        String prevKey = DAILY_STATS_KEY + LocalDateTime.ofInstant(
                Instant.ofEpochMilli(prevStart), ZoneId.systemDefault()).toLocalDate();
        String prevTotal = (String) redisTemplate.opsForHash().get(prevKey, "total");

        if (prevTotal == null) return TrendReport.TrendDirection.STABLE;

        int prev = Integer.parseInt(prevTotal);
        if (currentTotal > prev * 3) return TrendReport.TrendDirection.SPIKE;
        if (currentTotal > prev * 1.2) return TrendReport.TrendDirection.INCREASING;
        if (currentTotal < prev * 0.8) return TrendReport.TrendDirection.DECREASING;
        return TrendReport.TrendDirection.STABLE;
    }

    private double computeTrendChange(int currentTotal, long periodStart, long periodEnd) {
        long periodLength = periodEnd - periodStart;
        long prevStart = periodStart - periodLength;

        String prevKey = DAILY_STATS_KEY + LocalDateTime.ofInstant(
                Instant.ofEpochMilli(prevStart), ZoneId.systemDefault()).toLocalDate();
        String prevTotal = (String) redisTemplate.opsForHash().get(prevKey, "total");

        if (prevTotal == null || Integer.parseInt(prevTotal) == 0) return 0.0;
        int prev = Integer.parseInt(prevTotal);
        return ((double) (currentTotal - prev) / prev) * 100;
    }

    public List<TrendReport.HourlyDistribution> getPeakHours(int topN) {
        TrendReport report = generateReport(
                System.currentTimeMillis() - 86400000L, System.currentTimeMillis());

        return report.getHourlyDistribution().stream()
                .sorted(Comparator.comparingInt(TrendReport.HourlyDistribution::getAttackCount).reversed())
                .limit(topN)
                .collect(Collectors.toList());
    }

    private int parseIntSafe(Object obj, int defaultValue) {
        if (obj == null) return defaultValue;
        try { return Integer.parseInt(obj.toString()); } catch (NumberFormatException e) { return defaultValue; }
    }
}
