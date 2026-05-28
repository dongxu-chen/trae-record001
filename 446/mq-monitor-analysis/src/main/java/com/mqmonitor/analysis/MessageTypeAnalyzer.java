package com.mqmonitor.analysis;

import com.mqmonitor.common.enums.MQType;
import com.mqmonitor.common.model.MessageTrace;
import com.mqmonitor.common.model.MessageTypeAnalysis;
import com.mqmonitor.common.tracing.MessageTraceManager;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.util.*;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.TimeUnit;
import java.util.regex.Pattern;

public class MessageTypeAnalyzer {
    private static final Logger logger = LoggerFactory.getLogger(MessageTypeAnalyzer.class);

    private static final long DEFAULT_SLOW_THRESHOLD_MS = 5000;
    private static final long ANALYSIS_INTERVAL_MS = TimeUnit.MINUTES.toMillis(1);
    private static final int MAX_MESSAGE_TYPES = 1000;
    private static final double SAMPLING_RATE = 0.05;

    private final Map<String, MessageTypeAnalysis> typeAnalyses = new ConcurrentHashMap<>();
    private final List<Pattern> typePatterns = Collections.synchronizedList(new ArrayList<>());
    private final Map<String, String> headerTypeMappings = new ConcurrentHashMap<>();

    private long slowThresholdMs = DEFAULT_SLOW_THRESHOLD_MS;
    private boolean enabled = true;
    private volatile boolean running = false;
    private Thread analysisThread;

    private final MessageTraceManager traceManager;

    private static volatile MessageTypeAnalyzer instance;

    public static MessageTypeAnalyzer getInstance() {
        return getInstance(MessageTraceManager.getInstance());
    }

    public static MessageTypeAnalyzer getInstance(MessageTraceManager traceManager) {
        if (instance == null) {
            synchronized (MessageTypeAnalyzer.class) {
                if (instance == null) {
                    instance = new MessageTypeAnalyzer(traceManager);
                }
            }
        }
        return instance;
    }

    private MessageTypeAnalyzer(MessageTraceManager traceManager) {
        this.traceManager = traceManager;
        registerDefaultTypePatterns();
    }

    private void registerDefaultTypePatterns() {
        headerTypeMappings.put("x-message-type", "message_type");
        headerTypeMappings.put("event-type", "event_type");
        headerTypeMappings.put("type", "type");
        headerTypeMappings.put("msgType", "msg_type");
        headerTypeMappings.put("action", "action");
    }

    public void registerTypePattern(String regex) {
        typePatterns.add(Pattern.compile(regex));
    }

    public void registerHeaderTypeMapping(String headerName, String typeKey) {
        headerTypeMappings.put(headerName, typeKey);
    }

    public void start() {
        if (running) return;
        running = true;
        analysisThread = new Thread(this::runAnalysisLoop, "message-type-analyzer");
        analysisThread.setDaemon(true);
        analysisThread.start();
        logger.info("MessageTypeAnalyzer started");
    }

    public void stop() {
        running = false;
        if (analysisThread != null) {
            analysisThread.interrupt();
        }
        logger.info("MessageTypeAnalyzer stopped");
    }

    private void runAnalysisLoop() {
        while (running && !Thread.currentThread().isInterrupted()) {
            try {
                Thread.sleep(ANALYSIS_INTERVAL_MS);
                if (enabled) {
                    analyzeRecentTraces();
                    recalculateAllPercentiles();
                    updateSlowMessageRatios();
                    updateAnomalyScores();
                }
            } catch (InterruptedException e) {
                Thread.currentThread().interrupt();
                break;
            } catch (Exception e) {
                logger.error("Error in message type analysis loop", e);
            }
        }
    }

    public String identifyMessageType(MessageTrace trace) {
        if (trace.getMessageType() != null && !trace.getMessageType().isEmpty()) {
            return trace.getMessageType();
        }

        for (Map.Entry<String, String> entry : headerTypeMappings.entrySet()) {
            String value = trace.getHeaders().get(entry.getKey());
            if (value != null && !value.isEmpty()) {
                return value;
            }
        }

        String msgKey = trace.getMessageKey();
        if (msgKey != null && !msgKey.isEmpty()) {
            for (Pattern pattern : typePatterns) {
                if (pattern.matcher(msgKey).matches()) {
                    return msgKey;
                }
            }
        }

        String topic = trace.getTopic();
        if (topic != null && topic.contains(".")) {
            String[] parts = topic.split("\\.");
            if (parts.length >= 2) {
                return parts[parts.length - 2] + "." + parts[parts.length - 1];
            }
        }

        return topic != null ? topic : "unknown";
    }

