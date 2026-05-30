package com.ratelimit.recommender.service;

import com.ratelimit.recommender.model.*;
import org.springframework.stereotype.Service;

import java.time.LocalDateTime;
import java.util.*;
import java.util.concurrent.ConcurrentHashMap;

@Service
public class RateLimitDrillService {

    private final TopologyAnalysisService topologyService;
    private final QueueingTheoryService queueingService;
    private final Map<String, RateLimitDrill> activeDrills = new ConcurrentHashMap<>();
    private final Map<String, RateLimitDrill> completedDrills = new ConcurrentHashMap<>();

    public RateLimitDrillService(TopologyAnalysisService topologyService,
                                  QueueingTheoryService queueingService) {
        this.topologyService = topologyService;
        this.queueingService = queueingService;
    }

    public RateLimitDrill startDrill(String serviceId, RateLimitDrill.DrillConfig config) {
        String drillId = "drill-" + UUID.randomUUID().toString().substring(0, 8);

        RateLimitDrill drill = RateLimitDrill.builder()
                .drillId(drillId)
                .serviceId(serviceId)
                .status(RateLimitDrill.DrillStatus.RUNNING)
                .config(config)
                .startTime(LocalDateTime.now())
                .phases(new ArrayList<>())
                .metricsTimeSeries(new HashMap<>())
                .build();

        activeDrills.put(drillId, drill);

        executeDrill(drill);

        return drill;
    }

    private void executeDrill(RateLimitDrill drill) {
        RateLimitDrill.DrillConfig config = drill.getConfig();
        List<RateLimitDrill.DrillPhase> phases = drill.getPhases();
        List<ServiceNode> services = topologyService.generateSampleServices();

        ServiceNode service = services.stream()
                .filter(s -> s.getServiceId().equals(drill.getServiceId()))
                .findFirst()
                .orElse(null);

        double baseLatency = service != null && service.getMetrics() != null ?
                service.getMetrics().getAvgLatencyMs() : 50;
        double baseErrorRate = service != null && service.getMetrics() != null ?
                service.getMetrics().getErrorRate() : 0.01;

        RateLimitDrill.DrillPhase rampUp = simulateRampUpPhase(config, baseLatency, baseErrorRate);
        phases.add(rampUp);

        RateLimitDrill.DrillPhase sustain = simulateSustainPhase(config, baseLatency, baseErrorRate);
        phases.add(sustain);

        RateLimitDrill.DrillPhase atLimit = simulateAtLimitPhase(config, baseLatency, baseErrorRate);
        phases.add(atLimit);

        RateLimitDrill.DrillPhase overLimit = simulateOverLimitPhase(config, baseLatency, baseErrorRate);
        phases.add(overLimit);

        RateLimitDrill.DrillPhase rampDown = simulateRampDownPhase(config, baseLatency, baseErrorRate);
        phases.add(rampDown);

        RateLimitDrill.DrillSummary summary = calculateSummary(phases, config);
        drill.setSummary(summary);

        generateMetricsTimeSeries(drill);

        drill.setEndTime(LocalDateTime.now());
        drill.setStatus(RateLimitDrill.DrillStatus.COMPLETED);

        completedDrills.put(drill.getDrillId(), drill);
        activeDrills.remove(drill.getDrillId());
    }

    private RateLimitDrill.DrillPhase simulateRampUpPhase(RateLimitDrill.DrillConfig config,
                                                            double baseLatency, double baseErrorRate) {
        double avgQps = config.getTargetQps() * 0.5;
        double latency = baseLatency * (1 + avgQps / config.getThresholdQps() * 0.3);
        double errorRate = baseErrorRate * (1 + avgQps / config.getThresholdQps() * 0.5);

        return RateLimitDrill.DrillPhase.builder()
                .phaseName("流量爬坡")
                .startTime(LocalDateTime.now())
                .endTime(LocalDateTime.now().plusSeconds(config.getRampUpSeconds()))
                .qps(avgQps)
                .avgLatencyMs(latency)
                .errorRate(Math.min(1.0, errorRate))
                .rejectedRequests(0)
                .acceptedRequests((int) (avgQps * config.getRampUpSeconds()))
                .queueWaitTimeMs(0)
                .build();
    }

