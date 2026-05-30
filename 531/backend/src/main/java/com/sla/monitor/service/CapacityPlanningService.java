package com.sla.monitor.service;

import com.sla.monitor.engine.CalendarWindowMetrics;
import com.sla.monitor.model.CapacityPlan;
import com.sla.monitor.model.ServiceInfo;
import com.sla.monitor.model.SlaMetrics;
import com.sla.monitor.repository.ServiceInfoRepository;
import com.sla.monitor.repository.CapacityPlanRepository;
import com.sla.monitor.repository.SlaMetricsRepository;
import org.apache.commons.math3.stat.descriptive.DescriptiveStatistics;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.scheduling.annotation.Scheduled;
import org.springframework.stereotype.Service;

import java.time.LocalDateTime;
import java.util.ArrayList;
import java.util.List;

@Service
public class CapacityPlanningService {

    private static final Logger logger = LoggerFactory.getLogger(CapacityPlanningService.class);

    private final CapacityPlanRepository capacityPlanRepository;
    private final ServiceInfoRepository serviceInfoRepository;
    private final SlaMetricsRepository slaMetricsRepository;
    private final CalendarWindowMetrics calendarWindowMetrics;

    public CapacityPlanningService(CapacityPlanRepository capacityPlanRepository,
                                    ServiceInfoRepository serviceInfoRepository,
                                    SlaMetricsRepository slaMetricsRepository,
                                    CalendarWindowMetrics calendarWindowMetrics) {
        this.capacityPlanRepository = capacityPlanRepository;
        this.serviceInfoRepository = serviceInfoRepository;
        this.slaMetricsRepository = slaMetricsRepository;
        this.calendarWindowMetrics = calendarWindowMetrics;
    }

    @Scheduled(cron = "0 0 3 * * ?")
    public void dailyCapacityPlanning() {
        List<ServiceInfo> activeServices = serviceInfoRepository.findByActiveTrue();
        for (ServiceInfo service : activeServices) {
            generateCapacityPlan(service);
        }
        logger.info("Daily capacity planning completed for {} services", activeServices.size());
    }

    public CapacityPlan generateCapacityPlan(ServiceInfo service) {
        String serviceName = service.getServiceName();
        
        List<SlaMetrics> historicalMetrics = slaMetricsRepository
            .findByServiceNameAndTimestampAfterOrderByTimestampAsc(
                serviceName, LocalDateTime.now().minusDays(14));

        if (historicalMetrics.isEmpty()) {
            return null;
        }

        CalendarWindowMetrics.WindowMetrics currentMetrics = 
            calendarWindowMetrics.getWindowMetrics(serviceName, CalendarWindowMetrics.WindowType.CALENDAR_DAY);

        CapacityPlan throughputPlan = analyzeThroughputCapacity(service, historicalMetrics, currentMetrics);
        CapacityPlan latencyPlan = analyzeLatencyCapacity(service, historicalMetrics, currentMetrics);

        return capacityPlanRepository.save(throughputPlan);
    }

    private CapacityPlan analyzeThroughputCapacity(ServiceInfo service, 
                                                    List<SlaMetrics> historicalMetrics,
                                                    CalendarWindowMetrics.WindowMetrics currentMetrics) {
        DescriptiveStatistics requestStats = new DescriptiveStatistics();
        for (SlaMetrics metrics : historicalMetrics) {
            requestStats.addValue(metrics.getTotalRequests());
        }

        double avgRequests = requestStats.getMean();
        double stdRequests = requestStats.getStandardDeviation();
        double maxRequests = requestStats.getMax();
        double growthRate = calculateGrowthRate(historicalMetrics);

        double currentUtilization = Math.min(100.0, (currentMetrics.getTotalRequests() / Math.max(1, avgRequests * 2)) * 100);
        double predictedUtilization7d = currentUtilization * (1 + growthRate * 7);
        double predictedUtilization30d = currentUtilization * (1 + growthRate * 30);

        double slaLatencyTarget = service.getEffectiveLatencyTarget();
        double currentLatency = currentMetrics.getAvgLatencyMs();
        double headroomPercent = Math.max(0, (slaLatencyTarget - currentLatency) / slaLatencyTarget * 100);

        CapacityPlan plan = new CapacityPlan();
        plan.setServiceName(service.getServiceName());
        plan.setResourceType(CapacityPlan.ResourceType.REQUEST_THROUGHPUT);
        plan.setCurrentUtilization(currentUtilization);
        plan.setPredictedUtilization7d(Math.min(100.0, predictedUtilization7d));
        plan.setPredictedUtilization30d(Math.min(100.0, predictedUtilization30d));
        plan.setGrowthRate(growthRate * 100);
        plan.setPeakRequestsPerSecond((int) maxRequests);
        plan.setPredictedPeakRequests7d((int) (maxRequests * (1 + growthRate * 7)));
        plan.setPredictedPeakRequests30d((int) (maxRequests * (1 + growthRate * 30)));
        plan.setAvgLatencyMs(currentLatency);
        plan.setPredictedLatency7d(currentLatency * (1 + growthRate * 3));
        plan.setPredictedLatency30d(currentLatency * (1 + growthRate * 10));
        plan.setHeadroomPercent(headroomPercent);
        plan.setStatus(determineCapacityStatus(currentUtilization, predictedUtilization7d, headroomPercent));
        plan.setRecommendations(generateCapacityRecommendations(service, plan));
        plan.setSlaRequiredCapacity(calculateSlaRequiredCapacity(service));
        plan.setRecommendedCapacity(calculateRecommendedCapacity(plan, service));

        return plan;
    }

