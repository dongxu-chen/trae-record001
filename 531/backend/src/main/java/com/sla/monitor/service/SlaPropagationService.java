package com.sla.monitor.service;

import com.sla.monitor.engine.CalendarWindowMetrics;
import com.sla.monitor.model.*;
import com.sla.monitor.repository.ServiceDependencyRepository;
import com.sla.monitor.repository.ServiceInfoRepository;
import com.sla.monitor.repository.AlertRepository;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.scheduling.annotation.Scheduled;
import org.springframework.stereotype.Service;

import java.time.LocalDateTime;
import java.util.*;

@Service
public class SlaPropagationService {

    private static final Logger logger = LoggerFactory.getLogger(SlaPropagationService.class);

    private final ServiceDependencyRepository dependencyRepository;
    private final ServiceInfoRepository serviceInfoRepository;
    private final AlertRepository alertRepository;
    private final CalendarWindowMetrics calendarWindowMetrics;

    public SlaPropagationService(ServiceDependencyRepository dependencyRepository,
                               ServiceInfoRepository serviceInfoRepository,
                               AlertRepository alertRepository,
                               CalendarWindowMetrics calendarWindowMetrics) {
        this.dependencyRepository = dependencyRepository;
        this.serviceInfoRepository = serviceInfoRepository;
        this.alertRepository = alertRepository;
        this.calendarWindowMetrics = calendarWindowMetrics;
    }

    @Scheduled(fixedDelay = 60000)
    public void analyzePropagationCheck() {
        List<ServiceInfo> activeServices = serviceInfoRepository.findByActiveTrue();
        for (ServiceInfo service : activeServices) {
            analyzeServicePropagation(service);
        }
    }

    public PropagationResult analyzeServicePropagation(ServiceInfo service) {
        String serviceName = service.getServiceName();
        
        List<ServiceDependency> upstreamDependencies = 
            dependencyRepository.findByDownstreamServiceAndActiveTrue(serviceName);

        if (upstreamDependencies.isEmpty()) {
            return null;
        }

        PropagationResult result = new PropagationResult();
        result.setServiceName(serviceName);
        result.setAnalysisTime(LocalDateTime.now());

        double combinedAvailabilityImpact = 0.0;
        double combinedLatencyImpact = 0.0;
        double combinedErrorRateImpact = 0.0;

        List<DependencyImpact> impacts = new ArrayList<>();

        for (ServiceDependency dependency : upstreamDependencies) {
            String upstreamName = dependency.getUpstreamService();
            
            CalendarWindowMetrics.WindowMetrics upstreamMetrics = 
                calendarWindowMetrics.getWindowMetrics(
                    upstreamName, CalendarWindowMetrics.WindowType.SLIDING_HOUR);

            DependencyImpact impact = calculateDependencyImpact(dependency, upstreamMetrics, service);
            impacts.add(impact);

            combinedAvailabilityImpact += impact.getAvailabilityImpact();
            combinedLatencyImpact += impact.getLatencyImpact();
            combinedErrorRateImpact += impact.getErrorRateImpact();

            if (impact.isCriticalViolation()) {
                generatePropagationAlert(service, dependency, impact);
            }
        }

        result.setDependencyImpacts(impacts);
        result.setCombinedAvailabilityImpact(Math.min(100.0, combinedAvailabilityImpact));
        result.setCombinedLatencyImpact(combinedLatencyImpact);
        result.setCombinedErrorRateImpact(combinedErrorRateImpact);
        result.setOverallRiskLevel(calculateOverallRiskLevel(impacts));
        result.setRecommendations(generatePropagationRecommendations(service, impacts));

        return result;
    }

