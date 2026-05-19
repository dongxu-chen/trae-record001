package com.risk.engine.entity;

import lombok.Data;

import javax.persistence.*;
import java.time.LocalDateTime;

@Data
@Entity
@Table(name = "t_decision_trace", indexes = {
    @Index(name = "idx_trace_request_id", columnList = "requestId"),
    @Index(name = "idx_trace_user_id", columnList = "userId"),
    @Index(name = "idx_trace_step", columnList = "step"),
    @Index(name = "idx_trace_time", columnList = "traceTime")
})
public class DecisionTrace {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(name = "request_id", nullable = false, length = 128)
    private String requestId;

    @Column(name = "user_id", length = 128)
    private String userId;

    @Column(name = "scene", length = 64)
    private String scene;

    @Column(name = "step", nullable = false, length = 64)
    private String step;

    @Column(name = "step_desc", length = 256)
    private String stepDesc;

    @Column(name = "result", length = 64)
    private String result;

    @Lob
    @Column(name = "detail", columnDefinition = "TEXT")
    private String detail;

    @Column(name = "duration_ms")
    private Long durationMs;

    @Column(name = "trace_time")
    private LocalDateTime traceTime;

    @Column(name = "operator", length = 128)
    private String operator;

    @PrePersist
    protected void onCreate() {
        traceTime = LocalDateTime.now();
    }
}
