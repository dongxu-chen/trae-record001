package com.mqmonitor.common.model;

import com.mqmonitor.common.enums.MQType;

import java.time.Instant;
import java.util.ArrayList;
import java.util.List;
import java.util.Map;
import java.util.UUID;
import java.util.concurrent.ConcurrentHashMap;

public class MessageTrace {
    public enum TraceStage {
        PRODUCER_SENT,
        BROKER_RECEIVED,
        BROKER_STORED,
        CONSUMER_RECEIVED,
        CONSUMER_PROCESSING,
        CONSUMER_ACKED,
        CONSUMER_FAILED,
        COMPLETED,
        TIMEOUT,
        DLQ
    }

    private String traceId;
    private String messageId;
    private MQType mqType;
    private String clusterName;
    private String topic;
    private String consumerGroup;
    private String messageKey;
    private int messageSize;
    private String messageType;
    private Map<String, String> headers = new ConcurrentHashMap<>();
    private List<TraceEvent> events = new ArrayList<>();
    private long produceSendTime;
    private long brokerReceiveTime;
    private long consumerReceiveTime;
    private long consumerAckTime;
    private long endToEndLatencyMs;
    private long processingLatencyMs;
    private long queueLatencyMs;
    private boolean success;
    private String errorMessage;
    private String errorStack;
    private int retryCount;
    private boolean sampled;

    public MessageTrace() {
        this.traceId = UUID.randomUUID().toString();
    }

    public static class TraceEvent {
        private TraceStage stage;
        private long timestamp;
        private String serviceName;
        private String instanceId;
        private long durationMs;
        private Map<String, Object> attributes;

        public TraceEvent(TraceStage stage, long timestamp) {
            this.stage = stage;
            this.timestamp = timestamp;
        }

        public TraceStage getStage() { return stage; }
        public void setStage(TraceStage stage) { this.stage = stage; }
        public long getTimestamp() { return timestamp; }
        public void setTimestamp(long timestamp) { this.timestamp = timestamp; }
        public String getServiceName() { return serviceName; }
        public void setServiceName(String serviceName) { this.serviceName = serviceName; }
        public String getInstanceId() { return instanceId; }
        public void setInstanceId(String instanceId) { this.instanceId = instanceId; }
        public long getDurationMs() { return durationMs; }
        public void setDurationMs(long durationMs) { this.durationMs = durationMs; }
        public Map<String, Object> getAttributes() { return attributes; }
        public void setAttributes(Map<String, Object> attributes) { this.attributes = attributes; }
    }

    public void addEvent(TraceStage stage) {
        addEvent(stage, System.currentTimeMillis(), null);
    }

    public void addEvent(TraceStage stage, long timestamp, String serviceName) {
        TraceEvent event = new TraceEvent(stage, timestamp);
        event.setServiceName(serviceName);
        if (!events.isEmpty()) {
            TraceEvent lastEvent = events.get(events.size() - 1);
            event.setDurationMs(timestamp - lastEvent.getTimestamp());
        }
        events.add(event);
        updateLatencyMetrics(stage, timestamp);
    }

    private void updateLatencyMetrics(TraceStage stage, long timestamp) {
        switch (stage) {
            case PRODUCER_SENT:
                this.produceSendTime = timestamp;
                break;
            case BROKER_RECEIVED:
                this.brokerReceiveTime = timestamp;
                break;
            case CONSUMER_RECEIVED:
                this.consumerReceiveTime = timestamp;
                if (produceSendTime > 0) {
                    this.queueLatencyMs = timestamp - produceSendTime;
                }
                break;
            case CONSUMER_ACKED:
            case CONSUMER_FAILED:
            case COMPLETED:
                this.consumerAckTime = timestamp;
                if (consumerReceiveTime > 0) {
                    this.processingLatencyMs = timestamp - consumerReceiveTime;
                }
                if (produceSendTime > 0) {
                    this.endToEndLatencyMs = timestamp - produceSendTime;
                }
                this.success = stage == TraceStage.CONSUMER_ACKED || stage == TraceStage.COMPLETED;
                break;
        }
    }

