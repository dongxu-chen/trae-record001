package com.quota.management.service;

import com.quota.management.entity.QuotaProfile;
import com.quota.management.entity.QuotaProfile.Anomaly;
import com.quota.management.entity.QuotaProfile.TrendPrediction;
import com.quota.management.entity.QuotaProfile.UsageStatistics;
import com.quota.management.entity.QuotaUsage;
import com.quota.management.entity.QuotaUsageHistory;
import com.quota.management.entity.TenantQuota;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.data.redis.core.RedisTemplate;
import org.springframework.scheduling.annotation.Scheduled;
import org.springframework.stereotype.Service;

import java.time.LocalDateTime;
import java.time.ZoneOffset;
import java.util.*;
import java.util.concurrent.TimeUnit;
import java.util.stream.Collectors;

@Slf4j
@Service
@RequiredArgsConstructor
public class QuotaProfileService {

    private static final String HISTORY_PREFIX = "quota:history:";
    private static final String PROFILE_PREFIX = "quota:profile:";
    private static final String ANOMALY_PREFIX = "quota:anomaly:";

    private final RedisTemplate<String, Object> redisTemplate;
    private final QuotaManagementService quotaManagementService;

    @Scheduled(fixedRate = 60000)
    public void collectUsageMetrics() {
        List<TenantQuota> tenants = quotaManagementService.getAllTenantQuotas();
        long timestamp = System.currentTimeMillis() / 1000;
        LocalDateTime now = LocalDateTime.now();

        for (TenantQuota tenant : tenants) {
            try {
                QuotaUsage usage = quotaManagementService.getQuotaUsage(tenant.getTenantId());

                saveHistoryPoint(tenant.getTenantId(), "minute", timestamp, now,
                        usage.getMinuteUsed(), tenant.getMinuteLimit());
                saveHistoryPoint(tenant.getTenantId(), "hour", timestamp, now,
                        usage.getHourUsed(), tenant.getHourLimit());
                saveHistoryPoint(tenant.getTenantId(), "day", timestamp, now,
                        usage.getDayUsed(), tenant.getDayLimit());

            } catch (Exception e) {
                log.error("Failed to collect metrics for tenant {}", tenant.getTenantId(), e);
            }
        }

        log.debug("Collected usage metrics for {} tenants", tenants.size());
    }

    private void saveHistoryPoint(String tenantId, String granularity, long timestamp,
                                   LocalDateTime dateTime, long used, long limit) {
        QuotaUsageHistory point = QuotaUsageHistory.builder()
                .tenantId(tenantId)
                .granularity(granularity)
                .timestamp(timestamp)
                .dateTime(dateTime)
                .used(used)
                .limit(limit)
                .usageRate(limit > 0 ? (double) used / limit : 0)
                .build();

        String key = HISTORY_PREFIX + tenantId + ":" + granularity;
        redisTemplate.opsForZSet().add(key, point, timestamp);
        redisTemplate.expire(key, 30, TimeUnit.DAYS);
        redisTemplate.opsForZSet().removeRangeByScore(key, 0, timestamp - 2592000);
    }

    public QuotaProfile generateProfile(String tenantId) {
        TenantQuota tenant = quotaManagementService.getTenantQuota(tenantId);
        if (tenant == null) {
            throw new RuntimeException("Tenant not found");
        }

        Map<String, UsageStatistics> stats = new HashMap<>();
        Map<String, TrendPrediction> predictions = new HashMap<>();
        List<Anomaly> anomalies = new ArrayList<>();

        for (String granularity : Arrays.asList("minute", "hour", "day")) {
            List<QuotaUsageHistory> history = getHistory(tenantId, granularity, 100);
            if (!history.isEmpty()) {
                stats.put(granularity, calculateStatistics(history));
                predictions.put(granularity, predictTrend(history, granularity));
                anomalies.addAll(detectAnomalies(history, granularity));
            }
        }

        double stabilityScore = calculateStabilityScore(stats);
        double efficiencyScore = calculateEfficiencyScore(tenantId, stats);
        String profileLevel = determineProfileLevel(stabilityScore, efficiencyScore);
        String recommendation = generateRecommendation(tenantId, stats, predictions, anomalies);

        QuotaProfile profile = QuotaProfile.builder()
                .tenantId(tenantId)
                .tenantName(tenant.getTenantName())
                .statistics(stats)
                .predictions(predictions)
                .anomalies(anomalies)
                .stabilityScore(stabilityScore)
                .efficiencyScore(efficiencyScore)
                .profileLevel(profileLevel)
                .recommendation(recommendation)
                .build();

        String profileKey = PROFILE_PREFIX + tenantId;
        redisTemplate.opsForValue().set(profileKey, profile, 1, TimeUnit.HOURS);

        return profile;
    }