    private RateLimitDrill.DrillPhase simulateSustainPhase(RateLimitDrill.DrillConfig config,
                                                             double baseLatency, double baseErrorRate) {
        double avgQps = config.getTargetQps() * 0.8;
        double loadRatio = avgQps / config.getThresholdQps();
        double latency = baseLatency * (1 + loadRatio * 0.5);
        double errorRate = baseErrorRate * (1 + loadRatio);

        return RateLimitDrill.DrillPhase.builder()
                .phaseName("稳态运行")
                .startTime(LocalDateTime.now().plusSeconds(config.getRampUpSeconds()))
                .endTime(LocalDateTime.now().plusSeconds(config.getRampUpSeconds() + config.getSustainSeconds()))
                .qps(avgQps)
                .avgLatencyMs(latency)
                .errorRate(Math.min(1.0, errorRate))
                .rejectedRequests(0)
                .acceptedRequests((int) (avgQps * config.getSustainSeconds()))
                .queueWaitTimeMs(loadRatio > 0.7 ? latency * 0.1 : 0)
                .build();
    }

    private RateLimitDrill.DrillPhase simulateAtLimitPhase(RateLimitDrill.DrillConfig config,
                                                             double baseLatency, double baseErrorRate) {
        double avgQps = config.getThresholdQps();
        double loadRatio = 1.0;
        double latency = baseLatency * (1 + loadRatio * 0.8);
        double errorRate = baseErrorRate * (1 + loadRatio * 2);
        int rejected = (int) (avgQps * 0.05 * 10);

        return RateLimitDrill.DrillPhase.builder()
                .phaseName("达到限流阈值")
                .startTime(LocalDateTime.now().plusSeconds(config.getRampUpSeconds() + config.getSustainSeconds()))
                .endTime(LocalDateTime.now().plusSeconds(config.getRampUpSeconds() + config.getSustainSeconds() + 10))
                .qps(avgQps)
                .avgLatencyMs(latency)
                .errorRate(Math.min(1.0, errorRate))
                .rejectedRequests(rejected)
                .acceptedRequests((int) (avgQps * 10) - rejected)
                .queueWaitTimeMs(latency * 0.2)
                .build();
    }

    private RateLimitDrill.DrillPhase simulateOverLimitPhase(RateLimitDrill.DrillConfig config,
                                                              double baseLatency, double baseErrorRate) {
        double avgQps = config.getTargetQps();
        double overRatio = avgQps / config.getThresholdQps();
        double excessQps = Math.max(0, avgQps - config.getThresholdQps());

        double acceptedQps = config.getThresholdQps();
        double rejectedQps = excessQps;

        double latency;
        double errorRate;
        int rejected;

        if (config.isEnableFallback()) {
            latency = baseLatency * 1.5;
            errorRate = baseErrorRate * 3;
            rejected = (int) (rejectedQps * 15);
        } else {
            latency = baseLatency * (1 + overRatio * 1.5);
            errorRate = baseErrorRate * (1 + overRatio * 5);
            rejected = (int) (rejectedQps * 15);
        }

        return RateLimitDrill.DrillPhase.builder()
                .phaseName("超限流量")
                .startTime(LocalDateTime.now().plusSeconds(
                        config.getRampUpSeconds() + config.getSustainSeconds() + 10))
                .endTime(LocalDateTime.now().plusSeconds(
                        config.getRampUpSeconds() + config.getSustainSeconds() + 25))
                .qps(avgQps)
                .avgLatencyMs(latency)
                .errorRate(Math.min(1.0, errorRate))
                .rejectedRequests(rejected)
                .acceptedRequests((int) (acceptedQps * 15))
                .queueWaitTimeMs(latency * 0.3)
                .build();
    }

