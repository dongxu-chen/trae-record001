package com.pushcenter.service;

import com.pushcenter.disruptor.MessageEventProducer;
import com.pushcenter.enums.MessageStatus;
import com.pushcenter.model.PushMessage;
import com.pushcenter.model.PushResult;
import com.pushcenter.model.RetryState;
import lombok.extern.slf4j.Slf4j;
import org.springframework.data.redis.core.RedisTemplate;
import org.springframework.scheduling.annotation.Scheduled;
import org.springframework.stereotype.Service;

import javax.annotation.Resource;
import java.util.*;
import java.util.concurrent.TimeUnit;

@Slf4j
@Service
public class RetryService {

    @Resource
    private RedisTemplate<String, Object> redisTemplate;

    @Resource
    private MessageEventProducer messageEventProducer;

    private static final String RETRY_ZSET_KEY = "push_center:retry_queue";
    private static final String RETRY_STATE_PREFIX = "push_center:retry_state:";
    private static final String RETRY_HISTORY_PREFIX = "push_center:retry_history:";
    private static final String RETRY_STATS_KEY = "push_center:retry_stats";

    private static final long INITIAL_RETRY_DELAY_MS = 1000;
    private static final long MAX_RETRY_DELAY_MS = 60000;
    private static final long RETRY_STATE_TTL_HOURS = 24;

    public void scheduleRetry(PushMessage message, PushResult result) {
        int currentRetryCount = message.getRetryCount() + 1;

        if (currentRetryCount > message.getMaxRetryCount()) {
            log.warn("Message {} exceeded max retry count {}/{}, moving to dead letter",
                    message.getMessageId(), currentRetryCount, message.getMaxRetryCount());
            moveToDeadLetter(message, result);
            return;
        }

        long delay = calculateDelay(currentRetryCount);
        long retryTime = System.currentTimeMillis() + delay;

        RetryState retryState = RetryState.builder()
                .messageId(message.getMessageId())
                .userId(message.getUserId())
                .templateCode(message.getTemplateCode())
                .variables(message.getVariables())
                .title(message.getTitle())
                .content(message.getContent())
                .channel(message.getChannel())
                .receiver(message.getReceiver())
                .currentRetryCount(currentRetryCount)
                .maxRetryCount(message.getMaxRetryCount())
                .nextRetryTime(retryTime)
                .firstFailTime(message.getRetryCount() == 0 ? System.currentTimeMillis() : getFirstFailTime(message.getMessageId()))
                .lastFailTime(System.currentTimeMillis())
                .lastErrorMessage(result.getErrorMessage())
                .status(MessageStatus.RETRYING)
                .build();

        saveRetryState(retryState);

        redisTemplate.opsForZSet().add(RETRY_ZSET_KEY, message.getMessageId(), retryTime);

        recordRetryHistory(message.getMessageId(), currentRetryCount, result.getErrorMessage());

        incrementRetryStats();

        log.info("Scheduled retry for message {} at {}, attempt {}/{}, delay: {}ms",
                message.getMessageId(), retryTime, currentRetryCount, message.getMaxRetryCount(), delay);
    }

    private long getFirstFailTime(String messageId) {
        RetryState existing = getRetryState(messageId);
        return existing != null ? existing.getFirstFailTime() : System.currentTimeMillis();
    }

    private long calculateDelay(int retryCount) {
        long delay = INITIAL_RETRY_DELAY_MS * (long) Math.pow(2, retryCount - 1);
        return Math.min(delay, MAX_RETRY_DELAY_MS);
    }

    private void saveRetryState(RetryState retryState) {
        String key = RETRY_STATE_PREFIX + retryState.getMessageId();
        redisTemplate.opsForValue().set(key, retryState, RETRY_STATE_TTL_HOURS, TimeUnit.HOURS);
    }

    public RetryState getRetryState(String messageId) {
        String key = RETRY_STATE_PREFIX + messageId;
        Object obj = redisTemplate.opsForValue().get(key);
        return obj instanceof RetryState ? (RetryState) obj : null;
    }

    private void recordRetryHistory(String messageId, int retryCount, String errorMessage) {
        String key = RETRY_HISTORY_PREFIX + messageId;
        Map<String, Object> historyEntry = new HashMap<>();
        historyEntry.put("retryCount", retryCount);
        historyEntry.put("timestamp", System.currentTimeMillis());
        historyEntry.put("errorMessage", errorMessage);
        redisTemplate.opsForList().rightPush(key, historyEntry);
        redisTemplate.expire(key, RETRY_STATE_TTL_HOURS, TimeUnit.HOURS);
    }

    public List<Object> getRetryHistory(String messageId) {
        String key = RETRY_HISTORY_PREFIX + messageId;
        return redisTemplate.opsForList().range(key, 0, -1);
    }

