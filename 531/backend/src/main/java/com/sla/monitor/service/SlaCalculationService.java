package com.sla.monitor.service;

import com.sla.monitor.engine.CalendarWindowMetrics;
import com.sla.monitor.engine.CalendarWindowMetrics.WindowMetrics;
import com.sla.monitor.engine.CalendarWindowMetrics.WindowType;
import com.sla.monitor.model.ServiceInfo;
import com.sla.monitor.model.SlaMetrics;
import com.sla.monitor.repository.ServiceInfoRepository;
import com.sla.monitor.repository.SlaMetricsRepository;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.scheduling.annotation.Scheduled;
import org.springframework.stereotype.Service;

import java.time.LocalDateTime;
import java.util.*;

@Service
public class SlaCalculationService {

    private static final Logger logger = LoggerFactory.getLogger(SlaCalculationService.class);

    private final CalendarWindowMetrics calendarWindowMetrics;
    private final ServiceInfoRepository serviceInfoRepository;
    private final SlaMetricsRepository slaMetricsRepository;
    private final AlertService alertService;

    @Value("${sla.sliding-window.size-minutes:60}")
    private int windowSizeMinutes;

    @Value("${sla.data-retention-days:30}")
    private int dataRetentionDays;

    public SlaCalculationService(CalendarWindowMetrics calendarWindowMetrics,
                                  ServiceInfoRepository serviceInfoRepository,
                                  SlaMetricsRepository slaMetricsRepository,
                                  AlertService alertService) {
        this.calendarWindowMetrics = calendarWindowMetrics;
        this.serviceInfoRepository = serviceInfoRepository;
        this.slaMetricsRepository = slaMetricsRepository;
        this.alertService = alertService;
    }

    @Scheduled(fixedDelayString = "${sla.sliding-window.update-interval-seconds:10}000")
    public void calculateAndStoreMetrics() {
        calendarWindowMetrics.cleanupOldData(dataRetentionDays);

        List<ServiceInfo> activeServices = serviceInfoRepository.findByActiveTrue();
        for (ServiceInfo service : activeServices) {
            calculateServiceMetrics(service, WindowType.SLIDING_HOUR);
        }
    }

    @Scheduled(cron = "0 0 * * * ?")
    public void calculateCalendarHourlyMetrics() {
        List<ServiceInfo> activeServices = serviceInfoRepository.findByActiveTrue();
        for (ServiceInfo service : activeServices) {
            calculateServiceMetrics(service, WindowType.CALENDAR_DAY);
        }
    }

    @Scheduled(cron = "0 0 0 * * ?")
    public void calculateCalendarDailyMetrics() {
        List<ServiceInfo> activeServices = serviceInfoRepository.findByActiveTrue();
        for (ServiceInfo service : activeServices) {
            calculateServiceMetrics(service, WindowType.CALENDAR_WEEK);
            calculateServiceMetrics(service, WindowType.CALENDAR_MONTH);
        }
    }

    public void calculateServiceMetrics(ServiceInfo service, WindowType windowType) {
        String serviceName = service.getServiceName();
        WindowMetrics windowMetrics = calendarWindowMetrics.getWindowMetrics(serviceName, windowType);

        SlaMetrics slaMetrics = new SlaMetrics();
        slaMetrics.setServiceName(serviceName);
        slaMetrics.setTimestamp(LocalDateTime.now());
        slaMetrics.setTotalRequests(windowMetrics.getTotalRequests());
        slaMetrics.setSuccessfulRequests(windowMetrics.getSuccessfulRequests());
        slaMetrics.setFailedRequests(windowMetrics.getFailedRequests());
        slaMetrics.setAvailability(windowMetrics.getAvailability());
        slaMetrics.setAvgLatencyMs(windowMetrics.getAvgLatencyMs());
        slaMetrics.setP95LatencyMs(windowMetrics.getP95LatencyMs());
        slaMetrics.setP99LatencyMs(windowMetrics.getP99LatencyMs());
        slaMetrics.setErrorRate(windowMetrics.getErrorRate());
        slaMetrics.setWindowType(windowType.name());

        double achievementRate = calculateSlaAchievementRate(windowMetrics, service);
        slaMetrics.setSlaAchievementRate(achievementRate);

        boolean violated = isSlaViolated(windowMetrics, service);
        slaMetrics.setSlaViolated(violated);

        slaMetricsRepository.save(slaMetrics);

        if (violated && windowType == WindowType.SLIDING_HOUR) {
            alertService.checkAndCreateAlerts(service, windowMetrics);
        }

        logger.debug("Calculated SLA metrics for {} [{}]: availability={}, achievementRate={}",
                serviceName, windowType, windowMetrics.getAvailability(), achievementRate);
    }