    private RateLimitDrill.DrillPhase simulateRampDownPhase(RateLimitDrill.DrillConfig config,
                                                              double baseLatency, double baseErrorRate) {
        double avgQps = config.getTargetQps() * 0.3;
        double latency = baseLatency * 1.1;
        double errorRate = baseErrorRate;

        return RateLimitDrill.DrillPhase.builder()
                .phaseName("流量回落")
                .startTime(LocalDateTime.now().plusSeconds(
                        config.getRampUpSeconds() + config.getSustainSeconds() + 25))
                .endTime(LocalDateTime.now().plusSeconds(
                        config.getRampUpSeconds() + config.getSustainSeconds() + 25 + config.getRampDownSeconds()))
                .qps(avgQps)
                .avgLatencyMs(latency)
                .errorRate(errorRate)
                .rejectedRequests(0)
                .acceptedRequests((int) (avgQps * config.getRampDownSeconds()))
                .queueWaitTimeMs(0)
                .build();
    }

    private RateLimitDrill.DrillSummary calculateSummary(List<RateLimitDrill.DrillPhase> phases,
                                                          RateLimitDrill.DrillConfig config) {
        int totalRequests = phases.stream().mapToInt(p -> p.getAcceptedRequests() + p.getRejectedRequests()).sum();
        int acceptedRequests = phases.stream().mapToInt(RateLimitDrill.DrillPhase::getAcceptedRequests).sum();
        int rejectedRequests = phases.stream().mapToInt(RateLimitDrill.DrillPhase::getRejectedRequests).sum();
        int timeoutRequests = (int) (phases.stream()
                .mapToDouble(RateLimitDrill.DrillPhase::getErrorRate)
                .average()
                .orElse(0) * acceptedRequests);

        double rejectionRate = totalRequests > 0 ? (double) rejectedRequests / totalRequests : 0;
        double avgLatency = phases.stream().mapToDouble(RateLimitDrill.DrillPhase::getAvgLatencyMs).average().orElse(0);
        double peakLatency = phases.stream().mapToDouble(RateLimitDrill.DrillPhase::getAvgLatencyMs).max().orElse(0);
        double avgErrorRate = phases.stream().mapToDouble(RateLimitDrill.DrillPhase::getErrorRate).average().orElse(0);

        RateLimitDrill.DrillPhase atLimit = phases.stream()
                .filter(p -> "达到限流阈值".equals(p.getPhaseName()))
                .findFirst()
                .orElse(null);

        RateLimitDrill.DrillPhase overLimit = phases.stream()
                .filter(p -> "超限流量".equals(p.getPhaseName()))
                .findFirst()
                .orElse(null);

        double protectionEffectiveness = 0;
        if (overLimit != null && atLimit != null) {
            double latencyIncrease = (overLimit.getAvgLatencyMs() - atLimit.getAvgLatencyMs()) / atLimit.getAvgLatencyMs();
            protectionEffectiveness = Math.max(0, 1 - latencyIncrease) * 100;

            if (config.isEnableFallback()) {
                protectionEffectiveness = Math.min(100, protectionEffectiveness + 20);
            }
        }

        List<String> observations = new ArrayList<>();
        observations.add(String.format("总请求量: %d, 接受: %d, 拒绝: %d", totalRequests, acceptedRequests, rejectedRequests));
        observations.add(String.format("平均延迟: %.1fms, 峰值延迟: %.1fms", avgLatency, peakLatency));
        observations.add(String.format("平均错误率: %.2f%%, 拒绝率: %.2f%%", avgErrorRate * 100, rejectionRate * 100));

        if (rejectionRate > 0.1) {
            observations.add("限流保护生效，超量请求被有效拦截");
        }
        if (peakLatency < avgLatency * 2) {
            observations.add("限流后延迟波动较小，系统表现稳定");
        }
        if (config.isEnableFallback() && rejectedRequests > 0) {
            observations.add("降级策略生效，被限流请求得到妥善处理");
        }

        String conclusion;
        if (protectionEffectiveness >= 80) {
            conclusion = "限流保护效果优秀，系统在超限流量下保持稳定";
        } else if (protectionEffectiveness >= 50) {
            conclusion = "限流保护效果良好，建议微调阈值进一步优化";
        } else {
            conclusion = "限流保护效果有限，建议调整策略或增加降级保护";
        }

        return RateLimitDrill.DrillSummary.builder()
                .totalRequests(totalRequests)
                .acceptedRequests(acceptedRequests)
                .rejectedRequests(rejectedRequests)
                .timeoutRequests(timeoutRequests)
                .rejectionRate(rejectionRate)
                .avgLatencyMs(avgLatency)
                .peakLatencyMs(peakLatency)
                .avgErrorRate(avgErrorRate)
                .protectionEffectiveness(protectionEffectiveness)
                .conclusion(conclusion)
                .observations(observations)
                .build();
    }

