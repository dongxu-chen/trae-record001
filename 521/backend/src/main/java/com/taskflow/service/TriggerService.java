package com.taskflow.service;

import com.taskflow.dto.TriggerDto;
import com.taskflow.model.Trigger;
import com.taskflow.repository.TriggerRepository;
import com.taskflow.repository.WorkflowRepository;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import javax.crypto.Mac;
import javax.crypto.spec.SecretKeySpec;
import java.nio.charset.StandardCharsets;
import java.time.LocalDateTime;
import java.util.Base64;
import java.util.List;
import java.util.UUID;
import java.util.stream.Collectors;

@Slf4j
@Service
@RequiredArgsConstructor
public class TriggerService {

    private final TriggerRepository triggerRepository;
    private final WorkflowRepository workflowRepository;
    private final ExecutionService executionService;

    private static final String HMAC_ALGORITHM = "HmacSHA256";

    @Transactional
    public TriggerDto createTrigger(TriggerDto.CreateRequest request) {
        workflowRepository.findById(request.getWorkflowId())
                .orElseThrow(() -> new RuntimeException("Workflow not found: " + request.getWorkflowId()));

        Trigger trigger = new Trigger();
        trigger.setWorkflowId(request.getWorkflowId());
        trigger.setTriggerType(request.getTriggerType());
        trigger.setCronExpression(request.getCronExpression());
        trigger.setEventTopic(request.getEventTopic());
        trigger.setEventFilter(request.getEventFilter());
        trigger.setEnabled(true);

        if ("WEBHOOK".equals(request.getTriggerType())) {
            trigger.setWebhookPath(request.getWebhookPath() != null
                    ? request.getWebhookPath()
                    : "wh-" + UUID.randomUUID().toString().substring(0, 12));
            trigger.setWebhookSecret(request.getWebhookSecret() != null
                    ? request.getWebhookSecret()
                    : generateSecret());
        }

        trigger = triggerRepository.save(trigger);
        return toDto(trigger);
    }

    public TriggerDto getTrigger(Long id) {
        Trigger trigger = triggerRepository.findById(id)
                .orElseThrow(() -> new RuntimeException("Trigger not found: " + id));
        return toDto(trigger);
    }

    public List<TriggerDto> listTriggers(Long workflowId) {
        if (workflowId != null) {
            return triggerRepository.findByWorkflowId(workflowId).stream()
                    .map(this::toDto).collect(Collectors.toList());
        }
        return triggerRepository.findAll().stream()
                .map(this::toDto).collect(Collectors.toList());
    }

    @Transactional
    public TriggerDto updateTrigger(Long id, TriggerDto.CreateRequest request) {
        Trigger trigger = triggerRepository.findById(id)
                .orElseThrow(() -> new RuntimeException("Trigger not found: " + id));

        if (request.getTriggerType() != null) trigger.setTriggerType(request.getTriggerType());
        if (request.getCronExpression() != null) trigger.setCronExpression(request.getCronExpression());
        if (request.getEventTopic() != null) trigger.setEventTopic(request.getEventTopic());
        if (request.getEventFilter() != null) trigger.setEventFilter(request.getEventFilter());
        if (request.getWebhookPath() != null) trigger.setWebhookPath(request.getWebhookPath());
        if (request.getWebhookSecret() != null) trigger.setWebhookSecret(request.getWebhookSecret());
        trigger = triggerRepository.save(trigger);

        return toDto(trigger);
    }

    @Transactional
    public TriggerDto toggleTrigger(Long id, boolean enabled) {
        Trigger trigger = triggerRepository.findById(id)
                .orElseThrow(() -> new RuntimeException("Trigger not found: " + id));
        trigger.setEnabled(enabled);
        trigger = triggerRepository.save(trigger);
        return toDto(trigger);
    }

    @Transactional
    public void deleteTrigger(Long id) {
        triggerRepository.deleteById(id);
    }