    private DependencyImpact calculateDependencyImpact(ServiceDependency dependency,
                                               CalendarWindowMetrics.WindowMetrics upstreamMetrics,
                                               ServiceInfo downstreamService) {

        DependencyImpact impact = new DependencyImpact();
        impact.setUpstreamService(dependency.getUpstreamService());
        impact.setDependencyType(dependency.getDependencyType());
        impact.setImpactLevel(dependency.getImpactLevel());

        double impactFactor = dependency.getSlaImpactFactor();

        double upstreamAvailability = upstreamMetrics.getAvailability();
        double upstreamLatency = upstreamMetrics.getAvgLatencyMs();
        double upstreamErrorRate = upstreamMetrics.getErrorRate();

        ServiceInfo upstreamService = serviceInfoRepository
            .findByServiceName(dependency.getUpstreamService())
            .orElse(null);

        double upstreamAvailTarget = upstreamService != null ?
            upstreamService.getEffectiveAvailabilityTarget() : 99.9;
        double upstreamLatencyTarget = upstreamService != null ?
            upstreamService.getEffectiveLatencyTarget() : 500.0;
        double upstreamErrorTarget = upstreamService != null ?
            upstreamService.getEffectiveErrorRateTarget() : 1.0;

        double availabilityDeficit = Math.max(0, upstreamAvailTarget - upstreamAvailability);
        double availabilityImpact = availabilityDeficit *
            dependency.getAvailabilityDependencyWeight() * impactFactor;

        double latencyExcess = Math.max(0, upstreamLatency - upstreamLatencyTarget);
        double latencyImpact = (latencyExcess / Math.max(1, upstreamLatencyTarget)) *
            dependency.getLatencyDependencyWeight() * impactFactor * 100;

        double errorRateExcess = Math.max(0, upstreamErrorRate - upstreamErrorTarget);
        double errorRateImpact = errorRateExcess *
            dependency.getErrorRateDependencyWeight() * impactFactor;

        impact.setAvailabilityImpact(availabilityImpact);
        impact.setLatencyImpact(latencyImpact);
        impact.setErrorRateImpact(errorRateImpact);

        boolean thresholdViolation = availabilityDeficit > 0.1 ||
            latencyExcess > 50 ||
            errorRateExcess > 0.5;

        impact.setCriticalViolation(thresholdViolation &&
            (dependency.getImpactLevel() == ServiceDependency.ImpactLevel.CRITICAL ||
            dependency.getImpactLevel() == ServiceDependency.ImpactLevel.HIGH));

        return impact;
    }

    private void generatePropagationAlert(ServiceInfo downstreamService,
                                        ServiceDependency dependency,
                                        DependencyImpact impact) {

        String downstreamName = downstreamService.getServiceName();
        String upstreamName = dependency.getUpstreamService();

        List<Alert> existingAlerts = alertRepository
            .findByServiceNameAndResolvedFalseOrderByCreatedAtDesc(downstreamName);

        boolean alertExists = existingAlerts.stream()
            .anyMatch(a -> a.getAlertType() == Alert.AlertType.DEPENDENCY_SLA_PROPAGATION);

        if (alertExists) {
            return;
        }

        Alert alert = new Alert();
        alert.setServiceName(downstreamName);
        alert.setAlertType(Alert.AlertType.DEPENDENCY_SLA_PROPAGATION);
        alert.setSeverity(determinePropagationSeverity(dependency.getImpactLevel()));
        alert.setMessage(String.format(
            "上游服务 %s SLA违规可能影响下游服务 %s",
            upstreamName, downstreamName));
        alert.setCurrentValue(impact.getAvailabilityImpact());
        alert.setThresholdValue(0.1);
        alert.setAcknowledged(false);
        alert.setResolved(false);

        alertRepository.save(alert);
        logger.warn("Created propagation alert for {} due to upstream violation in {} SLA propagation impact",
            downstreamName, upstreamName);
    }

    private Alert.AlertSeverity determinePropagationSeverity(ServiceDependency.ImpactLevel impactLevel) {

        switch (impactLevel) {
            case CRITICAL:
                return Alert.AlertSeverity.CRITICAL;
            case HIGH:
                return Alert.AlertSeverity.HIGH;
            case MEDIUM:
                return Alert.AlertSeverity.MEDIUM;
            default:
                return Alert.AlertSeverity.LOW;
        }
    }

    private String calculateOverallRiskLevel(List<DependencyImpact> impacts) {

        boolean hasCritical = impacts.stream()
            .anyMatch(i -> i.isCriticalViolation() &&
                (i.getImpactLevel() == ServiceDependency.ImpactLevel.CRITICAL));

        if (hasCritical) return "CRITICAL";

        boolean hasHigh = impacts.stream()
            .anyMatch(i -> i.isCriticalViolation() &&
                i.getImpactLevel() == ServiceDependency.ImpactLevel.HIGH);

        if (hasHigh) return "HIGH";

        boolean hasWarning = impacts.stream()
            .anyMatch(DependencyImpact::isCriticalViolation);

        return hasWarning ? "WARNING" : "NORMAL";
    }

    private List<String> generatePropagationRecommendations(ServiceInfo service,
                                                       List<DependencyImpact> impacts) {

        List<String> recommendations = new ArrayList<>();

        long criticalCount = impacts.stream()
            .filter(i -> i.getImpactLevel() == ServiceDependency.ImpactLevel.CRITICAL)
            .count();

        if (criticalCount > 0) {
            recommendations.add(String.format("发现 %d 个关键依赖需要关注", criticalCount));
            recommendations.add("考虑为关键依赖配置熔断降级策略");
            recommendations.add("评估多活容灾方案");
        }

        impacts.stream()
            .filter(DependencyImpact::isCriticalViolation)
            .forEach(impact -> {
                recommendations.add(String.format(
                    "服务 %s 存在SLA传导风险",
                    impact.getUpstreamService()));
            });

        recommendations.add("定期审查服务依赖SLA适配性");

        return recommendations;
    }