    public List<QuotaUsageHistory> getHistory(String tenantId, String granularity, int limit) {
        String key = HISTORY_PREFIX + tenantId + ":" + granularity;
        Set<Object> members = redisTemplate.opsForZSet().reverseRange(key, 0, limit - 1);
        if (members == null) return List.of();

        List<QuotaUsageHistory> history = new ArrayList<>();
        for (Object member : members) {
            if (member instanceof QuotaUsageHistory) {
                history.add((QuotaUsageHistory) member);
            }
        }
        Collections.reverse(history);
        return history;
    }

    private UsageStatistics calculateStatistics(List<QuotaUsageHistory> history) {
        if (history.isEmpty()) return null;

        List<Double> values = history.stream()
                .map(QuotaUsageHistory::getUsageRate)
                .collect(Collectors.toList());

        double sum = values.stream().mapToDouble(Double::doubleValue).sum();
        double average = sum / values.size();
        double peak = values.stream().mapToDouble(Double::doubleValue).max().orElse(0);
        double trough = values.stream().mapToDouble(Double::doubleValue).min().orElse(0);

        double variance = values.stream()
                .mapToDouble(v -> Math.pow(v - average, 2))
                .average()
                .orElse(0);
        double stdDev = Math.sqrt(variance);

        List<Double> sorted = new ArrayList<>(values);
        Collections.sort(sorted);
        double p95 = percentile(sorted, 0.95);
        double p99 = percentile(sorted, 0.99);

        Map<Integer, Long> hourUsage = new HashMap<>();
        for (QuotaUsageHistory h : history) {
            int hour = h.getDateTime().getHour();
            hourUsage.merge(hour, h.getUsed(), Long::sum);
        }
        int peakHour = hourUsage.entrySet().stream()
                .max(Map.Entry.comparingByValue())
                .map(Map.Entry::getKey)
                .orElse(0);
        int troughHour = hourUsage.entrySet().stream()
                .min(Map.Entry.comparingByValue())
                .map(Map.Entry::getKey)
                .orElse(0);

        return UsageStatistics.builder()
                .totalUsed((long) history.stream().mapToLong(QuotaUsageHistory::getUsed).sum())
                .average(average)
                .peak(peak)
                .trough(trough)
                .variance(variance)
                .standardDeviation(stdDev)
                .percentile95(p95)
                .percentile99(p99)
                .peakHour(peakHour)
                .troughHour(troughHour)
                .build();
    }

    private double percentile(List<Double> sorted, double p) {
        if (sorted.isEmpty()) return 0;
        int index = (int) Math.ceil(p * sorted.size()) - 1;
        return sorted.get(Math.min(index, sorted.size() - 1));
    }

    private TrendPrediction predictTrend(List<QuotaUsageHistory> history, String granularity) {
        if (history.size() < 5) {
            return TrendPrediction.builder()
                    .granularity(granularity)
                    .currentTrend(0)
                    .predictedNextHour(0)
                    .predictedNextDay(0)
                    .predictedNextWeek(0)
                    .trendDirection(0)
                    .confidence(0)
                    .historicalData(List.of())
                    .predictedData(List.of())
                    .build();
        }

        int n = history.size();
        List<Long> historicalUsage = history.stream()
                .map(QuotaUsageHistory::getUsed)
                .collect(Collectors.toList());

        double sumX = 0, sumY = 0, sumXY = 0, sumX2 = 0;
        for (int i = 0; i < n; i++) {
            sumX += i;
            sumY += historicalUsage.get(i);
            sumXY += i * historicalUsage.get(i);
            sumX2 += (double) i * i;
        }

        double slope = (n * sumXY - sumX * sumY) / (n * sumX2 - sumX * sumX);
        double intercept = (sumY - slope * sumX) / n;

        double currentTrend = slope;
        double trendDirection = Math.signum(slope);

        double lastValue = historicalUsage.get(n - 1);
        double predictedNextHour = Math.max(0, lastValue + slope * 1);
        double predictedNextDay = Math.max(0, lastValue + slope * 24);
        double predictedNextWeek = Math.max(0, lastValue + slope * 168);

        double confidence = calculateConfidence(history, slope, intercept);

        List<Double> predictedData = new ArrayList<>();
        for (int i = 0; i < 10; i++) {
            predictedData.add(Math.max(0, intercept + slope * (n + i)));
        }

        return TrendPrediction.builder()
                .granularity(granularity)
                .currentTrend(currentTrend)
                .predictedNextHour(predictedNextHour)
                .predictedNextDay(predictedNextDay)
                .predictedNextWeek(predictedNextWeek)
                .trendDirection(trendDirection)
                .confidence(confidence)
                .historicalData(historicalUsage)
                .predictedData(predictedData)
                .build();
    }

