package com.sla.monitor.model;

import com.fasterxml.jackson.annotation.JsonProperty;
import jakarta.persistence.*;
import lombok.Data;

import java.time.LocalDateTime;

@Data
@Entity
@Table(name = "services")
public class ServiceInfo {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(unique = true, nullable = false)
    private String serviceName;

    private String description;

    private String endpoint;

    @ManyToOne(fetch = FetchType.EAGER)
    @JoinColumn(name = "sla_tier_id")
    private SlaTier slaTier;

    @Column(nullable = false)
    private Double availabilityTarget = 99.9;

    @Column(nullable = false)
    private Double latencyTargetMs = 500.0;

    @Column(nullable = false)
    private Double errorRateTarget = 1.0;

    private boolean useTierTargets = true;

    private boolean active = true;

    private LocalDateTime createdAt;

    private LocalDateTime updatedAt;

    @JsonProperty("effectiveAvailabilityTarget")
    public Double getEffectiveAvailabilityTarget() {
        if (useTierTargets && slaTier != null) {
            return slaTier.getAvailabilityTarget();
        }
        return availabilityTarget;
    }

    @JsonProperty("effectiveLatencyTarget")
    public Double getEffectiveLatencyTarget() {
        if (useTierTargets && slaTier != null) {
            return slaTier.getLatencyTargetMs();
        }
        return latencyTargetMs;
    }

    @JsonProperty("effectiveErrorRateTarget")
    public Double getEffectiveErrorRateTarget() {
        if (useTierTargets && slaTier != null) {
            return slaTier.getErrorRateTarget();
        }
        return errorRateTarget;
    }

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
