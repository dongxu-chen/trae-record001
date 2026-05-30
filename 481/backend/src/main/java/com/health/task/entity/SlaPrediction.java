package com.health.task.entity;

import jakarta.persistence.*;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.time.LocalDateTime;

@Entity
@Table(name = "sla_prediction")
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class SlaPrediction {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(nullable = false)
    private String taskName;

    @Column(nullable = false)
    private String taskGroup;

    @Column(nullable = false)
    private Integer slaTargetScore;

    @Column(nullable = false)
    private Double predictedMonthlyScore;

    @Column(nullable = false)
    private Double currentMonthlyAvg;

    @Column(nullable = false)
    private Double achievementProbability;

    private Integer daysRemainingInMonth;

    private Integer daysAnalyzed;

    private Double currentSuccessRate;

    private Double requiredSuccessRate;

    private Integer predictedFailuresRemaining;

    @Column(nullable = false)
    private String slaStatus;

    @Column(length = 500)
    private String recommendations;

    @Column(nullable = false)
    private LocalDateTime predictionTime;

    private LocalDateTime monthStart;

    private LocalDateTime monthEnd;

    private Double bestCaseScore;

    private Double worstCaseScore;

    private Integer healthyDays;

    private Integer warningDays;

    private Integer criticalDays;
}
