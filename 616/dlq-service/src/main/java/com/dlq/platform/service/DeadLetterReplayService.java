package com.dlq.platform.service;

import co.elastic.clients.elasticsearch.ElasticsearchClient;
import com.dlq.platform.common.config.QueueImportanceConfig;
import com.dlq.platform.common.dto.ReplayRequest;
import com.dlq.platform.common.entity.DeadLetterMessage;
import com.dlq.platform.common.enums.ProcessStatusEnum;
import com.dlq.platform.es.config.ElasticsearchConfig;
import com.dlq.platform.es.service.DeadLetterEsService;
import com.dlq.platform.entity.ReplayRecord;
import com.dlq.platform.mq.factory.MessageProducerFactory;
import com.dlq.platform.mq.producer.MessageProducer;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;
import org.springframework.util.DigestUtils;
import org.springframework.util.StringUtils;

import java.nio.charset.StandardCharsets;
import java.time.LocalDateTime;
import java.util.*;
import java.util.concurrent.ConcurrentHashMap;
import java.util.stream.Collectors;

@Slf4j
@Service
@RequiredArgsConstructor
public class DeadLetterReplayService {

    private final DeadLetterEsService deadLetterEsService;
    private final MessageProducerFactory producerFactory;
    private final ElasticsearchClient esClient;
    private final ElasticsearchConfig esConfig;
    private final QueueImportanceConfig queueImportanceConfig;

    private final Map<String, ReplayExecution> inProgressReplays = new ConcurrentHashMap<>();

    public Map<String, Object> replaySingle(String messageId, ReplayRequest request) {
        Map<String, Object> result = new HashMap<>();

        try {
            DeadLetterMessage message = deadLetterEsService.findById(messageId);
            if (message == null) {
                result.put("success", false);
                result.put("message", "死信消息不存在, id: " + messageId);
                return result;
            }

            String topicOrQueue = message.getTopic() != null ? message.getTopic() : message.getQueueName();
            QueueImportanceConfig.QueueThreshold threshold = queueImportanceConfig.getQueueThreshold(topicOrQueue);

            if (!Boolean.TRUE.equals(threshold.getReplayEnabled())) {
                result.put("success", false);
                result.put("message", "队列[" + topicOrQueue + "]已禁用重放功能");
                result.put("importanceLevel", threshold.getImportanceLevel().name());
                return result;
            }

            if (!queueImportanceConfig.canRetry(topicOrQueue, getCurrentReplayCount(message))) {
                result.put("success", false);
                result.put("message", "已达到最大重放次数限制, 当前: " + getCurrentReplayCount(message)
                        + ", 最大: " + threshold.getMaxRetryCount());
                result.put("importanceLevel", threshold.getImportanceLevel().name());
                result.put("currentCount", getCurrentReplayCount(message));
                result.put("maxCount", threshold.getMaxRetryCount());
                return result;
            }

            int currentReplayCount = getCurrentReplayCount(message);
            String idempotencyKey = generateIdempotencyKey(message, request, currentReplayCount);

            if (inProgressReplays.containsKey(idempotencyKey)) {
                result.put("success", true);
                result.put("message", "重放正在进行中");
                result.put("idempotencyKey", idempotencyKey);
                result.put("replayCount", currentReplayCount);
                return result;
            }

            ReplayExecution execution = new ReplayExecution(idempotencyKey, LocalDateTime.now(), messageId);
            inProgressReplays.put(idempotencyKey, execution);

            try {
                String targetTopic = determineTargetTopic(message, request);
                String targetQueue = determineTargetQueue(message, request);

                boolean success = doReplay(message, targetTopic, targetQueue, idempotencyKey, currentReplayCount);

                saveReplayRecord(message, request, targetTopic, targetQueue, success, null, idempotencyKey, currentReplayCount);

                if (success) {
                    updateMessageAfterReplay(message, currentReplayCount + 1);
                    result.put("success", true);
                    result.put("message", "重放成功");
                    result.put("replayCount", currentReplayCount + 1);
                    result.put("idempotencyKey", idempotencyKey);
                } else {
                    handleReplayFailure(message, null, currentReplayCount);
                    result.put("success", false);
                    result.put("message", "重放失败");
                    result.put("replayCount", currentReplayCount);
                    result.put("idempotencyKey", idempotencyKey);
                }
            } finally {
                inProgressReplays.remove(idempotencyKey);
            }
        } catch (Exception e) {
            log.error("单条重放异常, messageId: {}", messageId, e);
            result.put("success", false);
            result.put("message", "重放异常: " + e.getMessage());
        }

        return result;
    }

