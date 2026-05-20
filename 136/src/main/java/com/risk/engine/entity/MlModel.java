package com.risk.engine.entity;

import lombok.Data;

import javax.persistence.*;
import java.time.LocalDateTime;

@Data
@Entity
@Table(name = "t_ml_model")
public class MlModel {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(name = "model_code", unique = true, nullable = false, length = 64)
    private String modelCode;

    @Column(name = "model_name", nullable = false, length = 128)
    private String modelName;

    @Column(name = "model_type", nullable = false, length = 32)
    private String modelType;

    @Column(name = "model_version", nullable = false, length = 32)
    private String modelVersion;

    @Column(name = "scene", length = 64)
    private String scene;

    @Column(name = "model_path", length = 512)
    private String modelPath;

    @Lob
    @Column(name = "model_content")
    private byte[] modelContent;

    @Column(name = "feature_names", columnDefinition = "TEXT")
    private String featureNames;

    @Column(name = "target_name", length = 128)
    private String targetName;

    @Column(name = "threshold", precision = 10, scale = 4)
    private Double threshold;

    @Column(name = "weight", precision = 10, scale = 4)
    private Double weight = 1.0;

    @Column(name = "status", length = 16)
    private String status = "DISABLED";

    @Column(name = "description", length = 512)
    private String description;

    @Column(name = "create_time")
    private LocalDateTime createTime;

    @Column(name = "update_time")
    private LocalDateTime updateTime;

    @PrePersist
    protected void onCreate() {
        createTime = LocalDateTime.now();
        updateTime = LocalDateTime.now();
    }

    @PreUpdate
    protected void onUpdate() {
        updateTime = LocalDateTime.now();
    }
}