    private void incrementRetryStats() {
        redisTemplate.opsForValue().increment(RETRY_STATS_KEY + ":total", 1);
    }

    @Scheduled(fixedDelay = 100)
    public void processRetryQueue() {
        long now = System.currentTimeMillis();
        long maxScore = now;

        Set<Object> messageIds = redisTemplate.opsForZSet().rangeByScore(RETRY_ZSET_KEY, 0, maxScore, 0, 100);

        if (messageIds == null || messageIds.isEmpty()) {
            return;
        }

        for (Object idObj : messageIds) {
            String messageId = (String) idObj;

            Long removed = redisTemplate.opsForZSet().remove(RETRY_ZSET_KEY, messageId);
            if (removed == null || removed == 0) {
                continue;
            }

            RetryState retryState = getRetryState(messageId);
            if (retryState == null) {
                log.warn("Retry state not found for message: {}", messageId);
                continue;
            }

            PushMessage message = buildMessageFromState(retryState);
            messageEventProducer.onData(message);

            log.info("Retrying message {}, attempt {}", messageId, retryState.getCurrentRetryCount());
        }
    }

    private PushMessage buildMessageFromState(RetryState retryState) {
        return PushMessage.builder()
                .messageId(retryState.getMessageId())
                .userId(retryState.getUserId())
                .templateCode(retryState.getTemplateCode())
                .variables(retryState.getVariables())
                .title(retryState.getTitle())
                .content(retryState.getContent())
                .channel(retryState.getChannel())
                .receiver(retryState.getReceiver())
                .status(MessageStatus.PENDING)
                .retryCount(retryState.getCurrentRetryCount())
                .maxRetryCount(retryState.getMaxRetryCount())
                .nextRetryTime(retryState.getNextRetryTime())
                .createTime(retryState.getFirstFailTime())
                .build();
    }

    private void moveToDeadLetter(PushMessage message, PushResult result) {
        String deadLetterKey = "push_center:dead_letter:" + message.getMessageId();
        Map<String, Object> deadLetter = new HashMap<>();
        deadLetter.put("messageId", message.getMessageId());
        deadLetter.put("userId", message.getUserId());
        deadLetter.put("channel", message.getChannel());
        deadLetter.put("title", message.getTitle());
        deadLetter.put("content", message.getContent());
        deadLetter.put("receiver", message.getReceiver());
        deadLetter.put("finalError", result.getErrorMessage());
        deadLetter.put("timestamp", System.currentTimeMillis());
        deadLetter.put("retryCount", message.getRetryCount());

        redisTemplate.opsForValue().set(deadLetterKey, deadLetter, 7, TimeUnit.DAYS);
        redisTemplate.opsForValue().increment(RETRY_STATS_KEY + ":failed", 1);

        deleteRetryState(message.getMessageId());
    }

    public void deleteRetryState(String messageId) {
        redisTemplate.delete(RETRY_STATE_PREFIX + messageId);
        redisTemplate.delete(RETRY_HISTORY_PREFIX + messageId);
        redisTemplate.opsForZSet().remove(RETRY_ZSET_KEY, messageId);
    }

    public long getPendingRetryCount() {
        Long count = redisTemplate.opsForZSet().size(RETRY_ZSET_KEY);
        return count != null ? count : 0;
    }

    public Map<String, Object> getRetryStatistics() {
        Map<String, Object> stats = new HashMap<>();

        Long totalRetries = redisTemplate.opsForValue().get(RETRY_STATS_KEY + ":total");
        Long totalFailed = redisTemplate.opsForValue().get(RETRY_STATS_KEY + ":failed");

        stats.put("pendingRetryCount", getPendingRetryCount());
        stats.put("totalRetries", totalRetries != null ? totalRetries : 0);
        stats.put("totalPermanentFailures", totalFailed != null ? totalFailed : 0);

        return stats;
    }

    public List<Map<String, Object>> getPendingRetries(int page, int size) {
        long start = (long) (page - 1) * size;
        long end = start + size - 1;

        Set<Object> messageIds = redisTemplate.opsForZSet().range(RETRY_ZSET_KEY, start, end);
        List<Map<String, Object>> result = new ArrayList<>();

        if (messageIds != null) {
            for (Object idObj : messageIds) {
                String messageId = (String) idObj;
                RetryState state = getRetryState(messageId);
                if (state != null) {
                    Map<String, Object> info = new HashMap<>();
                    info.put("messageId", state.getMessageId());
                    info.put("userId", state.getUserId());
                    info.put("channel", state.getChannel());
                    info.put("currentRetryCount", state.getCurrentRetryCount());
                    info.put("maxRetryCount", state.getMaxRetryCount());
                    info.put("nextRetryTime", state.getNextRetryTime());
                    info.put("lastErrorMessage", state.getLastErrorMessage());
                    result.add(info);
                }
            }
        }

        return result;
    }
}
