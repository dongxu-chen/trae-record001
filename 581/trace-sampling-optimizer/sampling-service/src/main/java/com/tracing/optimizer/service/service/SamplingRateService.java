package com.tracing.optimizer.service.service;

import com.tracing.optimizer.core.cost.CostModel;
import com.tracing.optimizer.core.edge.EdgeSampler;
import com.tracing.optimizer.core.evaluation.SamplingEffectEvaluator;
import com.tracing.optimizer.core.feedback.FeedbackLoop;
import com.tracing.optimizer.core.model.*;
import com.tracing.optimizer.core.rl.SamplingAgent;
import com.tracing.optimizer.core.storage.DynamicStorageStrategy;
import jakarta.annotation.PostConstruct;
import jakarta.annotation.PreDestroy;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.stereotype.Service;

import java.util.*;

@Service
public class SamplingRateService {

    private static final Logger log = LoggerFactory.getLogger(SamplingRateService.class);

    private final com.tracing.optimizer.core.engine.SamplingOptimizer optimizer;
    private final CostModel costModel;

    public SamplingRateService(com.tracing.optimizer.core.engine.SamplingOptimizer optimizer,
                               CostModel costModel) {
        this.optimizer = optimizer;
        this.costModel = costModel;
    }

    @PostConstruct
    public void init() {
        optimizer.start();
        seedDemoData();
        log.info("SamplingRateService initialized and optimizer started");
    }

    @PreDestroy
    public void cleanup() {
        optimizer.stop();
    }

    private void seedDemoData() {
        registerService("order-service", "production", 0.95, 0.02, 350.0, 5000L);
        registerService("payment-service", "production", 0.99, 0.005, 200.0, 2000L);
        registerService("user-service", "production", 0.7, 0.03, 150.0, 8000L);
        registerService("notification-service", "production", 0.4, 0.08, 80.0, 15000L);
        registerService("analytics-service", "production", 0.3, 0.01, 500.0, 3000L);
        registerService("search-service", "production", 0.8, 0.04, 250.0, 12000L);
        registerService("inventory-service", "production", 0.85, 0.015, 180.0, 4000L);
        registerService("auth-service", "production", 0.9, 0.001, 50.0, 10000L);

        updateMetrics("order-service", 50000, 5000, 100, 120.0, 250.0, 350.0, 0.02, 58);
        updateMetrics("payment-service", 20000, 1990, 10, 40.0, 120.0, 200.0, 0.005, 23);
        updateMetrics("user-service", 80000, 2400, 2400, 50.0, 100.0, 150.0, 0.03, 93);
        updateMetrics("notification-service", 150000, 3000, 12000, 20.0, 50.0, 80.0, 0.08, 174);
        updateMetrics("analytics-service", 30000, 300, 30, 200.0, 350.0, 500.0, 0.01, 35);
        updateMetrics("search-service", 120000, 4800, 4800, 80.0, 180.0, 250.0, 0.04, 139);
        updateMetrics("inventory-service", 40000, 2800, 60, 60.0, 130.0, 180.0, 0.015, 46);
        updateMetrics("auth-service", 100000, 5000, 10, 15.0, 30.0, 50.0, 0.001, 116);
    }

    private void registerService(String name, String ns, double importance,
                                  double errorRate, double p99, long reqRate) {
        ServiceMetadata meta = new ServiceMetadata(name, importance, errorRate, p99, reqRate);
        meta.setServiceNamespace(ns);
        optimizer.registerService(meta);
    }

    private void updateMetrics(String name, long total, long sampled, long errors,
                                double p50, double p95, double p99, double errRate, long throughput) {
        TraceMetrics m = new TraceMetrics();
        m.setServiceName(name);
        m.setTotalSpans(total);
        m.setSampledSpans(sampled);
        m.setErrorSpans(errors);
        m.setP50LatencyMs(p50);
        m.setP95LatencyMs(p95);
        m.setP99LatencyMs(p99);
        m.setErrorRate(errRate);
        m.setThroughputPerSecond(throughput);
        m.setCurrentSamplingRate(sampled / (double) total);
        optimizer.updateMetrics(m);
    }

    public Map<String, SamplingRate> getAllSamplingRates() {
        return optimizer.getAllCurrentRates();
    }

    public SamplingRate getSamplingRate(String serviceName) {
        return optimizer.getCurrentRate(serviceName);
    }

    public SamplingRate updateServiceRate(String serviceName, double businessImportance,
                                           double errorRate, double p99LatencyMs, long requestRate) {
        ServiceMetadata meta = new ServiceMetadata(serviceName, businessImportance,
                errorRate, p99LatencyMs, requestRate);
        optimizer.registerService(meta);
        return optimizer.getCurrentRate(serviceName);
    }

