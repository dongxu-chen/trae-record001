package com.datasync.kafka.consumer;

import com.datasync.common.monitor.LagDetector;
import lombok.Builder;
import lombok.Data;
import lombok.extern.slf4j.Slf4j;
import org.apache.kafka.clients.admin.AdminClient;
import org.apache.kafka.clients.admin.AdminClientConfig;
import org.apache.kafka.clients.admin.ListConsumerGroupOffsetsResult;
import org.apache.kafka.clients.admin.OffsetSpec;
import org.apache.kafka.clients.consumer.OffsetAndMetadata;
import org.apache.kafka.common.TopicPartition;

import java.util.*;
import java.util.concurrent.ExecutionException;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.TimeoutException;

@Slf4j
public class LagMonitor implements LagDetector {
    private final String bootstrapServers;
    private final String consumerGroupId;
    private final long highWatermarkThreshold;
    private final long lowWatermarkThreshold;
    private final AdminClient adminClient;
    private final Set<String> monitoredTopics;

    @Builder
    public LagMonitor(String bootstrapServers,
                      String consumerGroupId,
                      long highWatermarkThreshold,
                      long lowWatermarkThreshold,
                      Set<String> monitoredTopics) {
        this.bootstrapServers = bootstrapServers;
        this.consumerGroupId = consumerGroupId;
        this.highWatermarkThreshold = highWatermarkThreshold > 0 ? highWatermarkThreshold : 10000L;
        this.lowWatermarkThreshold = lowWatermarkThreshold > 0 ? lowWatermarkThreshold : 1000L;
        this.monitoredTopics = monitoredTopics;

        Properties props = new Properties();
        props.put(AdminClientConfig.BOOTSTRAP_SERVERS_CONFIG, bootstrapServers);
        props.put(AdminClientConfig.REQUEST_TIMEOUT_MS_CONFIG, 10000);
        props.put(AdminClientConfig.DEFAULT_API_TIMEOUT_MS_CONFIG, 15000);
        this.adminClient = AdminClient.create(props);
    }

    public Map<TopicPartition, Long> getConsumerLag() {
        Map<TopicPartition, Long> lagMap = new HashMap<>();

        try {
            ListConsumerGroupOffsetsResult offsetsResult = adminClient.listConsumerGroupOffsets(consumerGroupId);
            Map<TopicPartition, OffsetAndMetadata> consumerOffsets = offsetsResult.partitionsToOffsetAndMetadata()
                    .get(10, TimeUnit.SECONDS);

            Set<TopicPartition> partitions = consumerOffsets.keySet();
            if (partitions.isEmpty()) {
                return lagMap;
            }

            Map<TopicPartition, OffsetSpec> offsetSpecs = new HashMap<>();
            for (TopicPartition tp : partitions) {
                if (monitoredTopics == null || monitoredTopics.isEmpty() || monitoredTopics.contains(tp.topic())) {
                    offsetSpecs.put(tp, OffsetSpec.latest());
                }
            }

            Map<TopicPartition, Long> endOffsets = adminClient.listOffsets(offsetSpecs)
                    .all()
                    .get(10, TimeUnit.SECONDS)
                    .entrySet().stream()
                    .collect(HashMap::new,
                            (m, e) -> m.put(e.getKey(), e.getValue().offset()),
                            HashMap::putAll);

            for (Map.Entry<TopicPartition, OffsetAndMetadata> entry : consumerOffsets.entrySet()) {
                TopicPartition tp = entry.getKey();
                if (monitoredTopics != null && !monitoredTopics.isEmpty() && !monitoredTopics.contains(tp.topic())) {
                    continue;
                }

                long consumerOffset = entry.getValue().offset();
                Long endOffset = endOffsets.get(tp);
                if (endOffset != null) {
                    long lag = endOffset - consumerOffset;
                    lagMap.put(tp, lag);
                }
            }
        } catch (InterruptedException | ExecutionException | TimeoutException e) {
            log.error("Failed to get consumer lag for group: {}", consumerGroupId, e);
        }

        return lagMap;
    }

    public long getTotalLag() {
        return getConsumerLag().values().stream().mapToLong(Long::longValue).sum();
    }

    public long getMaxLag() {
        return getConsumerLag().values().stream().mapToLong(Long::longValue).max().orElse(0);
    }

    public boolean isLagSafeForSwitch() {
        long totalLag = getTotalLag();
        boolean safe = totalLag <= lowWatermarkThreshold;
        log.info("Lag check for switch: totalLag={}, threshold={}, safe={}",
                totalLag, lowWatermarkThreshold, safe);
        return safe;
    }

    public boolean isLagHigh() {
        long totalLag = getTotalLag();
        boolean high = totalLag >= highWatermarkThreshold;
        if (high) {
            log.warn("High lag detected: totalLag={}, threshold={}", totalLag, highWatermarkThreshold);
        }
        return high;
    }

    public LagStatus getLagStatus() {
        Map<TopicPartition, Long> lagMap = getConsumerLag();
        long totalLag = lagMap.values().stream().mapToLong(Long::longValue).sum();
        long maxLag = lagMap.values().stream().mapToLong(Long::longValue).max().orElse(0);

        LagStatus status = LagStatus.builder()
                .consumerGroupId(consumerGroupId)
                .totalLag(totalLag)
                .maxLag(maxLag)
                .partitionCount(lagMap.size())
                .highWatermarkThreshold(highWatermarkThreshold)
                .lowWatermarkThreshold(lowWatermarkThreshold)
                .timestamp(System.currentTimeMillis())
                .lagByTopic(aggregateByTopic(lagMap))
                .build();

        status.setSafeForSwitch(totalLag <= lowWatermarkThreshold);
        status.setHighLag(totalLag >= highWatermarkThreshold);

        return status;
    }

    private Map<String, Long> aggregateByTopic(Map<TopicPartition, Long> lagMap) {
        Map<String, Long> topicLag = new HashMap<>();
        for (Map.Entry<TopicPartition, Long> entry : lagMap.entrySet()) {
            String topic = entry.getKey().topic();
            topicLag.merge(topic, entry.getValue(), Long::sum);
        }
        return topicLag;
    }

    public void waitForLagBelowThreshold(long thresholdMs) throws InterruptedException {
        long startTime = System.currentTimeMillis();
        while (System.currentTimeMillis() - startTime < thresholdMs) {
            if (isLagSafeForSwitch()) {
                log.info("Lag is now safe for switch");
                return;
            }
            Thread.sleep(1000);
        }
        log.warn("Timeout waiting for lag to drop below threshold, timeout={}ms", thresholdMs);
    }

    public void close() {
        if (adminClient != null) {
            adminClient.close();
        }
    }

    @Data
    @Builder
    public static class LagStatus implements LagDetector.LagStatus {
        private String consumerGroupId;
        private long totalLag;
        private long maxLag;
        private int partitionCount;
        private long highWatermarkThreshold;
        private long lowWatermarkThreshold;
        private long timestamp;
        private boolean isSafeForSwitch;
        private boolean isHighLag;
        private Map<String, Long> lagByTopic;
    }
}
