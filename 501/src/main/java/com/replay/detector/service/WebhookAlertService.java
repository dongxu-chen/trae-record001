package com.replay.detector.service;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.replay.detector.config.ReplayDetectionProperties;
import com.replay.detector.model.ReplayAlert;
import lombok.extern.slf4j.Slf4j;
import org.springframework.http.*;
import org.springframework.stereotype.Service;
import org.springframework.web.client.RestTemplate;

import javax.crypto.Mac;
import javax.crypto.spec.SecretKeySpec;
import java.nio.charset.StandardCharsets;
import java.time.Instant;
import java.util.HexFormat;
import java.util.LinkedHashMap;
import java.util.Map;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

@Slf4j
@Service
public class WebhookAlertService {

    private static final Pattern TEMPLATE_VAR = Pattern.compile("\\$\\{(\\w+)}");

    private final ReplayDetectionProperties properties;
    private final RestTemplate restTemplate;
    private final ObjectMapper objectMapper;

    public WebhookAlertService(ReplayDetectionProperties properties) {
        this.properties = properties;
        this.restTemplate = new RestTemplate();
        this.objectMapper = new ObjectMapper();
    }

    public void sendAlert(ReplayAlert alert) {
        if (!properties.getWebhook().isEnabled()) {
            log.debug("Webhook alerts are disabled, skipping alert: {}", alert.getAlertId());
            return;
        }

        try {
            Map<String, String> variables = buildVariables(alert);
            String payload = renderPayload(variables);
            String signature = computeHmac(payload, properties.getWebhook().getSecret());

            HttpHeaders headers = buildHeaders(alert, signature);

            HttpEntity<String> entity = new HttpEntity<>(payload, headers);

            ResponseEntity<String> response = restTemplate.exchange(
                    properties.getWebhook().getUrl(),
                    HttpMethod.POST,
                    entity,
                    String.class
            );

            if (response.getStatusCode().is2xxSuccessful()) {
                log.info("Webhook alert sent: alertId={}, level={}, format={}, status={}",
                        alert.getAlertId(), alert.getLevel(),
                        properties.getWebhook().getTemplate().getFormat(), response.getStatusCode());
            } else {
                log.warn("Webhook alert returned non-success: alertId={}, status={}",
                        alert.getAlertId(), response.getStatusCode());
            }

        } catch (Exception e) {
            log.error("Failed to send webhook alert: alertId={}, error={}", alert.getAlertId(), e.getMessage(), e);
        }
    }

    private Map<String, String> buildVariables(ReplayAlert alert) {
        Map<String, String> vars = new LinkedHashMap<>();
        vars.put("alertId", alert.getAlertId());
        vars.put("level", alert.getLevel().name());
        vars.put("fingerprintHash", alert.getFingerprintHash());
        vars.put("path", alert.getPath());
        vars.put("clientIp", alert.getClientIp());
        vars.put("replayCount", String.valueOf(alert.getReplayCount()));
        vars.put("windowSizeSeconds", String.valueOf(alert.getWindowSizeSeconds()));
        vars.put("detectedAt", String.valueOf(alert.getDetectedAt()));
        vars.put("detectedAtIso", Instant.ofEpochMilli(alert.getDetectedAt()).toString());
        vars.put("message", alert.getMessage());
        return vars;
    }

    private String renderPayload(Map<String, String> variables) {
        ReplayDetectionProperties.Webhook.Template template = properties.getWebhook().getTemplate();
        String format = template.getFormat();

        String bodyTemplate = template.getBodyTemplate();
        if (bodyTemplate != null && !bodyTemplate.isBlank()) {
            return resolveTemplate(bodyTemplate, variables);
        }

        return switch (format.toUpperCase()) {
            case "XML" -> renderXml(variables);
            case "PLAIN_TEXT" -> renderPlainText(variables);
            default -> renderJson(variables);
        };
    }

    private String renderJson(Map<String, String> variables) {
        try {
            ReplayDetectionProperties.Webhook.Template template = properties.getWebhook().getTemplate();
            String jsonTemplate = template.getJsonTemplate();

            if (jsonTemplate != null && !jsonTemplate.isBlank()) {
                String resolved = resolveTemplate(jsonTemplate, variables);
                objectMapper.readTree(resolved);
                return resolved;
            }

            return objectMapper.writeValueAsString(variables);
        } catch (Exception e) {
            log.error("Failed to render JSON payload, falling back to default", e);
            try {
                return objectMapper.writeValueAsString(variables);
            } catch (Exception ex) {
                return "{}";
            }
        }
    }

