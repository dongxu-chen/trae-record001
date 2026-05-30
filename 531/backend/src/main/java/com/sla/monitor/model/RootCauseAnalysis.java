package com.sla.monitor.model;

import jakarta.persistence.*;
import lombok.Data;

import java.time.LocalDateTime;

@Data
@Entity
@Table(name = "root_cause_analysis")
public class RootCauseAnalysis {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(nullable = false)
    private String serviceName;

    @Column(nullable = false)
    private LocalDateTime timestamp;

    @Lob
    private String analysisResult;

    @Lob
    private String contributingFactors;

    @Lob
    private String recommendations;

    private Double confidenceScore;

    @Enumerated(EnumType.STRING)
    private RootCauseCategory primaryCause;

    public enum RootCauseCategory {
        HIGH_ERROR_RATE,
        LATENCY_SPIKE,
        TRAFFIC_SURGE,
        DEPENDENCY_FAILURE,
        RESOURCE_EXHAUSTION,
        UNKNOWN
    }
}
