package com.dtmonitor.collector.event;

import com.dtmonitor.core.enums.TransactionMode;
import com.dtmonitor.core.enums.TransactionStatus;

public class SeataTransactionEvent {

    private String xid;
    private String branchId;
    private String eventType;
    private TransactionMode mode;
    private TransactionStatus status;
    private String applicationId;
    private String transactionServiceGroup;
    private String resourceId;
    private String lockKey;
    private Long timeoutMs;
    private String traceId;
    private String spanId;
    private String errorMessage;
    private String payload;
    private Long timestamp;

    public SeataTransactionEvent() {}

    public static Builder builder() {
        return new Builder();
    }

    public String getXid() { return xid; }
    public void setXid(String xid) { this.xid = xid; }
    public String getBranchId() { return branchId; }
    public void setBranchId(String branchId) { this.branchId = branchId; }
    public String getEventType() { return eventType; }
    public void setEventType(String eventType) { this.eventType = eventType; }
    public TransactionMode getMode() { return mode; }
    public void setMode(TransactionMode mode) { this.mode = mode; }
    public TransactionStatus getStatus() { return status; }
    public void setStatus(TransactionStatus status) { this.status = status; }
    public String getApplicationId() { return applicationId; }
    public void setApplicationId(String applicationId) { this.applicationId = applicationId; }
    public String getTransactionServiceGroup() { return transactionServiceGroup; }
    public void setTransactionServiceGroup(String transactionServiceGroup) { this.transactionServiceGroup = transactionServiceGroup; }
    public String getResourceId() { return resourceId; }
    public void setResourceId(String resourceId) { this.resourceId = resourceId; }
    public String getLockKey() { return lockKey; }
    public void setLockKey(String lockKey) { this.lockKey = lockKey; }
    public Long getTimeoutMs() { return timeoutMs; }
    public void setTimeoutMs(Long timeoutMs) { this.timeoutMs = timeoutMs; }
    public String getTraceId() { return traceId; }
    public void setTraceId(String traceId) { this.traceId = traceId; }
    public String getSpanId() { return spanId; }
    public void setSpanId(String spanId) { this.spanId = spanId; }
    public String getErrorMessage() { return errorMessage; }
    public void setErrorMessage(String errorMessage) { this.errorMessage = errorMessage; }
    public String getPayload() { return payload; }
    public void setPayload(String payload) { this.payload = payload; }
    public Long getTimestamp() { return timestamp; }
    public void setTimestamp(Long timestamp) { this.timestamp = timestamp; }

    public boolean isGlobalEvent() {
        return branchId == null || branchId.isEmpty();
    }

    public static class Builder {
        private final SeataTransactionEvent event = new SeataTransactionEvent();

        public Builder xid(String xid) { event.xid = xid; return this; }
        public Builder branchId(String branchId) { event.branchId = branchId; return this; }
        public Builder eventType(String eventType) { event.eventType = eventType; return this; }
        public Builder mode(TransactionMode mode) { event.mode = mode; return this; }
        public Builder status(TransactionStatus status) { event.status = status; return this; }
        public Builder applicationId(String applicationId) { event.applicationId = applicationId; return this; }
        public Builder transactionServiceGroup(String group) { event.transactionServiceGroup = group; return this; }
        public Builder resourceId(String resourceId) { event.resourceId = resourceId; return this; }
        public Builder lockKey(String lockKey) { event.lockKey = lockKey; return this; }
        public Builder timeoutMs(Long timeoutMs) { event.timeoutMs = timeoutMs; return this; }
        public Builder traceId(String traceId) { event.traceId = traceId; return this; }
        public Builder spanId(String spanId) { event.spanId = spanId; return this; }
        public Builder errorMessage(String errorMessage) { event.errorMessage = errorMessage; return this; }
        public Builder payload(String payload) { event.payload = payload; return this; }
        public Builder timestamp(Long timestamp) { event.timestamp = timestamp; return this; }
        public SeataTransactionEvent build() { return event; }
    }
}