    public Map<String, Object> getCostSummary() {
        Map<String, Object> summary = new LinkedHashMap<>();
        CostBudget budget = costModel.getBudget();
        summary.put("dailyBudgetUsd", budget.getDailyBudgetUsd());
        summary.put("currentSpendUsd", budget.getCurrentSpendUsd());
        summary.put("remainingBudget", budget.getRemainingBudget());
        summary.put("utilizationPercent", budget.getBudgetUtilization());
        summary.put("overBudget", budget.isOverBudget());
        summary.put("alertTriggered", budget.isAlertThresholdReached());
        summary.put("serviceBreakdown", budget.getServiceSpendMap());
        return summary;
    }

    public Map<String, Object> getCostProjections() {
        Map<String, ServiceMetadata> services = optimizer.getEnvironment().getServices();
        Map<String, Double> proposedRates = new LinkedHashMap<>();
        for (Map.Entry<String, SamplingRate> entry : optimizer.getAllCurrentRates().entrySet()) {
            proposedRates.put(entry.getKey(), entry.getValue().getRate());
        }
        return costModel.projectCostForRates(services, proposedRates, new HashMap<>());
    }

    public FeedbackLoop.FeedbackAnalysis getFeedbackAnalysis(String serviceName) {
        return optimizer.getFeedbackLoop().analyzeFeedback(serviceName);
    }

    public void submitFeedback(FeedbackSignal signal) {
        optimizer.submitFeedback(signal);
    }

    public Map<String, SamplingRate> triggerOptimization() {
        return optimizer.optimizeAll();
    }

    public Map<String, Object> getEdgeSamplerStatus() {
        Map<String, Object> status = new LinkedHashMap<>();
        status.put("localDecisions", optimizer.getEdgeSampler().getLocalDecisions());
        return status;
    }

    public boolean shouldSampleEdge(String serviceName, String traceId, double globalRate) {
        return optimizer.getEdgeSampler().shouldSample(serviceName, traceId, globalRate);
    }

    public Map<String, Object> getAgentStatus() {
        Map<String, Object> status = new LinkedHashMap<>();
        SamplingAgent agent = optimizer.getAgent();
        status.put("explorationRate", agent.getExplorationRate());
        status.put("useStateReduction", agent.isUseStateReduction());
        status.put("reductionStats", agent.getReductionStats());
        status.put("qTableSizes", new LinkedHashMap<String, Integer>());
        for (Map.Entry<String, double[]> entry : agent.getQTables().entrySet()) {
            ((Map<String, Integer>) status.get("qTableSizes")).put(entry.getKey(), entry.getValue().length);
        }
        return status;
    }

    public CostModel.ComprehensiveCostAssessment getCostAssessment(String serviceName, double proposedRate) {
        ServiceMetadata meta = optimizer.getEnvironment().getServices().get(serviceName);
        if (meta == null) {
            return null;
        }
        TraceMetrics metrics = null;
        return costModel.computeComprehensiveCostAssessment(serviceName, meta, metrics, proposedRate);
    }

    public Map<String, CostModel.ComprehensiveCostAssessment> getAllCostAssessments() {
        Map<String, CostModel.ComprehensiveCostAssessment> assessments = new LinkedHashMap<>();
        Map<String, SamplingRate> rates = optimizer.getAllCurrentRates();
        for (Map.Entry<String, SamplingRate> entry : rates.entrySet()) {
            String svc = entry.getKey();
            double rate = entry.getValue().getRate();
            CostModel.ComprehensiveCostAssessment assessment = getCostAssessment(svc, rate);
            if (assessment != null) {
                assessments.put(svc, assessment);
            }
        }
        return assessments;
    }

    public Map<String, Object> getCpuCostSummary() {
        Map<String, Object> summary = new LinkedHashMap<>();
        summary.put("cpuCostPerService", costModel.getCpuCostPerService());
        summary.put("cpuCostMultiplier", costModel.getCpuCostMultiplier());
        summary.put("overallCostEfficiency", costModel.getOverallCostEfficiency());
        CostBudget budget = costModel.getBudget();
        if (budget != null) {
            summary.put("costPerSpanCpu", budget.getCostPerSpanCpu());
            summary.put("cpuCoreCostPerHourUsd", budget.getCpuCoreCostPerHourUsd());
            summary.put("spansProcessedPerCoreSecond", budget.getSpansProcessedPerCoreSecond());
            summary.put("samplingCpuOverheadPercent", budget.getSamplingCpuOverheadPercent());
        }
        double totalCpu = costModel.getCpuCostPerService().values().stream().mapToDouble(Double::doubleValue).sum();
        summary.put("totalCpuCost", totalCpu);
        return summary;
    }

    public Map<String, Object> getEdgeAsyncStatus() {
        return optimizer.getEdgeSampler().getEdgeStats();
    }

