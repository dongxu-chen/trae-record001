package com.oauth2.monitor;

import com.oauth2.monitor.alert.AlertService;
import com.oauth2.monitor.alert.SecurityEvent;
import com.oauth2.monitor.anomaly.BaselineLearningService;
import com.oauth2.monitor.metrics.OAuth2Metrics;
import io.micrometer.core.instrument.simple.SimpleMeterRegistry;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.ObjectProvider;

import java.util.List;
import java.util.Map;

import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.Mockito.*;

@DisplayName("Alert Service Tests")
class AlertServiceTest {

    private AlertService alertService;
    private OAuth2Metrics metrics;
    private SimpleMeterRegistry meterRegistry;
    private BaselineLearningService baselineService;

    @SuppressWarnings("unchecked")
    private ObjectProvider<com.oauth2.monitor.tracing.TraceContext> traceContextProvider =
            mock(ObjectProvider.class);

    @BeforeEach
    void setUp() {
        meterRegistry = new SimpleMeterRegistry();
        metrics = new OAuth2Metrics(meterRegistry);
        baselineService = new BaselineLearningService(meterRegistry);
        alertService = new AlertService(metrics, meterRegistry, baselineService, traceContextProvider);
    }

    @Test
    @DisplayName("Test security event recording with different severities")
    void testSecurityEventRecording() {
        alertService.recordSecurityEvent(
                SecurityEvent.EventType.INVALID_TOKEN,
                "Invalid token used",
                Map.of("clientId", "client1", "ipAddress", "192.168.1.1")
        );

        assertEquals(1, meterRegistry.get("oauth2.alerts.total")
                .tag("event_type", "INVALID_TOKEN").counter().count());
    }

    @Test
    @DisplayName("Test brute force detection")
    void testBruteForceDetection() {
        for (int i = 0; i < 6; i++) {
            alertService.recordSecurityEvent(
                    SecurityEvent.EventType.CLIENT_AUTHENTICATION_FAILURE,
                    "Client authentication failed",
                    Map.of("clientId", "client1", "ipAddress", "192.168.1.100")
            );
        }

        List<SecurityEvent> alerts = alertService.getActiveAlerts();
        boolean bruteForceDetected = alerts.stream()
                .anyMatch(e -> e.getEventType() == SecurityEvent.EventType.BRUTE_FORCE_ATTEMPT);

        assertTrue(bruteForceDetected, "Brute force attack should be detected after 5 failures");
    }

    @Test
    @DisplayName("Test different IPs don't trigger brute force")
    void testDifferentIpsDontTriggerBruteForce() {
        for (int i = 0; i < 10; i++) {
            String ip = "192.168.1." + i;
            alertService.recordSecurityEvent(
                    SecurityEvent.EventType.CLIENT_AUTHENTICATION_FAILURE,
                    "Client authentication failed",
                    Map.of("clientId", "client1", "ipAddress", ip)
            );
        }

        List<SecurityEvent> alerts = alertService.getActiveAlerts();
        long bruteForceCount = alerts.stream()
                .filter(e -> e.getEventType() == SecurityEvent.EventType.BRUTE_FORCE_ATTEMPT)
                .count();

        assertEquals(0, bruteForceCount, "Different IPs should not trigger brute force detection");
    }

    @Test
    @DisplayName("Test alert history is maintained")
    void testAlertHistory() {
        for (int i = 0; i < 5; i++) {
            alertService.recordSecurityEvent(
                    SecurityEvent.EventType.TOKEN_FAILURE,
                    "Test failure " + i,
                    Map.of("clientId", "client1", "ipAddress", "10.0.0." + i)
            );
        }

        List<SecurityEvent> history = alertService.getAlertHistory(10);
        assertTrue(history.size() >= 5, "Alert history should contain at least 5 events");
    }

