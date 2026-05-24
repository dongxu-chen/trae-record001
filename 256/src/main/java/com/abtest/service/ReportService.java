package com.abtest.service;

import com.abtest.dto.StatisticalResultDTO;
import com.abtest.entity.Experiment;
import com.abtest.entity.Metric;
import com.abtest.entity.Variant;
import com.abtest.repository.ExperimentRepository;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;

import java.time.Duration;
import java.time.LocalDateTime;
import java.util.*;
import java.util.stream.Collectors;

@Slf4j
@Service
@RequiredArgsConstructor
public class ReportService {

    private static final long METRIC_DELAY_MINUTES = 60;

    private final ExperimentRepository experimentRepository;
    private final ClickHouseMetricsService metricsService;
    private final StatisticsService statisticsService;
    private final ExperimentService experimentService;

    public Map<String, Object> generateReport(Long experimentId) {
        Experiment experiment = experimentRepository.findById(experimentId)
            .orElseThrow(() -> new IllegalArgumentException("实验不存在: " + experimentId));

        Map<String, Object> report = new LinkedHashMap<>();

        report.put("experimentId", experiment.getId());
        report.put("experimentName", experiment.getName());
        report.put("description", experiment.getDescription());
        report.put("owner", experiment.getOwner());
        report.put("status", experiment.getStatus());
        report.put("trafficPercentage", experiment.getTrafficPercentage());
        report.put("trafficKey", experiment.getTrafficKey());
        report.put("startTime", experiment.getStartTime());
        report.put("endTime", experiment.getEndTime());

        if (experiment.getStartTime() != null) {
            LocalDateTime endTime = experiment.getEndTime() != null ? experiment.getEndTime() : LocalDateTime.now();
            Duration duration = Duration.between(experiment.getStartTime(), endTime);
            report.put("durationHours", duration.toHours());
        }

        List<Map<String, Object>> variantsReport = new ArrayList<>();
        for (Variant variant : experiment.getVariants()) {
            Map<String, Object> variantReport = new LinkedHashMap<>();
            variantReport.put("variantId", variant.getId());
            variantReport.put("variantName", variant.getName());
            variantReport.put("isControl", variant.getIsControl());
            variantReport.put("trafficWeight", variant.getTrafficWeight());
            variantReport.put("configuration", variant.getConfiguration());

            Map<String, Object> metricsData = new LinkedHashMap<>();
            for (Metric metric : experiment.getMetrics()) {
                Map<String, Object> metricValue = metricsService.calculateMetric(
                    experimentId, variant.getName(), metric, METRIC_DELAY_MINUTES);
                metricsData.put(metric.getName(), metricValue);
            }
            variantReport.put("metrics", metricsData);
            variantsReport.add(variantReport);
        }
        report.put("variants", variantsReport);

        List<StatisticalResultDTO> statisticalResults = new ArrayList<>();
        Variant controlVariant = experimentService.getControlVariant(experiment)
            .orElse(null);

        long testVariantCount = experiment.getVariants().stream()
            .filter(v -> !v.getIsControl())
            .count();
        int comparisonCount = (int) (testVariantCount * experiment.getMetrics().size());

        if (controlVariant != null) {
            for (Variant testVariant : experiment.getVariants()) {
                if (testVariant.getIsControl()) {
                    continue;
                }
                for (Metric metric : experiment.getMetrics()) {
                    StatisticalResultDTO result = calculateStatistics(
                        experimentId, controlVariant.getName(), testVariant.getName(), metric, comparisonCount);
                    if (result != null) {
                        statisticalResults.add(result);
                    }
                }
            }
        }
        report.put("statisticalResults", statisticalResults);
        report.put("comparisonCount", comparisonCount);
        report.put("delayMinutes", METRIC_DELAY_MINUTES);
        report.put("delayDescription", "用户进组满" + METRIC_DELAY_MINUTES + "分钟后的数据才计入统计");

        report.put("summary", generateSummary(statisticalResults));

        return report;
    }

    public StatisticalResultDTO getMetricStatistics(Long experimentId, String metricName) {
        Experiment experiment = experimentRepository.findById(experimentId)
            .orElseThrow(() -> new IllegalArgumentException("实验不存在: " + experimentId));

        Metric metric = experiment.getMetrics().stream()
            .filter(m -> m.getName().equals(metricName))
            .findFirst()
            .orElseThrow(() -> new IllegalArgumentException("指标不存在: " + metricName));

        Variant controlVariant = experimentService.getControlVariant(experiment)
            .orElseThrow(() -> new IllegalStateException("没有找到对照组"));

        Variant testVariant = experiment.getVariants().stream()
            .filter(v -> !v.getIsControl())
            .findFirst()
            .orElseThrow(() -> new IllegalStateException("没有找到测试组"));

        long testVariantCount = experiment.getVariants().stream()
            .filter(v -> !v.getIsControl())
            .count();
        int comparisonCount = (int) (testVariantCount * experiment.getMetrics().size());

        return calculateStatistics(experimentId, controlVariant.getName(), testVariant.getName(), metric, comparisonCount);
    }