    public Map<String, Object> replayBatch(ReplayRequest request) {
        Map<String, Object> result = new HashMap<>();

        try {
            List<String> messageIds = request.getMessageIds();
            if (messageIds == null || messageIds.isEmpty()) {
                result.put("success", false);
                result.put("message", "重放消息ID列表不能为空");
                return result;
            }

            List<DeadLetterMessage> messages = deadLetterEsService.findByIds(messageIds);
            if (messages.isEmpty()) {
                result.put("success", false);
                result.put("message", "未找到有效的死信消息");
                return result;
            }

            int successCount = 0;
            int failCount = 0;
            int skippedCount = 0;
            int disabledCount = 0;
            int limitExceededCount = 0;
            List<String> successIds = new ArrayList<>();
            List<String> failIds = new ArrayList<>();
            List<String> skippedIds = new ArrayList<>();
            List<String> disabledIds = new ArrayList<>();
            List<String> limitExceededIds = new ArrayList<>();
            List<Map<String, Object>> replayDetails = new ArrayList<>();

            for (DeadLetterMessage message : messages) {
                String topicOrQueue = message.getTopic() != null ? message.getTopic() : message.getQueueName();
                QueueImportanceConfig.QueueThreshold threshold = queueImportanceConfig.getQueueThreshold(topicOrQueue);

                int currentReplayCount = getCurrentReplayCount(message);
                String idempotencyKey = generateIdempotencyKey(message, request, currentReplayCount);

                Map<String, Object> detail = new HashMap<>();
                detail.put("messageId", message.getId());
                detail.put("originalMessageId", message.getMessageId());
                detail.put("idempotencyKey", idempotencyKey);
                detail.put("replayCount", currentReplayCount);
                detail.put("importanceLevel", threshold.getImportanceLevel().name());

                if (!Boolean.TRUE.equals(threshold.getReplayEnabled())) {
                    disabledCount++;
                    disabledIds.add(message.getId());
                    detail.put("status", "DISABLED");
                    detail.put("reason", "队列已禁用重放功能");
                    replayDetails.add(detail);
                    continue;
                }

                if (!queueImportanceConfig.canRetry(topicOrQueue, currentReplayCount)) {
                    limitExceededCount++;
                    limitExceededIds.add(message.getId());
                    detail.put("status", "LIMIT_EXCEEDED");
                    detail.put("reason", "已达到最大重放次数限制");
                    detail.put("maxRetryCount", threshold.getMaxRetryCount());
                    replayDetails.add(detail);
                    continue;
                }

                if (inProgressReplays.containsKey(idempotencyKey)) {
                    skippedCount++;
                    skippedIds.add(message.getId());
                    detail.put("status", "SKIPPED");
                    detail.put("reason", "重放正在进行中");
                    replayDetails.add(detail);
                    continue;
                }

                ReplayExecution execution = new ReplayExecution(idempotencyKey, LocalDateTime.now(), message.getId());
                inProgressReplays.put(idempotencyKey, execution);

                try {
                    String targetTopic = determineTargetTopic(message, request);
                    String targetQueue = determineTargetQueue(message, request);

                    boolean success = doReplay(message, targetTopic, targetQueue, idempotencyKey, currentReplayCount);
                    saveReplayRecord(message, request, targetTopic, targetQueue, success, null, idempotencyKey, currentReplayCount);

                    if (success) {
                        successCount++;
                        successIds.add(message.getId());
                        updateMessageAfterReplay(message, currentReplayCount + 1);
                        detail.put("status", "SUCCESS");
                        detail.put("replayCount", currentReplayCount + 1);
                    } else {
                        failCount++;
                        failIds.add(message.getId());
                        handleReplayFailure(message, null, currentReplayCount);
                        detail.put("status", "FAILED");
                    }
                } catch (Exception e) {
                    log.error("重放消息异常, messageId: {}", message.getId(), e);
                    failCount++;
                    failIds.add(message.getId());
                    saveReplayRecord(message, request, null, null, false, e.getMessage(), idempotencyKey, currentReplayCount);
                    handleReplayFailure(message, e, currentReplayCount);
                    detail.put("status", "FAILED");
                    detail.put("errorMessage", e.getMessage());
                } finally {
                    inProgressReplays.remove(idempotencyKey);
                }
                replayDetails.add(detail);
            }

            result.put("success", true);
            result.put("totalCount", messages.size());
            result.put("successCount", successCount);
            result.put("failCount", failCount);
            result.put("skippedCount", skippedCount);
            result.put("disabledCount", disabledCount);
            result.put("limitExceededCount", limitExceededCount);
            result.put("successIds", successIds);
            result.put("failIds", failIds);
            result.put("skippedIds", skippedIds);
            result.put("disabledIds", disabledIds);
            result.put("limitExceededIds", limitExceededIds);
            result.put("replayDetails", replayDetails);

            log.info("批量重放完成, 总数: {}, 成功: {}, 失败: {}, 跳过: {}, 禁用: {}, 超限: {}",
                    messages.size(), successCount, failCount, skippedCount, disabledCount, limitExceededCount);
        } catch (Exception e) {
            log.error("批量重放异常", e);
            result.put("success", false);
            result.put("message", "批量重放异常: " + e.getMessage());
        }

        return result;
    }

