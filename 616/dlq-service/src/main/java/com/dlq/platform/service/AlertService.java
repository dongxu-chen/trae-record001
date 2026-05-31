package com.dlq.platform.service;

import com.dlq.platform.common.config.QueueImportanceConfig;
import com.dlq.platform.common.dto.AlertRuleDTO;
import com.dlq.platform.common.dto.DeadLetterAnalysisResult;
import com.dlq.platform.common.entity.AlertRule;
import com.dlq.platform.common.entity.DeadLetterMessage;
import com.dlq.platform.common.enums.AlertLevelEnum;
import com.dlq.platform.es.service.AlertEsService;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.mail.SimpleMailMessage;
import org.springframework.mail.javamail.JavaMailSender;
import org.springframework.scheduling.annotation.Async;
import org.springframework.stereotype.Service;
import org.springframework.util.StringUtils;

import java.time.LocalDateTime;
import java.util.*;
import java.util.concurrent.CompletableFuture;

@Slf4j
@Service
@RequiredArgsConstructor
public class AlertService {

    private final AlertEsService alertEsService;
    private final JavaMailSender mailSender;
    private final QueueImportanceConfig queueImportanceConfig;

    @Value("${dlq.alert.enabled:true}")
    private boolean alertEnabled;

    @Value("${spring.mail.username:}")
    private String mailFrom;

    public AlertRule createAlertRule(AlertRule rule) {
        try {
            alertEsService.saveAlertRule(rule);
            return rule;
        } catch (Exception e) {
            log.error("创建告警规则失败", e);
            throw new RuntimeException("创建告警规则失败", e);
        }
    }

    public AlertRule updateAlertRule(AlertRule rule) {
        try {
            AlertRule existing = alertEsService.findAlertRuleById(rule.getId());
            if (existing == null) {
                throw new RuntimeException("告警规则不存在, id: " + rule.getId());
            }
            rule.setCreateTime(existing.getCreateTime());
            alertEsService.saveAlertRule(rule);
            return rule;
        } catch (Exception e) {
            log.error("更新告警规则失败, id: {}", rule.getId(), e);
            throw new RuntimeException("更新告警规则失败", e);
        }
    }

    public void deleteAlertRule(String id) {
        try {
            alertEsService.deleteAlertRule(id);
        } catch (Exception e) {
            log.error("删除告警规则失败, id: {}", id, e);
            throw new RuntimeException("删除告警规则失败", e);
        }
    }

    public AlertRule getAlertRule(String id) {
        return alertEsService.findAlertRuleById(id);
    }

    public Map<String, Object> queryAlertRules(AlertRuleDTO queryDTO) {
        return alertEsService.queryAlertRules(queryDTO);
    }

    public List<AlertRule> getEnabledRules() {
        return alertEsService.findAllEnabledAlertRules();
    }

    @Async
    public void checkAndTriggerAlert(DeadLetterMessage message, DeadLetterAnalysisResult analysisResult) {
        if (!alertEnabled) {
            return;
        }

        try {
            String topicOrQueue = message.getTopic() != null ? message.getTopic() : message.getQueueName();
            QueueImportanceConfig.QueueThreshold threshold = queueImportanceConfig.getQueueThreshold(topicOrQueue);

            if (!Boolean.TRUE.equals(threshold.getAlertEnabled())) {
                log.debug("队列[{}]告警已禁用, importanceLevel: {}", topicOrQueue, threshold.getImportanceLevel());
                return;
            }

            int queueSilentMinutes = threshold.getAlertSilenceMinutes() != null
                    ? threshold.getAlertSilenceMinutes() : 30;

            List<AlertRule> rules = getEnabledRules();
            if (rules.isEmpty()) {
                return;
            }

            for (AlertRule rule : rules) {
                if (matchRule(rule, message, analysisResult)) {
                    String messageKey = buildMessageKey(rule, message);

                    AlertLevelEnum effectiveLevel = adjustAlertLevelByImportance(
                            AlertLevelEnum.valueOf(rule.getAlertLevel().name()),
                            threshold.getImportanceLevel());

                    if (alertEsService.isAlertSilenced(rule.getId(), messageKey, queueSilentMinutes)) {
                        log.debug("告警静默中, ruleId: {}, messageKey: {}, silentMinutes: {}",
                                rule.getId(), messageKey, queueSilentMinutes);
                        continue;
                    }

                    triggerAlert(rule, message, analysisResult, messageKey, effectiveLevel, threshold);
                }
            }
        } catch (Exception e) {
            log.error("检查并触发告警异常", e);
        }
    }

