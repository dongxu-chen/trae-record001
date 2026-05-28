package com.mqmonitor.rocketmq;

public class RocketMQConsumerGroupInfo {
    private String groupId;
    private String state;
    private int consumerCount;
    private long totalLag;
    private long totalDiff;
    private long lastUpdateTime;

    public String getGroupId() { return groupId; }
    public void setGroupId(String groupId) { this.groupId = groupId; }
    public String getState() { return state; }
    public void setState(String state) { this.state = state; }
    public int getConsumerCount() { return consumerCount; }
    public void setConsumerCount(int consumerCount) { this.consumerCount = consumerCount; }
    public long getTotalLag() { return totalLag; }
    public void setTotalLag(long totalLag) { this.totalLag = totalLag; }
    public long getTotalDiff() { return totalDiff; }
    public void setTotalDiff(long totalDiff) { this.totalDiff = totalDiff; }
    public long getLastUpdateTime() { return lastUpdateTime; }
    public void setLastUpdateTime(long lastUpdateTime) { this.lastUpdateTime = lastUpdateTime; }
}