    private StatisticalResultDTO calculateStatistics(Long experimentId, String controlName,
                                                      String testName, Metric metric, int comparisonCount) {
        Map<String, Object> controlStats = metricsService.calculateMetric(experimentId, controlName, metric, METRIC_DELAY_MINUTES);
        Map<String, Object> testStats = metricsService.calculateMetric(experimentId, testName, metric, METRIC_DELAY_MINUTES);

        if (controlStats.containsKey("error") || testStats.containsKey("error")) {
            return null;
        }

        if (metric.getType() == Metric.MetricType.CONVERSION) {
            return statisticsService.performChiSquareTest(
                metric.getName(), controlName, testName, controlStats, testStats, comparisonCount);
        } else {
            return statisticsService.performTTest(
                metric.getName(), controlName, testName, controlStats, testStats, comparisonCount);
        }
    }

    private Map<String, Object> generateSummary(List<StatisticalResultDTO> results) {
        Map<String, Object> summary = new LinkedHashMap<>();

        long totalMetrics = results.size();
        long significantMetrics = results.stream()
            .filter(StatisticalResultDTO::getIsStatisticallySignificant)
            .count();
        long positiveMetrics = results.stream()
            .filter(r -> "POSITIVE".equals(r.getSignificance()))
            .count();
        long negativeMetrics = results.stream()
            .filter(r -> "NEGATIVE".equals(r.getSignificance()))
            .count();

        long bonferroniSignificantMetrics = results.stream()
            .filter(StatisticalResultDTO::getIsBonferroniSignificant)
            .count();
        long bonferroniPositiveMetrics = results.stream()
            .filter(r -> "POSITIVE".equals(r.getBonferroniSignificance()))
            .count();
        long bonferroniNegativeMetrics = results.stream()
            .filter(r -> "NEGATIVE".equals(r.getBonferroniSignificance()))
            .count();

        summary.put("totalMetrics", totalMetrics);

        Map<String, Object> unadjusted = new LinkedHashMap<>();
        unadjusted.put("significantMetrics", significantMetrics);
        unadjusted.put("positiveMetrics", positiveMetrics);
        unadjusted.put("negativeMetrics", negativeMetrics);
        unadjusted.put("notSignificantMetrics", totalMetrics - significantMetrics);

        if (significantMetrics > 0) {
            if (positiveMetrics > negativeMetrics) {
                unadjusted.put("overallConclusion", "实验组表现更优");
            } else if (negativeMetrics > positiveMetrics) {
                unadjusted.put("overallConclusion", "对照组表现更优");
            } else {
                unadjusted.put("overallConclusion", "结果混合，需要进一步分析");
            }
        } else {
            unadjusted.put("overallConclusion", "暂无统计显著差异");
        }
        summary.put("unadjusted", unadjusted);

        Map<String, Object> bonferroni = new LinkedHashMap<>();
        bonferroni.put("significantMetrics", bonferroniSignificantMetrics);
        bonferroni.put("positiveMetrics", bonferroniPositiveMetrics);
        bonferroni.put("negativeMetrics", bonferroniNegativeMetrics);
        bonferroni.put("notSignificantMetrics", totalMetrics - bonferroniSignificantMetrics);

        if (bonferroniSignificantMetrics > 0) {
            if (bonferroniPositiveMetrics > bonferroniNegativeMetrics) {
                bonferroni.put("overallConclusion", "实验组表现更优 (Bonferroni校正后)");
            } else if (bonferroniNegativeMetrics > bonferroniPositiveMetrics) {
                bonferroni.put("overallConclusion", "对照组表现更优 (Bonferroni校正后)");
            } else {
                bonferroni.put("overallConclusion", "结果混合，需要进一步分析 (Bonferroni校正后)");
            }
        } else {
            bonferroni.put("overallConclusion", "Bonferroni校正后暂无统计显著差异");
        }
        summary.put("bonferroni", bonferroni);

        if (!results.isEmpty()) {
            summary.put("bonferroniCorrectedAlpha", results.get(0).getBonferroniCorrectedAlpha());
        }

        return summary;
    }

    public Map<String, Object> getTrendData(Long experimentId, int days) {
        Experiment experiment = experimentRepository.findById(experimentId)
            .orElseThrow(() -> new IllegalArgumentException("实验不存在: " + experimentId));

        Map<String, Object> trend = new LinkedHashMap<>();
        trend.put("experimentId", experimentId);
        trend.put("days", days);

        Map<String, Object> variantTrends = new LinkedHashMap<>();
        for (Variant variant : experiment.getVariants()) {
            Map<String, Object> variantTrend = new LinkedHashMap<>();
            for (Metric metric : experiment.getMetrics()) {
                List<Map<String, Object>> metricTrend = metricsService.getMetricTrend(
                    experimentId, variant.getName(), metric, days, METRIC_DELAY_MINUTES);
                variantTrend.put(metric.getName(), metricTrend);
            }
            variantTrends.put(variant.getName(), variantTrend);
        }
        trend.put("variants", variantTrends);

        return trend;
    }
}
