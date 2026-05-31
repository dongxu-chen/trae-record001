package com.dlq.platform.service;

import com.dlq.platform.analysis.service.DeadLetterAnalysisService;
import com.dlq.platform.common.dto.DeadLetterAnalysisResult;
import com.dlq.platform.common.entity.DeadLetterMessage;
import com.dlq.platform.common.enums.MqTypeEnum;
import com.dlq.platform.common.enums.ProcessStatusEnum;
import com.dlq.platform.common.utils.MessageIdGenerator;
import com.dlq.platform.es.service.DeadLetterEsService;
import com.dlq.platform.mq.consumer.MessageConsumer;
import com.dlq.platform.mq.factory.MessageConsumerFactory;
import jakarta.annotation.PostConstruct;
import jakarta.annotation.PreDestroy;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;
import org.springframework.util.StringUtils;

import java.time.LocalDateTime;
import java.util.*;
import java.util.concurrent.ConcurrentHashMap;

@Slf4j
@Service
@RequiredArgsConstructor
public class DeadLetterConsumeService {

    private final MessageConsumerFactory consumerFactory;
    private final DeadLetterAnalysisService analysisService;
    private final DeadLetterEsService deadLetterEsService;
    private final AlertService alertService;

    @Value("${dlq.consume.mq-types:KAFKA,ROCKETMQ,RABBITMQ")
    private String mqTypes;

    @Value("${dlq.consume.topics:}")
    private String topics;

    @Value("${dlq.consume.deduplication-enabled:true}")
    private boolean deduplicationEnabled;

    private final Map<String, MessageConsumer> consumerMap = new ConcurrentHashMap<>();
    private final Set<String> processedMessageIds = Collections.synchronizedSet(new HashSet<>());

    @PostConstruct
    public void startConsumers() {
        log.info("开始启动死信消息消费者...");

        String[] mqTypeArray = mqTypes.split(",");
        String[] topicArray = StringUtils.hasText(topics) ? topics.split(",") : new String[0];

        for (String mqTypeStr : mqTypeArray) {
            try {
                MqTypeEnum mqType = MqTypeEnum.valueOf(mqTypeStr.trim().toUpperCase());
                startConsumer(mqType, topicArray);
            } catch (Exception e) {
                log.error("启动消费者失败, mqType: {}", mqTypeStr, e);
            }
        }

        log.info("死信消息消费者启动完成, 已启动消费者数量: {}", consumerMap.size());
    }

    private void startConsumer(MqTypeEnum mqType, String[] topicArray) {
        try {
            MessageConsumer consumer = consumerFactory.createConsumer(mqType);

            consumer.consume(message -> {
                log.debug("收到死信消息, mqType: {}, topic: {}", mqType, message.getTopic());

                DeadLetterMessage deadLetterMessage = convertToDeadLetter(message, mqType);

                if (deduplicationEnabled && isDuplicate(deadLetterMessage)) {
                    log.warn("重复消息，跳过处理, messageId: {}", deadLetterMessage.getMessageId());
                    return;
                }

                processDeadLetter(deadLetterMessage);
            });

            if (topicArray != null && topicArray.length > 0) {
                for (String topic : topicArray) {
                    if (StringUtils.hasText(topic)) {
                        consumer.subscribe(topic.trim());
                    }
                }
            }

            consumer.start();
            consumerMap.put(mqType.name(), consumer);

            log.info("启动消费者成功, mqType: {}", mqType);
        } catch (Exception e) {
            log.error("启动消费者失败, mqType: {}", mqType, e);
        }
    }

    private boolean isDuplicate(DeadLetterMessage message) {
        String messageId = message.getMessageId();
        if (messageId == null) {
            return false;
        }

        if (processedMessageIds.contains(messageId)) {
            return true;
        }

        if (deadLetterEsService.existsByMessageId(messageId)) {
            processedMessageIds.add(messageId);
            return true;
        }

        if (processedMessageIds.add(messageId)) {
            if (processedMessageIds.size() > 10000) {
                processedMessageIds.clear();
            }
        }
        return false;
    }

    private DeadLetterMessage convertToDeadLetter(Object message, MqTypeEnum mqType) {
        DeadLetterMessage deadLetter = new DeadLetterMessage();
        deadLetter.setId(MessageIdGenerator.generate());
        deadLetter.setMqType(mqType);
        deadLetter.setProcessStatus(ProcessStatusEnum.PENDING);
        deadLetter.setCreateTime(LocalDateTime.now());
        deadLetter.setUpdateTime(LocalDateTime.now());
        deadLetter.setRetryCount(0);

        if (message instanceof Map) {
            Map<String, Object> msgMap = (Map<String, Object>) message;
            deadLetter.setTopic((String) msgMap.get("topic"));
            deadLetter.setQueueName((String) msgMap.get("queueName"));
            deadLetter.setMessageId((String) msgMap.get("messageId"));
            deadLetter.setMessageBody((String) msgMap.get("body"));
            deadLetter.setHeaders((Map<String, Object>) msgMap.get("headers"));
            deadLetter.setDeadReason((String) msgMap.get("deadReason"));
            deadLetter.setOriginalTopic((String) msgMap.get("originalTopic"));
            deadLetter.setOriginalQueue((String) msgMap.get("originalQueue"));

            Object retryCount = msgMap.get("retryCount");
            if (retryCount instanceof Number) {
                deadLetter.setRetryCount(((Number) retryCount).intValue());
            }
        }

        if (deadLetter.getMessageId() == null) {
            deadLetter.setMessageId(deadLetter.getId());
        }

        return deadLetter;
    }

