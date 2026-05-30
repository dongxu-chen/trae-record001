package com.sla.monitor.service;

import com.sla.monitor.engine.CalendarWindowMetrics;
import com.sla.monitor.model.*;
import com.sla.monitor.repository.ServiceInfoRepository;
import com.sla.monitor.repository.SlaCompensationRepository;
import com.sla.monitor.repository.SlaMetricsRepository;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.scheduling.annotation.Scheduled;
import org.springframework.stereotype.Service;

import java.time.LocalDateTime;
import java.util.ArrayList;
import java.util.List;

@Service
public class SlaCompensationService {

    private static final Logger logger = LoggerFactory.getLogger(SlaCompensationService.class);

    private final SlaCompensationRepository compensationRepository;
    private final ServiceInfoRepository serviceInfoRepository;
    private final SlaMetricsRepository slaMetricsRepository;
    private final CalendarWindowMetrics calendarWindowMetrics;

    public SlaCompensationService(SlaCompensationRepository compensationRepository,
                                   ServiceInfoRepository serviceInfoRepository,
                                   SlaMetricsRepository slaMetricsRepository,
                                   CalendarWindowMetrics calendarWindowMetrics) {
        this.compensationRepository = compensationRepository;
        this.serviceInfoRepository = serviceInfoRepository;
        this.slaMetricsRepository = slaMetricsRepository;
        this.calendarWindowMetrics = calendarWindowMetrics;
    }

    @Scheduled(cron = "0 0 * * * ?")
    public void hourlyCompensationCheck() {
        List<ServiceInfo> activeServices = serviceInfoRepository.findByActiveTrue();
        for (ServiceInfo service : activeServices) {
            checkAndGenerateCompensation(service);
        }
    }

    public SlaCompensation checkAndGenerateCompensation(ServiceInfo service) {
        String serviceName = service.getServiceName();
        CalendarWindowMetrics.WindowMetrics dailyMetrics = 
            calendarWindowMetrics.getWindowMetrics(serviceName, CalendarWindowMetrics.WindowType.CALENDAR_DAY);

        double availabilityTarget = service.getEffectiveAvailabilityTarget();
        double actualAvailability = dailyMetrics.getAvailability();

        if (actualAvailability >= availabilityTarget) {
            return null;
        }

        double availabilityDeficit = availabilityTarget - actualAvailability;
        double downtimeMinutes = (availabilityDeficit / 100) * 1440;

        SlaCompensation.ViolationSeverity severity = determineSeverity(availabilityDeficit);
        SlaCompensation.CompensationType compensationType = determineCompensationType(service, severity);

        SlaCompensation compensation = new SlaCompensation();
        compensation.setServiceName(serviceName);
        compensation.setSlaTier(service.getSlaTier());
        compensation.setViolationSeverity(severity);
        compensation.setCompensationType(compensationType);
        compensation.setDowntimeMinutes(downtimeMinutes);
        compensation.setAvailabilityDeficit(availabilityDeficit);
        compensation.setCreditPercent(calculateCreditPercent(service, severity, downtimeMinutes));
        compensation.setCompensationDetails(generateCompensationDetails(service, severity, downtimeMinutes));
        compensation.setRecommendedActions(generateRecommendedActions(service, severity));

        return compensationRepository.save(compensation);
    }

    private SlaCompensation.ViolationSeverity determineSeverity(double availabilityDeficit) {
        if (availabilityDeficit >= 5.0) return SlaCompensation.ViolationSeverity.CRITICAL;
        if (availabilityDeficit >= 2.0) return SlaCompensation.ViolationSeverity.SEVERE;
        if (availabilityDeficit >= 0.5) return SlaCompensation.ViolationSeverity.MODERATE;
        return SlaCompensation.ViolationSeverity.MINOR;
    }

    private SlaCompensation.CompensationType determineCompensationType(ServiceInfo service, 
                                                                        SlaCompensation.ViolationSeverity severity) {
        if (service.getSlaTier() == null) {
            return SlaCompensation.CompensationType.SERVICE_CREDIT;
        }

        Integer priority = service.getSlaTier().getPriorityLevel();

        switch (severity) {
            case CRITICAL:
                return priority <= 2 ? SlaCompensation.CompensationType.REFUND : SlaCompensation.CompensationType.SERVICE_CREDIT;
            case SEVERE:
                return priority <= 2 ? SlaCompensation.CompensationType.UPGRADE_TIER : SlaCompensation.CompensationType.EXTENDED_SUPPORT;
            case MODERATE:
                return SlaCompensation.CompensationType.SERVICE_CREDIT;
            default:
                return SlaCompensation.CompensationType.EXTENDED_SUPPORT;
        }
    }

