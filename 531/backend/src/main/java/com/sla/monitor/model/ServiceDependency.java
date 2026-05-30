package com.sla.monitor.model;

import jakarta.persistence.*;
import lombok.Data;

import java.time.LocalDateTime;

@Data
@Entity
@Table(name = "service_dependencies")
public class ServiceDependency {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(nullable = false)
    private String downstreamService;

    @Column(nullable = false)
    private String upstreamService;

    @Column(nullable = false)
    @Enumerated(EnumType.STRING)
    private DependencyType dependencyType;

    @Column(nullable = false)
    @Enumerated(EnumType.STRING)
    private ImpactLevel impactLevel;

    private Double slaImpactFactor;

    @Column(length = 1000)
    private String description;

    private Double availabilityDependencyWeight;

    private Double latencyDependencyWeight;

    private Double errorRateDependencyWeight;

    private Boolean active;

    @Column(nullable = false)
    private LocalDateTime createdAt;

    private LocalDateTime updatedAt;

    public enum DependencyType {
        SYNCHRONOUS,
        ASYNCHRONOUS,
        DATABASE,
        CACHE,
        MESSAGE_QUEUE,
        EXTERNAL_API,
        STORAGE
    }

    public enum ImpactLevel {
        CRITICAL,
        HIGH,
        MEDIUM,
        LOW,
        INFORMATIONAL
    }

    @PrePersist
    protected void onCreate() {
        createdAt = LocalDateTime.now();
        updatedAt = LocalDateTime.now();
        if (active == null) active = true;
        if (slaImpactFactor == null) slaImpactFactor = 1.0;
        if (availabilityDependencyWeight == null) availabilityDependencyWeight = 0.3;
        if (latencyDependencyWeight == null) latencyDependencyWeight = 0.4;
        if (errorRateDependencyWeight == null) errorRateDependencyWeight = 0.3;
    }

    @PreUpdate
    protected void onUpdate() {
        updatedAt = LocalDateTime.now();
    }
}
