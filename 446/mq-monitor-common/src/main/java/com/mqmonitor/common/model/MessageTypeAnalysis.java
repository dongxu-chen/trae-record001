package com.mqmonitor.common.model;

import com.mqmonitor.common.enums.MQType;

import java.util.*;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.atomic.AtomicLong;
import java.util.concurrent.atomic.AtomicInteger;

public class MessageTypeAnalysis {
    private String messageType;
    private MQType mqType;
    private String clusterName;
    private String topic;
    private String consumerGroup;

    private AtomicLong totalMessages = new AtomicLong(0);
    private AtomicLong totalProcessingTimeMs = new AtomicLong(0);
    private AtomicLong totalQueueTimeMs = new AtomicLong(0);
    private AtomicLong totalEndToEndTimeMs = new AtomicLong(0);
    private AtomicLong failedMessages = new AtomicLong(0);
    private AtomicLong retryCount = new AtomicLong(0);

    private long minProcessingTimeMs = Long.MAX_VALUE;
    private long maxProcessingTimeMs = 0;
    private long p50ProcessingTimeMs = 0;
    private long p95ProcessingTimeMs = 0;
    private long p99ProcessingTimeMs = 0;

    private final List<Long> recentProcessingTimes = Collections.synchronizedList(new ArrayList<>());
    private static final int MAX_RECENT_SAMPLES = 1000;

    private long lastAnalysisTime;
    private double slowMessageRatio = 0.0;
    private double anomalyScore = 0.0;
    private String severityLevel = "NORMAL";

    private final Map<String, AtomicInteger> errorTypes = new ConcurrentHashMap<>();

    public MessageTypeAnalysis() {}

    public MessageTypeAnalysis(String messageType, MQType mqType, String clusterName,
                               String topic, String consumerGroup) {
        this.messageType = messageType;
        this.mqType = mqType;
        this.clusterName = clusterName;
        this.topic = topic;
        this.consumerGroup = consumerGroup;
        this.lastAnalysisTime = System.currentTimeMillis();
    }

    public synchronized void recordMessage(long processingTimeMs, long queueTimeMs,
                                         long endToEndTimeMs, boolean success,
                                         int retryCount, String errorType) {
        totalMessages.incrementAndGet();
        totalProcessingTimeMs.addAndGet(processingTimeMs);
        totalQueueTimeMs.addAndGet(queueTimeMs);
        totalEndToEndTimeMs.addAndGet(endToEndTimeMs);
        this.retryCount.addAndGet(retryCount);

        if (!success) {
            failedMessages.incrementAndGet();
            if (errorType != null) {
                errorTypes.computeIfAbsent(errorType, k -> new AtomicInteger(0)).incrementAndGet();
            }
        }

        if (processingTimeMs < minProcessingTimeMs) minProcessingTimeMs = processingTimeMs;
        if (processingTimeMs > maxProcessingTimeMs) maxProcessingTimeMs = processingTimeMs;

        recentProcessingTimes.add(processingTimeMs);
        while (recentProcessingTimes.size() > MAX_RECENT_SAMPLES) {
            recentProcessingTimes.remove(0);
        }

        if (totalMessages.get() % 100 == 0) {
            recalculatePercentiles();
        }
    }

    public synchronized void recalculatePercentiles() {
        if (recentProcessingTimes.isEmpty()) return;

        List<Long> sorted = new ArrayList<>(recentProcessingTimes);
        Collections.sort(sorted);

        p50ProcessingTimeMs = calculatePercentile(sorted, 50);
        p95ProcessingTimeMs = calculatePercentile(sorted, 95);
        p99ProcessingTimeMs = calculatePercentile(sorted, 99);
        lastAnalysisTime = System.currentTimeMillis();
    }

    private long calculatePercentile(List<Long> sorted, double percentile) {
        if (sorted.isEmpty()) return 0;
        double index = (percentile / 100.0) * (sorted.size() - 1);
        int lower = (int) Math.floor(index);
        int upper = (int) Math.ceil(index);
        if (lower == upper) return sorted.get(lower);
        double weight = index - lower;
        return Math.round(sorted.get(lower) * (1 - weight) + sorted.get(upper) * weight);
    }

    public double getAverageProcessingTimeMs() {
        return totalMessages.get() == 0 ? 0 :
                (double) totalProcessingTimeMs.get() / totalMessages.get();
    }

    public double getAverageQueueTimeMs() {
        return totalMessages.get() == 0 ? 0 :
                (double) totalQueueTimeMs.get() / totalMessages.get();
    }

    public double getAverageEndToEndTimeMs() {
        return totalMessages.get() == 0 ? 0 :
                (double) totalEndToEndTimeMs.get() / totalMessages.get();
    }

    public double getFailureRate() {
        return totalMessages.get() == 0 ? 0 :
                (double) failedMessages.get() / totalMessages.get();
    }

    public double getAverageRetryCount() {
        return totalMessages.get() == 0 ? 0 :
                (double) retryCount.get() / totalMessages.get();
    }

