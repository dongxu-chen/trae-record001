package com.datasync.kafka.consumer;

import com.datasync.common.constant.SyncConstants;
import com.datasync.common.model.DataChangeEvent;
import com.datasync.common.model.TableSyncChannel;
import com.datasync.kafka.channel.TableChannelManager;
import lombok.Builder;
import lombok.extern.slf4j.Slf4j;

import java.util.ArrayList;
import java.util.List;
import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import java.util.concurrent.atomic.AtomicBoolean;
import java.util.function.Consumer;

@Slf4j
public class MultiChannelConsumer {
    private final String bootstrapServers;
    private final String datacenterId;
    private final List<String> sourceDatacenterIds;
    private final TableChannelManager channelManager;
    private final AtomicBoolean running = new AtomicBoolean(false);
    private final Map<String, KafkaMessageConsumer> consumerMap = new ConcurrentHashMap<>();
    private final Map<String, ExecutorService> executorMap = new ConcurrentHashMap<>();
    private Consumer<List<DataChangeEvent>> eventListener;
    private final Long pollTimeoutMs;
    private final Integer maxPollRecords;
    private final Boolean enableAutoCommit;
    private final String autoOffsetReset;

    @Builder
    public MultiChannelConsumer(String bootstrapServers,
                                String datacenterId,
                                List<String> sourceDatacenterIds,
                                TableChannelManager channelManager,
                                Long pollTimeoutMs,
                                Integer maxPollRecords,
                                Boolean enableAutoCommit,
                                String autoOffsetReset) {
        this.bootstrapServers = bootstrapServers;
        this.datacenterId = datacenterId;
        this.sourceDatacenterIds = sourceDatacenterIds;
        this.channelManager = channelManager;
        this.pollTimeoutMs = pollTimeoutMs;
        this.maxPollRecords = maxPollRecords;
        this.enableAutoCommit = enableAutoCommit;
        this.autoOffsetReset = autoOffsetReset;
    }

    public void registerListener(Consumer<List<DataChangeEvent>> listener) {
        this.eventListener = listener;
    }

    public void start() {
        if (running.compareAndSet(false, true)) {
            log.info("Starting Multi-Channel Consumer for datacenter: {}", datacenterId);

            List<TableSyncChannel> channels = channelManager.getAllChannels();
            for (TableSyncChannel channel : channels) {
                if (channel.isEnabled()) {
                    createConsumerForChannel(channel);
                }
            }
            log.info("Multi-Channel Consumer started with {} channels", consumerMap.size());
        }
    }

    public void stop() {
        if (running.compareAndSet(true, false)) {
            log.info("Stopping Multi-Channel Consumer");
            for (Map.Entry<String, KafkaMessageConsumer> entry : consumerMap.entrySet()) {
                try {
                    entry.getValue().stop();
                } catch (Exception e) {
                    log.error("Error stopping consumer for channel: {}", entry.getKey(), e);
                }
            }
            for (Map.Entry<String, ExecutorService> entry : executorMap.entrySet()) {
                try {
                    entry.getValue().shutdownNow();
                } catch (Exception e) {
                    log.error("Error stopping executor for channel: {}", entry.getKey(), e);
                }
            }
            consumerMap.clear();
            executorMap.clear();
            log.info("Multi-Channel Consumer stopped");
        }
    }

    private void createConsumerForChannel(TableSyncChannel channel) {
        if (consumerMap.containsKey(channel.getChannelId())) {
            return;
        }

        List<String> topics = new ArrayList<>();
        for (String sourceDc : sourceDatacenterIds) {
            String sourceTopic = channel.getTopicName().replace(
                    SyncConstants.KAFKA_TOPIC_PREFIX + datacenterId + "_",
                    SyncConstants.KAFKA_TOPIC_PREFIX + sourceDc + "_"
            );
            topics.add(sourceTopic);
        }

        KafkaMessageConsumer consumer = KafkaMessageConsumer.builder()
                .bootstrapServers(bootstrapServers)
                .groupId(channel.getConsumerGroupId())
                .datacenterId(datacenterId)
                .sourceDatacenterIds(sourceDatacenterIds)
                .topics(topics)
                .pollTimeoutMs(pollTimeoutMs)
                .maxPollRecords(maxPollRecords)
                .enableAutoCommit(enableAutoCommit)
                .autoOffsetReset(autoOffsetReset)
                .build();

        consumer.registerListener(event -> {
            if (eventListener != null) {
                eventListener.accept(event);
            }
        });

        ExecutorService executor = Executors.newSingleThreadExecutor(r -> {
            Thread t = new Thread(r, "kafka-consumer-" + channel.getChannelId());
            t.setDaemon(true);
            t.setPriority(channel.isLargeTable() ? Thread.MAX_PRIORITY : Thread.NORM_PRIORITY);
            return t;
        });

        consumer.start();
        consumerMap.put(channel.getChannelId(), consumer);
        executorMap.put(channel.getChannelId(), executor);

        log.info("Created consumer for channel: {}, table: {}, topics: {}",
                channel.getChannelId(), channel.getTableName(), topics);
    }

    public void addChannel(TableSyncChannel channel) {
        if (running.get() && channel.isEnabled()) {
            channelManager.registerChannel(channel);
            createConsumerForChannel(channel);
        }
    }

    public void removeChannel(String channelId) {
        KafkaMessageConsumer consumer = consumerMap.remove(channelId);
        if (consumer != null) {
            consumer.stop();
        }
        ExecutorService executor = executorMap.remove(channelId);
        if (executor != null) {
            executor.shutdownNow();
        }
        log.info("Removed consumer for channel: {}", channelId);
    }

    public void pauseChannel(String channelId) {
        KafkaMessageConsumer consumer = consumerMap.get(channelId);
        if (consumer != null) {
            consumer.stop();
            log.info("Paused consumer for channel: {}", channelId);
        }
    }

    public void resumeChannel(String channelId) {
        KafkaMessageConsumer consumer = consumerMap.get(channelId);
        if (consumer != null && !consumer.isRunning()) {
            consumer.start();
            log.info("Resumed consumer for channel: {}", channelId);
        }
    }

    public int getActiveChannelCount() {
        return (int) consumerMap.values().stream().filter(KafkaMessageConsumer::isRunning).count();
    }

    public int getLargeTableChannelCount() {
        return (int) consumerMap.keySet().stream()
                .filter(id -> channelManager.getChannel(id) != null && channelManager.getChannel(id).isLargeTable())
                .count();
    }
}
