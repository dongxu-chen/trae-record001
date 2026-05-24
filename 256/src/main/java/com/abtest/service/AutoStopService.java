package com.abtest.service;

import com.abtest.dto.StatisticalResultDTO;
import com.abtest.entity.Experiment;
import com.abtest.entity.Metric;
import com.abtest.entity.Variant;
import com.abtest.repository.ExperimentRepository;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.time.LocalDateTime;
import java.util.ArrayList;
import java.util.List;
import java.util.Map;

@Slf4j
@Service
@RequiredArgsConstructor
public class AutoStopService {

    private static final long METRIC_DELAY_MINUTES = 60;
    private static final int MIN_SAMPLE_SIZE = 100;

    private final ExperimentRepository experimentRepository;
    private final ClickHouseMetricsService metricsService;
    private final StatisticsService statisticsService;
    private final ExperimentService experimentService;

    @Transactional
    public AutoStopCheckResult checkAndStopIfNeeded(Long experimentId) {
        Experiment experiment = experimentRepository.findById(experimentId)
            .orElseThrow(() -> new IllegalArgumentException("实验不存在: " + experimentId));

        AutoStopCheckResult result = checkAutoStopConditions(experiment);

        if (result.shouldStop()) {
            experimentService.completeExperiment(experimentId);
            log.info("Experiment {} automatically stopped. Reason: {}", experimentId, result.getStopReason());
        }

        return result;
    }

    public AutoStopCheckResult checkAutoStopConditions(Experiment experiment) {
        AutoStopCheckResult result = new AutoStopCheckResult();
        result.setExperimentId(experiment.getId());
        result.setExperimentName(experiment.getName());

        if (!Boolean.TRUE.equals(experiment.getAutoStopEnabled())) {
            result.setChecked(false);
            result.setShouldStop(false);
            result.setReason("自动停止未启用");
            return result;
        }

        if (experiment.getStatus() != Experiment.ExperimentStatus.RUNNING) {
            result.setChecked(false);
            result.setShouldStop(false);
            result.setReason("实验未在运行");
            return result;
        }

        result.setChecked(true);

        Variant controlVariant = experimentService.getControlVariant(experiment).orElse(null);
        if (controlVariant == null) {
            result.setShouldStop(false);
            result.setReason("未找到对照组");
            return result;
        }

        long totalUsers = 0;
        double confidenceThreshold = experiment.getAutoStopConfidenceThreshold() != null
            ? experiment.getAutoStopConfidenceThreshold()
            : 0.95;
        double significanceLevel = 1 - confidenceThreshold;

        List<MetricStopCheck> metricChecks = new ArrayList<>();
        boolean allMetricsSignificant = true;
        boolean anyMetricSignificant = false;

        for (Metric metric : experiment.getMetrics()) {
            MetricStopCheck check = new MetricStopCheck();
            check.setMetricName(metric.getName());

            List<Variant> testVariants = experiment.getVariants().stream()
                .filter(v -> !v.getIsControl())
                .toList();

            boolean metricSignificant = true;
            for (Variant testVariant : testVariants) {
                Map<String, Object> controlStats = metricsService.calculateMetric(
                    experiment.getId(), controlVariant.getName(), metric, METRIC_DELAY_MINUTES);
                Map<String, Object> testStats = metricsService.calculateMetric(
                    experiment.getId(), testVariant.getName(), metric, METRIC_DELAY_MINUTES);

                if (controlStats.containsKey("error") || testStats.containsKey("error")) {
                    check.addError(testVariant.getName(), "指标计算错误");
                    metricSignificant = false;
                    continue;
                }

                long metricUsers = ((Number) controlStats.getOrDefault("totalUsers",
                    controlStats.getOrDefault("userCount", 0))).longValue();
                totalUsers += metricUsers;

                if (metricUsers < MIN_SAMPLE_SIZE) {
                    check.addError(testVariant.getName(),
                        String.format("样本量不足: %d < %d", metricUsers, MIN_SAMPLE_SIZE));
                    metricSignificant = false;
                    continue;
                }

                StatisticalResultDTO statResult;
                if (metric.getType() == Metric.MetricType.CONVERSION) {
                    statResult = statisticsService.performChiSquareTest(
                        metric.getName(), controlVariant.getName(), testVariant.getName(),
                        controlStats, testStats, 1);
                } else {
                    statResult = statisticsService.performTTest(
                        metric.getName(), controlVariant.getName(), testVariant.getName(),
                        controlStats, testStats, 1);
                }

                check.addStatResult(testVariant.getName(), statResult);

                if (statResult.getPValue() > significanceLevel) {
                    metricSignificant = false;
                }
            }

            check.setSignificant(metricSignificant);
            metricChecks.add(check);

            if (metricSignificant) {
                anyMetricSignificant = true;
            } else {
                allMetricsSignificant = false;
            }
        }

        result.setMetricChecks(metricChecks);
        result.setTotalUsers(totalUsers);
        result.setAllMetricsSignificant(allMetricsSignificant);
        result.setAnyMetricSignificant(anyMetricSignificant);

        if (experiment.getAutoStopMaxSampleSize() != null
            && totalUsers >= experiment.getAutoStopMaxSampleSize()) {
            result.setShouldStop(true);
            result.setStopReason(String.format("达到样本量上限: %d >= %d",
                totalUsers, experiment.getAutoStopMaxSampleSize()));
            result.setStopType(AutoStopType.SAMPLE_SIZE_LIMIT);
            return result;
        }

        if (allMetricsSignificant && totalUsers >= MIN_SAMPLE_SIZE * 2) {
            result.setShouldStop(true);
            result.setStopReason(String.format("所有指标达到统计显著性 (置信度: %.0f%%)",
                confidenceThreshold * 100));
            result.setStopType(AutoStopType.STATISTICAL_SIGNIFICANCE);
            return result;
        }

        result.setShouldStop(false);
        if (anyMetricSignificant) {
            result.setReason("部分指标显著，等待所有指标达到显著性");
        } else {
            result.setReason("尚未达到统计显著性或样本量要求");
        }

        return result;
    }

