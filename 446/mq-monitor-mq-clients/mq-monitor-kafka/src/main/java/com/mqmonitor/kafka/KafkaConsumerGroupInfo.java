package com.mqmonitor.kafka;

import org.apache.kafka.common.TopicPartition;

import java.util.Map;

public class KafkaConsumerGroupInfo {
    private String groupId;
    private String state;
    private int memberCount;
    private Map<TopicPartition, Long> partitionOffsets;
    private Map<TopicPartition, Long> partitionLags;
    private long totalLag;

    public String getGroupId() { return groupId; }
    public void setGroupId(String groupId) { this.groupId = groupId; }
    public String getState() { return state; }
    public void setState(String state) { this.state = state; }
    public int getMemberCount() { return memberCount; }
    public void setMemberCount(int memberCount) { this.memberCount = memberCount; }
    public Map<TopicPartition, Long> getPartitionOffsets() { return partitionOffsets; }
    public void setPartitionOffsets(Map<TopicPartition, Long> partitionOffsets) { this.partitionOffsets = partitionOffsets; }
    public Map<TopicPartition, Long> getPartitionLags() { return partitionLags; }
    public void setPartitionLags(Map<TopicPartition, Long> partitionLags) { this.partitionLags = partitionLags; }
    public long getTotalLag() { return totalLag; }
    public void setTotalLag(long totalLag) { this.totalLag = totalLag; }
}