    private AlertLevelEnum adjustAlertLevelByImportance(AlertLevelEnum originalLevel,
                                                        QueueImportanceConfig.ImportanceLevel importanceLevel) {
        switch (importanceLevel) {
            case CORE:
                return AlertLevelEnum.CRITICAL;
            case HIGH:
                return originalLevel == AlertLevelEnum.INFO ? AlertLevelEnum.WARNING : originalLevel;
            case LOW:
                return originalLevel == AlertLevelEnum.CRITICAL ? AlertLevelEnum.WARNING : originalLevel;
            case NORMAL:
            default:
                return originalLevel;
        }
    }

    private boolean matchRule(AlertRule rule, DeadLetterMessage message, DeadLetterAnalysisResult analysisResult) {
        try {
            String condition = rule.getTriggerCondition();
            if (!StringUtils.hasText(condition)) {
                return true;
            }

            String topicOrQueue = message.getTopic() != null ? message.getTopic() : message.getQueueName();
            QueueImportanceConfig.QueueThreshold threshold = queueImportanceConfig.getQueueThreshold(topicOrQueue);

            Map<String, Object> context = buildEvaluationContext(message, analysisResult, threshold);

            return evaluateCondition(condition, context, threshold);
        } catch (Exception e) {
            log.error("匹配告警规则异常, ruleId: {}", rule.getId(), e);
            return false;
        }
    }

    private Map<String, Object> buildEvaluationContext(DeadLetterMessage message, DeadLetterAnalysisResult analysisResult,
                                                        QueueImportanceConfig.QueueThreshold threshold) {
        Map<String, Object> context = new HashMap<>();

        context.put("mqType", message.getMqType() != null ? message.getMqType().name() : null);
        context.put("topic", message.getTopic());
        context.put("queueName", message.getQueueName());
        context.put("deadReason", message.getDeadReason());
        context.put("deadReasonType", message.getDeadReasonType() != null ? message.getDeadReasonType().name() : null);
        context.put("retryCount", message.getRetryCount());
        context.put("processStatus", message.getProcessStatus() != null ? message.getProcessStatus().getCode() : null);
        context.put("importanceLevel", threshold.getImportanceLevel().name());
        context.put("maxRetryCount", threshold.getMaxRetryCount());
        context.put("alertThreshold", threshold.getAlertThreshold());

        if (analysisResult != null) {
            context.put("riskLevel", analysisResult.getRiskLevel() != null ? analysisResult.getRiskLevel().name() : null);
            context.put("rootCause", analysisResult.getRootCause());
            context.put("deadReasonType", analysisResult.getDeadReasonType() != null ? analysisResult.getDeadReasonType().name() : null);

            if (analysisResult.getAnalysisDetails() != null) {
                context.put("confidence", analysisResult.getAnalysisDetails().get("confidence"));
            }
        }

        return context;
    }

    private boolean evaluateCondition(String condition, Map<String, Object> context,
                                      QueueImportanceConfig.QueueThreshold threshold) {
        try {
            String normalizedCondition = condition.toLowerCase().trim();

            if (normalizedCondition.contains("risklevel")) {
                String level = (String) context.get("riskLevel");
                if (level != null) {
                    if (normalizedCondition.contains("critical") && "CRITICAL".equals(level)) {
                        return true;
                    }
                    if (normalizedCondition.contains("warning") && ("CRITICAL".equals(level) || "WARNING".equals(level))) {
                        return true;
                    }
                }
            }

            if (normalizedCondition.contains("retrycount")) {
                Integer retryCount = (Integer) context.get("retryCount");
                Integer maxRetryCount = (Integer) context.get("maxRetryCount");
                if (retryCount != null && maxRetryCount != null) {
                    if (normalizedCondition.contains("percentage")) {
                        double percentage = (double) retryCount / maxRetryCount;
                        if (percentage >= 0.8) {
                            return true;
                        }
                    } else if (retryCount >= maxRetryCount * 0.6) {
                        return true;
                    }
                }
            }

            if (normalizedCondition.contains("timeout")) {
                String reasonType = (String) context.get("deadReasonType");
                if ("TIMEOUT".equals(reasonType)) {
                    return true;
                }
            }

            if (normalizedCondition.contains("database") || normalizedCondition.contains("db")) {
                String reasonType = (String) context.get("deadReasonType");
                String rootCause = (String) context.get("rootCause");
                if ("BIZ_EXCEPTION".equals(reasonType) ||
                        (rootCause != null && rootCause.toLowerCase().contains("database"))) {
                    return true;
                }
            }

            return false;
        } catch (Exception e) {
            log.error("评估条件异常, condition: {}", condition, e);
            return false;
        }
    }

    private String buildMessageKey(AlertRule rule, DeadLetterMessage message) {
        StringBuilder key = new StringBuilder();
        key.append(rule.getId()).append(":");
        key.append(message.getMqType() != null ? message.getMqType().name() : "").append(":");
        key.append(message.getTopic() != null ? message.getTopic() : "").append(":");
        key.append(message.getDeadReasonType() != null ? message.getDeadReasonType().name() : "");
        return key.toString();
    }

