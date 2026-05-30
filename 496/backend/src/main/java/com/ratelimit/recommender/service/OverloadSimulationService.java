package com.ratelimit.recommender.service;

import com.ratelimit.recommender.model.*;
import org.springframework.stereotype.Service;

import java.time.LocalDateTime;
import java.util.*;

@Service
public class OverloadSimulationService {

    private final QueueingTheoryService queueingTheoryService;

    public OverloadSimulationService(QueueingTheoryService queueingTheoryService) {
        this.queueingTheoryService = queueingTheoryService;
    }

    public OverloadSimulationResult runSimulation(ServiceNode service,
                                               OverloadSimulationRequest request,
                                               boolean withRateLimit) {

        String simulationId = UUID.randomUUID().toString();
        LocalDateTime startTime = LocalDateTime.now();

        Map<String, List<SimulationMetric>> metrics = new HashMap<>();
        List<String> bottlenecks = new ArrayList<>();

        double baseQps = service.getMetrics() != null ?
                service.getMetrics().getAvgQps() : 100;
        double targetQps = baseQps * request.getTrafficMultiplier();

        List<String> apis = request.getAffectedApis() != null && request.getAffectedApis().size() > 0 ?
                request.getAffectedApis() :
                new ArrayList<>(service.getEndpoints().keySet());

        for (String api : apis) {
            List<SimulationMetric> apiMetrics = simulateApiOverload(
                    service, api, targetQps,
                    request.getDurationSeconds(), withRateLimit);
            metrics.put(api, apiMetrics);
        }

        double totalErrorRate = calculateTotalErrorRate(metrics);
        double latencyIncrease = calculateLatencyIncrease(metrics);
        int droppedRequests = calculateDroppedRequests(metrics);

        if (totalErrorRate > 0.1 || latencyIncrease > 2.0) {
            bottlenecks.add(service.getServiceId() + " - 高错误率或延迟激增");
        }

        String conclusion = generateConclusion(withRateLimit, totalErrorRate, latencyIncrease);

        LocalDateTime endTime = LocalDateTime.now();

        return OverloadSimulationResult.builder()
                .simulationId(simulationId)
                .serviceId(service.getServiceId())
                .withRateLimit(withRateLimit)
                .metrics(metrics)
                .bottlenecks(bottlenecks)
                .estimatedErrorRate(totalErrorRate)
                .estimatedLatencyIncrease(latencyIncrease)
                .droppedRequests(droppedRequests)
                .startTime(startTime)
                .endTime(endTime)
                .conclusion(conclusion)
                .build();
    }

    private List<SimulationMetric> simulateApiOverload(ServiceNode service, String apiPath,
                                                 double targetQps, int durationSeconds,
                                                 boolean withRateLimit) {

        List<SimulationMetric> result = new ArrayList<>();

        ApiEndpoint endpoint = service.getEndpoints().get(apiPath);
        double baseLatency = endpoint != null && endpoint.getMetrics() != null ?
                endpoint.getMetrics().getAvgLatencyMs() : 50;
        double baseErrorRate = endpoint != null && endpoint.getMetrics() != null ?
                endpoint.getMetrics().getErrorRate() : 0.01;

        RateLimitRule limitRule = null;
        if (withRateLimit) {
            limitRule = queueingTheoryService.recommendServiceRateLimit(service)
                    .getRecommendedServiceRule();
        }

        int steps = durationSeconds;

        for (int i = 0; i < steps; i++) {
            LocalDateTime timestamp = LocalDateTime.now().plusSeconds(i);

            double rampUpFactor = Math.min(1.0, (i + 1) / (double) Math.min(10, steps));
            double currentQps = targetQps * rampUpFactor;

            double actualQps = currentQps;
            int rejected = 0;
            int queueSize = 0;

            if (withRateLimit && limitRule != null) {
                if (currentQps > limitRule.getQpsThreshold()) {
                    actualQps = limitRule.getQpsThreshold();
                    rejected = (int) (currentQps - limitRule.getQpsThreshold());
                    queueSize = Math.min(rejected, limitRule.getBurstCapacity());
                }
            }

            double overloadFactor = actualQps / Math.max(1, baseLatency / 10);
            double latency = baseLatency * (1 + overloadFactor * 0.5);

            double errorRate = baseErrorRate * (1 + overloadFactor * 2);

            result.add(SimulationMetric.builder()
                    .timestamp(timestamp)
                    .qps(actualQps)
                    .latencyMs(latency)
                    .errorRate(Math.min(1.0, errorRate))
                    .queueSize(queueSize)
                    .rejectedRequests(rejected)
                    .build());
        }

        return result;
    }

    private double calculateTotalErrorRate(Map<String, List<SimulationMetric>> metrics) {
        double totalErrorRate = 0;
        int count = 0;

        for (List<SimulationMetric> apiMetrics : metrics.values()) {
            for (SimulationMetric m : apiMetrics) {
                totalErrorRate += m.getErrorRate();
                count++;
            }
        }

        return count > 0 ? totalErrorRate / count : 0;
    }

    private double calculateLatencyIncrease(Map<String, List<SimulationMetric>> metrics) {
        double totalIncrease = 0;
        int count = 0;

        for (List<SimulationMetric> apiMetrics : metrics.values()) {
            if (apiMetrics.size() >= 2) {
                double firstLatency = apiMetrics.get(0).getLatencyMs();
                double lastLatency = apiMetrics.get(apiMetrics.size() - 1).getLatencyMs();
                if (firstLatency > 0) {
                    totalIncrease += lastLatency / firstLatency;
                    count++;
                }
            }
        }

        return count > 0 ? totalIncrease / count : 1.0;
    }

    private int calculateDroppedRequests(Map<String, List<SimulationMetric>> metrics) {
        int total = 0;
        for (List<SimulationMetric> apiMetrics : metrics.values()) {
            for (SimulationMetric m : apiMetrics) {
                total += m.getRejectedRequests();
            }
        }
        return total;
    }

    private String generateConclusion(boolean withRateLimit, double errorRate, double latencyIncrease) {
        StringBuilder sb = new StringBuilder();

        if (withRateLimit) {
            sb.append("启用限流保护: ");
            if (errorRate < 0.05) {
                sb.append("限流配置有效，系统在过载情况下保持稳定。");
            } else if (errorRate < 0.15) {
                sb.append("限流配置部分有效，建议进一步优化阈值。");
            } else {
                sb.append("限流配置不足，需要加强保护。");
            }
        } else {
            sb.append("无限流保护: ");
            if (errorRate > 0.1 || latencyIncrease > 2.0) {
                sb.append("系统在过载情况下出现严重性能下降，建议立即配置限流保护。");
            } else {
                sb.append("系统尚能承受当前负载，但存在风险。");
            }
        }

        sb.append(String.format(" 错误率: %.2f%%", errorRate * 100));
        sb.append(String.format(" 延迟增加: %.2f%%", (latencyIncrease - 1) * 100));

        return sb.toString();
    }

    public List<OverloadSimulationResult> compareSimulation(ServiceNode service, OverloadSimulationRequest request) {
        List<OverloadSimulationResult> results = new ArrayList<>();
        results.add(runSimulation(service, request, false));
        results.add(runSimulation(service, request, true));
        return results;
    }
}
