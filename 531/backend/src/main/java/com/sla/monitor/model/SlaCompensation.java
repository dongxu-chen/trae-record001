package com.sla.monitor.model;

import jakarta.persistence.*;
import lombok.Data;

import java.time.LocalDateTime;

@Data
@Entity
@Table(name = "sla_compensations")
public class SlaCompensation {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(nullable = false)
    private String serviceName;

    @ManyToOne(fetch = FetchType.EAGER)
    @JoinColumn(name = "sla_tier_id")
    private SlaTier slaTier;

    @Column(nullable = false)
    @Enumerated(EnumType.STRING)
    private CompensationType compensationType;

    @Column(nullable = false)
    @Enumerated(EnumType.STRING)
    private ViolationSeverity violationSeverity;

    @Column(nullable = false)
    private Double downtimeMinutes;

    @Column(nullable = false)
    private Double availabilityDeficit;

    private Double creditAmount;

    private Double creditPercent;

    @Column(length = 1000)
    private String compensationDetails;

    @Column(length = 2000)
    private String recommendedActions;

    private Boolean approved;

    private LocalDateTime approvedAt;

    private String approvedBy;

    @Column(nullable = false)
    private LocalDateTime createdAt;

    private LocalDateTime resolvedAt;

    public enum CompensationType {
        SERVICE_CREDIT,
        EXTENDED_SUPPORT,
        UPGRADE_TIER,
        REFUND,
        CUSTOM
    }

    public enum ViolationSeverity {
        MINOR,
        MODERATE,
        SEVERE,
        CRITICAL
    }

    @PrePersist
    protected void onCreate() {
        createdAt = LocalDateTime.now();
        approved = false;
    }
}
