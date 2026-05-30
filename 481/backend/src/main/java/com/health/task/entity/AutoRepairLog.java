package com.health.task.entity;

import jakarta.persistence.*;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.time.LocalDateTime;

@Entity
@Table(name = "auto_repair_log")
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class AutoRepairLog {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(nullable = false)
    private String taskName;

    @Column(nullable = false)
    private String taskGroup;

    @Column(nullable = false)
    private String failureType;

    @Column(nullable = false)
    private String repairAction;

    private String oldValue;

    private String newValue;

    @Column(nullable = false)
    private LocalDateTime repairTime;

    @Column(nullable = false)
    private String status;

    @Column(length = 1000)
    private String repairDetails;

    private Integer maxRetriesBefore;

    private Integer maxRetriesAfter;

    private Long retryDelayMsBefore;

    private Long retryDelayMsAfter;

    private Long timeoutMsBefore;

    private Long timeoutMsAfter;

    private Double successRateAfterRepair;

    private Integer followUpScore;

    private String riskLevel;
}