    public Map<String, Object> replayByCondition(ReplayRequest request) {
        Map<String, Object> result = new HashMap<>();

        try {
            List<DeadLetterMessage> messages = findMessagesByCondition(request);
            if (messages.isEmpty()) {
                result.put("success", true);
                result.put("message", "没有符合条件的死信消息");
                result.put("totalCount", 0);
                return result;
            }

            request.setMessageIds(messages.stream().map(DeadLetterMessage::getId).collect(Collectors.toList()));
            return replayBatch(request);
        } catch (Exception e) {
            log.error("按条件重放异常", e);
            result.put("success", false);
            result.put("message", "按条件重放异常: " + e.getMessage());
        }

        return result;
    }

    private boolean doReplay(DeadLetterMessage message, String targetTopic, String targetQueue,
                             String idempotencyKey, int replayCount) {
        try {
            MessageProducer producer = producerFactory.createProducer(message.getMqType());
            producer.start();

            Map<String, Object> replayMessage = buildReplayMessage(message, idempotencyKey, replayCount);
            producer.send(targetTopic, replayMessage);

            producer.stop();
            log.info("重放消息成功, messageId: {}, topic: {}, replayCount: {}, idempotencyKey: {}",
                    message.getMessageId(), targetTopic, replayCount, idempotencyKey);
            return true;
        } catch (Exception e) {
            log.error("重放消息失败, messageId: {}, topic: {}, replayCount: {}",
                    message.getMessageId(), targetTopic, replayCount, e);
            return false;
        }
    }