    public Map<WindowType, WindowMetrics> getAllWindowMetrics(String serviceName) {
        return calendarWindowMetrics.getAllWindowMetrics(serviceName);
    }

    public WindowMetrics getWindowMetrics(String serviceName, WindowType windowType) {
        return calendarWindowMetrics.getWindowMetrics(serviceName, windowType);
    }

    public double calculateSlaAchievementRate(WindowMetrics metrics, ServiceInfo service) {
        double availabilityScore = calculateAvailabilityScore(
                metrics.getAvailability(), service.getEffectiveAvailabilityTarget());
        double latencyScore = calculateLatencyScore(
                metrics.getAvgLatencyMs(), service.getEffectiveLatencyTarget());
        double errorRateScore = calculateErrorRateScore(
                metrics.getErrorRate(), service.getEffectiveErrorRateTarget());

        return (availabilityScore * 0.5) + (latencyScore * 0.3) + (errorRateScore * 0.2);
    }

    private double calculateAvailabilityScore(double availability, double target) {
        if (availability >= target) return 100.0;
        double deficit = target - availability;
        return Math.max(0, 100 - (deficit * 50));
    }

    private double calculateLatencyScore(double latency, double target) {
        if (latency <= target) return 100.0;
        double ratio = latency / target;
        return Math.max(0, 100 - ((ratio - 1) * 50));
    }

    private double calculateErrorRateScore(double errorRate, double target) {
        if (errorRate <= target) return 100.0;
        double deficit = errorRate - target;
        return Math.max(0, 100 - (deficit * 20));
    }

    public boolean isSlaViolated(WindowMetrics metrics, ServiceInfo service) {
        return metrics.getAvailability() < service.getEffectiveAvailabilityTarget() ||
               metrics.getAvgLatencyMs() > service.getEffectiveLatencyTarget() ||
               metrics.getErrorRate() > service.getEffectiveErrorRateTarget();
    }

    public SlaMetrics getLatestMetrics(String serviceName) {
        return slaMetricsRepository.findFirstByServiceNameOrderByTimestampDesc(serviceName);
    }

    public List<SlaMetrics> getMetricsHistory(String serviceName, int hours) {
        LocalDateTime startTime = LocalDateTime.now().minusHours(hours);
        return slaMetricsRepository.findByServiceNameAndTimestampAfterOrderByTimestampAsc(serviceName, startTime);
    }

    public List<SlaMetrics> getMetricsHistoryByWindowType(String serviceName, WindowType windowType, int hours) {
        LocalDateTime startTime = LocalDateTime.now().minusHours(hours);
        return slaMetricsRepository.findByServiceNameAndWindowTypeAndTimestampAfterOrderByTimestampAsc(
                serviceName, windowType.name(), startTime);
    }

    public List<SlaMetrics> compareServices(List<String> serviceNames, int hours) {
        List<SlaMetrics> latestMetrics = new ArrayList<>();
        for (String serviceName : serviceNames) {
            SlaMetrics latest = slaMetricsRepository.findFirstByServiceNameOrderByTimestampDesc(serviceName);
            if (latest != null) {
                latestMetrics.add(latest);
            }
        }
        return latestMetrics;
    }

    public double calculateDailyAvailability(String serviceName) {
        return calculateAvailabilityForWindow(serviceName, WindowType.CALENDAR_DAY);
    }

    public double calculateWeeklyAvailability(String serviceName) {
        return calculateAvailabilityForWindow(serviceName, WindowType.CALENDAR_WEEK);
    }

    public double calculateMonthlyAvailability(String serviceName) {
        return calculateAvailabilityForWindow(serviceName, WindowType.CALENDAR_MONTH);
    }

    private double calculateAvailabilityForWindow(String serviceName, WindowType windowType) {
        WindowMetrics metrics = calendarWindowMetrics.getWindowMetrics(serviceName, windowType);
        return metrics.getAvailability();
    }

    public CalendarWindowMetrics.WindowBounds getWindowBounds(WindowType windowType) {
        return calendarWindowMetrics.getCurrentWindowBounds(windowType);
    }
}
