package com.ratelimit.recommender.service;

import com.ratelimit.recommender.model.*;
import org.springframework.stereotype.Service;

import java.time.LocalDateTime;
import java.util.*;

@Service
public class RateLimitEvaluationService {

    private final TopologyAnalysisService topologyService;
    private final QueueingTheoryService queueingService;
    private final Map<String, RateLimitEvaluation> evaluations = new ConcurrentHashMap<>();

    public RateLimitEvaluationService(TopologyAnalysisService topologyService,
                                       QueueingTheoryService queueingService) {
        this.topologyService = topologyService;
        this.queueingService = queueingService;
    }

    public RateLimitEvaluation evaluate(String serviceId, int durationMinutes) {
        List<ServiceNode> services = topologyService.generateSampleServices();
        ServiceNode service = services.stream()
                .filter(s -> s.getServiceId().equals(serviceId))
                .findFirst()
                .orElse(null);

        if (service == null || service.getMetrics() == null) {
            return createEmptyEvaluation(serviceId);
        }

        ServiceMetrics metrics = service.getMetrics();

        RateLimitEvaluation.StabilityMetrics beforeMetrics = simulateBeforeLimit(metrics);
        RateLimitEvaluation.StabilityMetrics afterMetrics = simulateAfterLimit(metrics);

        double stabilityImprovement = calculateStabilityImprovement(beforeMetrics, afterMetrics);
        double latencyReduction = calculateLatencyReduction(beforeMetrics, afterMetrics);
        double errorRateReduction = calculateErrorRateReduction(beforeMetrics, afterMetrics);
        double throughputChange = calculateThroughputChange(beforeMetrics, afterMetrics);

        double effectivenessScore = calculateEffectivenessScore(
                stabilityImprovement, latencyReduction, errorRateReduction);

        List<String> findings = generateFindings(beforeMetrics, afterMetrics, serviceId);

        String verdict = determineVerdict(effectivenessScore);

        Map<String, Object> recommendations = generateRecommendations(
                beforeMetrics, afterMetrics, effectivenessScore);

        RateLimitEvaluation evaluation = RateLimitEvaluation.builder()
                .evaluationId("eval-" + UUID.randomUUID().toString().substring(0, 8))
                .serviceId(serviceId)
                .evaluationTime(LocalDateTime.now())
                .evaluationDurationMinutes(durationMinutes)
                .beforeMetrics(beforeMetrics)
                .afterMetrics(afterMetrics)
                .stabilityImprovement(stabilityImprovement)
                .latencyReductionPercent(latencyReduction)
                .errorRateReductionPercent(errorRateReduction)
                .throughputChangePercent(throughputChange)
                .overallVerdict(verdict)
                .effectivenessScore(effectivenessScore)
                .findings(findings)
                .recommendations(recommendations)
                .build();

        evaluations.put(evaluation.getEvaluationId(), evaluation);
        return evaluation;
    }

    private RateLimitEvaluation.StabilityMetrics simulateBeforeLimit(ServiceMetrics metrics) {
        Random random = new Random();
        double overloadFactor = 1 + random.nextDouble() * 0.5;

        double avgLatency = metrics.getAvgLatencyMs() * overloadFactor;
        double p95Latency = metrics.getP95LatencyMs() * overloadFactor * 1.2;
        double p99Latency = metrics.getP99LatencyMs() * overloadFactor * 1.3;
        double errorRate = metrics.getErrorRate() * (1 + overloadFactor * 2);
        double cpuUtil = Math.min(0.99, metrics.getCpuUtilization() * overloadFactor);
        double memUtil = Math.min(0.99, metrics.getMemoryUtilization() * (1 + overloadFactor * 0.3));
        double stdDev = avgLatency * (0.3 + random.nextDouble() * 0.2);
        int timeouts = (int) (metrics.getTotalRequests() * errorRate * 0.1);

        double stabilityScore = calculateStabilityScore(avgLatency, p99Latency, errorRate, cpuUtil, stdDev);

        return RateLimitEvaluation.StabilityMetrics.builder()
                .avgLatencyMs(avgLatency)
                .p95LatencyMs(p95Latency)
                .p99LatencyMs(p99Latency)
                .errorRate(Math.min(1.0, errorRate))
                .throughputQps(metrics.getAvgQps() * (1 - errorRate * 0.5))
                .cpuUtilization(cpuUtil)
                .memoryUtilization(memUtil)
                .stabilityScore(stabilityScore)
                .timeoutCount(timeouts)
                .rejectedCount(0)
                .avgResponseTimeStdDev(stdDev)
                .build();
    }

