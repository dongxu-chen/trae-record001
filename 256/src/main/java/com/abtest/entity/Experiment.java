package com.abtest.entity;

import jakarta.persistence.*;
import lombok.Data;
import java.time.LocalDateTime;
import java.util.ArrayList;
import java.util.List;

@Data
@Entity
@Table(name = "experiments")
public class Experiment {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(nullable = false, unique = true)
    private String name;

    @Column(length = 1000)
    private String description;

    @Column(nullable = false)
    private String owner;

    @Column(nullable = false)
    @Enumerated(EnumType.STRING)
    private ExperimentStatus status;

    @Column(nullable = false)
    private Integer trafficPercentage;

    @Column(nullable = false)
    private String trafficKey;

    @ManyToOne(fetch = FetchType.LAZY)
    @JoinColumn(name = "layer_id")
    private Layer layer;

    @Column(nullable = false)
    @Enumerated(EnumType.STRING)
    private TrafficAllocationMode trafficMode = TrafficAllocationMode.FIXED;

    private Double mabEpsilon = 0.1;

    private Integer mabUpdateIntervalMinutes = 60;

    private Boolean autoStopEnabled = false;

    private Double autoStopConfidenceThreshold = 0.95;

    private Long autoStopMaxSampleSize;

    private LocalDateTime lastTrafficAdjustmentTime;

    private LocalDateTime startTime;

    private LocalDateTime endTime;

    @OneToMany(mappedBy = "experiment", cascade = CascadeType.ALL, orphanRemoval = true)
    private List<Variant> variants = new ArrayList<>();

    @OneToMany(mappedBy = "experiment", cascade = CascadeType.ALL, orphanRemoval = true)
    private List<Metric> metrics = new ArrayList<>();

    @Column(nullable = false)
    private LocalDateTime createdAt;

    @Column(nullable = false)
    private LocalDateTime updatedAt;

    public enum TrafficAllocationMode {
        FIXED,
        THOMPSON_SAMPLING,
        EPSILON_GREEDY,
        UCB
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

    public enum ExperimentStatus {
        DRAFT, RUNNING, PAUSED, COMPLETED
    }
}