    private double calculateConfidence(List<QuotaUsageHistory> history, double slope, double intercept) {
        if (history.size() < 5) return 0.5;

        double sumSquaredError = 0;
        for (int i = 0; i < history.size(); i++) {
            double predicted = intercept + slope * i;
            double actual = history.get(i).getUsed();
            sumSquaredError += Math.pow(predicted - actual, 2);
        }

        double meanSquaredError = sumSquaredError / history.size();
        double maxValue = history.stream().mapToLong(QuotaUsageHistory::getUsed).max().orElse(1);
        double normalizedError = Math.sqrt(meanSquaredError) / maxValue;

        return Math.max(0, Math.min(1, 1 - normalizedError * 2));
    }

    private List<Anomaly> detectAnomalies(List<QuotaUsageHistory> history, String granularity) {
        List<Anomaly> anomalies = new ArrayList<>();
        if (history.size() < 10) return anomalies;

        List<Double> values = history.stream()
                .map(QuotaUsageHistory::getUsageRate)
                .collect(Collectors.toList());

        double mean = values.stream().mapToDouble(Double::doubleValue).average().orElse(0);
        double variance = values.stream()
                .mapToDouble(v -> Math.pow(v - mean, 2))
                .average()
                .orElse(0);
        double stdDev = Math.sqrt(variance);

        double threshold = mean + 2 * stdDev;

        for (int i = Math.max(0, history.size() - 24); i < history.size(); i++) {
            QuotaUsageHistory h = history.get(i);
            if (h.getUsageRate() > threshold && threshold > 0.1) {
                double deviation = (h.getUsageRate() - mean) / (stdDev > 0 ? stdDev : 1);
                String severity = deviation > 3 ? "CRITICAL" : deviation > 2 ? "WARNING" : "INFO";

                anomalies.add(Anomaly.builder()
                        .type("SPIKE")
                        .granularity(granularity)
                        .timestamp(h.getTimestamp())
                        .expected(mean)
                        .actual(h.getUsageRate())
                        .deviation(deviation)
                        .severity(severity)
                        .build());
            }
        }

        return anomalies;
    }

    private double calculateStabilityScore(Map<String, UsageStatistics> stats) {
        if (!stats.containsKey("hour")) return 0.5;
        UsageStatistics hourStats = stats.get("hour");
        double cv = hourStats.getAverage() > 0 ?
                hourStats.getStandardDeviation() / hourStats.getAverage() : 1;
        return Math.max(0, Math.min(1, 1 - cv * 2));
    }

    private double calculateEfficiencyScore(String tenantId, Map<String, UsageStatistics> stats) {
        if (!stats.containsKey("day")) return 0.5;
        UsageStatistics dayStats = stats.get("day");
        double avgUsage = dayStats.getAverage();
        double peakUsage = dayStats.getPeak();
        double wasteRatio = peakUsage > 0 ? (peakUsage - avgUsage) / peakUsage : 0;
        return Math.max(0, Math.min(1, 1 - wasteRatio * 0.5));
    }

    private String determineProfileLevel(double stability, double efficiency) {
        double composite = (stability + efficiency) / 2;
        if (composite >= 0.8) return "ELITE";
        if (composite >= 0.6) return "GOLD";
        if (composite >= 0.4) return "SILVER";
        return "BRONZE";
    }

    private String generateRecommendation(String tenantId, Map<String, UsageStatistics> stats,
                                           Map<String, TrendPrediction> predictions, List<Anomaly> anomalies) {
        List<String> recommendations = new ArrayList<>();

        if (predictions.containsKey("day")) {
            TrendPrediction dayPred = predictions.get("day");
            if (dayPred.getTrendDirection() > 0 && dayPred.getConfidence() > 0.7) {
                recommendations.add("用量呈上升趋势，建议增加日配额或考虑购买更多配额");
            }
        }

        if (stats.containsKey("hour")) {
            UsageStatistics hourStats = stats.get("hour");
            if (hourStats.getPeak() > 0.9) {
                recommendations.add("存在高峰时段（" + hourStats.getPeakHour() + "点），建议错峰调用或增加配额");
            }
        }

        long criticalAnomalies = anomalies.stream().filter(a -> "CRITICAL".equals(a.getSeverity())).count();
        if (criticalAnomalies > 0) {
            recommendations.add("检测到" + criticalAnomalies + "个严重异常点，建议检查调用模式");
        }

        if (recommendations.isEmpty()) {
            recommendations.add("配额使用健康，模式稳定");
        }

        return String.join("；", recommendations);
    }

    public QuotaProfile getCachedProfile(String tenantId) {
        String profileKey = PROFILE_PREFIX + tenantId;
        Object obj = redisTemplate.opsForValue().get(profileKey);
        if (obj instanceof QuotaProfile) {
            return (QuotaProfile) obj;
        }
        return generateProfile(tenantId);
    }
}
