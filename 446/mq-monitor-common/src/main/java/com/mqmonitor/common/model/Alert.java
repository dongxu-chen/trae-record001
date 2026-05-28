package com.mqmonitor.common.model;

import com.mqmonitor.common.enums.AlertLevel;
import com.mqmonitor.common.enums.AlertType;
import com.mqmonitor.common.enums.MQType;

import java.time.Instant;
import java.util.Map;

public class Alert {
    private String id;
    private AlertType type;
    private AlertLevel level;
    private MQType mqType;
    private String clusterName;
    private String topic;
    private String consumerGroup;
    private String message;
    private Map<String, Object> details;
    private long timestamp;
    private boolean resolved;
    private long resolvedTimestamp;

    public Alert() {
        this.id = java.util.UUID.randomUUID().toString();
        this.timestamp = Instant.now().toEpochMilli();
        this.resolved = false;
    }

    public Alert(AlertType type, AlertLevel level, String message) {
        this();
        this.type = type;
        this.level = level;
        this.message = message;
    }

    public String getId() { return id; }
    public void setId(String id) { this.id = id; }
    public AlertType getType() { return type; }
    public void setType(AlertType type) { this.type = type; }
    public AlertLevel getLevel() { return level; }
    public void setLevel(AlertLevel level) { this.level = level; }
    public MQType getMqType() { return mqType; }
    public void setMqType(MQType mqType) { this.mqType = mqType; }
    public String getClusterName() { return clusterName; }
    public void setClusterName(String clusterName) { this.clusterName = clusterName; }
    public String getTopic() { return topic; }
    public void setTopic(String topic) { this.topic = topic; }
    public String getConsumerGroup() { return consumerGroup; }
    public void setConsumerGroup(String consumerGroup) { this.consumerGroup = consumerGroup; }
    public String getMessage() { return message; }
    public void setMessage(String message) { this.message = message; }
    public Map<String, Object> getDetails() { return details; }
    public void setDetails(Map<String, Object> details) { this.details = details; }
    public long getTimestamp() { return timestamp; }
    public void setTimestamp(long timestamp) { this.timestamp = timestamp; }
    public boolean isResolved() { return resolved; }
    public void setResolved(boolean resolved) { this.resolved = resolved; }
    public long getResolvedTimestamp() { return resolvedTimestamp; }
    public void setResolvedTimestamp(long resolvedTimestamp) { this.resolvedTimestamp = resolvedTimestamp; }

    public void resolve() {
        this.resolved = true;
        this.resolvedTimestamp = Instant.now().toEpochMilli();
    }
}
