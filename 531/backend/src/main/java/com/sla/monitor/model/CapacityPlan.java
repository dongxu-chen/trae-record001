package com.sla.monitor.model;

import jakarta.persistence.*;
import lombok.Data;

import java.time.LocalDateTime;

@Data
@Entity
@Table(name = "capacity_plans")
public class CapacityPlan {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(nullable = false)
    private String serviceName;

    @Column(nullable = false)
    @Enumerated(EnumType.STRING)
    private ResourceType resourceType;

    @Column(nullable = false)
    private Double currentUtilization;

    @Column(nullable = false)
    private Double predictedUtilization7d;

    @Column(nullable = false)
    private Double predictedUtilization30d;

    private Double recommendedCapacity;

    private Double currentCapacity;

    private Double slaRequiredCapacity;

    @Column(nullable = false)
    @Enumerated(EnumType.STRING)
    private CapacityStatus status;

    @Column(length = 2000)
    private String recommendations;

    private Double growthRate;

    private Integer peakRequestsPerSecond;

    private Integer predictedPeakRequests7d;

    private Integer predictedPeakRequests30d;

    private Double avgLatencyMs;

    private Double predictedLatency7d;

    private Double predictedLatency30d;

    private Double headroomPercent;

    @Column(nullable = false)
    private LocalDateTime createdAt;

    private LocalDateTime validUntil;

    public enum ResourceType {
        CPU,
        MEMORY,
        DISK,
        NETWORK,
        DATABASE_CONNECTIONS,
        THREAD_POOL,
        REQUEST_THROUGHPUT
    }

    public enum CapacityStatus {
        NORMAL,
        WARNING,
        CRITICAL,
        NEEDS_EXPANSION,
        OVER_PROVISIONED
    }

    @PrePersist
    protected void onCreate() {
        createdAt = LocalDateTime.now();
        validUntil = LocalDateTime.now().plusDays(7);
    }
}
