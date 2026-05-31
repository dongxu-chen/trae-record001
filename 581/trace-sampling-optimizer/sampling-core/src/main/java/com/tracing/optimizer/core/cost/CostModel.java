package com.tracing.optimizer.core.cost;

import com.tracing.optimizer.core.model.CostBudget;
import com.tracing.optimizer.core.model.ServiceMetadata;
import com.tracing.optimizer.core.model.TraceMetrics;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.util.*;

public class CostModel {

    private static final Logger log = LoggerFactory.getLogger(CostModel.class);

    private CostBudget budget;
    private final Map<String, Double> historicalCostPerService;
    private double storageCostMultiplier;
    private double networkCostMultiplier;
    private double computeCostMultiplier;
    private double cpuCostMultiplier;
    private double retentionDays;
    private double overallCostEfficiency;
    private final Map<String, Double> cpuCostPerService;

    public CostModel() {
        this.historicalCostPerService = new HashMap<>();
        this.cpuCostPerService = new HashMap<>();
        this.storageCostMultiplier = 1.0;
        this.networkCostMultiplier = 0.3;
        this.computeCostMultiplier = 0.2;
        this.cpuCostMultiplier = 1.2;
        this.retentionDays = 30.0;
        this.overallCostEfficiency = 0.0;
    }

    public CostModel(CostBudget budget) {
        this();
        this.budget = budget;
    }

    public double computeOptimalSamplingRate(ServiceMetadata metadata, TraceMetrics metrics) {
        if (budget == null) return 1.0;

        double baseRate = computePriorityBasedRate(metadata);
        double budgetConstrainedRate = budget.computeMaxAllowedRate(
                metrics != null ? metrics.getThroughputPerSecond() * 86400L : 1000000L
        );
        double rate = Math.min(baseRate, budgetConstrainedRate);

        if (budget.isAlertThresholdReached()) {
            double compressionFactor = 1.0 - (budget.getBudgetUtilization() - budget.getAlertThresholdPercent()) / 100.0;
            compressionFactor = Math.max(0.1, compressionFactor);
            rate *= compressionFactor;
            log.info("Budget alert threshold reached, compressing rate by factor {}", compressionFactor);
        }

        rate = applyCostEfficiencyAdjustment(metadata, rate);

        return Math.max(0.01, Math.min(1.0, rate));
    }

    private double computePriorityBasedRate(ServiceMetadata metadata) {
        double priority = metadata.computePriorityScore();
        if (priority >= 0.8) return 1.0;
        if (priority >= 0.6) return 0.7;
        if (priority >= 0.4) return 0.4;
        if (priority >= 0.2) return 0.2;
        return 0.05;
    }

    private double applyCostEfficiencyAdjustment(ServiceMetadata metadata, double currentRate) {
        Double historicalCost = historicalCostPerService.get(metadata.getServiceName());
        if (historicalCost == null || budget == null) return currentRate;

        double budgetShare = budget.getDailyBudgetUsd() * 0.3;
        if (historicalCost > budgetShare) {
            double overRatio = budgetShare / historicalCost;
            return currentRate * overRatio;
        }
        return currentRate;
    }

    public double estimateDailyCost(String serviceName, long throughputPerSecond, double samplingRate) {
        long dailySpans = throughputPerSecond * 86400L;
        long sampledSpans = (long) (dailySpans * samplingRate);
        double storageCost = sampledSpans * budget.getCostPerSpanStorage() * storageCostMultiplier;
        double networkCost = sampledSpans * budget.getCostPerSpanNetwork() * networkCostMultiplier;
        double computeCost = sampledSpans * budget.getCostPerSpanCompute() * computeCostMultiplier;
        double cpuCost = computeCpuCost(sampledSpans, throughputPerSecond, samplingRate);
        cpuCostPerService.put(serviceName, cpuCost);
        return storageCost + networkCost + computeCost + cpuCost;
    }

    public double computeCpuCost(long sampledSpans, long throughputPerSecond, double samplingRate) {
        double cpuCostPerSpan = budget != null ? budget.getCostPerSpanCpu() : 0.000008;
        double coreCostPerHour = budget != null ? budget.getCpuCoreCostPerHourUsd() : 0.05;
        double spansPerCoreSec = budget != null ? budget.getSpansProcessedPerCoreSecond() : 10000.0;
        double overhead = budget != null ? budget.getSamplingCpuOverheadPercent() : 0.15;

        double baseCpuCost = sampledSpans * cpuCostPerSpan * cpuCostMultiplier;
        double coreHoursNeeded = (throughputPerSecond * samplingRate * overhead * 24.0) / spansPerCoreSec;
        double processingCpuCost = coreHoursNeeded * coreCostPerHour;
        return baseCpuCost + processingCpuCost;
    }

