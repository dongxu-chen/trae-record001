package com.taskflow.model;

import jakarta.persistence.*;
import lombok.Data;
import java.time.LocalDateTime;

@Data
@Entity
@Table(name = "tf_task")
public class Task {
    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(name = "workflow_id", nullable = false)
    private Long workflowId;

    @Column(name = "task_key", nullable = false, length = 128)
    private String taskKey;

    @Column(name = "task_name", nullable = false, length = 128)
    private String taskName;

    @Column(name = "task_type", nullable = false, length = 64)
    private String taskType;

    @Column(name = "task_config", columnDefinition = "JSON")
    private String taskConfig;

    @Column(name = "task_priority", nullable = false)
    private Integer taskPriority = 5;

    @Column(name = "retry_count", nullable = false)
    private Integer retryCount = 0;

    @Column(name = "retry_interval", nullable = false)
    private Integer retryInterval = 30;

    @Column(name = "retry_strategy", length = 32)
    private String retryStrategy = "FIXED";

    @Column(name = "timeout_seconds", nullable = false)
    private Integer timeoutSeconds = 3600;

    @Column(name = "upstream_keys", columnDefinition = "JSON")
    private String upstreamKeys;

    @Column(name = "data_products", columnDefinition = "JSON")
    private String dataProducts;

    @Column(name = "position_x")
    private Double positionX = 0.0;

    @Column(name = "position_y")
    private Double positionY = 0.0;

    @Column(name = "created_at", updatable = false)
    private LocalDateTime createdAt;

    @Column(name = "updated_at")
    private LocalDateTime updatedAt;

    @PrePersist
    protected void onCreate() {
        createdAt = LocalDateTime.now();
        updatedAt = LocalDateTime.now();
    }

    @PreUpdate
    protected void onUpdate() {
        updatedAt = LocalDateTime.now();
    }
}
