package com.ratelimit.recommender.service;

import com.ratelimit.recommender.model.*;
import org.apache.commons.math3.distribution.ExponentialDistribution;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;

import java.time.LocalDateTime;
import java.util.*;

@Service
public class QueueingTheoryService {

    @Value("${rate-limit.default.target-utilization:0.7}")
    private double targetUtilization;

    @Value("${rate-limit.default.queue-timeout:500}")
    private int queueTimeoutMs;

    public RateLimitRecommendation recommendServiceRateLimit(ServiceNode service) {
        List<String> reasoning = new ArrayList<>();
        ServiceMetrics metrics = service.getMetrics();

        if (metrics == null) {
            return createDefaultRecommendation(service.getServiceId());
        }

        double lambda = metrics.getPeakQps();
        double mu = calculateServiceRate(metrics);
        int servers = metrics.getInstanceCount();

        QueueingResult mmcResult = calculateMMc(lambda, mu, servers);

        int recommendedQps = calculateOptimalQps(mmcResult, metrics);
        int burstCapacity = calculateBurstCapacity(metrics, recommendedQps);

        reasoning.add(String.format("基于排队论M/M/c模型分析: 到达率λ=%.2f req/s, 服务率μ=%.2f req/s, 服务实例数c=%d",
                lambda, mu, servers));
        reasoning.add(String.format("当前系统利用率ρ=%.2f%%, 目标利用率=%.0f%%",
                mmcResult.getUtilization() * 100, targetUtilization * 100));
        reasoning.add(String.format("平均排队时间Wq=%.2fms, P99排队时间=%.2fms",
                mmcResult.getAvgQueueTimeMs(), mmcResult.getP99QueueTimeMs()));
        reasoning.add(String.format("推荐服务级限流阈值: %d QPS, 突发容量: %d",
                recommendedQps, burstCapacity));

        double riskScore = calculateRiskScore(mmcResult, metrics);

        Map<String, RateLimitRule> apiRules = recommendApiRateLimits(service);

        RateLimitRule serviceRule = RateLimitRule.builder()
                .qpsThreshold(recommendedQps)
                .burstCapacity(burstCapacity)
                .warmUpPeriodSec(60)
                .maxWaitTimeMs(queueTimeoutMs)
                .limitType("TOKEN_BUCKET")
                .fallbackStrategy("REJECT")
                .confidenceScore(calculateConfidence(metrics))
                .build();

        return RateLimitRecommendation.builder()
                .serviceId(service.getServiceId())
                .recommendedServiceRule(serviceRule)
                .recommendedApiRules(apiRules)
                .reasoning(reasoning)
                .riskScore(riskScore)
                .generateTime(LocalDateTime.now())
                .build();
    }

    private Map<String, RateLimitRule> recommendApiRateLimits(ServiceNode service) {
        Map<String, RateLimitRule> apiRules = new HashMap<>();

        if (service.getEndpoints() == null) {
            return apiRules;
        }

        for (Map.Entry<String, ApiEndpoint> entry : service.getEndpoints().entrySet()) {
            ApiEndpoint endpoint = entry.getValue();
            ApiMetrics metrics = endpoint.getMetrics();

            if (metrics == null) {
                continue;
            }

            double lambda = metrics.getPeakQps();
            double mu = 1000.0 / metrics.getAvgLatencyMs();

            QueueingResult mm1Result = calculateMM1(lambda, mu);

            int qpsThreshold = (int) Math.ceil(lambda * 1.2);
            int burst = (int) Math.ceil(metrics.getPeakQps() * 1.5);

            RateLimitRule rule = RateLimitRule.builder()
                    .qpsThreshold(qpsThreshold)
                    .burstCapacity(burst)
                    .warmUpPeriodSec(30)
                    .maxWaitTimeMs(200)
                    .limitType("LEAKY_BUCKET")
                    .fallbackStrategy("QUEUE")
                    .confidenceScore(Math.min(0.9, metrics.getTotalRequests() > 10000 ? 0.85 : 0.6))
                    .build();

            apiRules.put(entry.getKey(), rule);
        }

        return apiRules;
    }

    private QueueingResult calculateMMc(double lambda, double mu, int c) {
        if (lambda <= 0 || mu <= 0 || c <= 0) {
            return QueueingResult.builder().build();
        }

        double rho = lambda / (c * mu);

        if (rho >= 1.0) {
            rho = 0.95;
        }

        double p0 = calculateP0(lambda, mu, c, rho);
        double lq = (p0 * Math.pow(lambda / mu, c) * rho) / (factorial(c) * Math.pow(1 - rho, 2));
        double wq = lq / lambda;
        double w = wq + 1 / mu;
        double l = lambda * w;

        double p99QueueTime = calculatePercentileQueueTime(wq, 0.99);

        return QueueingResult.builder()
                .arrivalRate(lambda)
                .serviceRate(mu)
                .servers(c)
                .utilization(rho)
                .avgQueueLength(lq)
                .avgSystemLength(l)
                .avgQueueTimeMs(wq * 1000)
                .avgSystemTimeMs(w * 1000)
                .p99QueueTimeMs(p99QueueTime)
                .idleProbability(p0)
                .build();
    }