    public void analyzeTrace(MessageTrace trace) {
        if (!enabled || trace == null || !trace.isComplete()) return;

        if (Math.random() > SAMPLING_RATE && !trace.isSampled()) {
            return;
        }

        try {
            String messageType = identifyMessageType(trace);
            trace.setMessageType(messageType);

            String key = buildKey(trace.getMqType(), trace.getClusterName(),
                    trace.getTopic(), trace.getConsumerGroup(), messageType);

            MessageTypeAnalysis analysis = typeAnalyses.computeIfAbsent(key,
                    k -> new MessageTypeAnalysis(messageType, trace.getMqType(),
                            trace.getClusterName(), trace.getTopic(), trace.getConsumerGroup()));

            analysis.recordMessage(
                    trace.getProcessingLatencyMs(),
                    trace.getQueueLatencyMs(),
                    trace.getEndToEndLatencyMs(),
                    trace.isSuccess(),
                    trace.getRetryCount(),
                    trace.getErrorMessage()
            );

            enforceLimits();
        } catch (Exception e) {
            logger.warn("Error analyzing trace", e);
        }
    }

    private void analyzeRecentTraces() {
        if (traceManager == null) return;

        List<MessageTrace> slowTraces = traceManager.getSlowTraces(slowThresholdMs, 100);
        for (MessageTrace trace : slowTraces) {
            analyzeTrace(trace);
        }

        List<MessageTrace> recentTraces = traceManager.getTracesByTopic(null, 200);
        for (MessageTrace trace : recentTraces) {
            if (trace.isComplete()) {
                analyzeTrace(trace);
            }
        }
    }

    private void recalculateAllPercentiles() {
        for (MessageTypeAnalysis analysis : typeAnalyses.values()) {
            analysis.recalculatePercentiles();
        }
    }

    private void updateSlowMessageRatios() {
        for (MessageTypeAnalysis analysis : typeAnalyses.values()) {
            analysis.calculateSlowMessageRatio(slowThresholdMs);
        }
    }

    private void updateAnomalyScores() {
        double globalAvg = calculateGlobalAverageProcessingTime();

        for (MessageTypeAnalysis analysis : typeAnalyses.values()) {
            analysis.calculateAnomalyScore(globalAvg);
        }
    }

    private double calculateGlobalAverageProcessingTime() {
        long totalTime = 0;
        long totalCount = 0;

        for (MessageTypeAnalysis analysis : typeAnalyses.values()) {
            totalTime += analysis.getAverageProcessingTimeMs() * analysis.getTotalMessages();
            totalCount += analysis.getTotalMessages();
        }

        return totalCount == 0 ? 0 : (double) totalTime / totalCount;
    }

    private void enforceLimits() {
        if (typeAnalyses.size() > MAX_MESSAGE_TYPES) {
            logger.warn("Message type limit exceeded: {}, removing types with fewest messages",
                    typeAnalyses.size());

            List<Map.Entry<String, MessageTypeAnalysis>> sorted = new ArrayList<>(typeAnalyses.entrySet());
            sorted.sort(Comparator.comparingLong(e -> e.getValue().getTotalMessages()));

            int toRemove = typeAnalyses.size() - MAX_MESSAGE_TYPES + 100;
            for (int i = 0; i < toRemove && i < sorted.size(); i++) {
                typeAnalyses.remove(sorted.get(i).getKey());
            }
        }
    }

    private String buildKey(MQType mqType, String clusterName, String topic,
                            String consumerGroup, String messageType) {
        return mqType + ":" + clusterName + ":" + topic + ":" +
                (consumerGroup != null ? consumerGroup : "*") + ":" + messageType;
    }

    public MessageTypeAnalysis getAnalysis(MQType mqType, String clusterName,
                                           String topic, String consumerGroup,
                                           String messageType) {
        String key = buildKey(mqType, clusterName, topic, consumerGroup, messageType);
        return typeAnalyses.get(key);
    }