    private Map<String, Object> buildReplayMessage(DeadLetterMessage message, String idempotencyKey, int replayCount) {
        Map<String, Object> replayMessage = new HashMap<>();
        replayMessage.put("messageId", message.getMessageId());
        replayMessage.put("body", message.getMessageBody());
        replayMessage.put("originalMessageId", message.getId());
        replayMessage.put("replayTime", LocalDateTime.now().toString());
        replayMessage.put("replayCount", replayCount);
        replayMessage.put("idempotencyKey", idempotencyKey);
        replayMessage.put("isReplay", true);

        if (message.getHeaders() != null) {
            replayMessage.putAll(message.getHeaders());
        }

        return replayMessage;
    }

    private int getCurrentReplayCount(DeadLetterMessage message) {
        return message.getRetryCount() != null ? message.getRetryCount() : 0;
    }

    private String generateIdempotencyKey(DeadLetterMessage message, ReplayRequest request, int replayCount) {
        StringBuilder sb = new StringBuilder();
        sb.append(message.getId()).append("_");
        sb.append(message.getMessageId()).append("_");
        sb.append(replayCount).append("_");
        if (request != null && request.getTargetTopic() != null) {
            sb.append(request.getTargetTopic()).append("_");
        }
        if (request != null && request.getOperator() != null) {
            sb.append(request.getOperator());
        }
        return DigestUtils.md5DigestAsHex(sb.toString().getBytes(StandardCharsets.UTF_8));
    }

    private void updateMessageAfterReplay(DeadLetterMessage message, int newReplayCount) {
        try {
            message.setRetryCount(newReplayCount);
            message.setUpdateTime(LocalDateTime.now());
            if (message.getProcessStatus() == ProcessStatusEnum.PENDING
                    || message.getProcessStatus() == ProcessStatusEnum.REPLAYED) {
                message.setProcessStatus(ProcessStatusEnum.REPLAYED);
            }
            deadLetterEsService.save(message);
        } catch (Exception e) {
            log.error("更新消息重放状态失败, messageId: {}", message.getId(), e);
        }
    }

    private String determineTargetTopic(DeadLetterMessage message, ReplayRequest request) {
        if (request != null && Boolean.TRUE.equals(request.getUseOriginalDestination())
                && StringUtils.hasText(message.getOriginalTopic())) {
            return message.getOriginalTopic();
        }
        if (request != null && StringUtils.hasText(request.getTargetTopic())) {
            return request.getTargetTopic();
        }
        if (StringUtils.hasText(message.getOriginalTopic())) {
            return message.getOriginalTopic();
        }
        return message.getTopic();
    }

    private String determineTargetQueue(DeadLetterMessage message, ReplayRequest request) {
        if (request != null && Boolean.TRUE.equals(request.getUseOriginalDestination())
                && StringUtils.hasText(message.getOriginalQueue())) {
            return message.getOriginalQueue();
        }
        if (request != null && StringUtils.hasText(request.getTargetQueue())) {
            return request.getTargetQueue();
        }
        if (StringUtils.hasText(message.getOriginalQueue())) {
            return message.getOriginalQueue();
        }
        return message.getQueueName();
    }

    private void handleReplayFailure(DeadLetterMessage message, Exception e, int replayCount) {
        try {
            message.setRetryCount(replayCount);
            message.setUpdateTime(LocalDateTime.now());

            if (e != null) {
                String errorMsg = e.getMessage();
                String replayErrorMsg = String.format("[第%d次重放失败] %s", replayCount + 1, errorMsg);
                message.setDeadReason(message.getDeadReason() != null
                        ? message.getDeadReason() + "; " + replayErrorMsg
                        : replayErrorMsg);
            }

            deadLetterEsService.save(message);
            log.warn("重放失败消息重新入队, messageId: {}, retryCount: {}", message.getMessageId(), replayCount);
        } catch (Exception ex) {
            log.error("处理重放失败异常, messageId: {}", message.getId(), ex);
        }
    }

