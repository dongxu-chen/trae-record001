package com.oauth2.monitor.alert;

import com.oauth2.monitor.anomaly.BaselineLearningService;
import com.oauth2.monitor.anomaly.MetricsBaseline;
import com.oauth2.monitor.metrics.OAuth2Metrics;
import com.oauth2.monitor.tracing.TraceContext;
import io.micrometer.core.instrument.Counter;
import io.micrometer.core.instrument.MeterRegistry;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.ObjectProvider;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.scheduling.annotation.Scheduled;
import org.springframework.stereotype.Service;
import org.springframework.web.client.RestTemplate;

import java.time.Instant;
import java.util.*;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.atomic.AtomicInteger;
import java.util.concurrent.atomic.AtomicLong;

@Slf4j
@Service
public class AlertService {

    private final OAuth2Metrics metrics;
    private final MeterRegistry meterRegistry;
    private final BaselineLearningService baselineService;
    private final ObjectProvider<TraceContext> traceContextProvider;
    private final RestTemplate restTemplate;

    @Value("${oauth2.monitor.alert.enabled:true}")
    private boolean alertEnabled;

    @Value("${oauth2.monitor.alert.webhook-url:}")
    private String webhookUrl;

    private final Map<String, Counter> alertCounters = new ConcurrentHashMap<>();
    private final Map<String, SecurityEvent> activeAlerts = new ConcurrentHashMap<>();
    private final List<SecurityEvent> alertHistory = Collections.synchronizedList(new ArrayList<>());

    private final Map<String, AtomicInteger> ipFailureCounts = new ConcurrentHashMap<>();
    private final Map<String, AtomicLong> clientLastFailureTime = new ConcurrentHashMap<>();

    private static final int MAX_ALERT_HISTORY = 1000;
    private static final long BRUTE_FORCE_WINDOW_MS = 60000;
    private static final int BRUTE_FORCE_THRESHOLD = 5;

    private final Map<String, Long> lastAnomalyAlertTime = new ConcurrentHashMap<>();
    private static final long ANOMALY_ALERT_COOLDOWN_MS = 300000;

    public AlertService(OAuth2Metrics metrics, MeterRegistry meterRegistry,
                        BaselineLearningService baselineService,
                        ObjectProvider<TraceContext> traceContextProvider) {
        this.metrics = metrics;
        this.meterRegistry = meterRegistry;
        this.baselineService = baselineService;
        this.traceContextProvider = traceContextProvider;
        this.restTemplate = new RestTemplate();

        for (SecurityEvent.EventType eventType : SecurityEvent.EventType.values()) {
            alertCounters.put(eventType.name(),
                    Counter.builder("oauth2.alerts.total")
                            .description("Security alerts by type")
                            .tag("event_type", eventType.name())
                            .register(meterRegistry));
        }
    }

    public void recordSecurityEvent(SecurityEvent.EventType eventType,
                                    String description,
                                    Map<String, Object> details) {
        if (!alertEnabled) {
            return;
        }

        String traceId = getCurrentTraceId();
        String clientId = details != null ? (String) details.get("clientId") : null;
        String userId = details != null ? (String) details.get("userId") : null;
        String ipAddress = details != null ? (String) details.get("ipAddress") : null;
        String userAgent = details != null ? (String) details.get("userAgent") : null;

        SecurityEvent event = SecurityEvent.builder()
                .eventId(UUID.randomUUID().toString())
                .eventType(eventType)
                .severity(determineSeverity(eventType))
                .description(description)
                .traceId(traceId)
                .clientId(clientId)
                .userId(userId)
                .ipAddress(ipAddress)
                .userAgent(userAgent)
                .timestamp(Instant.now())
                .details(details)
                .build();

        processEvent(event);
    }

    private void processEvent(SecurityEvent event) {
        alertCounters.get(event.getEventType().name()).increment();
        logAlert(event);
        checkForBruteForce(event);
        addToHistory(event);

        feedBaseline(event);
    }

    private void feedBaseline(SecurityEvent event) {
        String metricKey = "event_rate_" + event.getEventType().name().toLowerCase();
        baselineService.recordSample(metricKey, 1.0);
    }

    private SecurityEvent.Severity determineSeverity(SecurityEvent.EventType eventType) {
        return switch (eventType) {
            case BRUTE_FORCE_ATTEMPT, SUSPICIOUS_ACTIVITY, CONCURRENT_SESSIONS ->
                    SecurityEvent.Severity.CRITICAL;
            case AUTHORIZATION_FAILURE, TOKEN_FAILURE, CLIENT_AUTHENTICATION_FAILURE,
                 INVALID_TOKEN, EXPIRED_TOKEN_USAGE, REVOKED_TOKEN_USAGE ->
                    SecurityEvent.Severity.HIGH;
            case RATE_LIMIT_EXCEEDED, UNUSUAL_LOCATION, INVALID_GRANT_TYPE ->
                    SecurityEvent.Severity.MEDIUM;
            default -> SecurityEvent.Severity.LOW;
        };
    }

