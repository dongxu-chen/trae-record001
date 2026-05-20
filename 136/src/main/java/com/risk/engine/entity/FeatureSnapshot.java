package com.risk.engine.entity;

import lombok.Data;

import javax.persistence.*;
import java.time.LocalDateTime;

@Data
@Entity
@Table(name = "t_feature_snapshot", indexes = {
    @Index(name = "idx_request_id", columnList = "requestId"),
    @Index(name = "idx_user_id", columnList = "userId"),
    @Index(name = "idx_scene", columnList = "scene"),
    @Index(name = "idx_create_time", columnList = "createTime")
})
public class FeatureSnapshot {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(name = "request_id", nullable = false, length = 128)
    private String requestId;

    @Column(name = "user_id", length = 128)
    private String userId;

    @Column(name = "scene", length = 64)
    private String scene;

    @Lob
    @Column(name = "raw_data", columnDefinition = "TEXT")
    private String rawData;

    @Lob
    @Column(name = "calculated_features", columnDefinition = "TEXT")
    private String calculatedFeatures;

    @Lob
    @Column(name = "model_results", columnDefinition = "TEXT")
    private String modelResults;

    @Column(name = "decision", length = 32)
    private String decision;

    @Column(name = "score")
    private Integer score;

    @Column(name = "create_time")
    private LocalDateTime createTime;

    @PrePersist
    protected void onCreate() {
        createTime = LocalDateTime.now();
    }
}