    private RateLimitEvaluation.StabilityMetrics simulateAfterLimit(ServiceMetrics metrics) {
        Random random = new Random();

        double avgLatency = metrics.getAvgLatencyMs() * 0.85;
        double p95Latency = metrics.getP95LatencyMs() * 0.8;
        double p99Latency = metrics.getP99LatencyMs() * 0.75;
        double errorRate = metrics.getErrorRate() * 0.4;
        double cpuUtil = metrics.getCpuUtilization() * 0.75;
        double memUtil = metrics.getMemoryUtilization() * 0.9;
        double stdDev = avgLatency * 0.15;
        int timeouts = (int) (metrics.getTotalRequests() * errorRate * 0.02);

        int rejectedRequests = (int) (metrics.getAvgQps() * 0.05 * 3600);

        double stabilityScore = calculateStabilityScore(avgLatency, p99Latency, errorRate, cpuUtil, stdDev);

        return RateLimitEvaluation.StabilityMetrics.builder()
                .avgLatencyMs(avgLatency)
                .p95LatencyMs(p95Latency)
                .p99LatencyMs(p99Latency)
                .errorRate(errorRate)
                .throughputQps(metrics.getAvgQps() * 0.95)
                .cpuUtilization(cpuUtil)
                .memoryUtilization(memUtil)
                .stabilityScore(stabilityScore)
                .timeoutCount(timeouts)
                .rejectedCount(rejectedRequests)
                .avgResponseTimeStdDev(stdDev)
                .build();
    }

    private double calculateStabilityScore(double avgLatency, double p99Latency,
                                            double errorRate, double cpuUtil, double stdDev) {
        double latencyScore = Math.max(0, 1 - avgLatency / 1000);
        double p99Score = Math.max(0, 1 - p99Latency / 2000);
        double errorScore = Math.max(0, 1 - errorRate * 20);
        double cpuScore = Math.max(0, 1 - cpuUtil);
        double consistencyScore = Math.max(0, 1 - stdDev / 500);

        return latencyScore * 0.2 + p99Score * 0.25 + errorScore * 0.3 + cpuScore * 0.15 + consistencyScore * 0.1;
    }

    private double calculateStabilityImprovement(RateLimitEvaluation.StabilityMetrics before,
                                                  RateLimitEvaluation.StabilityMetrics after) {
        return (after.getStabilityScore() - before.getStabilityScore()) / before.getStabilityScore() * 100;
    }

    private double calculateLatencyReduction(RateLimitEvaluation.StabilityMetrics before,
                                              RateLimitEvaluation.StabilityMetrics after) {
        if (before.getAvgLatencyMs() == 0) return 0;
        return (before.getAvgLatencyMs() - after.getAvgLatencyMs()) / before.getAvgLatencyMs() * 100;
    }

    private double calculateErrorRateReduction(RateLimitEvaluation.StabilityMetrics before,
                                                RateLimitEvaluation.StabilityMetrics after) {
        if (before.getErrorRate() == 0) return 0;
        return (before.getErrorRate() - after.getErrorRate()) / before.getErrorRate() * 100;
    }

    private double calculateThroughputChange(RateLimitEvaluation.StabilityMetrics before,
                                              RateLimitEvaluation.StabilityMetrics after) {
        if (before.getThroughputQps() == 0) return 0;
        return (after.getThroughputQps() - before.getThroughputQps()) / before.getThroughputQps() * 100;
    }

    private double calculateEffectivenessScore(double stability, double latency,
                                                double errorRate) {
        return Math.min(100, (stability * 0.4 + latency * 0.3 + errorRate * 0.3));
    }

