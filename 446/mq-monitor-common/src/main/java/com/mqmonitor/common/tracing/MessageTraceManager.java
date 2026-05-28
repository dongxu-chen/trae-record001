package com.mqmonitor.common.tracing;

import com.mqmonitor.common.enums.MQType;
import com.mqmonitor.common.model.MessageTrace;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.util.*;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.atomic.AtomicLong;
import java.util.stream.Collectors;

public class MessageTraceManager {
    private static final Logger logger = LoggerFactory.getLogger(MessageTraceManager.class);

    private static final long DEFAULT_TRACE_TTL_MS = TimeUnit.HOURS.toMillis(24);
    private static final int DEFAULT_MAX_TRACES = 100000;
    private static final double DEFAULT_SAMPLE_RATE = 0.01;

    private final Map<String, MessageTrace> activeTraces = new ConcurrentHashMap<>();
    private final Map<String, MessageTrace> completedTraces = new ConcurrentHashMap<>();
    private final AtomicLong traceCounter = new AtomicLong(0);
    private final AtomicLong sampledCounter = new AtomicLong(0);

    private long traceTtlMs = DEFAULT_TRACE_TTL_MS;
    private int maxTraces = DEFAULT_MAX_TRACES;
    private double sampleRate = DEFAULT_SAMPLE_RATE;
    private boolean enabled = true;

    private static volatile MessageTraceManager instance;

    public static MessageTraceManager getInstance() {
        if (instance == null) {
            synchronized (MessageTraceManager.class) {
                if (instance == null) {
                    instance = new MessageTraceManager();
                }
            }
        }
        return instance;
    }

    private MessageTraceManager() {
        startCleanupThread();
    }

    public boolean shouldSample() {
        if (!enabled || sampleRate >= 1.0) {
            return enabled;
        }
        if (sampleRate <= 0) {
            return false;
        }
        return Math.random() < sampleRate;
    }

    public MessageTrace createTrace(MQType mqType, String clusterName, String topic,
                                    String messageId, String messageKey) {
        return createTrace(mqType, clusterName, topic, null, messageId, messageKey);
    }

    public MessageTrace createTrace(MQType mqType, String clusterName, String topic,
                                    String consumerGroup, String messageId, String messageKey) {
        if (!enabled) {
            return null;
        }

        boolean sampled = shouldSample();
        if (!sampled) {
            return null;
        }

        MessageTrace trace = new MessageTrace();
        trace.setMqType(mqType);
        trace.setClusterName(clusterName);
        trace.setTopic(topic);
        trace.setConsumerGroup(consumerGroup);
        trace.setMessageId(messageId);
        trace.setMessageKey(messageKey);
        trace.setSampled(true);

        activeTraces.put(trace.getTraceId(), trace);
        traceCounter.incrementAndGet();
        sampledCounter.incrementAndGet();

        enforceLimits();

        return trace;
    }

    public void recordProducerSent(String traceId) {
        MessageTrace trace = activeTraces.get(traceId);
        if (trace != null) {
            trace.addEvent(MessageTrace.TraceStage.PRODUCER_SENT);
        }
    }

    public void recordBrokerReceived(String traceId) {
        MessageTrace trace = activeTraces.get(traceId);
        if (trace != null) {
            trace.addEvent(MessageTrace.TraceStage.BROKER_RECEIVED);
        }
    }

    public void recordConsumerReceived(String traceId, String consumerGroup) {
        MessageTrace trace = activeTraces.get(traceId);
        if (trace != null) {
            trace.setConsumerGroup(consumerGroup);
            trace.addEvent(MessageTrace.TraceStage.CONSUMER_RECEIVED);
        }
    }

    public void recordConsumerProcessing(String traceId) {
        MessageTrace trace = activeTraces.get(traceId);
        if (trace != null) {
            trace.addEvent(MessageTrace.TraceStage.CONSUMER_PROCESSING);
        }
    }