    private void triggerAlert(AlertRule rule, DeadLetterMessage message,
                              DeadLetterAnalysisResult analysisResult, String messageKey,
                              AlertLevelEnum effectiveLevel, QueueImportanceConfig.QueueThreshold threshold) {
        try {
            String content = buildAlertContent(rule, message, analysisResult, effectiveLevel, threshold);

            sendNotification(rule, content);

            saveAlertHistory(rule, message, analysisResult, messageKey, content);

            log.info("告警触发成功, ruleId: {}, ruleName: {}, messageId: {}, level: {}, importance: {}",
                    rule.getId(), rule.getName(), message.getId(), effectiveLevel,
                    threshold.getImportanceLevel());
        } catch (Exception e) {
            log.error("触发告警异常, ruleId: {}", rule.getId(), e);
        }
    }

    private String buildAlertContent(AlertRule rule, DeadLetterMessage message,
                                     DeadLetterAnalysisResult analysisResult,
                                     AlertLevelEnum effectiveLevel,
                                     QueueImportanceConfig.QueueThreshold threshold) {
        StringBuilder content = new StringBuilder();
        content.append("【死信队列告警】\n");
        content.append("告警规则: ").append(rule.getName()).append("\n");
        content.append("配置级别: ").append(rule.getAlertLevel() != null ? rule.getAlertLevel().getDesc() : "未知").append("\n");
        content.append("生效级别: ").append(effectiveLevel.getDesc()).append("\n");
        content.append("队列重要性: ").append(threshold.getImportanceLevel().getLabel()).append("\n");
        if (threshold.getDescription() != null) {
            content.append("队列描述: ").append(threshold.getDescription()).append("\n");
        }
        content.append("消息ID: ").append(message.getId()).append("\n");
        content.append("MQ类型: ").append(message.getMqType() != null ? message.getMqType().getDesc() : "未知").append("\n");
        content.append("主题: ").append(message.getTopic() != null ? message.getTopic() : message.getQueueName()).append("\n");
        content.append("死信原因: ").append(message.getDeadReason()).append("\n");
        content.append("当前重试次数: ").append(message.getRetryCount()).append("/").append(threshold.getMaxRetryCount()).append("\n");
        content.append("创建时间: ").append(message.getCreateTime()).append("\n");

        if (analysisResult != null) {
            content.append("风险级别: ").append(analysisResult.getRiskLevel() != null ? analysisResult.getRiskLevel().getDesc() : "未知").append("\n");
            content.append("根因分析: ").append(analysisResult.getRootCause()).append("\n");
            content.append("建议处理: ").append(analysisResult.getSuggestedAction()).append("\n");
        }

        return content.toString();
    }

    private void sendNotification(AlertRule rule, String content) {
        String notificationType = rule.getNotificationType();
        String target = rule.getNotificationTarget();

        if (!StringUtils.hasText(notificationType) || !StringUtils.hasText(target)) {
            log.warn("告警通知配置不完整, ruleId: {}", rule.getId());
            return;
        }

        try {
            switch (notificationType.toUpperCase()) {
                case "EMAIL":
                    sendEmail(target, rule.getName(), content);
                    break;
                case "WEBHOOK":
                    sendWebhook(target, rule, content);
                    break;
                case "DINGTALK":
                    sendDingTalk(target, rule, content);
                    break;
                case "WECHAT":
                    sendWeChat(target, rule, content);
                    break;
                default:
                    log.warn("不支持的通知类型: {}", notificationType);
            }
        } catch (Exception e) {
            log.error("发送告警通知失败, type: {}, target: {}", notificationType, target, e);
        }
    }

    private void sendEmail(String to, String subject, String content) {
        try {
            if (!StringUtils.hasText(mailFrom)) {
                log.warn("邮件发件人未配置，跳过邮件发送");
                return;
            }

            SimpleMailMessage message = new SimpleMailMessage();
            message.setFrom(mailFrom);
            message.setTo(to.split(","));
            message.setSubject("【死信告警】" + subject);
            message.setText(content);

            CompletableFuture.runAsync(() -> {
                try {
                    mailSender.send(message);
                    log.info("告警邮件发送成功, to: {}", to);
                } catch (Exception e) {
                    log.error("告警邮件发送失败, to: {}", to, e);
                }
            });
        } catch (Exception e) {
            log.error("构建告警邮件失败", e);
        }
    }