    public static class AutoStopCheckResult {
        private Long experimentId;
        private String experimentName;
        private boolean checked;
        private boolean shouldStop;
        private String reason;
        private String stopReason;
        private AutoStopType stopType;
        private long totalUsers;
        private boolean allMetricsSignificant;
        private boolean anyMetricSignificant;
        private List<MetricStopCheck> metricChecks;

        public Long getExperimentId() { return experimentId; }
        public void setExperimentId(Long experimentId) { this.experimentId = experimentId; }
        public String getExperimentName() { return experimentName; }
        public void setExperimentName(String experimentName) { this.experimentName = experimentName; }
        public boolean isChecked() { return checked; }
        public void setChecked(boolean checked) { this.checked = checked; }
        public boolean shouldStop() { return shouldStop; }
        public void setShouldStop(boolean shouldStop) { this.shouldStop = shouldStop; }
        public String getReason() { return reason; }
        public void setReason(String reason) { this.reason = reason; }
        public String getStopReason() { return stopReason; }
        public void setStopReason(String stopReason) { this.stopReason = stopReason; }
        public AutoStopType getStopType() { return stopType; }
        public void setStopType(AutoStopType stopType) { this.stopType = stopType; }
        public long getTotalUsers() { return totalUsers; }
        public void setTotalUsers(long totalUsers) { this.totalUsers = totalUsers; }
        public boolean isAllMetricsSignificant() { return allMetricsSignificant; }
        public void setAllMetricsSignificant(boolean allMetricsSignificant) { this.allMetricsSignificant = allMetricsSignificant; }
        public boolean isAnyMetricSignificant() { return anyMetricSignificant; }
        public void setAnyMetricSignificant(boolean anyMetricSignificant) { this.anyMetricSignificant = anyMetricSignificant; }
        public List<MetricStopCheck> getMetricChecks() { return metricChecks; }
        public void setMetricChecks(List<MetricStopCheck> metricChecks) { this.metricChecks = metricChecks; }
    }

    public static class MetricStopCheck {
        private String metricName;
        private boolean significant;
        private Map<String, StatisticalResultDTO> statResults;
        private Map<String, String> errors;

        public String getMetricName() { return metricName; }
        public void setMetricName(String metricName) { this.metricName = metricName; }
        public boolean isSignificant() { return significant; }
        public void setSignificant(boolean significant) { this.significant = significant; }
        public Map<String, StatisticalResultDTO> getStatResults() { return statResults; }
        public void addStatResult(String variant, StatisticalResultDTO result) {
            if (this.statResults == null) this.statResults = new java.util.HashMap<>();
            this.statResults.put(variant, result);
        }
        public Map<String, String> getErrors() { return errors; }
        public void addError(String variant, String error) {
            if (this.errors == null) this.errors = new java.util.HashMap<>();
            this.errors.put(variant, error);
        }
    }

    public enum AutoStopType {
        STATISTICAL_SIGNIFICANCE,
        SAMPLE_SIZE_LIMIT,
        NONE
    }
}
