package com.sla.monitor.service;

import com.sla.monitor.engine.CalendarWindowMetrics;
import com.sla.monitor.model.Alert;
import com.sla.monitor.model.ServiceInfo;
import com.sla.monitor.model.SlaTier;
import com.sla.monitor.repository.AlertRepository;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.stereotype.Service;

import java.time.LocalDateTime;
import java.util.List;

@Service
public class AlertService {

    private static final Logger logger = LoggerFactory.getLogger(AlertService.class);

    private final AlertRepository alertRepository;
    private final TimeSeriesPredictionService predictionService;

    public AlertService(AlertRepository alertRepository, TimeSeriesPredictionService predictionService) {
        this.alertRepository = alertRepository;
        this.predictionService = predictionService;
    }

    public void checkAndCreateAlerts(ServiceInfo service, CalendarWindowMetrics.WindowMetrics metrics) {
        String serviceName = service.getServiceName();

        double availTarget = service.getEffectiveAvailabilityTarget();
        double latencyTarget = service.getEffectiveLatencyTarget();
        double errorTarget = service.getEffectiveErrorRateTarget();

        if (metrics.getAvailability() < availTarget) {
            createAlert(service, Alert.AlertType.AVAILABILITY_VIOLATION,
                    metrics.getAvailability(), availTarget,
                    "Availability below " + getTierLabel(service) + " target");
        }

        if (metrics.getAvgLatencyMs() > latencyTarget) {
            createAlert(service, Alert.AlertType.LATENCY_VIOLATION,
                    metrics.getAvgLatencyMs(), latencyTarget,
                    "Latency exceeds " + getTierLabel(service) + " target");
        }

        if (metrics.getErrorRate() > errorTarget) {
            createAlert(service, Alert.AlertType.ERROR_RATE_VIOLATION,
                    metrics.getErrorRate(), errorTarget,
                    "Error rate exceeds " + getTierLabel(service) + " target");
        }

        checkPredictedViolations(service);
    }

    private String getTierLabel(ServiceInfo service) {
        if (service.getSlaTier() != null) {
            return service.getSlaTier().getTierName();
        }
        return "default";
    }

    private void checkPredictedViolations(ServiceInfo service) {
        double trendSlope = predictionService.calculateTrendSlope(service.getServiceName());
        
        if (trendSlope < -0.1) {
            LocalDateTime futureTime = LocalDateTime.now().plusHours(2);
            double predictedAvailability = predictionService.predictAvailability(
                    service.getServiceName(), futureTime);
            
            double target = service.getEffectiveAvailabilityTarget();
            if (predictedAvailability < target) {
                createAlert(service, Alert.AlertType.SLA_PREDICTED_VIOLATION,
                        predictedAvailability, target,
                        "Predicted SLA violation within 2 hours for " + getTierLabel(service));
            }
        }
    }

    private void createAlert(ServiceInfo service, Alert.AlertType alertType,
                             double currentValue, double thresholdValue, String message) {
        String serviceName = service.getServiceName();
        List<Alert> existingAlerts = alertRepository.findByServiceNameAndResolvedFalseOrderByCreatedAtDesc(serviceName);
        
        boolean alertExists = existingAlerts.stream()
                .anyMatch(a -> a.getAlertType() == alertType);

        if (alertExists) {
            return;
        }

        Alert alert = new Alert();
        alert.setServiceName(serviceName);
        alert.setAlertType(alertType);
        alert.setSeverity(determineSeverity(alertType, currentValue, thresholdValue, service));
        alert.setMessage(message);
        alert.setCurrentValue(currentValue);
        alert.setThresholdValue(thresholdValue);
        alert.setAcknowledged(false);
        alert.setResolved(false);

        alertRepository.save(alert);
        logger.warn("Created alert: {} for service {} - {} vs {}", 
                alertType, serviceName, currentValue, thresholdValue);
    }

    private Alert.AlertSeverity determineSeverity(Alert.AlertType alertType,
                                                   double currentValue, double thresholdValue,
                                                   ServiceInfo service) {
        double deviationPercent = 0;
        
        switch (alertType) {
            case AVAILABILITY_VIOLATION:
                deviationPercent = ((thresholdValue - currentValue) / thresholdValue) * 100;
                break;
            case LATENCY_VIOLATION:
            case ERROR_RATE_VIOLATION:
                deviationPercent = ((currentValue - thresholdValue) / thresholdValue) * 100;
                break;
            case SLA_PREDICTED_VIOLATION:
                return getSeverityByTier(service, Alert.AlertSeverity.MEDIUM);
        }

        Alert.AlertSeverity baseSeverity;
        if (deviationPercent > 20) {
            baseSeverity = Alert.AlertSeverity.CRITICAL;
        } else if (deviationPercent > 10) {
            baseSeverity = Alert.AlertSeverity.HIGH;
        } else if (deviationPercent > 5) {
            baseSeverity = Alert.AlertSeverity.MEDIUM;
        } else {
            baseSeverity = Alert.AlertSeverity.LOW;
        }

        return getSeverityByTier(service, baseSeverity);
    }

    private Alert.AlertSeverity getSeverityByTier(ServiceInfo service, Alert.AlertSeverity baseSeverity) {
        if (service == null || service.getSlaTier() == null) {
            return baseSeverity;
        }

        Integer priorityLevel = service.getSlaTier().getPriorityLevel();
        if (priorityLevel == null) {
            return baseSeverity;
        }

        if (priorityLevel <= 2) {
            return upgradeSeverity(baseSeverity, 1);
        } else if (priorityLevel >= 5) {
            return downgradeSeverity(baseSeverity, 1);
        }

        return baseSeverity;
    }

    private Alert.AlertSeverity upgradeSeverity(Alert.AlertSeverity severity, int levels) {
        Alert.AlertSeverity[] values = Alert.AlertSeverity.values();
        int currentIndex = severity.ordinal();
        int newIndex = Math.min(values.length - 1, currentIndex + levels);
        return values[newIndex];
    }

    private Alert.AlertSeverity downgradeSeverity(Alert.AlertSeverity severity, int levels) {
        Alert.AlertSeverity[] values = Alert.AlertSeverity.values();
        int currentIndex = severity.ordinal();
        int newIndex = Math.max(0, currentIndex - levels);
        return values[newIndex];
    }

    public List<Alert> getActiveAlerts() {
        return alertRepository.findByResolvedFalseOrderByCreatedAtDesc();
    }

    public List<Alert> getAlertsForService(String serviceName) {
        return alertRepository.findByServiceNameOrderByCreatedAtDesc(serviceName);
    }

    public Alert acknowledgeAlert(Long alertId) {
        return alertRepository.findById(alertId).map(alert -> {
            alert.setAcknowledged(true);
            return alertRepository.save(alert);
        }).orElse(null);
    }

    public Alert resolveAlert(Long alertId) {
        return alertRepository.findById(alertId).map(alert -> {
            alert.setResolved(true);
            alert.setResolvedAt(LocalDateTime.now());
            return alertRepository.save(alert);
        }).orElse(null);
    }

    public List<Alert> getRecentAlerts(int hours) {
        return alertRepository.findByCreatedAtAfterOrderByCreatedAtDesc(
                LocalDateTime.now().minusHours(hours));
    }
}
