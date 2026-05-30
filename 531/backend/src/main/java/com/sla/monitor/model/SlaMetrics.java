package com.sla.monitor.model;

import jakarta.persistence.*;
import lombok.Data;

import java.time.LocalDateTime;

@Data
@Entity
@Table(name = "sla_metrics", indexes = {
    @Index(name = "idx_service_time", columnList = "serviceName, timestamp")
})
public class SlaMetrics {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(nullable = false)
    private String serviceName;

    @Column(nullable = false)
    private LocalDateTime timestamp;

    private Long totalRequests;

    private Long successfulRequests;

    private Long failedRequests;

    private Double availability;

    private Double avgLatencyMs;

    private Double p95LatencyMs;

    private Double p99LatencyMs;

    private Double errorRate;

    private Double slaAchievementRate;

    private boolean slaViolated;

    private String windowType;
}