    private void sendWebhook(String url, AlertRule rule, String content) {
        try {
            Map<String, Object> payload = new HashMap<>();
            payload.put("msgtype", "text");
            Map<String, String> text = new HashMap<>();
            text.put("content", content);
            payload.put("text", text);

            CompletableFuture.runAsync(() -> {
                try {
                    doHttpPost(url, payload);
                    log.info("Webhook告警发送成功, url: {}", url);
                } catch (Exception e) {
                    log.error("Webhook告警发送失败, url: {}", url, e);
                }
            });
        } catch (Exception e) {
            log.error("构建Webhook告警失败", e);
        }
    }

    private void sendDingTalk(String webhookUrl, AlertRule rule, String content) {
        try {
            Map<String, Object> payload = new HashMap<>();
            payload.put("msgtype", "markdown");
            Map<String, Object> markdown = new HashMap<>();
            markdown.put("title", "死信队列告警");
            markdown.put("text", content.replace("\n", "  \n"));
            payload.put("markdown", markdown);

            if (rule.getAlertLevel() == AlertLevelEnum.CRITICAL) {
                Map<String, Object> at = new HashMap<>();
                at.put("isAtAll", true);
                payload.put("at", at);
            }

            CompletableFuture.runAsync(() -> {
                try {
                    doHttpPost(webhookUrl, payload);
                    log.info("钉钉告警发送成功");
                } catch (Exception e) {
                    log.error("钉钉告警发送失败", e);
                }
            });
        } catch (Exception e) {
            log.error("构建钉钉告警失败", e);
        }
    }

    private void sendWeChat(String webhookUrl, AlertRule rule, String content) {
        try {
            Map<String, Object> payload = new HashMap<>();
            payload.put("msgtype", "markdown");
            Map<String, Object> markdown = new HashMap<>();
            markdown.put("content", content);
            payload.put("markdown", markdown);

            CompletableFuture.runAsync(() -> {
                try {
                    doHttpPost(webhookUrl, payload);
                    log.info("企业微信告警发送成功");
                } catch (Exception e) {
                    log.error("企业微信告警发送失败", e);
                }
            });
        } catch (Exception e) {
            log.error("构建企业微信告警失败", e);
        }
    }

    private void doHttpPost(String url, Map<String, Object> payload) throws Exception {
        java.net.URL obj = new java.net.URL(url);
        java.net.HttpURLConnection con = (java.net.HttpURLConnection) obj.openConnection();
        con.setRequestMethod("POST");
        con.setRequestProperty("Content-Type", "application/json");
        con.setDoOutput(true);

        String jsonBody = com.dlq.platform.common.utils.JsonUtils.toJson(payload);

        try (java.io.OutputStream os = con.getOutputStream()) {
            byte[] input = jsonBody.getBytes("utf-8");
            os.write(input, 0, input.length);
        }

        int responseCode = con.getResponseCode();
        if (responseCode >= 400) {
            throw new RuntimeException("HTTP请求失败, responseCode: " + responseCode);
        }
    }

    private void saveAlertHistory(AlertRule rule, DeadLetterMessage message,
                                   DeadLetterAnalysisResult analysisResult, String messageKey, String content) {
        try {
            Map<String, Object> history = new HashMap<>();
            history.put("ruleId", rule.getId());
            history.put("ruleName", rule.getName());
            history.put("alertLevel", rule.getAlertLevel() != null ? rule.getAlertLevel().name() : null);
            history.put("messageId", message.getId());
            history.put("mqType", message.getMqType() != null ? message.getMqType().name() : null);
            history.put("topic", message.getTopic());
            history.put("messageKey", messageKey);
            history.put("content", content);
            history.put("notificationType", rule.getNotificationType());
            history.put("notificationTarget", rule.getNotificationTarget());
            history.put("createTime", LocalDateTime.now());

            if (analysisResult != null) {
                history.put("riskLevel", analysisResult.getRiskLevel() != null ? analysisResult.getRiskLevel().name() : null);
                history.put("rootCause", analysisResult.getRootCause());
            }

            alertEsService.saveAlertHistory(history);
        } catch (Exception e) {
            log.error("保存告警历史失败", e);
        }
    }

    public Map<String, Object> queryAlertHistory(String ruleId, AlertLevelEnum level,
                                                 LocalDateTime startTime, LocalDateTime endTime,
                                                 int pageNum, int pageSize) {
        return alertEsService.queryAlertHistory(ruleId, level, startTime, endTime, pageNum, pageSize);
    }

    public void checkAlertsForMessages(List<DeadLetterMessage> messages,
                                       Map<String, DeadLetterAnalysisResult> analysisResultMap) {
        if (!alertEnabled || messages == null || messages.isEmpty()) {
            return;
        }

        for (DeadLetterMessage message : messages) {
            DeadLetterAnalysisResult analysisResult = analysisResultMap != null
                    ? analysisResultMap.get(message.getMessageId())
                    : null;
            checkAndTriggerAlert(message, analysisResult);
        }
    }
}