    public List<MessageTypeAnalysis> getAnalysesByTopic(MQType mqType, String clusterName, String topic) {
        List<MessageTypeAnalysis> results = new ArrayList<>();
        String prefix = mqType + ":" + clusterName + ":" + topic + ":";

        for (Map.Entry<String, MessageTypeAnalysis> entry : typeAnalyses.entrySet()) {
            if (entry.getKey().startsWith(prefix)) {
                results.add(entry.getValue());
            }
        }
        return results;
    }

    public List<MessageTypeAnalysis> getSlowMessageTypes(int limit) {
        List<MessageTypeAnalysis> allTypes = new ArrayList<>(typeAnalyses.values());

        allTypes.sort((a, b) -> {
            if (a.getSeverityLevel().equals(b.getSeverityLevel())) {
                return Double.compare(b.getSlowMessageRatio(), a.getSlowMessageRatio());
            }
            return getSeverityRank(b.getSeverityLevel()) - getSeverityRank(a.getSeverityLevel());
        });

        return limit > 0 && allTypes.size() > limit ?
                allTypes.subList(0, limit) : allTypes;
    }

    public List<MessageTypeAnalysis> getAnomalousMessageTypes(double minAnomalyScore, int limit) {
        List<MessageTypeAnalysis> result = new ArrayList<>();

        for (MessageTypeAnalysis analysis : typeAnalyses.values()) {
            if (analysis.getAnomalyScore() >= minAnomalyScore) {
                result.add(analysis);
            }
        }

        result.sort((a, b) -> Double.compare(b.getAnomalyScore(), a.getAnomalyScore()));

        return limit > 0 && result.size() > limit ?
                result.subList(0, limit) : result;
    }

    private int getSeverityRank(String level) {
        switch (level) {
            case "CRITICAL": return 4;
            case "WARNING": return 3;
            case "NOTICE": return 2;
            default: return 1;
        }
    }

    public Map<String, Object> getStats() {
        Map<String, Object> stats = new LinkedHashMap<>();
        stats.put("enabled", enabled);
        stats.put("messageTypes", typeAnalyses.size());
        stats.put("slowThresholdMs", slowThresholdMs);
        stats.put("samplingRate", SAMPLING_RATE);

        long totalMessages = 0;
        long totalSlow = 0;
        int criticalTypes = 0, warningTypes = 0, noticeTypes = 0;

        for (MessageTypeAnalysis analysis : typeAnalyses.values()) {
            totalMessages += analysis.getTotalMessages();
            if (analysis.getSlowMessageRatio() > 0) {
                totalSlow += analysis.getTotalMessages() * analysis.getSlowMessageRatio();
            }
            switch (analysis.getSeverityLevel()) {
                case "CRITICAL": criticalTypes++; break;
                case "WARNING": warningTypes++; break;
                case "NOTICE": noticeTypes++; break;
            }
        }

        stats.put("totalMessagesSampled", totalMessages);
        stats.put("estimatedSlowMessages", totalSlow);
        stats.put("criticalTypes", criticalTypes);
        stats.put("warningTypes", warningTypes);
        stats.put("noticeTypes", noticeTypes);
        stats.put("globalAverageProcessingMs", calculateGlobalAverageProcessingTime());

        return stats;
    }

    public List<Map<String, Object>> getAllAnalyses() {
        List<Map<String, Object>> result = new ArrayList<>();
        for (MessageTypeAnalysis analysis : typeAnalyses.values()) {
            result.add(analysis.toSummary());
        }
        result.sort((a, b) -> Double.compare(
                ((Number) b.get("anomalyScore")).doubleValue(),
                ((Number) a.get("anomalyScore")).doubleValue()
        ));
        return result;
    }

    public void setSlowThresholdMs(long slowThresholdMs) {
        this.slowThresholdMs = slowThresholdMs;
    }

    public void setEnabled(boolean enabled) {
        this.enabled = enabled;
    }

    public boolean isEnabled() {
        return enabled;
    }

    public long getSlowThresholdMs() {
        return slowThresholdMs;
    }

    public void clearAll() {
        typeAnalyses.clear();
    }
}