    private void saveReplayRecord(DeadLetterMessage message, ReplayRequest request,
                                   String targetTopic, String targetQueue, boolean success, String errorMessage,
                                   String idempotencyKey, int replayCount) {
        try {
            ReplayRecord record = ReplayRecord.builder()
                    .id(UUID.randomUUID().toString().replace("-", ""))
                    .messageId(message.getId())
                    .mqType(message.getMqType() != null ? message.getMqType().name() : null)
                    .targetTopic(targetTopic)
                    .targetQueue(targetQueue)
                    .useOriginalDestination(request != null ? request.getUseOriginalDestination() : null)
                    .operator(request != null ? request.getOperator() : null)
                    .remark(request != null ? request.getRemark() : null)
                    .retryCount(replayCount)
                    .success(success)
                    .errorMessage(errorMessage)
                    .replayTime(LocalDateTime.now())
                    .createTime(LocalDateTime.now())
                    .idempotencyKey(idempotencyKey)
                    .build();

            esClient.index(i -> i
                    .index(esConfig.getReplayRecordIndex())
                    .id(record.getId())
                    .document(record));
        } catch (Exception e) {
            log.error("保存重放记录失败, messageId: {}", message.getId(), e);
        }
    }

    public static class ReplayExecution {
        private final String idempotencyKey;
        private final LocalDateTime startTime;
        private final String messageId;

        public ReplayExecution(String idempotencyKey, LocalDateTime startTime, String messageId) {
            this.idempotencyKey = idempotencyKey;
            this.startTime = startTime;
            this.messageId = messageId;
        }

        public String getIdempotencyKey() { return idempotencyKey; }
        public LocalDateTime getStartTime() { return startTime; }
        public String getMessageId() { return messageId; }
    }

    public Map<String, Object> getReplayStatus(String idempotencyKey) {
        Map<String, Object> result = new HashMap<>();
        ReplayExecution execution = inProgressReplays.get(idempotencyKey);
        if (execution != null) {
            result.put("exists", true);
            result.put("messageId", execution.getMessageId());
            result.put("startTime", execution.getStartTime());
            result.put("status", "IN_PROGRESS");
        } else {
            result.put("exists", false);
            result.put("status", "NOT_FOUND");
        }
        return result;
    }

    public Map<String, Object> getReplayRecords(String messageId, int pageNum, int pageSize) {
        try {
            int from = (pageNum - 1) * pageSize;

            var response = esClient.search(s -> {
                s.index(esConfig.getReplayRecordIndex())
                        .from(from)
                        .size(pageSize)
                        .sort(so -> so.field(f -> f.field("replayTime").order(co.elastic.clients.elasticsearch._types.SortOrder.Desc)));

                if (StringUtils.hasText(messageId)) {
                    s.query(q -> q
                            .term(t -> t
                                    .field("messageId.keyword")
                                    .value(messageId)));
                }
                return s;
            }, ReplayRecord.class);

            List<ReplayRecord> list = response.hits().hits().stream()
                    .map(hit -> hit.source())
                    .filter(Objects::nonNull)
                    .collect(Collectors.toList());

            Map<String, Object> result = new HashMap<>();
            result.put("total", response.hits().total() != null ? response.hits().total().value() : 0);
            result.put("list", list);
            result.put("pageNum", pageNum);
            result.put("pageSize", pageSize);
            return result;
        } catch (Exception e) {
            log.error("查询重放记录失败", e);
            throw new RuntimeException("查询重放记录失败", e);
        }
    }

    private List<DeadLetterMessage> findMessagesByCondition(ReplayRequest request) {
        com.dlq.platform.common.dto.DeadLetterQueryDTO queryDTO = new com.dlq.platform.common.dto.DeadLetterQueryDTO();
        queryDTO.setMqType(request.getMqType());
        queryDTO.setProcessStatus(ProcessStatusEnum.PENDING);
        queryDTO.setPageSize(10000);

        return deadLetterEsService.queryForList(queryDTO);
    }
}
