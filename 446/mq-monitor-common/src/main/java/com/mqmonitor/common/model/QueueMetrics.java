package com.mqmonitor.common.model;

import com.mqmonitor.common.enums.MQType;

import java.time.Instant;
import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;

public class QueueMetrics {
    private MQType mqType;
    private String clusterName;
    private String topic;
    private String queue;
    private String consumerGroup;
    private long timestamp;

    private long produceLatencyMs;
    private long consumeLatencyMs;
    private long endToEndLatencyMs;
    private long p50LatencyMs;
    private long p95LatencyMs;
    private long p99LatencyMs;
    private long backlogSize;
    private long messagesProduced;
    private long messagesConsumed;
    private double produceThroughput;
    private double consumeThroughput;
    private long consumerLag;
    private long clockOffsetNs;
    private boolean useMonotonicClock;

    private Map<String, Object> additionalMetrics = new ConcurrentHashMap<>();

    public QueueMetrics() {
        this.timestamp = Instant.now().toEpochMilli();
    }

    public QueueMetrics(MQType mqType, String clusterName, String topic) {
        this();
        this.mqType = mqType;
        this.clusterName = clusterName;
        this.topic = topic;
    }

    public MQType getMqType() { return mqType; }
    public void setMqType(MQType mqType) { this.mqType = mqType; }
    public String getClusterName() { return clusterName; }
    public void setClusterName(String clusterName) { this.clusterName = clusterName; }
    public String getTopic() { return topic; }
    public void setTopic(String topic) { this.topic = topic; }
    public String getQueue() { return queue; }
    public void setQueue(String queue) { this.queue = queue; }
    public String getConsumerGroup() { return consumerGroup; }
    public void setConsumerGroup(String consumerGroup) { this.consumerGroup = consumerGroup; }
    public long getTimestamp() { return timestamp; }
    public void setTimestamp(long timestamp) { this.timestamp = timestamp; }
    public long getProduceLatencyMs() { return produceLatencyMs; }
    public void setProduceLatencyMs(long produceLatencyMs) { this.produceLatencyMs = produceLatencyMs; }
    public long getConsumeLatencyMs() { return consumeLatencyMs; }
    public void setConsumeLatencyMs(long consumeLatencyMs) { this.consumeLatencyMs = consumeLatencyMs; }
    public long getEndToEndLatencyMs() { return endToEndLatencyMs; }
    public void setEndToEndLatencyMs(long endToEndLatencyMs) { this.endToEndLatencyMs = endToEndLatencyMs; }
    public long getBacklogSize() { return backlogSize; }
    public void setBacklogSize(long backlogSize) { this.backlogSize = backlogSize; }
    public long getMessagesProduced() { return messagesProduced; }
    public void setMessagesProduced(long messagesProduced) { this.messagesProduced = messagesProduced; }
    public long getMessagesConsumed() { return messagesConsumed; }
    public void setMessagesConsumed(long messagesConsumed) { this.messagesConsumed = messagesConsumed; }
    public double getProduceThroughput() { return produceThroughput; }
    public void setProduceThroughput(double produceThroughput) { this.produceThroughput = produceThroughput; }
    public double getConsumeThroughput() { return consumeThroughput; }
    public void setConsumeThroughput(double consumeThroughput) { this.consumeThroughput = consumeThroughput; }
    public long getConsumerLag() { return consumerLag; }
    public void setConsumerLag(long consumerLag) { this.consumerLag = consumerLag; }
    public long getP50LatencyMs() { return p50LatencyMs; }
    public void setP50LatencyMs(long p50LatencyMs) { this.p50LatencyMs = p50LatencyMs; }
    public long getP95LatencyMs() { return p95LatencyMs; }
    public void setP95LatencyMs(long p95LatencyMs) { this.p95LatencyMs = p95LatencyMs; }
    public long getP99LatencyMs() { return p99LatencyMs; }
    public void setP99LatencyMs(long p99LatencyMs) { this.p99LatencyMs = p99LatencyMs; }
    public long getClockOffsetNs() { return clockOffsetNs; }
    public void setClockOffsetNs(long clockOffsetNs) { this.clockOffsetNs = clockOffsetNs; }
    public boolean isUseMonotonicClock() { return useMonotonicClock; }
    public void setUseMonotonicClock(boolean useMonotonicClock) { this.useMonotonicClock = useMonotonicClock; }
    public Map<String, Object> getAdditionalMetrics() { return additionalMetrics; }
    public void setAdditionalMetrics(Map<String, Object> additionalMetrics) { this.additionalMetrics = additionalMetrics; }
    public void addMetric(String key, Object value) { this.additionalMetrics.put(key, value); }
    public Object getMetric(String key) { return this.additionalMetrics.get(key); }
}
