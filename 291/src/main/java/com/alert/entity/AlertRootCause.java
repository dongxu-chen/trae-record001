package com.alert.entity;

import lombok.Data;
import org.hibernate.annotations.CreationTimestamp;

import javax.persistence.*;
import java.time.LocalDateTime;

@Data
@Entity
@Table(name = "alert_root_cause")
public class AlertRootCause {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(name = "root_cause_id", unique = true, nullable = false, length = 64)
    private String rootCauseId;

    @Column(nullable = false, length = 255)
    private String title;

    @Column(columnDefinition = "TEXT")
    private String description;

    @Column(name = "root_alert_id", length = 64)
    private String rootAlertId;

    @Column(name = "confidence_score")
    private Double confidenceScore;

    @Column(nullable = false, length = 50)
    private String status = "ANALYZING";

    @Column(name = "analysis_time")
    private LocalDateTime analysisTime;

    @Column(length = 500)
    private String tags;

    @Column(name = "affected_count")
    private Integer affectedCount = 0;

    @CreationTimestamp
    @Column(name = "create_time", nullable = false, updatable = false)
    private LocalDateTime createTime;
}