    public void recordConsumerAcked(String traceId) {
        MessageTrace trace = activeTraces.get(traceId);
        if (trace != null) {
            trace.addEvent(MessageTrace.TraceStage.CONSUMER_ACKED);
            trace.addEvent(MessageTrace.TraceStage.COMPLETED);
            moveToCompleted(trace);
        }
    }

    public void recordConsumerFailed(String traceId, String errorMessage, String errorStack) {
        MessageTrace trace = activeTraces.get(traceId);
        if (trace != null) {
            trace.setErrorMessage(errorMessage);
            trace.setErrorStack(errorStack);
            trace.addEvent(MessageTrace.TraceStage.CONSUMER_FAILED);
            moveToCompleted(trace);
        }
    }

    public void recordDlq(String traceId) {
        MessageTrace trace = activeTraces.get(traceId);
        if (trace != null) {
            trace.addEvent(MessageTrace.TraceStage.DLQ);
            moveToCompleted(trace);
        }
    }

    public void updateTraceMessageType(String traceId, String messageType) {
        MessageTrace trace = activeTraces.get(traceId);
        if (trace != null) {
            trace.setMessageType(messageType);
        } else {
            trace = completedTraces.get(traceId);
            if (trace != null) {
                trace.setMessageType(messageType);
            }
        }
    }

    public void updateTraceHeaders(String traceId, Map<String, String> headers) {
        MessageTrace trace = activeTraces.get(traceId);
        if (trace != null) {
            trace.getHeaders().putAll(headers);
        }
    }

    public void incrementRetryCount(String traceId) {
        MessageTrace trace = activeTraces.get(traceId);
        if (trace != null) {
            trace.setRetryCount(trace.getRetryCount() + 1);
        }
    }

    private void moveToCompleted(MessageTrace trace) {
        activeTraces.remove(trace.getTraceId());
        completedTraces.put(trace.getTraceId(), trace);
    }

    public MessageTrace getTrace(String traceId) {
        MessageTrace trace = activeTraces.get(traceId);
        if (trace != null) {
            return trace;
        }
        return completedTraces.get(traceId);
    }

    public List<MessageTrace> getTracesByTopic(String topic, int limit) {
        return completedTraces.values().stream()
                .filter(t -> topic.equals(t.getTopic()))
                .sorted((a, b) -> Long.compare(b.getProduceSendTime(), a.getProduceSendTime()))
                .limit(limit)
                .collect(Collectors.toList());
    }

    public List<MessageTrace> getTracesByConsumerGroup(String consumerGroup, int limit) {
        return completedTraces.values().stream()
                .filter(t -> consumerGroup.equals(t.getConsumerGroup()))
                .sorted((a, b) -> Long.compare(b.getProduceSendTime(), a.getProduceSendTime()))
                .limit(limit)
                .collect(Collectors.toList());
    }

    public List<MessageTrace> getSlowTraces(long minLatencyMs, int limit) {
        return completedTraces.values().stream()
                .filter(t -> t.getEndToEndLatencyMs() >= minLatencyMs)
                .sorted((a, b) -> Long.compare(b.getEndToEndLatencyMs(), a.getEndToEndLatencyMs()))
                .limit(limit)
                .collect(Collectors.toList());
    }

    public List<MessageTrace> getFailedTraces(int limit) {
        return completedTraces.values().stream()
                .filter(t -> !t.isSuccess())
                .sorted((a, b) -> Long.compare(b.getConsumerAckTime(), a.getConsumerAckTime()))
                .limit(limit)
                .collect(Collectors.toList());
    }

    public List<MessageTrace> getActiveTraces() {
        return new ArrayList<>(activeTraces.values());
    }

    public List<MessageTrace> getActiveTracesOlderThan(long ageMs) {
        long cutoff = System.currentTimeMillis() - ageMs;
        return activeTraces.values().stream()
                .filter(t -> t.getProduceSendTime() < cutoff)
                .collect(Collectors.toList());
    }