    private void generateMetricsTimeSeries(RateLimitDrill drill) {
        Map<String, List<TimeSeriesPoint>> series = new HashMap<>();
        LocalDateTime startTime = drill.getStartTime();

        List<TimeSeriesPoint> qpsSeries = new ArrayList<>();
        List<TimeSeriesPoint> latencySeries = new ArrayList<>();
        List<TimeSeriesPoint> errorRateSeries = new ArrayList<>();

        int pointIndex = 0;
        for (RateLimitDrill.DrillPhase phase : drill.getPhases()) {
            int durationSeconds = (int) java.time.Duration.between(phase.getStartTime(), phase.getEndTime()).getSeconds();
            int points = Math.max(1, durationSeconds);

            for (int i = 0; i < points; i++) {
                LocalDateTime ts = startTime.plusSeconds(pointIndex);
                double noise = (Math.random() - 0.5) * 0.1;

                qpsSeries.add(TimeSeriesPoint.builder()
                        .timestamp(ts)
                        .value(phase.getQps() * (1 + noise))
                        .upperBound(phase.getQps() * 1.1)
                        .lowerBound(phase.getQps() * 0.9)
                        .build());

                latencySeries.add(TimeSeriesPoint.builder()
                        .timestamp(ts)
                        .value(phase.getAvgLatencyMs() * (1 + noise * 0.5))
                        .upperBound(phase.getAvgLatencyMs() * 1.2)
                        .lowerBound(phase.getAvgLatencyMs() * 0.8)
                        .build());

                errorRateSeries.add(TimeSeriesPoint.builder()
                        .timestamp(ts)
                        .value(phase.getErrorRate() * (1 + noise * 0.3))
                        .upperBound(phase.getErrorRate() * 1.3)
                        .lowerBound(phase.getErrorRate() * 0.7)
                        .build());

                pointIndex++;
            }
        }

        series.put("qps", qpsSeries);
        series.put("latency", latencySeries);
        series.put("errorRate", errorRateSeries);

        drill.setMetricsTimeSeries(series);
    }

    public List<RateLimitDrill> getActiveDrills() {
        return new ArrayList<>(activeDrills.values());
    }

    public List<RateLimitDrill> getCompletedDrills() {
        return new ArrayList<>(completedDrills.values());
    }

    public RateLimitDrill getDrill(String drillId) {
        RateLimitDrill drill = activeDrills.get(drillId);
        if (drill == null) {
            drill = completedDrills.get(drillId);
        }
        return drill;
    }

    public boolean abortDrill(String drillId) {
        RateLimitDrill drill = activeDrills.remove(drillId);
        if (drill != null) {
            drill.setStatus(RateLimitDrill.DrillStatus.ABORTED);
            drill.setEndTime(LocalDateTime.now());
            completedDrills.put(drillId, drill);
            return true;
        }
        return false;
    }

    public RateLimitDrill.DrillConfig createDefaultDrillConfig(String serviceId) {
        List<ServiceNode> services = topologyService.generateSampleServices();
        ServiceNode service = services.stream()
                .filter(s -> s.getServiceId().equals(serviceId))
                .findFirst()
                .orElse(null);

        double peakQps = service != null && service.getMetrics() != null ?
                service.getMetrics().getPeakQps() : 200;
        double targetQps = peakQps * 1.5;
        int thresholdQps = (int) (peakQps * 1.2);

        return RateLimitDrill.DrillConfig.builder()
                .targetQps(targetQps)
                .thresholdQps(thresholdQps)
                .rampUpSeconds(10)
                .sustainSeconds(30)
                .rampDownSeconds(10)
                .limitType("TOKEN_BUCKET")
                .enableFallback(true)
                .fallbackStrategy("QUEUE")
                .build();
    }
}