    public boolean isComplete() {
        TraceStage lastStage = events.isEmpty() ? null : events.get(events.size() - 1).getStage();
        return lastStage == TraceStage.CONSUMER_ACKED
                || lastStage == TraceStage.COMPLETED
                || lastStage == TraceStage.CONSUMER_FAILED
                || lastStage == TraceStage.DLQ
                || lastStage == TraceStage.TIMEOUT;
    }

    public long getCurrentLatency() {
        if (endToEndLatencyMs > 0) {
            return endToEndLatencyMs;
        }
        return System.currentTimeMillis() - produceSendTime;
    }

    public String getTraceId() { return traceId; }
    public void setTraceId(String traceId) { this.traceId = traceId; }
    public String getMessageId() { return messageId; }
    public void setMessageId(String messageId) { this.messageId = messageId; }
    public MQType getMqType() { return mqType; }
    public void setMqType(MQType mqType) { this.mqType = mqType; }
    public String getClusterName() { return clusterName; }
    public void setClusterName(String clusterName) { this.clusterName = clusterName; }
    public String getTopic() { return topic; }
    public void setTopic(String topic) { this.topic = topic; }
    public String getConsumerGroup() { return consumerGroup; }
    public void setConsumerGroup(String consumerGroup) { this.consumerGroup = consumerGroup; }
    public String getMessageKey() { return messageKey; }
    public void setMessageKey(String messageKey) { this.messageKey = messageKey; }
    public int getMessageSize() { return messageSize; }
    public void setMessageSize(int messageSize) { this.messageSize = messageSize; }
    public String getMessageType() { return messageType; }
    public void setMessageType(String messageType) { this.messageType = messageType; }
    public Map<String, String> getHeaders() { return headers; }
    public void setHeaders(Map<String, String> headers) { this.headers = headers; }
    public List<TraceEvent> getEvents() { return events; }
    public void setEvents(List<TraceEvent> events) { this.events = events; }
    public long getProduceSendTime() { return produceSendTime; }
    public void setProduceSendTime(long produceSendTime) { this.produceSendTime = produceSendTime; }
    public long getBrokerReceiveTime() { return brokerReceiveTime; }
    public void setBrokerReceiveTime(long brokerReceiveTime) { this.brokerReceiveTime = brokerReceiveTime; }
    public long getConsumerReceiveTime() { return consumerReceiveTime; }
    public void setConsumerReceiveTime(long consumerReceiveTime) { this.consumerReceiveTime = consumerReceiveTime; }
    public long getConsumerAckTime() { return consumerAckTime; }
    public void setConsumerAckTime(long consumerAckTime) { this.consumerAckTime = consumerAckTime; }
    public long getEndToEndLatencyMs() { return endToEndLatencyMs; }
    public void setEndToEndLatencyMs(long endToEndLatencyMs) { this.endToEndLatencyMs = endToEndLatencyMs; }
    public long getProcessingLatencyMs() { return processingLatencyMs; }
    public void setProcessingLatencyMs(long processingLatencyMs) { this.processingLatencyMs = processingLatencyMs; }
    public long getQueueLatencyMs() { return queueLatencyMs; }
    public void setQueueLatencyMs(long queueLatencyMs) { this.queueLatencyMs = queueLatencyMs; }
    public boolean isSuccess() { return success; }
    public void setSuccess(boolean success) { this.success = success; }
    public String getErrorMessage() { return errorMessage; }
    public void setErrorMessage(String errorMessage) { this.errorMessage = errorMessage; }
    public String getErrorStack() { return errorStack; }
    public void setErrorStack(String errorStack) { this.errorStack = errorStack; }
    public int getRetryCount() { return retryCount; }
    public void setRetryCount(int retryCount) { this.retryCount = retryCount; }
    public boolean isSampled() { return sampled; }
    public void setSampled(boolean sampled) { this.sampled = sampled; }
}
