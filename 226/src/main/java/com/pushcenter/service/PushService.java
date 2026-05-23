package com.pushcenter.service;

import com.pushcenter.disruptor.PriorityMessageProducer;
import com.pushcenter.enums.MessagePriority;
import com.pushcenter.enums.MessageStatus;
import com.pushcenter.enums.PushChannel;
import com.pushcenter.model.PushMessage;
import com.pushcenter.model.PushTemplate;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;

import javax.annotation.Resource;
import java.util.Map;
import java.util.UUID;

@Slf4j
@Service
public class PushService {

    @Resource
    private TemplateService templateService;

    @Resource
    private ChannelSelectorService channelSelectorService;

    @Resource
    private UserConfigService userConfigService;

    @Resource
    private PriorityMessageProducer priorityMessageProducer;

    @Resource
    private PushAnalyticsService analyticsService;

    public String push(String userId, String templateCode, Map<String, Object> variables) {
        return push(userId, templateCode, variables, null, null, false);
    }

    public String push(String userId, String templateCode, Map<String, Object> variables, PushChannel preferredChannel) {
        return push(userId, templateCode, variables, preferredChannel, null, false);
    }

    public String push(String userId, String templateCode, Map<String, Object> variables,
                       PushChannel preferredChannel, MessagePriority priority, boolean jumpQueue) {
        PushTemplate template = templateService.getTemplate(templateCode);
        if (template == null) {
            log.error("Template not found: {}", templateCode);
            return null;
        }

        if (!template.isEnabled()) {
            log.error("Template is disabled: {}", templateCode);
            return null;
        }

        if (!templateService.validateVariables(template, variables)) {
            log.error("Invalid variables for template: {}", templateCode);
            return null;
        }

        PushChannel channel = channelSelectorService.selectOptimalChannel(userId, template, preferredChannel);
        if (channel == null) {
            log.error("No available channel for user: {}, template: {}", userId, templateCode);
            return null;
        }

        String title = templateService.renderTitle(template, variables);
        String content = templateService.renderContent(template, variables);

        String receiver = userConfigService.getReceiverForChannel(userId, channel);

        String messageId = UUID.randomUUID().toString();

        MessagePriority msgPriority = priority != null ? priority : MessagePriority.NORMAL;

        PushMessage message = PushMessage.builder()
                .messageId(messageId)
                .userId(userId)
                .templateCode(templateCode)
                .variables(variables)
                .title(title)
                .content(content)
                .channel(channel)
                .receiver(receiver)
                .status(MessageStatus.PENDING)
                .retryCount(0)
                .maxRetryCount(template.getMaxRetryCount())
                .createTime(System.currentTimeMillis())
                .priority(msgPriority)
                .jumpQueue(jumpQueue)
                .build();

        boolean published = priorityMessageProducer.publish(message);
        if (!published) {
            log.warn("Failed to publish message to disruptor, messageId: {}", messageId);
            return null;
        }

        analyticsService.recordMessageMetadata(messageId, channel, templateCode, userId);
        analyticsService.recordSent(channel, messageId, userId, templateCode);

        log.info("Message queued: {}, channel: {}, user: {}, priority: {}, jumpQueue: {}",
                messageId, channel, userId, msgPriority.getName(), jumpQueue);
        return messageId;
    }

    public String pushDirect(String userId, PushChannel channel, String title, String content) {
        return pushDirect(userId, channel, title, content, null, false);
    }

    public String pushDirect(String userId, PushChannel channel, String title, String content,
                             MessagePriority priority, boolean jumpQueue) {
        String receiver = userConfigService.getReceiverForChannel(userId, channel);
        if (receiver == null) {
            log.error("No receiver found for user: {}, channel: {}", userId, channel);
            return null;
        }

        String messageId = UUID.randomUUID().toString();
        MessagePriority msgPriority = priority != null ? priority : MessagePriority.NORMAL;

        PushMessage message = PushMessage.builder()
                .messageId(messageId)
                .userId(userId)
                .title(title)
                .content(content)
                .channel(channel)
                .receiver(receiver)
                .status(MessageStatus.PENDING)
                .retryCount(0)
                .maxRetryCount(3)
                .createTime(System.currentTimeMillis())
                .priority(msgPriority)
                .jumpQueue(jumpQueue)
                .build();

        boolean published = priorityMessageProducer.publish(message);
        if (!published) {
            log.warn("Failed to publish message to disruptor, messageId: {}", messageId);
            return null;
        }

        log.info("Direct message queued: {}, channel: {}, user: {}, priority: {}",
                messageId, channel, userId, msgPriority.getName());
        return messageId;
    }

    public void batchPush(String[] userIds, String templateCode, Map<String, Object> variables) {
        for (String userId : userIds) {
            push(userId, templateCode, variables);
        }
    }

    public Map<MessagePriority, Long> getPendingCounts() {
        return priorityMessageProducer.getAllPendingCounts();
    }
}