    public ComprehensiveCostAssessment computeComprehensiveCostAssessment(String serviceName,
                                                                           ServiceMetadata metadata,
                                                                           TraceMetrics metrics,
                                                                           double proposedRate) {
        ComprehensiveCostAssessment assessment = new ComprehensiveCostAssessment();
        assessment.serviceName = serviceName;
        assessment.proposedSamplingRate = proposedRate;

        long throughput = metrics != null ? metrics.getThroughputPerSecond() : 1000L;
        long dailySpans = throughput * 86400L;
        long sampledSpans = (long) (dailySpans * proposedRate);
        long unsampledSpans = dailySpans - sampledSpans;

        double storageCost = sampledSpans * budget.getCostPerSpanStorage() * storageCostMultiplier;
        double networkCost = sampledSpans * budget.getCostPerSpanNetwork() * networkCostMultiplier;
        double computeCost = sampledSpans * budget.getCostPerSpanCompute() * computeCostMultiplier;
        double cpuCost = computeCpuCost(sampledSpans, throughput, proposedRate);
        double totalCost = storageCost + networkCost + computeCost + cpuCost;

        double observabilityGain = metadata.computePriorityScore() * proposedRate;
        double costEfficiency = totalCost > 0 ? observabilityGain / totalCost : 0.0;
        double costSaving = unsampledSpans * (
                budget.getCostPerSpanStorage() + budget.getCostPerSpanNetwork()
                        + budget.getCostPerSpanCompute() + budget.getCostPerSpanCpu()
        );

        double observabilityLossRisk = (1.0 - proposedRate) * metadata.computePriorityScore();
        double errorDetectionRisk = (1.0 - proposedRate) * metadata.getErrorRate();
        double latencyDetectionRisk = (1.0 - proposedRate) * Math.min(metadata.getP99LatencyMs() / 5000.0, 1.0);
        double aggregateRisk = observabilityLossRisk * 0.4 + errorDetectionRisk * 0.35 + latencyDetectionRisk * 0.25;

        double costWeight = 0.5;
        double riskWeight = 0.5;
        double compositeScore = 1.0 - (costWeight * Math.min(totalCost / budget.getDailyBudgetUsd(), 1.0)
                + riskWeight * Math.min(aggregateRisk, 1.0));

        assessment.storageCost = storageCost;
        assessment.networkCost = networkCost;
        assessment.computeCost = computeCost;
        assessment.cpuCost = cpuCost;
        assessment.totalCost = totalCost;
        assessment.costSaving = costSaving;
        assessment.observabilityGain = observabilityGain;
        assessment.costEfficiency = costEfficiency;
        assessment.observabilityLossRisk = observabilityLossRisk;
        assessment.errorDetectionRisk = errorDetectionRisk;
        assessment.latencyDetectionRisk = latencyDetectionRisk;
        assessment.aggregateRisk = aggregateRisk;
        assessment.compositeScore = compositeScore;
        assessment.budgetUtilization = totalCost / budget.getDailyBudgetUsd();

        if (compositeScore < 0.4) {
            assessment.recommendation = "REDUCE_SAMPLING";
            assessment.recommendedRate = Math.max(0.01, proposedRate * 0.7);
        } else if (compositeScore > 0.7) {
            assessment.recommendation = "INCREASE_SAMPLING";
            assessment.recommendedRate = Math.min(1.0, proposedRate * 1.3);
        } else {
            assessment.recommendation = "MAINTAIN";
            assessment.recommendedRate = proposedRate;
        }

        overallCostEfficiency = (overallCostEfficiency * 0.9) + (costEfficiency * 0.1);

        return assessment;
    }

    public static class ComprehensiveCostAssessment {
        public String serviceName;
        public double proposedSamplingRate;
        public double storageCost;
        public double networkCost;
        public double computeCost;
        public double cpuCost;
        public double totalCost;
        public double costSaving;
        public double observabilityGain;
        public double costEfficiency;
        public double observabilityLossRisk;
        public double errorDetectionRisk;
        public double latencyDetectionRisk;
        public double aggregateRisk;
        public double compositeScore;
        public double budgetUtilization;
        public String recommendation;
        public double recommendedRate;
    }

    public Map<String, Double> projectCostForRates(Map<String, ServiceMetadata> services,
                                                    Map<String, Double> proposedRates,
                                                    Map<String, TraceMetrics> metricsMap) {
        Map<String, Double> projections = new LinkedHashMap<>();
        double totalProjected = 0.0;

        for (Map.Entry<String, ServiceMetadata> entry : services.entrySet()) {
            String svc = entry.getKey();
            Double rate = proposedRates.getOrDefault(svc, 0.1);
            TraceMetrics metrics = metricsMap.get(svc);
            long throughput = metrics != null ? metrics.getThroughputPerSecond() : 100L;
            double cost = estimateDailyCost(svc, throughput, rate);
            projections.put(svc, cost);
            totalProjected += cost;
        }

        projections.put("__TOTAL__", totalProjected);
        return projections;
    }

    public void recordActualCost(String serviceName, double cost) {
        historicalCostPerService.put(serviceName, cost);
        if (budget != null) {
            budget.recordServiceSpend(serviceName, cost);
        }
    }

    public CostBudget getBudget() { return budget; }
    public void setBudget(CostBudget budget) { this.budget = budget; }

    public double getStorageCostMultiplier() { return storageCostMultiplier; }
    public void setStorageCostMultiplier(double m) { this.storageCostMultiplier = m; }

    public double getNetworkCostMultiplier() { return networkCostMultiplier; }
    public void setNetworkCostMultiplier(double m) { this.networkCostMultiplier = m; }

    public double getComputeCostMultiplier() { return computeCostMultiplier; }
    public void setComputeCostMultiplier(double m) { this.computeCostMultiplier = m; }

    public double getCpuCostMultiplier() { return cpuCostMultiplier; }
    public void setCpuCostMultiplier(double m) { this.cpuCostMultiplier = m; }

    public double getRetentionDays() { return retentionDays; }
    public void setRetentionDays(double retentionDays) { this.retentionDays = retentionDays; }

    public double getOverallCostEfficiency() { return overallCostEfficiency; }
    public Map<String, Double> getHistoricalCostPerService() { return historicalCostPerService; }
    public Map<String, Double> getCpuCostPerService() { return cpuCostPerService; }
}
