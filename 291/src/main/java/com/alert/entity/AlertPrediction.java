package com.alert.entity;

import lombok.Data;
import org.hibernate.annotations.CreationTimestamp;

import javax.persistence.*;
import java.time.LocalDateTime;

@Data
@Entity
@Table(name = "alert_prediction")
public class AlertPrediction {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(name = "prediction_id", unique = true, nullable = false, length = 64)
    private String predictionId;

    @Column(nullable = false, length = 255)
    private String title;

    @Column(columnDefinition = "TEXT")
    private String description;

    @Column(name = "predicted_severity", length = 20)
    private String predictedSeverity;

    @Column(name = "prediction_probability")
    private Double probability;

    @Column(name = "predicted_time")
    private LocalDateTime predictedTime;

    @Column(name = "prediction_window_minutes")
    private Integer predictionWindowMinutes;

    @Column(name = "source_pattern")
    private String sourcePattern;

    @Column(name = "host_pattern")
    private String hostPattern;

    @Column(length = 50)
    private String status = "PREDICTED";

    @Column(name = "actual_alert_id", length = 64)
    private String actualAlertId;

    @CreationTimestamp
    @Column(name = "create_time", nullable = false, updatable = false)
    private LocalDateTime createTime;
}