    private CapacityPlan analyzeLatencyCapacity(ServiceInfo service,
                                                 List<SlaMetrics> historicalMetrics,
                                                 CalendarWindowMetrics.WindowMetrics currentMetrics) {
        DescriptiveStatistics latencyStats = new DescriptiveStatistics();
        for (SlaMetrics metrics : historicalMetrics) {
            latencyStats.addValue(metrics.getAvgLatencyMs());
        }

        double avgLatency = latencyStats.getMean();
        double p95Latency = latencyStats.getPercentile(95);
        double slaLatencyTarget = service.getEffectiveLatencyTarget();

        double currentUtilization = (currentMetrics.getAvgLatencyMs() / slaLatencyTarget) * 100;
        double latencyGrowthRate = (p95Latency - avgLatency) / avgLatency;

        CapacityPlan plan = new CapacityPlan();
        plan.setServiceName(service.getServiceName());
        plan.setResourceType(CapacityPlan.ResourceType.CPU);
        plan.setCurrentUtilization(Math.min(100.0, currentUtilization));
        plan.setPredictedUtilization7d(Math.min(100.0, currentUtilization * (1 + latencyGrowthRate * 7)));
        plan.setPredictedUtilization30d(Math.min(100.0, currentUtilization * (1 + latencyGrowthRate * 30)));
        plan.setStatus(determineCapacityStatus(currentUtilization, plan.getPredictedUtilization7d(), 
            (slaLatencyTarget - currentMetrics.getAvgLatencyMs()) / slaLatencyTarget * 100));
        plan.setAvgLatencyMs(currentMetrics.getAvgLatencyMs());
        plan.setRecommendations(generateLatencyRecommendations(service, plan, p95Latency, slaLatencyTarget));

        return capacityPlanRepository.save(plan);
    }

    private double calculateGrowthRate(List<SlaMetrics> metrics) {
        if (metrics.size() < 2) return 0.01;

        double firstWeekAvg = metrics.subList(0, Math.min(7, metrics.size())).stream()
            .mapToLong(SlaMetrics::getTotalRequests)
            .average()
            .orElse(0);

        double lastWeekAvg = metrics.subList(Math.max(0, metrics.size() - 7), metrics.size()).stream()
            .mapToLong(SlaMetrics::getTotalRequests)
            .average()
            .orElse(0);

        if (firstWeekAvg == 0) return 0.01;
        return Math.max(0, (lastWeekAvg - firstWeekAvg) / firstWeekAvg / 7);
    }

    private CapacityPlan.CapacityStatus determineCapacityStatus(double currentUtilization, 
                                                                 double predictedUtilization7d,
                                                                 double headroomPercent) {
        if (currentUtilization >= 90 || predictedUtilization7d >= 95) {
            return CapacityPlan.CapacityStatus.CRITICAL;
        }
        if (currentUtilization >= 80 || predictedUtilization7d >= 85) {
            return CapacityPlan.CapacityStatus.NEEDS_EXPANSION;
        }
        if (currentUtilization >= 70 || predictedUtilization7d >= 75) {
            return CapacityPlan.CapacityStatus.WARNING;
        }
        if (currentUtilization < 30 && headroomPercent > 70) {
            return CapacityPlan.CapacityStatus.OVER_PROVISIONED;
        }
        return CapacityPlan.CapacityStatus.NORMAL;
    }

