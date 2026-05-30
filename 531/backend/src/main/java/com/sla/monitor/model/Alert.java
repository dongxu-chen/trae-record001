package com.sla.monitor.model;

import jakarta.persistence.*;
import lombok.Data;

import java.time.LocalDateTime;

@Data
@Entity
@Table(name = "alerts")
public class Alert {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(nullable = false)
    private String serviceName;

    @Column(nullable = false)
    @Enumerated(EnumType.STRING)
    private AlertType alertType;

    @Enumerated(EnumType.STRING)
    private AlertSeverity severity;

    private String message;

    private Double currentValue;

    private Double thresholdValue;

    private boolean acknowledged;

    private LocalDateTime createdAt;

    private LocalDateTime resolvedAt;

    private boolean resolved;

    public enum AlertType {
        AVAILABILITY_VIOLATION,
        LATENCY_VIOLATION,
        ERROR_RATE_VIOLATION,
        SLA_PREDICTED_VIOLATION,
        DEPENDENCY_SLA_PROPAGATION
    }

    public enum AlertSeverity {
        LOW,
        MEDIUM,
        HIGH,
        CRITICAL
    }

    @PrePersist
    protected void onCreate() {
        createdAt = LocalDateTime.now();
    }
}
