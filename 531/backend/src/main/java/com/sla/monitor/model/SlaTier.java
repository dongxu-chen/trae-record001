package com.sla.monitor.model;

import jakarta.persistence.*;
import lombok.Data;

import java.time.LocalDateTime;

@Data
@Entity
@Table(name = "sla_tiers")
public class SlaTier {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(unique = true, nullable = false)
    private String tierName;

    @Column(nullable = false)
    private String tierCode;

    private String description;

    @Column(nullable = false)
    private Double availabilityTarget;

    @Column(nullable = false)
    private Double latencyTargetMs;

    @Column(nullable = false)
    private Double errorRateTarget;

    private Double monthlyAvailabilityTarget;

    private Double quarterlyAvailabilityTarget;

    private Integer priorityLevel;

    private String responseTimeSla;

    private String resolutionTimeSla;

    private Double uptimeCreditPercent;

    private boolean active = true;

    private LocalDateTime createdAt;

    private LocalDateTime updatedAt;

    public static final String TIER_GOLD = "GOLD";
    public static final String TIER_SILVER = "SILVER";
    public static final String TIER_BRONZE = "BRONZE";
    public static final String TIER_STANDARD = "STANDARD";
    public static final String TIER_PREMIUM = "PREMIUM";

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