    @Transactional
    public void fireCronTriggers() {
        List<Trigger> cronTriggers = triggerRepository.findByTriggerTypeAndEnabledTrue("CRON");
        for (Trigger trigger : cronTriggers) {
            try {
                executionService.triggerExecution(trigger.getWorkflowId(), "CRON");
                trigger.setLastTriggerTime(LocalDateTime.now());
                triggerRepository.save(trigger);
            } catch (Exception e) {
                log.error("Failed to fire cron trigger {}: {}", trigger.getId(), e.getMessage());
            }
        }
    }

    @Transactional
    public void fireEventTrigger(String topic) {
        List<Trigger> eventTriggers = triggerRepository.findByTriggerTypeAndEnabledTrue("EVENT");
        for (Trigger trigger : eventTriggers) {
            if (topic.equals(trigger.getEventTopic())) {
                try {
                    executionService.triggerExecution(trigger.getWorkflowId(), "EVENT");
                    trigger.setLastTriggerTime(LocalDateTime.now());
                    triggerRepository.save(trigger);
                } catch (Exception e) {
                    log.error("Failed to fire event trigger {}: {}", trigger.getId(), e.getMessage());
                }
            }
        }
    }

    @Transactional
    public TriggerDto handleWebhook(String webhookPath, String payload, String signatureHeader) {
        Trigger trigger = triggerRepository.findByWebhookPath(webhookPath)
                .orElseThrow(() -> new RuntimeException("Webhook not found: " + webhookPath));

        if (!trigger.getEnabled()) {
            throw new RuntimeException("Webhook trigger is disabled");
        }

        if (trigger.getWebhookSecret() != null && !trigger.getWebhookSecret().isEmpty()) {
            if (signatureHeader == null || signatureHeader.isEmpty()) {
                throw new RuntimeException("Missing signature header");
            }
            String expectedSignature = computeHmac(payload, trigger.getWebhookSecret());
            if (!constantTimeEquals(expectedSignature, signatureHeader)) {
                throw new RuntimeException("Invalid webhook signature");
            }
        }

        long startTime = System.currentTimeMillis();
        executionService.triggerExecution(trigger.getWorkflowId(), "WEBHOOK");
        long elapsed = System.currentTimeMillis() - startTime;

        trigger.setLastTriggerTime(LocalDateTime.now());
        triggerRepository.save(trigger);

        log.info("Webhook [{}] triggered workflow [{}] in {}ms", webhookPath, trigger.getWorkflowId(), elapsed);

        return toDto(trigger);
    }

    private String computeHmac(String payload, String secret) {
        try {
            Mac mac = Mac.getInstance(HMAC_ALGORITHM);
            SecretKeySpec keySpec = new SecretKeySpec(secret.getBytes(StandardCharsets.UTF_8), HMAC_ALGORITHM);
            mac.init(keySpec);
            byte[] hash = mac.doFinal(payload.getBytes(StandardCharsets.UTF_8));
            return "sha256=" + Base64.getEncoder().encodeToString(hash);
        } catch (Exception e) {
            throw new RuntimeException("Failed to compute HMAC", e);
        }
    }

    private boolean constantTimeEquals(String a, String b) {
        if (a.length() != b.length()) return false;
        int result = 0;
        for (int i = 0; i < a.length(); i++) {
            result |= a.charAt(i) ^ b.charAt(i);
        }
        return result == 0;
    }

    private String generateSecret() {
        byte[] randomBytes = new byte[32];
        new java.security.SecureRandom().nextBytes(randomBytes);
        return Base64.getEncoder().encodeToString(randomBytes);
    }

    private TriggerDto toDto(Trigger trigger) {
        TriggerDto dto = new TriggerDto();
        dto.setId(trigger.getId());
        dto.setWorkflowId(trigger.getWorkflowId());
        dto.setTriggerType(trigger.getTriggerType());
        dto.setCronExpression(trigger.getCronExpression());
        dto.setEventTopic(trigger.getEventTopic());
        dto.setEventFilter(trigger.getEventFilter());
        dto.setWebhookPath(trigger.getWebhookPath());
        dto.setWebhookSecret(trigger.getWebhookSecret());
        dto.setEnabled(trigger.getEnabled());
        return dto;
    }
}