    @Scheduled(fixedDelay = 60000)
    public void checkBaselineAnomalies() {
        if (!alertEnabled) {
            return;
        }

        Map<String, Double> currentMetrics = collectCurrentMetrics();

        List<BaselineLearningService.AnomalyResult> anomalies =
                baselineService.scanForAnomalies(currentMetrics);

        for (BaselineLearningService.AnomalyResult anomaly : anomalies) {
            if (anomaly.isSignificant()) {
                long now = System.currentTimeMillis();
                Long lastAlert = lastAnomalyAlertTime.get(anomaly.getMetricName());
                if (lastAlert == null || (now - lastAlert) > ANOMALY_ALERT_COOLDOWN_MS) {
                    triggerBaselineAnomalyAlert(anomaly);
                    lastAnomalyAlertTime.put(anomaly.getMetricName(), now);
                }
            }
        }

        recordBaselineMetrics(currentMetrics);
    }

    private Map<String, Double> collectCurrentMetrics() {
        Map<String, Double> current = new HashMap<>();

        current.put("token_failure_rate", 100.0 - metrics.getTokenSuccessRate());
        current.put("authorization_code_failure_rate", 100.0 - metrics.getAuthorizationCodeSuccessRate());
        current.put("refresh_token_failure_rate", 100.0 - metrics.getRefreshTokenSuccessRate());

        return current;
    }

    private void recordBaselineMetrics(Map<String, Double> currentMetrics) {
        currentMetrics.forEach(baselineService::recordSample);
    }

    private void triggerBaselineAnomalyAlert(BaselineLearningService.AnomalyResult anomaly) {
        MetricsBaseline baseline = anomaly.getBaseline();
        SecurityEvent.EventType eventType = mapMetricToEventType(anomaly.getMetricName());

        Map<String, Object> details = new HashMap<>();
        details.put("metricName", anomaly.getMetricName());
        details.put("currentValue", anomaly.getValue());
        details.put("baselineMean", baseline.getMean());
        details.put("baselineStdDev", baseline.getStandardDeviation());
        details.put("zScore", anomaly.getZScore());
        details.put("deviationPercentage", anomaly.getDeviationPercentage());
        details.put("anomalyLevel", anomaly.getAnomalyLevel().name());
        details.put("upperBound2Sigma", baseline.getUpperBound2Sigma());
        details.put("lowerBound2Sigma", baseline.getLowerBound2Sigma());
        details.put("upperBound3Sigma", baseline.getUpperBound3Sigma());
        details.put("lowerBound3Sigma", baseline.getLowerBound3Sigma());

        SecurityEvent event = SecurityEvent.builder()
                .eventId(UUID.randomUUID().toString())
                .eventType(eventType)
                .severity(mapAnomalyLevelToSeverity(anomaly.getAnomalyLevel()))
                .description(anomaly.getDescription())
                .traceId(getCurrentTraceId())
                .timestamp(Instant.now())
                .details(details)
                .build();

        String alertKey = "baseline:" + anomaly.getMetricName();
        activeAlerts.put(alertKey, event);

        log.error("BASELINE ANOMALY ALERT - {}: value={}, zScore={}, mean={}, sigma={}, {}",
                anomaly.getMetricName(),
                String.format("%.2f", anomaly.getValue()),
                String.format("%.2f", anomaly.getZScore()),
                String.format("%.2f", baseline.getMean()),
                String.format("%.2f", baseline.getStandardDeviation()),
                anomaly.getDescription());

        alertCounters.get(eventType.name()).increment();
        addToHistory(event);
        sendWebhookNotification(event);
    }

    private SecurityEvent.EventType mapMetricToEventType(String metricName) {
        if (metricName.contains("token_failure") || metricName.contains("token_request")) {
            return SecurityEvent.EventType.TOKEN_FAILURE;
        } else if (metricName.contains("authorization_code")) {
            return SecurityEvent.EventType.AUTHORIZATION_FAILURE;
        } else if (metricName.contains("invalid_token")) {
            return SecurityEvent.EventType.INVALID_TOKEN;
        } else if (metricName.contains("invalid_client")) {
            return SecurityEvent.EventType.CLIENT_AUTHENTICATION_FAILURE;
        }
        return SecurityEvent.EventType.SUSPICIOUS_ACTIVITY;
    }

    private SecurityEvent.Severity mapAnomalyLevelToSeverity(MetricsBaseline.AnomalyLevel level) {
        return switch (level) {
            case EXTREME -> SecurityEvent.Severity.CRITICAL;
            case CRITICAL -> SecurityEvent.Severity.HIGH;
            case WARNING -> SecurityEvent.Severity.MEDIUM;
            default -> SecurityEvent.Severity.LOW;
        };
    }

