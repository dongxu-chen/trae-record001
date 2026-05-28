package com.datasync.kafka.channel;

import com.datasync.common.constant.SyncConstants;
import com.datasync.common.model.DataChangeEvent;
import com.datasync.common.model.TableSyncChannel;
import lombok.Builder;
import lombok.Data;
import lombok.extern.slf4j.Slf4j;

import java.util.*;
import java.util.concurrent.ConcurrentHashMap;
import java.util.regex.Pattern;
import java.util.stream.Collectors;

@Slf4j
public class TableChannelManager {
    private final String datacenterId;
    private final String topicPrefix;
    private final Map<String, TableSyncChannel> channelMap = new ConcurrentHashMap<>();
    private final List<TableSyncChannel> largeTableChannels = new ArrayList<>();
    private final List<TableSyncChannel> regularTableChannels = new ArrayList<>();
    private final long largeTableThresholdRows;

    @Builder
    public TableChannelManager(String datacenterId,
                               String topicPrefix,
                               long largeTableThresholdRows,
                               List<TableSyncChannel> predefinedChannels) {
        this.datacenterId = datacenterId;
        this.topicPrefix = topicPrefix != null ? topicPrefix : SyncConstants.KAFKA_TOPIC_PREFIX;
        this.largeTableThresholdRows = largeTableThresholdRows > 0 ? largeTableThresholdRows : 1000000L;

        if (predefinedChannels != null) {
            for (TableSyncChannel channel : predefinedChannels) {
                registerChannel(channel);
            }
        }
    }

    public TableSyncChannel getOrCreateChannel(String fullTableName, long estimatedRowCount) {
        TableSyncChannel existing = channelMap.get(fullTableName);
        if (existing != null) {
            return existing;
        }
        return createChannel(fullTableName, estimatedRowCount);
    }

    public TableSyncChannel getOrCreateChannel(String fullTableName) {
        return getOrCreateChannel(fullTableName, 0);
    }

    private synchronized TableSyncChannel createChannel(String fullTableName, long estimatedRowCount) {
        TableSyncChannel existing = channelMap.get(fullTableName);
        if (existing != null) {
            return existing;
        }

        boolean isLarge = estimatedRowCount >= largeTableThresholdRows;
        String channelId = generateChannelId(fullTableName, isLarge);
        String topicName = generateTopicName(fullTableName);
        String consumerGroupId = generateConsumerGroupId(channelId);
        int partitionCount = isLarge ? Math.min(12, Math.max(3, (int) (estimatedRowCount / 500000) + 1)) : 3;

        TableSyncChannel channel = TableSyncChannel.builder()
                .channelId(channelId)
                .tableName(fullTableName)
                .topicName(topicName)
                .consumerGroupId(consumerGroupId)
                .priority(isLarge ? 0 : 5)
                .isLargeTable(isLarge)
                .expectedRowCount(estimatedRowCount)
                .partitionCount(partitionCount)
                .enabled(true)
                .build();

        registerChannel(channel);
        log.info("Created {} channel for table: {}, topic: {}, partitions: {}",
                isLarge ? "LARGE TABLE" : "regular", fullTableName, topicName, partitionCount);
        return channel;
    }

    public void registerChannel(TableSyncChannel channel) {
        channelMap.put(channel.getTableName(), channel);
        if (channel.isLargeTable()) {
            if (!largeTableChannels.contains(channel)) {
                largeTableChannels.add(channel);
            }
        } else {
            if (!regularTableChannels.contains(channel)) {
                regularTableChannels.add(channel);
            }
        }
    }

    public TableSyncChannel getChannel(String fullTableName) {
        return channelMap.get(fullTableName);
    }

    public List<TableSyncChannel> getAllChannels() {
        return new ArrayList<>(channelMap.values());
    }

    public List<TableSyncChannel> getLargeTableChannels() {
        return new ArrayList<>(largeTableChannels);
    }

    public List<TableSyncChannel> getRegularTableChannels() {
        return new ArrayList<>(regularTableChannels);
    }

    public List<String> getAllTopics() {
        return channelMap.values().stream()
                .map(TableSyncChannel::getTopicName)
                .collect(Collectors.toList());
    }

    public List<String> getChannelTopics() {
        return channelMap.values().stream()
                .filter(TableSyncChannel::isEnabled)
                .map(TableSyncChannel::getTopicName)
                .collect(Collectors.toList());
    }

    public Map<String, List<String>> getConsumerGroupTopicsMap() {
        Map<String, List<String>> groupTopics = new HashMap<>();
        for (TableSyncChannel channel : channelMap.values()) {
            if (channel.isEnabled()) {
                groupTopics.computeIfAbsent(channel.getConsumerGroupId(), k -> new ArrayList<>())
                        .add(channel.getTopicName());
            }
        }
        return groupTopics;
    }

    public boolean isLargeTable(String fullTableName) {
        TableSyncChannel channel = channelMap.get(fullTableName);
        return channel != null && channel.isLargeTable();
    }

    public String getTopicForEvent(DataChangeEvent event) {
        TableSyncChannel channel = getOrCreateChannel(event.getFullTableName());
        return channel.getTopicName();
    }

    public String getConsumerGroupForTable(String fullTableName) {
        TableSyncChannel channel = getOrCreateChannel(fullTableName);
        return channel.getConsumerGroupId();
    }

    private String generateChannelId(String fullTableName, boolean isLarge) {
        String prefix = isLarge ? "large_" : "reg_";
        return prefix + fullTableName.replace(".", "_");
    }

    private String generateTopicName(String fullTableName) {
        return topicPrefix + datacenterId + "_" + fullTableName.replace(".", "_");
    }

    private String generateConsumerGroupId(String channelId) {
        return SyncConstants.KAFKA_CONSUMER_GROUP_PREFIX + datacenterId + "_" + channelId;
    }

    public void disableChannel(String fullTableName) {
        TableSyncChannel channel = channelMap.get(fullTableName);
        if (channel != null) {
            channel.setEnabled(false);
            log.info("Disabled channel for table: {}", fullTableName);
        }
    }

    public void enableChannel(String fullTableName) {
        TableSyncChannel channel = channelMap.get(fullTableName);
        if (channel != null) {
            channel.setEnabled(true);
            log.info("Enabled channel for table: {}", fullTableName);
        }
    }

    public int getChannelCount() {
        return channelMap.size();
    }

    public int getLargeTableCount() {
        return (int) channelMap.values().stream().filter(TableSyncChannel::isLargeTable).count();
    }
}
