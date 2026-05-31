package com.datacheck.service;

import com.datacheck.check.CheckEngine;
import com.datacheck.model.CheckReport;
import com.datacheck.model.CheckResult;
import com.datacheck.model.DiffResult;
import com.datacheck.model.enums.DiffType;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.scheduling.annotation.Scheduled;
import org.springframework.stereotype.Service;

import java.time.LocalDateTime;
import java.time.temporal.ChronoUnit;
import java.util.*;
import java.util.concurrent.ConcurrentHashMap;
import java.util.stream.Collectors;

@Slf4j
@Service
public class PredictiveCheckService {

    private final CheckEngine checkEngine;
    private final ReportService reportService;

    @Value("${check.predictive.enabled:true}")
    private boolean predictiveEnabled;

    @Value("${check.predictive.history-window-hours:24}")
    private int historyWindowHours;

    @Value("${check.predictive.diff-trend-threshold:0.1}")
    private double diffTrendThreshold;

    @Value("${check.predictive.latency-trend-threshold:0.2}")
    private double latencyTrendThreshold;

    private final Map<String, List<TrendDataPoint>> trendData = new ConcurrentHashMap<>();
    private final Map<String, PredictionResult> predictions = new ConcurrentHashMap<>();

    @Autowired
    public PredictiveCheckService(CheckEngine checkEngine, ReportService reportService) {
        this.checkEngine = checkEngine;
        this.reportService = reportService;
    }

    @Scheduled(fixedDelayString = "${check.predictive.analysis-interval-ms:300000}")
    public void analyzeTrends() {
        if (!predictiveEnabled) return;

        Collection<CheckResult> results = checkEngine.getRecentResults();
        LocalDateTime cutoff = LocalDateTime.now().minusHours(historyWindowHours);

        Map<String, List<CheckResult>> resultsByTable = results.stream()
                .filter(r -> r.getEndTime() != null && r.getEndTime().isAfter(cutoff))
                .collect(Collectors.groupingBy(CheckResult::getTableName));

        for (Map.Entry<String, List<CheckResult>> entry : resultsByTable.entrySet()) {
            String tableName = entry.getKey();
            List<CheckResult> tableResults = entry.getValue();

            List<TrendDataPoint> dataPoints = tableResults.stream()
                    .sorted(Comparator.comparing(CheckResult::getEndTime))
                    .map(r -> TrendDataPoint.builder()
                            .timestamp(r.getEndTime())
                            .diffCount(r.getDiffCount())
                            .totalRecords(r.getTotalSourceRecords())
                            .avgLatencyMs(r.getAvgLatencyMs())
                            .maxLatencyMs(r.getMaxLatencyMs())
                            .diffRate(r.getTotalSourceRecords() > 0 ?
                                    (double) r.getDiffCount() / r.getTotalSourceRecords() : 0)
                            .build())
                    .collect(Collectors.toList());

            trendData.put(tableName, dataPoints);

            PredictionResult prediction = generatePrediction(tableName, dataPoints);
            predictions.put(tableName, prediction);

            if (prediction.isAlertTriggered()) {
                log.warn("Predictive alert for table {}: risk={}, recommendation={}",
                        tableName, prediction.getRiskLevel(), prediction.getRecommendation());
            }
        }

        log.debug("Trend analysis completed for {} tables", resultsByTable.size());
    }

    private PredictionResult generatePrediction(String tableName, List<TrendDataPoint> dataPoints) {
        if (dataPoints.size() < 3) {
            return PredictionResult.builder()
                    .tableName(tableName)
                    .analyzedAt(LocalDateTime.now())
                    .riskLevel("LOW")
                    .alertTriggered(false)
                    .recommendation("Insufficient data for prediction, need at least 3 data points")
                    .build();
        }

        double diffTrendRate = calculateTrendRate(dataPoints, TrendDataPoint::getDiffCount);
        double latencyTrendRate = calculateTrendRate(dataPoints, TrendDataPoint::getAvgLatencyMs);
        double diffRateTrend = calculateTrendRate(dataPoints, TrendDataPoint::getDiffRate);

        TrendDataPoint latest = dataPoints.get(dataPoints.size() - 1);
        double predictedDiffCount = predictNextValue(dataPoints, TrendDataPoint::getDiffCount);
        double predictedAvgLatency = predictNextValue(dataPoints, TrendDataPoint::getAvgLatencyMs);

        String riskLevel = assessRiskLevel(diffTrendRate, latencyTrendRate, diffRateTrend, latest);
        boolean alertTriggered = "HIGH".equals(riskLevel) || "CRITICAL".equals(riskLevel);

        String recommendation = generateRecommendation(riskLevel, diffTrendRate, latencyTrendRate, latest);

        LocalDateTime nextCheckSuggestion = calculateNextCheckTime(riskLevel, latest.getTimestamp());

        return PredictionResult.builder()
                .tableName(tableName)
                .analyzedAt(LocalDateTime.now())
                .diffTrendRate(diffTrendRate)
                .latencyTrendRate(latencyTrendRate)
                .diffRateTrend(diffRateTrend)
                .predictedDiffCount(predictedDiffCount)
                .predictedAvgLatency(predictedAvgLatency)
                .currentDiffRate(latest.getDiffRate())
                .currentAvgLatency(latest.getAvgLatencyMs())
                .riskLevel(riskLevel)
                .alertTriggered(alertTriggered)
                .recommendation(recommendation)
                .nextCheckSuggestion(nextCheckSuggestion)
                .dataPoints(dataPoints)
                .build();
    }