    private double calculateCreditPercent(ServiceInfo service, SlaCompensation.ViolationSeverity severity, double downtimeMinutes) {
        double basePercent = service.getSlaTier() != null ? 
            service.getSlaTier().getUptimeCreditPercent() : 10.0;

        double severityMultiplier;
        switch (severity) {
            case CRITICAL: severityMultiplier = 3.0; break;
            case SEVERE: severityMultiplier = 2.0; break;
            case MODERATE: severityMultiplier = 1.5; break;
            default: severityMultiplier = 1.0;
        }

        return Math.min(100.0, basePercent * severityMultiplier * Math.min(downtimeMinutes / 60, 24));
    }

    private String generateCompensationDetails(ServiceInfo service, SlaCompensation.ViolationSeverity severity, double downtimeMinutes) {
        StringBuilder details = new StringBuilder();
        details.append(String.format("服务 %s 发生SLA违规\n", service.getServiceName()));
        details.append(String.format("严重程度: %s\n", severity));
        details.append(String.format("预计宕机时间: %.2f分钟\n", downtimeMinutes));
        
        if (service.getSlaTier() != null) {
            details.append(String.format("SLA等级: %s\n", service.getSlaTier().getTierName()));
            details.append(String.format("标准赔偿比例: %.1f%%\n", service.getSlaTier().getUptimeCreditPercent()));
        }

        return details.toString();
    }

    private String generateRecommendedActions(ServiceInfo service, SlaCompensation.ViolationSeverity severity) {
        List<String> actions = new ArrayList<>();
        
        actions.add("立即通知客户服务团队");
        
        if (severity == SlaCompensation.ViolationSeverity.CRITICAL || severity == SlaCompensation.ViolationSeverity.SEVERE) {
            actions.add("启动紧急事故响应流程");
            actions.add("安排高级工程师进行根因分析");
            actions.add("考虑临时资源扩容");
        }
        
        if (service.getSlaTier() != null && service.getSlaTier().getPriorityLevel() <= 2) {
            actions.add("安排专属客户经理跟进");
            actions.add("提供7x24小时技术支持");
        }
        
        actions.add("更新服务状态页面");
        actions.add("准备事后分析报告");
        
        return String.join(" | ", actions);
    }

    public List<SlaCompensation> getCompensationsForService(String serviceName) {
        return compensationRepository.findByServiceNameOrderByCreatedAtDesc(serviceName);
    }

    public List<SlaCompensation> getPendingCompensations() {
        return compensationRepository.findByApprovedFalseOrderByCreatedAtDesc();
    }

    public List<SlaCompensation> getRecentCompensations(int days) {
        LocalDateTime startTime = LocalDateTime.now().minusDays(days);
        return compensationRepository.findByCreatedAtAfterOrderByCreatedAtDesc(startTime);
    }

    public SlaCompensation approveCompensation(Long id, String approvedBy) {
        return compensationRepository.findById(id).map(compensation -> {
            compensation.setApproved(true);
            compensation.setApprovedAt(LocalDateTime.now());
            compensation.setApprovedBy(approvedBy);
            return compensationRepository.save(compensation);
        }).orElse(null);
    }

    public SlaCompensation resolveCompensation(Long id) {
        return compensationRepository.findById(id).map(compensation -> {
            compensation.setResolvedAt(LocalDateTime.now());
            return compensationRepository.save(compensation);
        }).orElse(null);
    }

    public SlaCompensation generateManualCompensation(String serviceName, 
                                                       SlaCompensation.ViolationSeverity severity,
                                                       String reason) {
        return serviceInfoRepository.findByServiceName(serviceName).map(service -> {
            SlaCompensation compensation = new SlaCompensation();
            compensation.setServiceName(serviceName);
            compensation.setSlaTier(service.getSlaTier());
            compensation.setViolationSeverity(severity);
            compensation.setCompensationType(SlaCompensation.CompensationType.CUSTOM);
            compensation.setDowntimeMinutes(0.0);
            compensation.setAvailabilityDeficit(0.0);
            compensation.setCompensationDetails("手动生成补偿: " + reason);
            compensation.setRecommendedActions("手动审核后执行");
            return compensationRepository.save(compensation);
        }).orElse(null);
    }

    public SlaCompensationRepository getCompensationRepository() {
        return compensationRepository;
    }
}