    private void checkForBruteForce(SecurityEvent event) {
        if (event.getIpAddress() != null) {
            long now = Instant.now().toEpochMilli();
            AtomicLong lastFailure = clientLastFailureTime
                    .computeIfAbsent(event.getIpAddress(), k -> new AtomicLong(now));

            if (now - lastFailure.get() < BRUTE_FORCE_WINDOW_MS) {
                int count = ipFailureCounts
                        .computeIfAbsent(event.getIpAddress(), k -> new AtomicInteger(0))
                        .incrementAndGet();

                MetricsBaseline ipBaseline = baselineService.getBaseline(
                        "ip_failure_rate_" + event.getIpAddress());

                if (ipBaseline.isInitialized() && ipBaseline.isSpike(count)) {
                    triggerBruteForceAlert(event, count, ipBaseline);
                } else if (count >= BRUTE_FORCE_THRESHOLD) {
                    triggerBruteForceAlert(event, count, null);
                }
            } else {
                ipFailureCounts.computeIfAbsent(event.getIpAddress(),
                        k -> new AtomicInteger(0)).set(1);
            }
            lastFailure.set(now);

            baselineService.recordSample(
                    "ip_failure_rate_" + event.getIpAddress(), count);
        }
    }

    private void triggerBruteForceAlert(SecurityEvent event, int count,
                                         MetricsBaseline baseline) {
        SecurityEvent bruteForceEvent = SecurityEvent.builder()
                .eventId(UUID.randomUUID().toString())
                .eventType(SecurityEvent.EventType.BRUTE_FORCE_ATTEMPT)
                .severity(SecurityEvent.Severity.CRITICAL)
                .description("Brute force attack detected from IP: " + event.getIpAddress() +
                        (baseline != null ?
                                String.format(" (count=%d, baseline_mean=%.1f)", count, baseline.getMean()) :
                                String.format(" (count=%d)", count)))
                .traceId(event.getTraceId())
                .ipAddress(event.getIpAddress())
                .timestamp(Instant.now())
                .details(Map.of("attemptCount", count,
                        "windowMs", BRUTE_FORCE_WINDOW_MS,
                        "baselineDetected", baseline != null))
                .build();

        String alertKey = "bruteforce:" + event.getIpAddress();
        activeAlerts.put(alertKey, bruteForceEvent);

        log.error("ALERT TRIGGERED - Type: {}, Severity: {}, IP: {}, Description: {}",
                bruteForceEvent.getEventType(), bruteForceEvent.getSeverity(),
                bruteForceEvent.getIpAddress(), bruteForceEvent.getDescription());

        sendWebhookNotification(bruteForceEvent);
        ipFailureCounts.get(event.getIpAddress()).set(0);
    }

    private void sendWebhookNotification(SecurityEvent event) {
        if (webhookUrl == null || webhookUrl.isEmpty()) {
            return;
        }
        try {
            Map<String, Object> payload = new HashMap<>();
            payload.put("eventId", event.getEventId());
            payload.put("eventType", event.getEventType().name());
            payload.put("severity", event.getSeverity().name());
            payload.put("description", event.getDescription());
            payload.put("traceId", event.getTraceId());
            payload.put("timestamp", event.getTimestamp().toString());
            payload.put("details", event.getDetails());
            restTemplate.postForObject(webhookUrl, payload, String.class);
        } catch (Exception e) {
            log.error("Failed to send alert webhook - eventId: {}, error: {}",
                    event.getEventId(), e.getMessage());
        }
    }

    private void logAlert(SecurityEvent event) {
        switch (event.getSeverity()) {
            case CRITICAL -> log.error("CRITICAL SECURITY EVENT - {}: {} - traceId: {}, IP: {}",
                    event.getEventType(), event.getDescription(),
                    event.getTraceId(), event.getIpAddress());
            case HIGH -> log.error("HIGH SECURITY EVENT - {}: {} - traceId: {}, IP: {}",
                    event.getEventType(), event.getDescription(),
                    event.getTraceId(), event.getIpAddress());
            case MEDIUM -> log.warn("MEDIUM SECURITY EVENT - {}: {} - traceId: {}, IP: {}",
                    event.getEventType(), event.getDescription(),
                    event.getTraceId(), event.getIpAddress());
            default -> log.info("LOW SECURITY EVENT - {}: {} - traceId: {}, IP: {}",
                    event.getEventType(), event.getDescription(),
                    event.getTraceId(), event.getIpAddress());
        }
    }

    private void addToHistory(SecurityEvent event) {
        synchronized (alertHistory) {
            if (alertHistory.size() >= MAX_ALERT_HISTORY) {
                alertHistory.remove(0);
            }
            alertHistory.add(event);
        }
    }

    public void acknowledgeAlert(String alertKey) {
        activeAlerts.remove(alertKey);
        log.info("Alert acknowledged - key: {}", alertKey);
    }

    public List<SecurityEvent> getActiveAlerts() {
        return new ArrayList<>(activeAlerts.values());
    }

    public List<SecurityEvent> getAlertHistory(int limit) {
        List<SecurityEvent> result = new ArrayList<>();
        synchronized (alertHistory) {
            int start = Math.max(0, alertHistory.size() - limit);
            result.addAll(alertHistory.subList(start, alertHistory.size()));
        }
        return result;
    }

    private String getCurrentTraceId() {
        try {
            TraceContext context = traceContextProvider.getIfAvailable();
            return context != null ? context.getTraceId() : "system-" + System.currentTimeMillis();
        } catch (Exception e) {
            return "system-" + System.currentTimeMillis();
        }
    }
}
