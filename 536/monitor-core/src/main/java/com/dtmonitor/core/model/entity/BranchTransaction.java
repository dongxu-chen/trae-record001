package com.dtmonitor.core.model.entity;

import com.dtmonitor.core.enums.BranchStatus;
import com.dtmonitor.core.enums.TransactionMode;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import javax.persistence.*;
import java.time.LocalDateTime;

@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
@Entity
@Table(name = "branch_transaction")
public class BranchTransaction {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(name = "branch_id", length = 64)
    private String branchId;

    @Column(name = "xid", length = 64)
    private String xid;

    @Column(length = 128)
    private String resourceId;

    @Column(length = 64)
    private String lockKey;

    @Enumerated(EnumType.STRING)
    @Column(length = 16)
    private BranchStatus status;

    @Enumerated(EnumType.STRING)
    @Column(length = 16)
    private TransactionMode mode;

    @Column(name = "application_id", length = 64)
    private String applicationId;

    @Column(name = "begin_time")
    private LocalDateTime beginTime;

    @Column(name = "end_time")
    private LocalDateTime endTime;

    @Column(name = "trace_id", length = 64)
    private String traceId;

    @Column(name = "span_id", length = 64)
    private String spanId;

    @Column(name = "error_message", length = 2048)
    private String errorMessage;

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
}