    private double calculateTrendRate(List<TrendDataPoint> dataPoints,
                                       java.util.function.ToDoubleFunction<TrendDataPoint> extractor) {
        if (dataPoints.size() < 2) return 0;

        int n = dataPoints.size();
        double sumX = 0, sumY = 0, sumXY = 0, sumX2 = 0;

        for (int i = 0; i < n; i++) {
            double x = i;
            double y = extractor.applyAsDouble(dataPoints.get(i));
            sumX += x;
            sumY += y;
            sumXY += x * y;
            sumX2 += x * x;
        }

        double denominator = n * sumX2 - sumX * sumX;
        if (denominator == 0) return 0;

        double slope = (n * sumXY - sumX * sumY) / denominator;
        double meanY = sumY / n;

        return meanY != 0 ? slope / Math.abs(meanY) : 0;
    }

    private double predictNextValue(List<TrendDataPoint> dataPoints,
                                     java.util.function.ToDoubleFunction<TrendDataPoint> extractor) {
        if (dataPoints.isEmpty()) return 0;

        int n = dataPoints.size();
        double sumX = 0, sumY = 0, sumXY = 0, sumX2 = 0;

        for (int i = 0; i < n; i++) {
            double x = i;
            double y = extractor.applyAsDouble(dataPoints.get(i));
            sumX += x;
            sumY += y;
            sumXY += x * y;
            sumX2 += x * x;
        }

        double denominator = n * sumX2 - sumX * sumX;
        if (denominator == 0) return extractor.applyAsDouble(dataPoints.get(n - 1));

        double slope = (n * sumXY - sumX * sumY) / denominator;
        double intercept = (sumY - slope * sumX) / n;

        double predicted = slope * n + intercept;
        return Math.max(0, predicted);
    }

    private String assessRiskLevel(double diffTrendRate, double latencyTrendRate,
                                    double diffRateTrend, TrendDataPoint latest) {
        int riskScore = 0;

        if (diffTrendRate > diffTrendThreshold) riskScore += 2;
        else if (diffTrendRate > diffTrendThreshold / 2) riskScore += 1;

        if (latencyTrendRate > latencyTrendThreshold) riskScore += 2;
        else if (latencyTrendRate > latencyTrendThreshold / 2) riskScore += 1;

        if (latest.getDiffRate() > 0.05) riskScore += 3;
        else if (latest.getDiffRate() > 0.01) riskScore += 1;

        if (latest.getAvgLatencyMs() > 5000) riskScore += 2;
        else if (latest.getAvgLatencyMs() > 2000) riskScore += 1;

        if (diffRateTrend > 0.05) riskScore += 2;

        if (riskScore >= 7) return "CRITICAL";
        if (riskScore >= 5) return "HIGH";
        if (riskScore >= 3) return "MEDIUM";
        return "LOW";
    }

    private String generateRecommendation(String riskLevel, double diffTrendRate,
                                           double latencyTrendRate, TrendDataPoint latest) {
        List<String> recommendations = new ArrayList<>();

        if ("CRITICAL".equals(riskLevel)) {
            recommendations.add("差异趋势严重恶化，建议立即检查同步链路");
        } else if ("HIGH".equals(riskLevel)) {
            recommendations.add("差异趋势加速增长，建议提前介入排查");
        }

        if (diffTrendRate > diffTrendThreshold) {
            recommendations.add(String.format("差异增长率 %.1f%% 超过阈值，建议缩短校验间隔", diffTrendRate * 100));
        }

        if (latencyTrendRate > latencyTrendThreshold) {
            recommendations.add(String.format("延迟增长率 %.1f%% 超过阈值，建议检查网络和负载", latencyTrendRate * 100));
        }

        if (latest.getDiffRate() > 0.05) {
            recommendations.add("当前差异率超过5%，建议暂停灰度放量并排查原因");
        }

        if (recommendations.isEmpty()) {
            recommendations.add("数据同步状态正常，维持当前校验策略即可");
        }

        return String.join("；", recommendations);
    }

    private LocalDateTime calculateNextCheckTime(String riskLevel, LocalDateTime lastCheck) {
        return switch (riskLevel) {
            case "CRITICAL" -> lastCheck.plusMinutes(5);
            case "HIGH" -> lastCheck.plusMinutes(15);
            case "MEDIUM" -> lastCheck.plusMinutes(30);
            default -> lastCheck.plusHours(1);
        };
    }

    public PredictionResult getPrediction(String tableName) {
        return predictions.get(tableName);
    }

    public Collection<PredictionResult> getAllPredictions() {
        return predictions.values();
    }

    public List<TrendDataPoint> getTrendData(String tableName) {
        return trendData.getOrDefault(tableName, Collections.emptyList());
    }

    @Data
    @Builder
    @NoArgsConstructor
    @AllArgsConstructor
    public static class TrendDataPoint {
        private LocalDateTime timestamp;
        private long diffCount;
        private long totalRecords;
        private double avgLatencyMs;
        private double maxLatencyMs;
        private double diffRate;
    }

    @Data
    @Builder
    @NoArgsConstructor
    @AllArgsConstructor
    public static class PredictionResult {
        private String tableName;
        private LocalDateTime analyzedAt;
        private double diffTrendRate;
        private double latencyTrendRate;
        private double diffRateTrend;
        private double predictedDiffCount;
        private double predictedAvgLatency;
        private double currentDiffRate;
        private double currentAvgLatencyMs;
        private String riskLevel;
        private boolean alertTriggered;
        private String recommendation;
        private LocalDateTime nextCheckSuggestion;
        private List<TrendDataPoint> dataPoints;
    }
}
