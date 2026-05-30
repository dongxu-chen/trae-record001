package com.dtmonitor.core.model.entity;

import com.dtmonitor.core.enums.TransactionMode;
import com.dtmonitor.core.enums.TransactionStatus;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import javax.persistence.*;
import java.time.LocalDateTime;
import java.util.HashMap;
import java.util.Map;

@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
@Entity
@Table(name = "global_transaction")
public class GlobalTransaction {

    @Id
    @Column(length = 64)
    private String xid;

    @Column(length = 64)
    private String applicationId;

    @Column(length = 128)
    private String transactionServiceGroup;

    @Enumerated(EnumType.STRING)
    @Column(length = 16)
    private TransactionMode mode;

    @Enumerated(EnumType.STRING)
    @Column(length = 16)
    private TransactionStatus status;

    @Column(name = "begin_time")
    private LocalDateTime beginTime;

    @Column(name = "end_time")
    private LocalDateTime endTime;

    @Column(name = "timeout_ms")
    private Long timeoutMs;

    @Column(name = "trace_id", length = 64)
    private String traceId;

    @Column(length = 512)
    private String remark;

    @Column(name = "rollback_reason", length = 1024)
    private String rollbackReason;

    @Column(name = "traffic_color", length = 32)
    private String trafficColor;

    @Column(name = "business_type", length = 64)
    private String businessType;

    @ElementCollection(fetch = FetchType.EAGER)
    @CollectionTable(name = "transaction_tags", joinColumns = @JoinColumn(name = "xid"))
    @MapKeyColumn(name = "tag_key", length = 64)
    @Column(name = "tag_value", length = 256)
    @Builder.Default
    private Map<String, String> tags = new HashMap<>();

    @Column(name = "created_at")
    private LocalDateTime createdAt;

    @Column(name = "updated_at")
    private LocalDateTime updatedAt;

    @PrePersist
    protected void onCreate() {
        createdAt = LocalDateTime.now();
        updatedAt = LocalDateTime.now();
    }

    @PreUpdate
    protected void onUpdate() {
        updatedAt = LocalDateTime.now();
    }

    public boolean isTimeout() {
        if (timeoutMs == null || beginTime == null) {
            return false;
        }
        if (status == TransactionStatus.BEGIN || status == TransactionStatus.COMMITTING || status == TransactionStatus.ROLLBACKING) {
            long elapsed = java.time.Duration.between(beginTime, LocalDateTime.now()).toMillis();
            return elapsed > timeoutMs;
        }
        return false;
    }

    public long getDurationMs() {
        if (beginTime == null) return 0;
        LocalDateTime end = endTime != null ? endTime : LocalDateTime.now();
        return java.time.Duration.between(beginTime, end).toMillis();
    }
}