    public List<ServiceDependency> getUpstreamDependencies(String serviceName) {
        return dependencyRepository.findByDownstreamServiceAndActiveTrue(serviceName);
    }

    public List<ServiceDependency> getDownstreamDependencies(String serviceName) {
        return dependencyRepository.findByUpstreamServiceAndActiveTrue(serviceName);
    }

    public ServiceDependency addDependency(ServiceDependency dependency) {

        boolean exists = dependencyRepository.existsByDownstreamServiceAndUpstreamService(
            dependency.getDownstreamService(),
            dependency.getUpstreamService());

        if (exists) {
            throw new IllegalArgumentException("Dependency already exists");
        }

        return dependencyRepository.save(dependency);
    }

    public void removeDependency(Long id) {
        dependencyRepository.deleteById(id);
    }

    public List<ServiceDependency> getAllDependencies() {
        return dependencyRepository.findByActiveTrue();
    }

    public static class PropagationResult {
        private String serviceName;
        private LocalDateTime analysisTime;
        private List<DependencyImpact> dependencyImpacts;
        private double combinedAvailabilityImpact;
        private double combinedLatencyImpact;
        private double combinedErrorRateImpact;
        private String overallRiskLevel;
        private List<String> recommendations;

        public String getServiceName() { return serviceName; }
        public void setServiceName(String serviceName) { this.serviceName = serviceName; }
        public LocalDateTime getAnalysisTime() { return analysisTime; }
        public void setAnalysisTime(LocalDateTime analysisTime) { this.analysisTime = analysisTime; }
        public List<DependencyImpact> getDependencyImpacts() { return dependencyImpacts; }
        public void setDependencyImpacts(List<DependencyImpact> dependencyImpacts) { this.dependencyImpacts = dependencyImpacts; }
        public double getCombinedAvailabilityImpact() { return combinedAvailabilityImpact; }
        public void setCombinedAvailabilityImpact(double combinedAvailabilityImpact) { this.combinedAvailabilityImpact = combinedAvailabilityImpact; }
        public double getCombinedLatencyImpact() { return combinedLatencyImpact; }
        public void setCombinedLatencyImpact(double combinedLatencyImpact) { this.combinedLatencyImpact = combinedLatencyImpact; }
        public double getCombinedErrorRateImpact() { return combinedErrorRateImpact; }
        public void setCombinedErrorRateImpact(double combinedErrorRateImpact) { this.combinedErrorRateImpact = combinedErrorRateImpact; }
        public String getOverallRiskLevel() { return overallRiskLevel; }
        public void setOverallRiskLevel(String overallRiskLevel) { this.overallRiskLevel = overallRiskLevel; }
        public List<String> getRecommendations() { return recommendations; }
        public void setRecommendations(List<String> recommendations) { this.recommendations = recommendations; }
    }

    public static class DependencyImpact {
        private String upstreamService;
        private ServiceDependency.DependencyType dependencyType;
        private ServiceDependency.ImpactLevel impactLevel;
        private double availabilityImpact;
        private double latencyImpact;
        private double errorRateImpact;
        private boolean criticalViolation;

        public String getUpstreamService() { return upstreamService; }
        public void setUpstreamService(String upstreamService) { this.upstreamService = upstreamService; }
        public ServiceDependency.DependencyType getDependencyType() { return dependencyType; }
        public void setDependencyType(ServiceDependency.DependencyType dependencyType) { this.dependencyType = dependencyType; }
        public ServiceDependency.ImpactLevel getImpactLevel() { return impactLevel; }
        public void setImpactLevel(ServiceDependency.ImpactLevel impactLevel) { this.impactLevel = impactLevel; }
        public double getAvailabilityImpact() { return availabilityImpact; }
        public void setAvailabilityImpact(double availabilityImpact) { this.availabilityImpact = availabilityImpact; }
        public double getLatencyImpact() { return latencyImpact; }
        public void setLatencyImpact(double latencyImpact) { this.latencyImpact = latencyImpact; }
        public double getErrorRateImpact() { return errorRateImpact; }
        public void setErrorRateImpact(double errorRateImpact) { this.errorRateImpact = errorRateImpact; }
        public boolean isCriticalViolation() { return criticalViolation; }
        public void setCriticalViolation(boolean criticalViolation) { this.criticalViolation = criticalViolation; }
    }
}