    public void processDeadLetter(DeadLetterMessage deadLetter) {
        try {
            log.info("开始处理死信消息, messageId: {}, topic: {}", deadLetter.getMessageId(), deadLetter.getTopic());

            preprocess(deadLetter);

            DeadLetterAnalysisResult analysisResult = analysisService.analyze(deadLetter);

            enrichWithAnalysisResult(deadLetter, analysisResult);

            deadLetterEsService.save(deadLetter);

            alertService.checkAndTriggerAlert(deadLetter, analysisResult);

            log.info("死信消息处理完成, messageId: {}", deadLetter.getMessageId());
        } catch (Exception e) {
            log.error("处理死信消息异常, messageId: {}", deadLetter.getMessageId(), e);
            deadLetter.setDeadReason("处理异常: " + e.getMessage());
            deadLetterEsService.save(deadLetter);
        }
    }

    private void preprocess(DeadLetterMessage deadLetter) {
        if (deadLetter.getMessageBody() != null) {
            String body = deadLetter.getMessageBody().trim();
            if (body.length() > 10000) {
                deadLetter.setMessageBody(body.substring(0, 10000) + "...(truncated)");
            } else {
                deadLetter.setMessageBody(body);
            }
        }

        if (deadLetter.getHeaders() != null && !deadLetter.getHeaders().isEmpty()) {
            Map<String, Object> cleanedHeaders = new HashMap<>();
            deadLetter.getHeaders().forEach((k, v) -> {
                if (v != null && v.toString().length() <= 1000) {
                    cleanedHeaders.put(k, v);
                }
            });
            deadLetter.setHeaders(cleanedHeaders);
        }

        if (deadLetter.getDeadReason() != null) {
            String reason = deadLetter.getDeadReason().trim();
            if (reason.length() > 2000) {
                deadLetter.setDeadReason(reason.substring(0, 2000) + "...(truncated)");
            } else {
                deadLetter.setDeadReason(reason);
            }
        }
    }

    private void enrichWithAnalysisResult(DeadLetterMessage deadLetter, DeadLetterAnalysisResult analysisResult) {
        if (analysisResult != null) {
            deadLetter.setDeadReasonType(analysisResult.getDeadReasonType());
            deadLetter.setProcessStatus(ProcessStatusEnum.PROCESSED);
            deadLetter.setUpdateTime(LocalDateTime.now());

            Map<String, Object> analysisInfo = new HashMap<>();
            analysisInfo.put("rootCause", analysisResult.getRootCause());
            analysisInfo.put("suggestedAction", analysisResult.getSuggestedAction());
            analysisInfo.put("riskLevel", analysisResult.getRiskLevel() != null ? analysisResult.getRiskLevel().name() : null);
            analysisInfo.put("analysisDetails", analysisResult.getAnalysisDetails());
            analysisInfo.put("analysisTime", analysisResult.getAnalysisTime() != null ? analysisResult.getAnalysisTime().toString() : null);

            if (deadLetter.getHeaders() == null) {
                deadLetter.setHeaders(new HashMap<>());
            }
            deadLetter.getHeaders().put("analysisInfo", analysisInfo);
        }
    }

    public void processBatch(List<DeadLetterMessage> messages) {
        if (messages == null || messages.isEmpty()) {
            return;
        }

        List<DeadLetterMessage> nonDuplicateMessages = new ArrayList<>();
        for (DeadLetterMessage message : messages) {
            if (!deduplicationEnabled && isDuplicate(message)) {
                log.warn("重复消息，跳过处理, messageId: {}", message.getMessageId());
                continue;
            }
            nonDuplicateMessages.add(message);
        }

        if (nonDuplicateMessages.isEmpty()) {
            return;
        }

        List<DeadLetterAnalysisResult> analysisResults = analysisService.analyzeBatch(nonDuplicateMessages);
        Map<String, DeadLetterAnalysisResult> resultMap = new HashMap<>();
        for (DeadLetterAnalysisResult result : analysisResults) {
            if (result.getMessageId() != null) {
                resultMap.put(result.getMessageId(), result);
            }
        }

        List<DeadLetterMessage> toSave = new ArrayList<>();
        for (DeadLetterMessage message : nonDuplicateMessages) {
            preprocess(message);
            DeadLetterAnalysisResult analysisResult = resultMap.get(message.getMessageId());
            enrichWithAnalysisResult(message, analysisResult);
            toSave.add(message);

            if (analysisResult != null) {
                alertService.checkAndTriggerAlert(message, analysisResult);
            }
        }

        deadLetterEsService.saveBatch(toSave);
        log.info("批量处理死信消息完成, 总数: {}, 处理成功: {}", messages.size(), toSave.size());
    }

    public void restartConsumer(String mqTypeStr) {
        MqTypeEnum mqType = MqTypeEnum.valueOf(mqTypeStr.toUpperCase());
        stopConsumer(mqType.name());

        String[] topicArray = StringUtils.hasText(topics) ? topics.split(",") : new String[0];
        startConsumer(mqType, topicArray);
    }

    public void stopConsumer(String consumerKey) {
        MessageConsumer consumer = consumerMap.remove(consumerKey);
        if (consumer != null) {
            try {
                consumer.stop();
                log.info("停止消费者成功, mqType: {}", consumerKey);
            } catch (Exception e) {
                log.error("停止消费者失败, mqType: {}", consumerKey, e);
            }
        }
    }

    public Map<String, Boolean> getConsumerStatus() {
        Map<String, Boolean> status = new HashMap<>();
        consumerMap.forEach((key, consumer) -> {
            status.put(key, true);
        });
        return status;
    }

    @PreDestroy
    public void stopAllConsumers() {
        log.info("开始停止所有死信消息消费者...");
        consumerMap.keySet().forEach(this::stopConsumer);
        log.info("所有死信消息消费者已停止");
    }
}