    private QueueingResult calculateMM1(double lambda, double mu) {
        if (lambda <= 0 || mu <= 0) {
            return QueueingResult.builder().build();
        }

        double rho = lambda / mu;

        if (rho >= 1.0) {
            rho = 0.9;
        }

        double p0 = 1 - rho;
        double lq = (rho * rho) / (1 - rho);
        double wq = lq / lambda;
        double w = wq + 1 / mu;
        double l = lambda * w;

        double p99QueueTime = calculatePercentileQueueTime(wq, 0.99);

        return QueueingResult.builder()
                .arrivalRate(lambda)
                .serviceRate(mu)
                .servers(1)
                .utilization(rho)
                .avgQueueLength(lq)
                .avgSystemLength(l)
                .avgQueueTimeMs(wq * 1000)
                .avgSystemTimeMs(w * 1000)
                .p99QueueTimeMs(p99QueueTime)
                .idleProbability(p0)
                .build();
    }

    private double calculateP0(double lambda, double mu, int c, double rho) {
        double sum = 0.0;
        for (int n = 0; n < c; n++) {
            sum += Math.pow(lambda / mu, n) / factorial(n);
        }
        double term = Math.pow(lambda / mu, c) / (factorial(c) * (1 - rho));
        return 1.0 / (sum + term);
    }

    private long factorial(int n) {
        if (n <= 1) return 1;
        long result = 1;
        for (int i = 2; i <= n; i++) {
            result *= i;
        }
        return result;
    }

    private double calculatePercentileQueueTime(double avgWaitTime, double percentile) {
        if (avgWaitTime <= 0) return 0;
        ExponentialDistribution dist = new ExponentialDistribution(avgWaitTime);
        return dist.inverseCumulativeProbability(percentile);
    }

    private double calculateServiceRate(ServiceMetrics metrics) {
        double avgLatencySec = metrics.getAvgLatencyMs() / 1000.0;
        if (avgLatencySec <= 0) return 10.0;
        return 1.0 / avgLatencySec;
    }

    private int calculateOptimalQps(QueueingResult result, ServiceMetrics metrics) {
        double currentPeak = metrics.getPeakQps();
        double currentUtil = result.getUtilization();

        if (currentUtil <= targetUtilization) {
            return (int) Math.ceil(currentPeak * 1.3);
        }

        double optimalLambda = targetUtilization * result.getServers() * result.getServiceRate();
        return (int) Math.ceil(Math.max(optimalLambda, currentPeak * 0.8));
    }

    private int calculateBurstCapacity(ServiceMetrics metrics, int recommendedQps) {
        double peakToAvgRatio = metrics.getPeakQps() / Math.max(1, metrics.getAvgQps());
        int burst = (int) (recommendedQps * Math.max(1.5, Math.min(peakToAvgRatio, 3.0)));
        return Math.max(recommendedQps + 10, burst);
    }

    private double calculateRiskScore(QueueingResult result, ServiceMetrics metrics) {
        double utilRisk = Math.max(0, (result.getUtilization() - 0.7) / 0.3);
        double latencyRisk = Math.min(1.0, metrics.getP99LatencyMs() / 1000.0);
        double errorRisk = Math.min(1.0, metrics.getErrorRate() * 20);

        return (utilRisk * 0.4 + latencyRisk * 0.35 + errorRisk * 0.25);
    }

    private double calculateConfidence(ServiceMetrics metrics) {
        double dataConfidence = Math.min(1.0, metrics.getTotalRequests() / 100000.0);
        double stabilityConfidence = Math.max(0, 1 - metrics.getErrorRate() * 10);

        return (dataConfidence * 0.6 + stabilityConfidence * 0.4);
    }

    private RateLimitRecommendation createDefaultRecommendation(String serviceId) {
        RateLimitRule defaultRule = RateLimitRule.builder()
                .qpsThreshold(100)
                .burstCapacity(200)
                .warmUpPeriodSec(60)
                .maxWaitTimeMs(500)
                .limitType("TOKEN_BUCKET")
                .fallbackStrategy("REJECT")
                .confidenceScore(0.5)
                .build();

        return RateLimitRecommendation.builder()
                .serviceId(serviceId)
                .recommendedServiceRule(defaultRule)
                .recommendedApiRules(new HashMap<>())
                .reasoning(Collections.singletonList("数据不足，使用默认限流配置"))
                .riskScore(0.5)
                .generateTime(LocalDateTime.now())
                .build();
    }

    @lombok.Data
    @lombok.Builder
    public static class QueueingResult {
        private double arrivalRate;
        private double serviceRate;
        private int servers;
        private double utilization;
        private double avgQueueLength;
        private double avgSystemLength;
        private double avgQueueTimeMs;
        private double avgSystemTimeMs;
        private double p99QueueTimeMs;
        private double idleProbability;
    }
}