    private List<String> generateFindings(RateLimitEvaluation.StabilityMetrics before,
                                           RateLimitEvaluation.StabilityMetrics after,
                                           String serviceId) {
        List<String> findings = new ArrayList<>();

        findings.add(String.format("[%s] 限流前平均延迟: %.1fms → 限流后: %.1fms (降低%.1f%%)",
                serviceId, before.getAvgLatencyMs(), after.getAvgLatencyMs(),
                calculateLatencyReduction(before, after)));

        findings.add(String.format("[%s] 限流前P99延迟: %.1fms → 限流后: %.1fms",
                serviceId, before.getP99LatencyMs(), after.getP99LatencyMs()));

        findings.add(String.format("[%s] 限流前错误率: %.2f%% → 限流后: %.2f%% (降低%.1f%%)",
                serviceId, before.getErrorRate() * 100, after.getErrorRate() * 100,
                calculateErrorRateReduction(before, after)));

        findings.add(String.format("[%s] 限流前CPU使用率: %.1f%% → 限流后: %.1f%%",
                serviceId, before.getCpuUtilization() * 100, after.getCpuUtilization() * 100));

        findings.add(String.format("[%s] 响应时间标准差: %.1fms → %.1fms (波动性改善)",
                serviceId, before.getAvgResponseTimeStdDev(), after.getAvgResponseTimeStdDev()));

        findings.add(String.format("[%s] 超时次数: %d → %d",
                serviceId, before.getTimeoutCount(), after.getTimeoutCount()));

        if (after.getRejectedCount() > 0) {
            findings.add(String.format("[%s] 限流拒绝请求: %d (保护了系统稳定性)",
                    serviceId, after.getRejectedCount()));
        }

        return findings;
    }

    private String determineVerdict(double effectivenessScore) {
        if (effectivenessScore >= 70) return "限流效果显著，建议正式启用";
        if (effectivenessScore >= 50) return "限流效果良好，建议微调后启用";
        if (effectivenessScore >= 30) return "限流效果一般，建议优化阈值后重试";
        return "限流效果有限，需重新评估限流策略";
    }

    private Map<String, Object> generateRecommendations(RateLimitEvaluation.StabilityMetrics before,
                                                         RateLimitEvaluation.StabilityMetrics after,
                                                         double effectivenessScore) {
        Map<String, Object> recs = new HashMap<>();

        if (after.getRejectedCount() > before.getThroughputQps() * 3600 * 0.1) {
            recs.put("thresholdAdjustment", "建议适当提高QPS阈值，当前拒绝率偏高");
        }

        if (after.getP99LatencyMs() > 500) {
            recs.put("latencyOptimization", "P99延迟仍较高，建议增加服务实例或优化热点接口");
        }

        if (after.getErrorRate() > 0.01) {
            recs.put("errorHandling", "错误率仍偏高，建议增加熔断降级策略");
        }

        recs.put("warmUpPeriod", effectivenessScore < 50 ? "建议启用预热期，逐步放流" : "可直接上线");
        recs.put("monitoringWindow", "建议观察窗口: 30分钟");

        return recs;
    }

    private RateLimitEvaluation createEmptyEvaluation(String serviceId) {
        return RateLimitEvaluation.builder()
                .evaluationId("eval-" + UUID.randomUUID().toString().substring(0, 8))
                .serviceId(serviceId)
                .evaluationTime(LocalDateTime.now())
                .evaluationDurationMinutes(0)
                .overallVerdict("数据不足，无法评估")
                .effectivenessScore(0)
                .findings(Collections.singletonList("服务指标数据缺失"))
                .recommendations(new HashMap<>())
                .build();
    }

    public List<RateLimitEvaluation> getAllEvaluations() {
        return new ArrayList<>(evaluations.values());
    }

    public RateLimitEvaluation getEvaluation(String evaluationId) {
        return evaluations.get(evaluationId);
    }

    public List<RateLimitEvaluation> evaluateAllServices(int durationMinutes) {
        List<ServiceNode> services = topologyService.generateSampleServices();
        List<RateLimitEvaluation> results = new ArrayList<>();

        for (ServiceNode service : services) {
            results.add(evaluate(service.getServiceId(), durationMinutes));
        }

        return results;
    }
}