    private String generateCapacityRecommendations(ServiceInfo service, CapacityPlan plan) {
        List<String> recommendations = new ArrayList<>();

        switch (plan.getStatus()) {
            case CRITICAL:
                recommendations.add("立即扩容：资源利用率已达临界值");
                recommendations.add("考虑启用备用实例或服务降级");
                recommendations.add("紧急容量审查");
                break;
            case NEEDS_EXPANSION:
                recommendations.add(String.format("建议在7天内扩容：预计7天后利用率达%.1f%%", plan.getPredictedUtilization7d()));
                recommendations.add("评估当前架构可扩展性");
                break;
            case WARNING:
                recommendations.add("监控容量趋势");
                recommendations.add("准备扩容预案");
                break;
            case OVER_PROVISIONED:
                recommendations.add("考虑资源优化：当前利用率偏低");
                recommendations.add("评估缩容可能性以降低成本");
                break;
            default:
                recommendations.add("容量状态正常，继续监控");
        }

        if (service.getSlaTier() != null && service.getSlaTier().getPriorityLevel() <= 2) {
            recommendations.add("高等级服务，建议保持30%以上冗余容量");
        }

        recommendations.add(String.format("当前QPS峰值: %d, 预测7天峰值: %d", 
            plan.getPeakRequestsPerSecond(), plan.getPredictedPeakRequests7d()));

        return String.join(" | ", recommendations);
    }

    private String generateLatencyRecommendations(ServiceInfo service, CapacityPlan plan, 
                                                   double p95Latency, double slaTarget) {
        List<String> recommendations = new ArrayList<>();

        if (p95Latency > slaTarget * 0.9) {
            recommendations.add("P95延迟接近SLA目标，需要性能优化");
            recommendations.add("考虑数据库查询优化");
            recommendations.add("检查缓存命中率");
        }

        if (plan.getStatus() == CapacityPlan.CapacityStatus.CRITICAL || 
            plan.getStatus() == CapacityPlan.CapacityStatus.NEEDS_EXPANSION) {
            recommendations.add("考虑增加计算资源");
            recommendations.add("评估是否需要水平扩展");
        }

        return String.join(" | ", recommendations);
    }

    private double calculateSlaRequiredCapacity(ServiceInfo service) {
        double baseCapacity = 100.0;
        if (service.getSlaTier() != null) {
            switch (service.getSlaTier().getPriorityLevel()) {
                case 1: return baseCapacity * 1.5;
                case 2: return baseCapacity * 1.3;
                case 3: return baseCapacity * 1.15;
                case 4: return baseCapacity * 1.05;
                default: return baseCapacity;
            }
        }
        return baseCapacity;
    }

    private double calculateRecommendedCapacity(CapacityPlan plan, ServiceInfo service) {
        double peakCapacity = plan.getPeakRequestsPerSecond() * 1.5;
        double slaRequired = calculateSlaRequiredCapacity(service);
        double predictedCapacity = plan.getPredictedPeakRequests30d() * 1.2;
        return Math.max(Math.max(peakCapacity, slaRequired), predictedCapacity);
    }

    public CapacityPlan getLatestCapacityPlan(String serviceName) {
        return capacityPlanRepository.findFirstByServiceNameOrderByCreatedAtDesc(serviceName).orElse(null);
    }

    public List<CapacityPlan> getCapacityPlansForService(String serviceName) {
        return capacityPlanRepository.findByServiceNameOrderByCreatedAtDesc(serviceName);
    }

    public List<CapacityPlan> getAlertsForCapacity() {
        return capacityPlanRepository.findByStatusIn(
            List.of(CapacityPlan.CapacityStatus.CRITICAL, 
                    CapacityPlan.CapacityStatus.NEEDS_EXPANSION,
                    CapacityPlan.CapacityStatus.WARNING));
    }

    public List<CapacityPlan> getCriticalCapacityPlans() {
        return capacityPlanRepository.findByStatusOrderByCreatedAtDesc(CapacityPlan.CapacityStatus.CRITICAL);
    }

    public List<CapacityPlan> getRecentCapacityPlans(int days) {
        LocalDateTime startTime = LocalDateTime.now().minusDays(days);
        return capacityPlanRepository.findByCreatedAtAfterOrderByCreatedAtDesc(startTime);
    }
}