    private String renderXml(Map<String, String> variables) {
        ReplayDetectionProperties.Webhook.Template template = properties.getWebhook().getTemplate();
        String xmlTemplate = template.getXmlTemplate();

        if (xmlTemplate != null && !xmlTemplate.isBlank()) {
            return resolveTemplate(xmlTemplate, variables);
        }

        StringBuilder sb = new StringBuilder();
        sb.append("<?xml version=\"1.0\" encoding=\"UTF-8\"?>");
        sb.append("<replayAlert>");
        for (Map.Entry<String, String> entry : variables.entrySet()) {
            sb.append("<").append(entry.getKey()).append(">");
            sb.append(escapeXml(entry.getValue()));
            sb.append("</").append(entry.getKey()).append(">");
        }
        sb.append("</replayAlert>");
        return sb.toString();
    }

    private String renderPlainText(Map<String, String> variables) {
        ReplayDetectionProperties.Webhook.Template template = properties.getWebhook().getTemplate();
        String textTemplate = template.getTextTemplate();

        if (textTemplate != null && !textTemplate.isBlank()) {
            return resolveTemplate(textTemplate, variables);
        }

        StringBuilder sb = new StringBuilder();
        sb.append("=== Replay Attack Alert ===\n");
        for (Map.Entry<String, String> entry : variables.entrySet()) {
            sb.append(entry.getKey()).append(": ").append(entry.getValue()).append("\n");
        }
        return sb.toString().trim();
    }

    private String resolveTemplate(String template, Map<String, String> variables) {
        Matcher matcher = TEMPLATE_VAR.matcher(template);
        StringBuffer result = new StringBuffer();
        while (matcher.find()) {
            String key = matcher.group(1);
            String replacement = variables.getOrDefault(key, "${" + key + "}");
            matcher.appendReplacement(result, Matcher.quoteReplacement(replacement));
        }
        matcher.appendTail(result);
        return result.toString();
    }

    private HttpHeaders buildHeaders(ReplayAlert alert, String signature) {
        ReplayDetectionProperties.Webhook.Template template = properties.getWebhook().getTemplate();
        HttpHeaders headers = new HttpHeaders();

        String format = template.getFormat();
        headers.setContentType(switch (format.toUpperCase()) {
            case "XML" -> MediaType.APPLICATION_XML;
            case "PLAIN_TEXT" -> MediaType.TEXT_PLAIN;
            default -> MediaType.APPLICATION_JSON;
        });

        headers.set("X-Replay-Signature", signature);
        headers.set("X-Alert-Level", alert.getLevel().name());
        headers.set("X-Alert-Id", alert.getAlertId());
        headers.set("X-Alert-Format", format.toUpperCase());

        Map<String, String> headerTemplates = template.getHeaderTemplates();
        if (headerTemplates != null) {
            Map<String, String> variables = buildVariables(alert);
            headerTemplates.forEach((key, value) -> {
                if (!key.startsWith("X-Replay") && !key.startsWith("X-Alert")) {
                    headers.set(key, resolveTemplate(value, variables));
                }
            });
        }

        return headers;
    }

    private String escapeXml(String input) {
        if (input == null) return "";
        return input.replace("&", "&amp;")
                .replace("<", "&lt;")
                .replace(">", "&gt;")
                .replace("\"", "&quot;")
                .replace("'", "&apos;");
    }

    private String computeHmac(String payload, String secret) {
        try {
            Mac mac = Mac.getInstance("HmacSHA256");
            SecretKeySpec keySpec = new SecretKeySpec(secret.getBytes(StandardCharsets.UTF_8), "HmacSHA256");
            mac.init(keySpec);
            byte[] hash = mac.doFinal(payload.getBytes(StandardCharsets.UTF_8));
            return HexFormat.of().formatHex(hash);
        } catch (Exception e) {
            log.error("Failed to compute HMAC signature", e);
            return "error";
        }
    }
}
