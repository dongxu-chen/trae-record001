package com.sessionguard.service;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.datatype.jsr310.JavaTimeModule;
import com.sessionguard.model.RiskAssessment;
import com.sessionguard.model.SessionProfile;
import com.sessionguard.model.WebhookPayload;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.http.*;
import org.springframework.stereotype.Service;
import org.springframework.web.client.RestTemplate;

import java.util.List;
import java.util.UUID;

@Slf4j
@Service
public class WebhookNotificationService {

    private final RestTemplate restTemplate;
    private final ObjectMapper objectMapper;
    private final List<String> webhookUrls;
    private final int retryCount;
    private final long retryDelayMs;
    private final int timeoutMs;
    private final boolean enabled;

    public WebhookNotificationService(
            @Value("${session-guard.webhook.urls:}") List<String> webhookUrls,
            @Value("${session-guard.webhook.retry-count:3}") int retryCount,
            @Value("${session-guard.webhook.retry-delay-ms:1000}") long retryDelayMs,
            @Value("${session-guard.webhook.timeout-ms:5000}") int timeoutMs,
            @Value("${session-guard.webhook.enabled:true}") boolean enabled) {
        this.restTemplate = new RestTemplate();
        this.objectMapper = new ObjectMapper();
        this.objectMapper.registerModule(new JavaTimeModule());
        this.webhookUrls = webhookUrls;
        this.retryCount = retryCount;
        this.retryDelayMs = retryDelayMs;
        this.timeoutMs = timeoutMs;
        this.enabled = enabled;
    }

    public void sendAlert(WebhookPayload payload) {
        if (!enabled || webhookUrls == null || webhookUrls.isEmpty()) {
            log.debug("Webhook notifications disabled or no URLs configured");
            return;
        }

        for (String url : webhookUrls) {
            sendWithRetry(url, payload);
        }
    }

    public void sendSessionInvalidationAlert(SessionProfile profile, String reason) {
        WebhookPayload payload = WebhookPayload.builder()
                .alertId(UUID.randomUUID().toString())
                .sessionId(profile.getSessionId())
                .userId(profile.getUserId())
                .riskLevel(RiskAssessment.RiskLevel.CRITICAL)
                .riskScore(100)
                .alertType("SESSION_INVALIDATED")
                .message("Session forcibly invalidated for user " + profile.getUserId() + ": " + reason)
                .details(java.util.Map.of("reason", reason, "ipAddress",
                        profile.getIpContext() != null ? profile.getIpContext().getIpAddress() : "unknown"))
                .timestamp(java.time.LocalDateTime.now())
                .build();

        sendAlert(payload);
    }

    private void sendWithRetry(String url, WebhookPayload payload) {
        for (int attempt = 1; attempt <= retryCount; attempt++) {
            try {
                String json = objectMapper.writeValueAsString(payload);

                HttpHeaders headers = new HttpHeaders();
                headers.setContentType(MediaType.APPLICATION_JSON);
                headers.set("X-SessionGuard-Signature", computeSignature(json));

                HttpEntity<String> entity = new HttpEntity<>(json, headers);

                ResponseEntity<String> response = restTemplate.exchange(
                        url, HttpMethod.POST, entity, String.class);

                if (response.getStatusCode().is2xxSuccessful()) {
                    log.info("Webhook alert sent successfully to {} (attempt {}/{})",
                            url, attempt, retryCount);
                    return;
                }

                log.warn("Webhook returned non-2xx status: {} from {} (attempt {}/{})",
                        response.getStatusCode(), url, attempt, retryCount);
            } catch (Exception e) {
                log.warn("Webhook delivery failed to {} (attempt {}/{}): {}",
                        url, attempt, retryCount, e.getMessage());
            }

            if (attempt < retryCount) {
                try {
                    Thread.sleep(retryDelayMs);
                } catch (InterruptedException ie) {
                    Thread.currentThread().interrupt();
                    break;
                }
            }
        }

        log.error("Webhook delivery to {} failed after {} attempts", url, retryCount);
    }

    private String computeSignature(String payload) {
        try {
            java.security.MessageDigest digest = java.security.MessageDigest.getInstance("SHA-256");
            byte[] hash = digest.digest(payload.getBytes(java.nio.charset.StandardCharsets.UTF_8));
            return java.util.HexFormat.of().formatHex(hash);
        } catch (Exception e) {
            return "unsigned";
        }
    }
}
