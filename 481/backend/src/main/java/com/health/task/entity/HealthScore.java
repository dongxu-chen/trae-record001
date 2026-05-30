package com.health.task.entity;

import jakarta.persistence.*;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.time.LocalDateTime;

@Entity
@Table(name = "health_score")
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class HealthScore {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(nullable = false)
    private String taskName;

    @Column(nullable = false)
    private String taskGroup;

    @Column(nullable = false)
    private Integer overallScore;

    @Column(nullable = false)
    private Integer durationScore;

    @Column(nullable = false)
    private Integer successRateScore;

    @Column(nullable = false)
    private Integer frequencyScore;

    @Column(nullable = false)
    private Integer resourceScore;

    @Column(nullable = false)
    private LocalDateTime calculatedAt;

    private String diagnosis;

    private String suggestion;
}