    private void enforceLimits() {
        if (activeTraces.size() > maxTraces) {
            logger.warn("Active traces limit exceeded: {}, removing oldest", activeTraces.size());
            List<Map.Entry<String, MessageTrace>> sorted = new ArrayList<>(activeTraces.entrySet());
            sorted.sort(Comparator.comparingLong(e -> e.getValue().getProduceSendTime()));
            int toRemove = activeTraces.size() - maxTraces + maxTraces / 10;
            for (int i = 0; i < toRemove && i < sorted.size(); i++) {
                activeTraces.remove(sorted.get(i).getKey());
            }
        }

        if (completedTraces.size() > maxTraces * 2) {
            logger.warn("Completed traces limit exceeded: {}, removing oldest", completedTraces.size());
            List<Map.Entry<String, MessageTrace>> sorted = new ArrayList<>(completedTraces.entrySet());
            sorted.sort(Comparator.comparingLong(e -> e.getValue().getProduceSendTime()));
            int toRemove = completedTraces.size() - maxTraces * 2 + maxTraces / 5;
            for (int i = 0; i < toRemove && i < sorted.size(); i++) {
                completedTraces.remove(sorted.get(i).getKey());
            }
        }
    }

    private void startCleanupThread() {
        Thread cleanupThread = new Thread(() -> {
            while (!Thread.currentThread().isInterrupted()) {
                try {
                    Thread.sleep(TimeUnit.MINUTES.toMillis(5));
                    cleanupExpiredTraces();
                } catch (InterruptedException e) {
                    Thread.currentThread().interrupt();
                    break;
                } catch (Exception e) {
                    logger.error("Error in trace cleanup thread", e);
                }
            }
        }, "message-trace-cleanup");
        cleanupThread.setDaemon(true);
        cleanupThread.start();
    }

    private void cleanupExpiredTraces() {
        long cutoff = System.currentTimeMillis() - traceTtlMs;

        completedTraces.entrySet().removeIf(entry ->
                entry.getValue().getProduceSendTime() < cutoff
        );

        List<MessageTrace> staleActive = getActiveTracesOlderThan(traceTtlMs);
        for (MessageTrace trace : staleActive) {
            trace.addEvent(MessageTrace.TraceStage.TIMEOUT);
            moveToCompleted(trace);
            logger.debug("Trace timed out: {}", trace.getTraceId());
        }
    }

    public Map<String, Object> getStats() {
        Map<String, Object> stats = new LinkedHashMap<>();
        stats.put("activeTraces", activeTraces.size());
        stats.put("completedTraces", completedTraces.size());
        stats.put("totalTraces", traceCounter.get());
        stats.put("sampledTraces", sampledCounter.get());
        stats.put("sampleRate", sampleRate);
        stats.put("enabled", enabled);

        double avgLatency = completedTraces.values().stream()
                .mapToLong(MessageTrace::getEndToEndLatencyMs)
                .average()
                .orElse(0);
        stats.put("averageEndToEndLatencyMs", avgLatency);

        long successCount = completedTraces.values().stream()
                .filter(MessageTrace::isSuccess)
                .count();
        stats.put("successCount", successCount);
        stats.put("failureCount", completedTraces.size() - successCount);
        stats.put("successRate", completedTraces.isEmpty() ? 1.0 :
                (double) successCount / completedTraces.size());

        return stats;
    }

    public void setTraceTtlMs(long traceTtlMs) {
        this.traceTtlMs = traceTtlMs;
    }

    public void setMaxTraces(int maxTraces) {
        this.maxTraces = maxTraces;
    }

    public void setSampleRate(double sampleRate) {
        this.sampleRate = sampleRate;
    }

    public void setEnabled(boolean enabled) {
        this.enabled = enabled;
    }

    public boolean isEnabled() {
        return enabled;
    }

    public void clearAll() {
        activeTraces.clear();
        completedTraces.clear();
    }
}
