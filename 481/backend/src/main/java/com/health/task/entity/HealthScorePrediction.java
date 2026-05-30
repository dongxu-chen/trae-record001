package com.health.task.entity;

import jakarta.persistence.*;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.time.LocalDateTime;

@Entity
@Table(name = "health_score_prediction")
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class HealthScorePrediction {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(nullable = false)
    private String taskName;

    @Column(nullable = false)
    private String taskGroup;

    @Column(nullable = false)
    private Integer predictedScore;

    private Double confidence;

    private String trendDirection;

    private Double trendSlope;

    @Column(nullable = false)
    private LocalDateTime predictionTime;

    @Column(nullable = false)
    private LocalDateTime targetTime;

    private Integer predictionHorizonHours;

    private String algorithmUsed;

    @Column(length = 1000)
    private String predictionDetails;

    private Integer lowerBound;

    private Integer upperBound;
}
