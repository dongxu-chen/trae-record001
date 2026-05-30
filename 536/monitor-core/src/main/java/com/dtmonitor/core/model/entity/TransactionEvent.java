package com.dtmonitor.core.model.entity;

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
@Table(name = "transaction_event")
public class TransactionEvent {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(name = "xid", length = 64)
    private String xid;

    @Column(name = "branch_id", length = 64)
    private String branchId;

    @Column(length = 64)
    private String eventType;

    @Column(length = 32)
    private String phase;

    @Column(name = "trace_id", length = 64)
    private String traceId;

    @Column(name = "span_id", length = 64)
    private String spanId;

    @Column(name = "application_id", length = 64)
    private String applicationId;

    @Column(length = 2048)
    private String payload;

    @Column(name = "error_message", length = 2048)
    private String errorMessage;

    @Column(name = "event_time")
    private LocalDateTime eventTime;

    @Column(name = "created_at")
    private LocalDateTime createdAt;

    @PrePersist
    protected void onCreate() {
        createdAt = LocalDateTime.now();
        if (eventTime == null) {
            eventTime = LocalDateTime.now();
        }
    }
}