    public Map<String, EdgeSampler.CentralDecision> getCentralDecisions() {
        return optimizer.getEdgeSampler().getCentralDecisions();
    }

    public void pushCentralDecisions() {
        optimizer.pushCentralDecisionsToEdge();
    }

    public Map<String, Object> getAnomalyEnhancementStats() {
        return optimizer.getAnomalyEnhancer().getEnhancementStats();
    }

    public double getServiceErrorRate(String serviceName) {
        return optimizer.getAnomalyEnhancer().getServiceErrorRate(serviceName);
    }

    public double getBoostedSamplingRate(String serviceName) {
        return optimizer.getAnomalyEnhancer().getBoostedSamplingRate(serviceName);
    }

    public boolean checkForceSample(String traceId, String serviceName, boolean hasError, int statusCode) {
        return optimizer.shouldForceSample(traceId, serviceName, hasError, statusCode);
    }

    public Map<String, Object> getSamplingEffectReport(String serviceName) {
        SamplingEffectEvaluator.EvaluationReport report = optimizer.getEffectEvaluator().generateReport(serviceName);
        Map<String, Object> result = new LinkedHashMap<>();
        result.put("serviceName", report.serviceName);
        result.put("totalProblems", report.totalProblems);
        result.put("problemsDetected", report.problemsDetected);
        result.put("problemsMissed", report.problemsMissed);
        result.put("detectionRate", report.detectionRate);
        result.put("detectionRateChange", report.detectionRateChange);
        result.put("detectionByType", report.detectionByType);
        result.put("averageSamplingRate", report.averageSamplingRate);
        result.put("costEfficiency", optimizer.getEffectEvaluator().getEffectiveCostEfficiency(serviceName));
        return result;
    }

    public Map<String, Map<String, Object>> getAllSamplingEffectReports() {
        Map<String, SamplingEffectEvaluator.EvaluationReport> reports = optimizer.getEffectEvaluator().generateAllReports();
        Map<String, Map<String, Object>> result = new LinkedHashMap<>();
        for (Map.Entry<String, SamplingEffectEvaluator.EvaluationReport> entry : reports.entrySet()) {
            SamplingEffectEvaluator.EvaluationReport report = entry.getValue();
            Map<String, Object> serviceResult = new LinkedHashMap<>();
            serviceResult.put("serviceName", report.serviceName);
            serviceResult.put("totalProblems", report.totalProblems);
            serviceResult.put("problemsDetected", report.problemsDetected);
            serviceResult.put("problemsMissed", report.problemsMissed);
            serviceResult.put("detectionRate", report.detectionRate);
            serviceResult.put("detectionRateChange", report.detectionRateChange);
            serviceResult.put("detectionByType", report.detectionByType);
            serviceResult.put("averageSamplingRate", report.averageSamplingRate);
            serviceResult.put("costEfficiency", optimizer.getEffectEvaluator().getEffectiveCostEfficiency(entry.getKey()));
            result.put(entry.getKey(), serviceResult);
        }
        Map<String, Object> overall = new LinkedHashMap<>();
        overall.put("overallDetectionRate", optimizer.getEffectEvaluator().getOverallDetectionRate());
        overall.put("detectionRateByProblemType", optimizer.getEffectEvaluator().getDetectionRateByProblemType());
        overall.put("samplingRateDetectionCorrelation", optimizer.getEffectEvaluator().getSamplingRateDetectionCorrelation());
        result.put("_overall", overall);
        return result;
    }

    public void recordProblem(String problemId, String serviceName, String type, boolean detected, double samplingRate) {
        SamplingEffectEvaluator.ProblemType problemType;
        try {
            problemType = SamplingEffectEvaluator.ProblemType.valueOf(type);
        } catch (IllegalArgumentException e) {
            problemType = SamplingEffectEvaluator.ProblemType.UNCLASSIFIED;
        }
        optimizer.recordProblem(problemId, serviceName, problemType, detected, samplingRate);
    }

    public Map<String, Object> getHeatTierStats(String serviceName) {
        return optimizer.getStorageStrategy().getHeatStats(serviceName);
    }

    public Map<String, String> getAllHeatTiers() {
        Map<String, DynamicStorageStrategy.HeatTier> tiers = optimizer.getStorageStrategy().getAllHeatTiers();
        Map<String, String> result = new LinkedHashMap<>();
        for (Map.Entry<String, DynamicStorageStrategy.HeatTier> entry : tiers.entrySet()) {
            result.put(entry.getKey(), entry.getValue().name());
        }
        return result;
    }

    public double applyHeatTierAdjustment(String serviceName, double baseRate) {
        return optimizer.applyHeatTierAdjustment(serviceName, baseRate);
    }

    public void recordServiceHeat(String serviceName) {
        optimizer.recordServiceHeat(serviceName);
    }
}