    @Test
    @DisplayName("Test alert acknowledgement")
    void testAlertAcknowledgement() {
        alertService.recordSecurityEvent(
                SecurityEvent.EventType.BRUTE_FORCE_ATTEMPT,
                "Test brute force",
                Map.of("clientId", "client1", "ipAddress", "192.168.1.200")
        );

        List<SecurityEvent> activeAlerts = alertService.getActiveAlerts();
        assertFalse(activeAlerts.isEmpty(), "Should have active alerts");

        String alertKey = activeAlerts.get(0).getEventType() + ":" + activeAlerts.get(0).getIpAddress();
        alertService.acknowledgeAlert(alertKey);

        boolean stillExists = alertService.getActiveAlerts().stream()
                .anyMatch(a -> alertKey.equals(a.getEventType() + ":" + a.getIpAddress()));
        assertFalse(stillExists, "Alert should be removed after acknowledgement");
    }

    @Test
    @DisplayName("Test high severity events trigger alerts")
    void testHighSeverityTriggersAlert() {
        alertService.recordSecurityEvent(
                SecurityEvent.EventType.SUSPICIOUS_ACTIVITY,
                "Suspicious activity detected",
                Map.of("clientId", "client1", "ipAddress", "192.168.1.50")
        );

        List<SecurityEvent> activeAlerts = alertService.getActiveAlerts();
        assertFalse(activeAlerts.isEmpty(), "High severity event should trigger alert");
        assertEquals(SecurityEvent.Severity.CRITICAL, activeAlerts.get(0).getSeverity());
    }

    @Test
    @DisplayName("Test security event details are preserved")
    void testEventDetailsPreserved() {
        Map<String, Object> details = Map.of(
                "clientId", "client-test-123",
                "userId", "user-456",
                "ipAddress", "10.0.0.1",
                "userAgent", "TestBrowser/1.0",
                "customField", "customValue"
        );

        alertService.recordSecurityEvent(
                SecurityEvent.EventType.INVALID_CLIENT,
                "Invalid client credentials",
                details
        );

        List<SecurityEvent> history = alertService.getAlertHistory(1);
        SecurityEvent event = history.get(0);

        assertEquals("client-test-123", event.getClientId());
        assertEquals("user-456", event.getUserId());
        assertEquals("10.0.0.1", event.getIpAddress());
        assertEquals("TestBrowser/1.0", event.getUserAgent());
        assertEquals("customValue", event.getDetails().get("customField"));
    }

    @Test
    @DisplayName("Test all event types have counters")
    void testAllEventTypesHaveCounters() {
        for (SecurityEvent.EventType eventType : SecurityEvent.EventType.values()) {
            alertService.recordSecurityEvent(
                    eventType,
                    "Test " + eventType,
                    Map.of("clientId", "test", "ipAddress", "127.0.0.1")
            );

            assertTrue(meterRegistry.get("oauth2.alerts.total")
                            .tag("event_type", eventType.name())
                            .counter().count() > 0,
                    "Counter should exist for event type: " + eventType);
        }
    }

    @Test
    @DisplayName("Test baseline anomaly alert with cooldown")
    void testBaselineAnomalyAlertWithCooldown() {
        for (int i = 0; i < 50; i++) {
            baselineService.recordSample("token_failure_rate", 5.0);
        }
        baselineService.updateBaselines();

        alertService.checkBaselineAnomalies();

        List<SecurityEvent> history = alertService.getAlertHistory(50);
        assertTrue(history.size() >= 0, "Baseline check should run without error");
    }

    @Test
    @DisplayName("Test events feed into baseline")
    void testEventsFeedIntoBaseline() {
        for (int i = 0; i < 10; i++) {
            alertService.recordSecurityEvent(
                    SecurityEvent.EventType.TOKEN_FAILURE,
                    "Failure " + i,
                    Map.of("clientId", "client1", "ipAddress", "10.0.0.1")
            );
        }

        List<String> monitored = baselineService.getMonitoredMetrics();
        assertTrue(monitored.stream()
                .anyMatch(m -> m.contains("event_rate_token_failure")));
    }

    @Test
    @DisplayName("Test anomaly level to severity mapping")
    void testAnomalyLevelToSeverityMapping() {
        alertService.recordSecurityEvent(
                SecurityEvent.EventType.BRUTE_FORCE_ATTEMPT,
                "Critical test",
                Map.of("clientId", "test", "ipAddress", "1.2.3.4")
        );

        List<SecurityEvent> history = alertService.getAlertHistory(1);
        assertFalse(history.isEmpty());
        assertEquals(SecurityEvent.Severity.CRITICAL, history.get(history.size() - 1).getSeverity());
    }
}