    public void calculateSlowMessageRatio(long slowThresholdMs) {
        if (recentProcessingTimes.isEmpty()) {
            slowMessageRatio = 0.0;
            return;
        }

        long slowCount = recentProcessingTimes.stream()
                .filter(t -> t > slowThresholdMs)
                .count();
        slowMessageRatio = (double) slowCount / recentProcessingTimes.size();

        if (slowMessageRatio > 0.2) {
            severityLevel = "CRITICAL";
        } else if (slowMessageRatio > 0.1) {
            severityLevel = "WARNING";
        } else if (slowMessageRatio > 0.05) {
            severityLevel = "NOTICE";
        } else {
            severityLevel = "NORMAL";
        }
    }

    public void calculateAnomalyScore(double globalAvgProcessingTime) {
        if (globalAvgProcessingTime <= 0) {
            anomalyScore = 0.0;
            return;
        }

        double avgProcessing = getAverageProcessingTimeMs();
        double ratio = avgProcessing / globalAvgProcessingTime;

        if (ratio >= 5.0) {
            anomalyScore = 1.0;
        } else if (ratio >= 3.0) {
            anomalyScore = 0.7 + (ratio - 3.0) / 2.0 * 0.3;
        } else if (ratio >= 2.0) {
            anomalyScore = 0.4 + (ratio - 2.0) * 0.3;
        } else if (ratio >= 1.5) {
            anomalyScore = 0.1 + (ratio - 1.5) * 0.6;
        } else {
            anomalyScore = Math.max(0, (ratio - 1.0) * 0.2);
        }

        anomalyScore = Math.min(1.0, anomalyScore + getFailureRate() * 0.3 + slowMessageRatio * 0.3);
    }

    public Map<String, Object> toSummary() {
        Map<String, Object> summary = new LinkedHashMap<>();
        summary.put("messageType", messageType);
        summary.put("mqType", mqType);
        summary.put("topic", topic);
        summary.put("consumerGroup", consumerGroup);
        summary.put("totalMessages", totalMessages.get());
        summary.put("failedMessages", failedMessages.get());
        summary.put("failureRate", getFailureRate());
        summary.put("averageProcessingTimeMs", getAverageProcessingTimeMs());
        summary.put("averageQueueTimeMs", getAverageQueueTimeMs());
        summary.put("averageEndToEndTimeMs", getAverageEndToEndTimeMs());
        summary.put("minProcessingTimeMs", minProcessingTimeMs == Long.MAX_VALUE ? 0 : minProcessingTimeMs);
        summary.put("maxProcessingTimeMs", maxProcessingTimeMs);
        summary.put("p50ProcessingTimeMs", p50ProcessingTimeMs);
        summary.put("p95ProcessingTimeMs", p95ProcessingTimeMs);
        summary.put("p99ProcessingTimeMs", p99ProcessingTimeMs);
        summary.put("averageRetryCount", getAverageRetryCount());
        summary.put("slowMessageRatio", slowMessageRatio);
        summary.put("anomalyScore", anomalyScore);
        summary.put("severityLevel", severityLevel);
        summary.put("lastAnalysisTime", lastAnalysisTime);
        summary.put("recentSampleCount", recentProcessingTimes.size());

        if (!errorTypes.isEmpty()) {
            Map<String, Integer> errors = new LinkedHashMap<>();
            errorTypes.forEach((k, v) -> errors.put(k, v.get()));
            summary.put("errorTypes", errors);
        }

        return summary;
    }

    public String getMessageType() { return messageType; }
    public void setMessageType(String messageType) { this.messageType = messageType; }
    public MQType getMqType() { return mqType; }
    public void setMqType(MQType mqType) { this.mqType = mqType; }
    public String getClusterName() { return clusterName; }
    public void setClusterName(String clusterName) { this.clusterName = clusterName; }
    public String getTopic() { return topic; }
    public void setTopic(String topic) { this.topic = topic; }
    public String getConsumerGroup() { return consumerGroup; }
    public void setConsumerGroup(String consumerGroup) { this.consumerGroup = consumerGroup; }
    public long getTotalMessages() { return totalMessages.get(); }
    public long getFailedMessages() { return failedMessages.get(); }
    public long getMinProcessingTimeMs() { return minProcessingTimeMs == Long.MAX_VALUE ? 0 : minProcessingTimeMs; }
    public long getMaxProcessingTimeMs() { return maxProcessingTimeMs; }
    public long getP50ProcessingTimeMs() { return p50ProcessingTimeMs; }
    public long getP95ProcessingTimeMs() { return p95ProcessingTimeMs; }
    public long getP99ProcessingTimeMs() { return p99ProcessingTimeMs; }
    public double getSlowMessageRatio() { return slowMessageRatio; }
    public double getAnomalyScore() { return anomalyScore; }
    public String getSeverityLevel() { return severityLevel; }
    public List<Long> getRecentProcessingTimes() { return new ArrayList<>(recentProcessingTimes); }
}
